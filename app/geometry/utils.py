"""
Geometry utilities for ORRG.
Provides geodesic calculations using pyproj and geographiclib.
All calculations are true geodesic on the WGS84 ellipsoid.
"""

from typing import Optional, Callable

from geographiclib.geodesic import Geodesic
from pyproj import Geod
from shapely.geometry import (
    LineString,
    MultiPolygon,
    Point,
    Polygon,
    mapping,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


# WGS84 ellipsoid parameters
WGS84 = Geodesic.WGS84
GEOD = Geod(ellps="WGS84")

# -----------------------------------------------------------------------------
# Global constants
# -----------------------------------------------------------------------------

# Approximate Earth radius in kilometers (WGS84 mean radius)
EARTH_RADIUS_KM = 6371.0088

# World polygon in WGS84 (used for near-global / antipodal logic)
WORLD_POLYGON_WGS84 = Polygon([
    (-180.0, -90.0),
    (-180.0,  90.0),
    ( 180.0,  90.0),
    ( 180.0, -90.0),
    (-180.0, -90.0),
])


def antipode(lat: float, lon: float) -> tuple[float, float]:
    """
    Compute the antipodal point on the WGS84 ellipsoid.
    Longitude is normalized to (-180, 180].
    """
    anti_lat = -lat
    anti_lon = (lon + 180.0) % 360.0
    if anti_lon > 180.0:
        anti_lon -= 360.0
    return anti_lat, anti_lon

def geodesic_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the geodesic distance between two points on WGS84 ellipsoid.
    
    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees
        
    Returns:
        Distance in kilometers
    """
    result = WGS84.Inverse(lat1, lon1, lat2, lon2)
    return result["s12"] / 1000.0  # Convert meters to kilometers


def geodesic_point_at_distance(
    lat: float, lon: float, azimuth: float, distance_km: float
) -> tuple[float, float]:
    """
    Calculate a point at a given distance and azimuth from a starting point.
    
    Args:
        lat: Starting latitude in decimal degrees
        lon: Starting longitude in decimal degrees
        azimuth: Azimuth (bearing) in degrees from north
        distance_km: Distance in kilometers
        
    Returns:
        Tuple of (latitude, longitude) of the destination point
    """
    result = WGS84.Direct(lat, lon, azimuth, distance_km * 1000.0)
    return result["lat2"], result["lon2"]


def create_geodesic_circle(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    num_points: int = 360,
) -> Polygon:
    """
    Create a geodesic circle (buffer) around a point.
    
    Handles antimeridian crossing by splitting the polygon if needed.
    
    Args:
        center_lat: Center latitude in decimal degrees
        center_lon: Center longitude in decimal degrees
        radius_km: Radius in kilometers
        num_points: Number of points to use for the circle (default 360)
        
    Returns:
        Shapely Polygon representing the geodesic circle
    """
    points = []
    for i in range(num_points):
        azimuth = (360.0 / num_points) * i
        lat, lon = geodesic_point_at_distance(center_lat, center_lon, azimuth, radius_km)
        points.append((lon, lat))  # Shapely uses (lon, lat) order
    
    # Close the ring
    points.append(points[0])
    
    # Check if we cross the antimeridian (large jumps in longitude)
    crosses_antimeridian = False
    for i in range(len(points) - 1):
        lon_diff = abs(points[i+1][0] - points[i][0])
        if lon_diff > 180:
            crosses_antimeridian = True
            break

    # NOTE: This normalization is only safe for non-antipodal radii.
    # Large (>~90° arc) buffers must use antipodal exclusion logic.
    if crosses_antimeridian:
        # Normalize longitudes to avoid wrapping issues
        # Shift everything to be relative to center longitude
        normalized_points = []
        for lon, lat in points:
            # Calculate relative longitude
            rel_lon = lon - center_lon
            # Normalize to -180 to 180
            while rel_lon > 180:
                rel_lon -= 360
            while rel_lon < -180:
                rel_lon += 360
            # Add back center longitude
            normalized_lon = center_lon + rel_lon
            normalized_points.append((normalized_lon, lat))
        points = normalized_points
    
    return Polygon(points)


def create_geodesic_buffer(
    geometry: BaseGeometry,
    distance_km: float,
    resolution: str = "normal",
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> BaseGeometry:
    """
    Create a geodesic buffer around any Shapely geometry.
    
    For Points: Creates a single geodesic circle.
    For Polygons/LineStrings with small/medium ranges (<5500 km): 
        Samples points along the boundary and creates geodesic circles from each,
        then unions them together. This ensures the buffer extends from the actual
        boundary, not just the centroid.
    For large ranges (>5500 km): Uses antipodal exclusion strategy which is more
        numerically stable for global-scale buffers.
    
    Args:
        geometry: Input Shapely geometry (Point, LineString, Polygon, etc.)
        distance_km: Buffer distance in kilometers
        resolution: Resolution setting ('low', 'normal', 'high')
        progress_callback: Optional callback function(progress: float, status: str)
                          where progress is 0.0-1.0 and status is a description
        
    Returns:
        Buffered Shapely geometry
    """
    def report_progress(pct: float, status: str):
        if progress_callback:
            progress_callback(pct, status)
    
    report_progress(0.0, "Initializing buffer calculation...")
    
    # For points, just create a geodesic circle directly
    if geometry.geom_type == "Point":
        report_progress(0.1, "Creating geodesic circle...")
        num_points = {"low": 72, "normal": 180, "high": 360}.get(resolution, 180)
        result = create_geodesic_circle(geometry.y, geometry.x, distance_km, num_points)
        report_progress(1.0, "Complete")
        return result
    
    # -----------------------------------------------------------------------------
    # For very large ranges (>5500 km), use antipodal exclusion strategy
    # This is more numerically stable than unioning hundreds of near-global circles
    # -----------------------------------------------------------------------------
    
    HEMISPHERIC_THRESHOLD_KM = 5500.0

    if distance_km > HEMISPHERIC_THRESHOLD_KM:
        result = _create_hemispheric_buffer_from_polygon(
            geometry, distance_km, resolution, progress_callback
        )

        # ------------------------------------------------------------
        # CRITICAL FIX: remove origin geometry from final buffer
        # ------------------------------------------------------------
        try:
            result = result.difference(geometry)
        except Exception:
            pass

        return result

    # -----------------------------------------------------------------------------
    # For smaller ranges: Sample boundary points and union circles
    # This ensures the buffer extends from the actual boundary, not just centroid
    # 
    # IMPORTANT: For short-range missiles, we need MUCH denser sampling because
    # the small buffer circles don't overlap as much, leaving visible gaps.
    # The sampling density is now adaptive based on the range.
    # -----------------------------------------------------------------------------
    
    report_progress(0.1, "Extracting boundary coordinates...")
    
    # Get all boundary coordinates
    boundary_coords = _extract_all_coordinates(geometry)
    
    # Determine base sampling density based on resolution
    # (Reduced by 200% from previous 4x values: 1200→400, 600→200, 300→100)
    if resolution == "high":
        base_max_samples = 400
        circle_points = 180
    elif resolution == "normal":
        base_max_samples = 200
        circle_points = 120
    else:  # low
        base_max_samples = 100
        circle_points = 72
    
    # ADAPTIVE SAMPLING: Increase sample density for shorter ranges
    # Short-range missiles (< 500 km) need denser sampling
    if distance_km < 300:
        range_multiplier = 2.5
    elif distance_km < 500:
        range_multiplier = 2.0
    elif distance_km < 1000:
        range_multiplier = 1.5
    elif distance_km < 2000:
        range_multiplier = 1.25
    else:
        range_multiplier = 1.0
    
    max_samples = int(base_max_samples * range_multiplier)
    
    # Cap at reasonable maximum
    max_samples = min(max_samples, 1000)
    
    report_progress(0.12, f"Analyzing boundary curvature for adaptive sampling...")
    
    # =========================================================================
    # ADAPTIVE DENSITY SAMPLING based on boundary curvature
    # This ensures high-curvature areas (corners, complex coastlines) get more
    # sample points, while straight sections get fewer.
    # =========================================================================
    sampled_coords = _adaptive_curvature_sampling(
        boundary_coords, max_samples, progress_callback,
        start_pct=0.12, end_pct=0.20
    )
    
    report_progress(0.20, f"Using {len(sampled_coords)} adaptively sampled points for {distance_km:.0f}km range...")
    
    report_progress(0.2, f"Creating geodesic circles from {len(sampled_coords)} boundary points...")
    
    # Create geodesic circles from each boundary point
    circles = []
    total_coords = len(sampled_coords)
    
    for i, (lon, lat) in enumerate(sampled_coords):
        try:
            circle = create_geodesic_circle(lat, lon, distance_km, circle_points)
            if circle.is_valid and not circle.is_empty:
                circles.append(circle)
        except Exception as e:
            # Skip invalid points
            continue
        
        # Report progress periodically
        if i % max(1, total_coords // 10) == 0:
            pct = 0.2 + 0.5 * (i / total_coords)
            report_progress(pct, f"Circle {i+1}/{total_coords}...")
    
    if not circles:
        # Fallback to centroid-based circle if no boundary circles could be created
        centroid = geometry.centroid
        report_progress(0.8, "Fallback to centroid circle...")
        result = create_geodesic_circle(centroid.y, centroid.x, distance_km, circle_points)
        report_progress(1.0, "Complete")
        return result
    
    report_progress(0.75, f"Merging {len(circles)} circles...")

    # Union all circles together
    result = unary_union(circles)

    # Fix antimeridian FIRST
    result = fix_antimeridian_crossing(result)

    if not result.is_valid:
        result = result.buffer(0)

    # ------------------------------------------------------------
    # CRITICAL: subtract origin geometry LAST
    # ------------------------------------------------------------
    try:
        result = result.difference(geometry)
    except Exception:
        pass

    report_progress(1.0, "Complete")

    return result


def _create_hemispheric_buffer_from_polygon(
    geometry: BaseGeometry,
    distance_km: float,
    resolution: str = "normal",
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> BaseGeometry:
    """
    Create a hemispheric/global buffer for large ranges (>5500 km) using
    antipodal exclusion strategy.
    
    For very large ranges, the "out of range" area is a small region at
    the farthest points from the polygon. We compute this by:
    1. Finding the centroid's antipode
    2. Computing the "out of range" radius
    3. Subtracting that hole from the world polygon
    
    For polygon inputs, we sample boundary points to find the farthest
    antipode and use that to define the exclusion area.
    
    Args:
        geometry: Input polygon geometry
        distance_km: Buffer distance in kilometers
        resolution: Resolution setting
        progress_callback: Optional progress callback
        
    Returns:
        Buffered geometry covering most of the world
    """
    def report_progress(pct: float, status: str):
        if progress_callback:
            progress_callback(pct, status)
    
    report_progress(0.1, f"Hemispheric buffer ({distance_km:.0f} km) - computing antipodal exclusion...")
    
    # Get boundary coordinates to find farthest points from antipode
    boundary_coords = _extract_all_coordinates(geometry)
    
    # Sample if too many
    if len(boundary_coords) > 100:
        step = max(1, len(boundary_coords) // 100)
        boundary_coords = boundary_coords[::step]
    
    # Find the centroid and its antipode
    centroid = geometry.centroid
    center_lat, center_lon = centroid.y, centroid.x
    anti_lat, anti_lon = antipode(center_lat, center_lon)
    
    report_progress(0.3, "Computing out-of-range exclusion zone...")

    # Half Earth circumference (antipodal distance)
    half_circumference_km = EARTH_RADIUS_KM * 3.141592653589793  # ~20,015 km

    # If range equals/exceeds antipodal distance, entire globe is reachable
    if distance_km >= half_circumference_km:
        return WORLD_POLYGON_WGS84

    # Primary antipodal exclusion radius dictated by geometry of the sphere
    # (points farther than distance_km from the origin)
    primary_hole_radius = half_circumference_km - distance_km

    # Tighten the exclusion using the closest boundary point to the antipode
    min_dist_to_antipode = float('inf')
    for lon, lat in boundary_coords:
        d = geodesic_distance(lat, lon, anti_lat, anti_lon)
        if d < min_dist_to_antipode:
            min_dist_to_antipode = d

    # A point is out of range only if it is farther than distance_km from ALL boundary points
    # Therefore the exclusion radius cannot exceed (min_dist_to_antipode - distance_km)
    boundary_limited_radius = max(0.0, min_dist_to_antipode - distance_km)

    # Final hole radius: never larger than primary antipodal cap, never negative
    hole_radius = max(
        50.0,  # numerical stability floor
        min(primary_hole_radius, boundary_limited_radius)
    )

    report_progress(0.5, f"Creating exclusion hole ({hole_radius:.0f} km) at antipode...")
    
    # Create the exclusion hole at the antipode
    num_points = {
        "low": 240,
        "normal": 480,
        "high": 960,
    }.get(resolution, 480)

    hole = create_geodesic_circle(anti_lat, anti_lon, hole_radius, num_points)

    report_progress(0.7, "Subtracting from world polygon...")

    # Subtract antipodal hole from world polygon
    result = WORLD_POLYGON_WGS84.difference(hole)

    # Fix antimeridian FIRST
    result = fix_antimeridian_crossing(result)

    if not result.is_valid:
        result = result.buffer(0)

    # ------------------------------------------------------------
    # CRITICAL: subtract origin geometry LAST
    # (must happen AFTER antimeridian fixing)
    # ------------------------------------------------------------
    try:
        result = result.difference(geometry)
    except Exception:
        pass

    report_progress(1.0, "Complete")
    return result


def _transform_geometry(geometry: BaseGeometry, transformer) -> BaseGeometry:
    """
    Transform a geometry using a pyproj Transformer.
    
    Args:
        geometry: Input Shapely geometry
        transformer: pyproj Transformer object
        
    Returns:
        Transformed geometry
    """
    from shapely.ops import transform
    
    def transform_coords(x, y):
        return transformer.transform(x, y)
    
    return transform(transform_coords, geometry)


def _cascaded_union_with_progress(
    geometries: list[BaseGeometry],
    progress_callback: Optional[Callable[[float, str], None]],
    start_pct: float,
    end_pct: float,
    batch_size: int = 50,
) -> BaseGeometry:
    """
    Perform a cascaded union of geometries in batches for robustness.
    
    This approach:
    1. Splits geometries into small batches
    2. Unions each batch separately
    3. Unions the batch results together
    
    This is more numerically stable than unioning all at once.
    
    Args:
        geometries: List of geometries to union
        progress_callback: Optional progress callback
        start_pct: Starting progress percentage
        end_pct: Ending progress percentage
        batch_size: Number of geometries per batch
        
    Returns:
        Unioned geometry
    """
    def report(pct: float, status: str):
        if progress_callback:
            progress_callback(pct, status)
    
    if len(geometries) == 0:
        return Point(0, 0).buffer(0)  # Empty polygon
    
    if len(geometries) == 1:
        return geometries[0]
    
    # Make all geometries valid first
    valid_geoms = []
    for g in geometries:
        if not g.is_valid:
            g = g.buffer(0)
        if not g.is_empty:
            valid_geoms.append(g)
    
    if len(valid_geoms) == 0:
        return Point(0, 0).buffer(0)
    
    # If small number, just union directly
    if len(valid_geoms) <= batch_size:
        return unary_union(valid_geoms)
    
    # Split into batches and union each batch
    batches = []
    total_batches = (len(valid_geoms) + batch_size - 1) // batch_size
    
    for i in range(0, len(valid_geoms), batch_size):
        batch = valid_geoms[i:i + batch_size]
        batch_result = unary_union(batch)
        if not batch_result.is_valid:
            batch_result = batch_result.buffer(0)
        batches.append(batch_result)
        
        batch_num = len(batches)
        pct = start_pct + (end_pct - start_pct) * 0.8 * (batch_num / total_batches)
        report(pct, f"Merging batch {batch_num}/{total_batches}...")
    
    # Now union all the batches together
    if len(batches) == 1:
        return batches[0]
    
    report(start_pct + (end_pct - start_pct) * 0.85, "Final merge...")
    result = unary_union(batches)
    
    return result


def _adaptive_curvature_sampling(
    coords: list[tuple[float, float]],
    max_samples: int,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    start_pct: float = 0.0,
    end_pct: float = 1.0,
) -> list[tuple[float, float]]:
    """
    Sample boundary coordinates with adaptive density based on curvature.
    
    High-curvature areas (corners, complex coastlines) get more sample points,
    while straight sections get fewer. This ensures gaps don't appear at
    complex boundary sections without wasting samples on straight edges.
    
    The algorithm:
    1. Calculate the turning angle (curvature) at each point
    2. Assign sampling weights based on curvature (higher curvature = more weight)
    3. Select points proportionally to their weights
    
    Args:
        coords: List of (lon, lat) coordinate tuples
        max_samples: Maximum number of samples to return
        progress_callback: Optional progress callback
        start_pct: Starting progress percentage
        end_pct: Ending progress percentage
        
    Returns:
        List of sampled coordinates with adaptive density
    """
    import math
    
    def report(pct: float, status: str):
        if progress_callback:
            progress_callback(pct, status)
    
    n = len(coords)
    
    # If we have fewer points than max_samples, return all
    if n <= max_samples:
        return coords
    
    # If very few points, just return uniform sample
    if n < 10:
        return coords
    
    report(start_pct + (end_pct - start_pct) * 0.2, "Computing boundary curvature...")
    
    # Calculate curvature (turning angle) at each point
    # Curvature is approximated as the angle change between consecutive segments
    curvatures = []
    for i in range(n):
        # Get three consecutive points (wrapping around)
        p_prev = coords[(i - 1) % n]
        p_curr = coords[i]
        p_next = coords[(i + 1) % n]
        
        # Vector from prev to curr
        v1_lon = p_curr[0] - p_prev[0]
        v1_lat = p_curr[1] - p_prev[1]
        
        # Vector from curr to next
        v2_lon = p_next[0] - p_curr[0]
        v2_lat = p_next[1] - p_curr[1]
        
        # Calculate lengths
        len1 = math.sqrt(v1_lon**2 + v1_lat**2)
        len2 = math.sqrt(v2_lon**2 + v2_lat**2)
        
        if len1 < 1e-10 or len2 < 1e-10:
            # Degenerate case - no curvature
            curvatures.append(0.0)
            continue
        
        # Normalize vectors
        v1_lon /= len1
        v1_lat /= len1
        v2_lon /= len2
        v2_lat /= len2
        
        # Dot product gives cos(angle)
        dot = v1_lon * v2_lon + v1_lat * v2_lat
        dot = max(-1.0, min(1.0, dot))  # Clamp for numerical stability
        
        # Angle in radians (0 = straight, pi = complete reversal)
        angle = math.acos(dot)
        curvatures.append(angle)
    
    report(start_pct + (end_pct - start_pct) * 0.5, "Computing sampling weights...")
    
    # Convert curvatures to sampling weights
    # Add a base weight so even straight sections get some samples
    base_weight = 0.1
    curvature_boost = 5.0  # How much extra weight for high curvature
    
    weights = []
    for c in curvatures:
        # Normalize curvature (0 to 1 scale, where 1 is a sharp corner)
        normalized = c / math.pi
        weight = base_weight + curvature_boost * normalized
        weights.append(weight)
    
    # Compute cumulative weights for weighted sampling
    total_weight = sum(weights)
    cumulative = []
    running = 0.0
    for w in weights:
        running += w
        cumulative.append(running)
    
    report(start_pct + (end_pct - start_pct) * 0.7, "Selecting adaptive samples...")
    
    # Select samples proportionally to weights
    sampled_indices = set()
    
    # Always include high-curvature points (corners)
    curvature_threshold = 0.3 * math.pi  # ~54 degrees
    for i, c in enumerate(curvatures):
        if c >= curvature_threshold:
            sampled_indices.add(i)
    
    # Fill remaining slots with weighted random sampling
    remaining = max_samples - len(sampled_indices)
    if remaining > 0:
        # Use deterministic weighted selection (not random, for reproducibility)
        step = total_weight / remaining
        target = step / 2  # Start at half step
        
        for _ in range(remaining):
            # Find the index where cumulative weight exceeds target
            for i, cum_w in enumerate(cumulative):
                if cum_w >= target and i not in sampled_indices:
                    sampled_indices.add(i)
                    break
            target += step
            # Wrap around if needed
            if target > total_weight:
                target -= total_weight
    
    # Sort indices and extract coordinates
    sorted_indices = sorted(sampled_indices)
    sampled_coords = [coords[i] for i in sorted_indices]
    
    report(end_pct, f"Selected {len(sampled_coords)} points (including {sum(1 for c in curvatures if c >= curvature_threshold)} high-curvature points)")
    
    return sampled_coords


def _extract_all_coordinates(geometry: BaseGeometry) -> list[tuple[float, float]]:
    """Extract all coordinates from any geometry type."""
    coords = []
    
    if geometry.geom_type == "Point":
        coords.append((geometry.x, geometry.y))
    elif geometry.geom_type == "LineString":
        coords.extend(list(geometry.coords))
    elif geometry.geom_type == "Polygon":
        coords.extend(list(geometry.exterior.coords))
        for interior in geometry.interiors:
            coords.extend(list(interior.coords))
    elif geometry.geom_type == "MultiPoint":
        for point in geometry.geoms:
            coords.append((point.x, point.y))
    elif geometry.geom_type == "MultiLineString":
        for line in geometry.geoms:
            coords.extend(list(line.coords))
    elif geometry.geom_type == "MultiPolygon":
        for polygon in geometry.geoms:
            coords.extend(list(polygon.exterior.coords))
            for interior in polygon.interiors:
                coords.extend(list(interior.coords))
    elif geometry.geom_type == "GeometryCollection":
        for geom in geometry.geoms:
            coords.extend(_extract_all_coordinates(geom))
    
    return coords


def create_geodesic_donut(
    center_lat: float,
    center_lon: float,
    inner_radius_km: float,
    outer_radius_km: float,
    num_points: int = 360,
) -> Polygon:
    """
    Create a geodesic donut (ring with hole) around a point.
    
    Args:
        center_lat: Center latitude in decimal degrees
        center_lon: Center longitude in decimal degrees
        inner_radius_km: Inner radius in kilometers
        outer_radius_km: Outer radius in kilometers
        num_points: Number of points for each circle
        
    Returns:
        Shapely Polygon with a hole
    """
    outer_circle = create_geodesic_circle(center_lat, center_lon, outer_radius_km, num_points)
    
    if inner_radius_km <= 0:
        return outer_circle
    
    inner_circle = create_geodesic_circle(center_lat, center_lon, inner_radius_km, num_points)
    
    # Create polygon with hole
    return Polygon(
        shell=list(outer_circle.exterior.coords),
        holes=[list(inner_circle.exterior.coords)]
    )


def simplify_geometry(
    geometry: BaseGeometry,
    tolerance_km: float = 5.0,
    preserve_topology: bool = True,
) -> BaseGeometry:
    """
    Simplify a geometry while preserving its general shape.
    
    Note: This uses planar simplification. For very large geometries,
    consider using a suitable projection first.
    
    Args:
        geometry: Input geometry
        tolerance_km: Tolerance in kilometers (approximate)
        preserve_topology: Whether to preserve topology
        
    Returns:
        Simplified geometry
    """
    # Convert tolerance from km to approximate degrees
    # This is a rough approximation: 1 degree ≈ 111 km at equator
    tolerance_degrees = tolerance_km / 111.0
    
    return geometry.simplify(tolerance_degrees, preserve_topology=preserve_topology)


def get_geometry_centroid(geometry: BaseGeometry) -> tuple[float, float]:
    """
    Get the centroid of a geometry.
    
    Args:
        geometry: Input geometry
        
    Returns:
        Tuple of (latitude, longitude)
    """
    centroid = geometry.centroid
    return centroid.y, centroid.x


def get_geometry_bounds(
    geometry: BaseGeometry,
) -> tuple[float, float, float, float]:
    """
    Get the bounding box of a geometry.
    
    Args:
        geometry: Input geometry
        
    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat)
    """
    return geometry.bounds  # Returns (minx, miny, maxx, maxy)


def count_vertices(geometry: BaseGeometry) -> int:
    """
    Count the total number of vertices in a geometry.
    
    Args:
        geometry: Input geometry
        
    Returns:
        Number of vertices
    """
    coords = _extract_all_coordinates(geometry)
    return len(coords)


def geometry_to_geojson(geometry: BaseGeometry, fix_antimeridian: bool = True) -> dict:
    """
    Convert a Shapely geometry to GeoJSON dict.
    
    Optionally fixes antimeridian crossing by splitting polygons that wrap around the 180° line.
    Uses the 'antimeridian' package for proper handling.
    
    Args:
        geometry: Input Shapely geometry
        fix_antimeridian: If True, split polygons at the antimeridian
        
    Returns:
        GeoJSON geometry dict
    """
    if geometry.geom_type in ("Polygon", "MultiPolygon"):
        geometry = fix_antimeridian_crossing(geometry)

    return mapping(geometry)


def fix_antimeridian_crossing(geometry: BaseGeometry) -> BaseGeometry:
    """
    Fix geometries that cross the antimeridian (180° longitude).
    
    Uses the 'antimeridian' package to properly split polygons at the 180° line.
    Preserves interior rings (holes) through the process.
    
    Args:
        geometry: Input geometry
        
    Returns:
        Fixed geometry (may be MultiPolygon if split was needed)
    """
    try:
        import antimeridian
        
        if geometry.is_empty:
            return geometry
        
        # Check if the geometry actually needs antimeridian fixing
        # by looking at the coordinate range
        coords = _extract_all_coordinates(geometry)
        if coords:
            lons = [c[0] for c in coords]
            min_lon, max_lon = min(lons), max(lons)
            
            # If all coordinates are within a reasonable range and don't span
            # across the antimeridian, don't fix (preserves holes better)
            if min_lon > -170 and max_lon < 170:
                # Doesn't cross antimeridian, return as-is to preserve holes
                return geometry
            if max_lon - min_lon < 180:
                # Coordinates don't wrap around, return as-is
                return geometry
        
        # Need to fix antimeridian crossing
        if geometry.geom_type == "Polygon":
            # Preserve interior rings (holes) through the fix
            original_interiors = list(geometry.interiors)
            fixed = antimeridian.fix_polygon(geometry, fix_winding=False)
            
            # If we had interior rings and lost them, try to restore
            if original_interiors and fixed.geom_type == "Polygon" and not list(fixed.interiors):
                # Interior rings were lost - try to add them back
                try:
                    for interior in original_interiors:
                        hole_poly = Polygon(interior)
                        fixed = fixed.difference(hole_poly)
                except Exception:
                    pass
            
            return fixed
        elif geometry.geom_type == "MultiPolygon":
            fixed_parts = []
            for poly in geometry.geoms:
                fixed = fix_antimeridian_crossing(poly)
                if fixed.geom_type == "MultiPolygon":
                    fixed_parts.extend(fixed.geoms)
                else:
                    fixed_parts.append(fixed)
            return MultiPolygon(fixed_parts) if len(fixed_parts) > 1 else fixed_parts[0]
        
        return geometry
    except Exception as e:
        # If antimeridian package fails, return original
        print(f"Warning: antimeridian fix failed: {e}")
        return geometry


def geodesic_line(
    lat1: float, lon1: float, lat2: float, lon2: float, num_points: int = 100
) -> LineString:
    """
    Create a geodesic line (great circle arc) between two points.
    
    Args:
        lat1, lon1: Start point coordinates
        lat2, lon2: End point coordinates
        num_points: Number of intermediate points
        
    Returns:
        Shapely LineString following the geodesic path
    """
    # Calculate the geodesic line
    result = WGS84.InverseLine(lat1, lon1, lat2, lon2)
    total_distance = result.s13  # Total distance in meters
    
    points = []
    for i in range(num_points + 1):
        s = (total_distance / num_points) * i
        pos = result.Position(s)
        points.append((pos["lon2"], pos["lat2"]))
    
    return LineString(points)


def find_closest_points(
    geometry_a: BaseGeometry,
    geometry_b: BaseGeometry,
    sample_points: int = 100,
) -> tuple[tuple[float, float], tuple[float, float], float]:
    """
    Find the closest points between two geometries using geodesic distance.
    
    This is an approximation that samples points from both geometries.
    
    Args:
        geometry_a: First geometry
        geometry_b: Second geometry
        sample_points: Number of sample points to use
        
    Returns:
        Tuple of ((lat_a, lon_a), (lat_b, lon_b), distance_km)
    """
    coords_a = _extract_all_coordinates(geometry_a)
    coords_b = _extract_all_coordinates(geometry_b)
    
    # Sample if too many points
    if len(coords_a) > sample_points:
        step = len(coords_a) // sample_points
        coords_a = coords_a[::step]
    if len(coords_b) > sample_points:
        step = len(coords_b) // sample_points
        coords_b = coords_b[::step]
    
    min_distance = float('inf')
    closest_a = None
    closest_b = None
    
    for lon_a, lat_a in coords_a:
        for lon_b, lat_b in coords_b:
            dist = geodesic_distance(lat_a, lon_a, lat_b, lon_b)
            if dist < min_distance:
                min_distance = dist
                closest_a = (lat_a, lon_a)
                closest_b = (lat_b, lon_b)
    
    return closest_a, closest_b, min_distance


def buffer_geometry_union(
    geometries: list[BaseGeometry],
    distance_km: float,
    resolution: str = "normal",
) -> BaseGeometry:
    """
    Create a geodesic buffer around multiple geometries and union them.
    
    Args:
        geometries: List of input geometries
        distance_km: Buffer distance in kilometers
        resolution: Resolution setting
        
    Returns:
        Unioned buffered geometry
    """
    buffered = []
    for geom in geometries:
        buffered.append(create_geodesic_buffer(geom, distance_km, resolution))
    
    return unary_union(buffered)


def validate_geometry(geometry: BaseGeometry) -> tuple[bool, Optional[str]]:
    """
    Validate a geometry and return any issues.
    
    Args:
        geometry: Input geometry
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not geometry.is_valid:
        return False, f"Invalid geometry: {geometry.geom_type}"
    
    if geometry.is_empty:
        return False, "Empty geometry"
    
    return True, None


def make_geometry_valid(geometry: BaseGeometry) -> BaseGeometry:
    """
    Attempt to make an invalid geometry valid.
    
    Args:
        geometry: Input geometry
        
    Returns:
        Valid geometry (or original if already valid)
    """
    if geometry.is_valid:
        return geometry
    
    # Try buffer(0) trick to fix self-intersections
    return geometry.buffer(0)
