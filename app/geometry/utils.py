"""
Geometry utilities for ORRG.
Provides geodesic calculations using pyproj and geographiclib.
All calculations are true geodesic on the WGS84 ellipsoid.
"""

import math
from typing import Optional, Callable

import numpy as np
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
    
    Uses an Azimuthal Equidistant projection centered on the geometry's centroid
    to perform an accurate geodesic buffer, then transforms back to WGS84.
    
    Args:
        geometry: Input Shapely geometry (Point, LineString, Polygon, etc.)
        distance_km: Buffer distance in kilometers
        resolution: Resolution setting ('low', 'normal', 'high')
        progress_callback: Optional callback function(progress: float, status: str)
                          where progress is 0.0-1.0 and status is a description
        
    Returns:
        Buffered Shapely geometry
    """
    from pyproj import CRS, Transformer
    
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
    
    report_progress(0.1, "Computing geometry centroid...")
    
    # Get the centroid for the projection center
    centroid = geometry.centroid
    center_lon, center_lat = centroid.x, centroid.y
    
    report_progress(0.2, "Setting up projection...")
    
    # Create an Azimuthal Equidistant projection centered on the geometry
    # This projection preserves distances from the center point
    aeqd_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m"
    )
    wgs84_crs = CRS.from_epsg(4326)
    
    # Create transformers
    to_aeqd = Transformer.from_crs(wgs84_crs, aeqd_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(aeqd_crs, wgs84_crs, always_xy=True)
    
    report_progress(0.3, "Projecting geometry...")
    
    # Transform geometry to projected CRS
    projected_geom = _transform_geometry(geometry, to_aeqd)
    
    report_progress(0.5, "Applying buffer...")
    
    # Buffer in meters
    distance_m = distance_km * 1000
    
    # Apply buffer with appropriate resolution
    buffer_resolution = {"low": 8, "normal": 16, "high": 32}.get(resolution, 16)
    buffered_projected = projected_geom.buffer(distance_m, resolution=buffer_resolution)
    
    report_progress(0.7, "Transforming back to WGS84...")
    
    # Transform back to WGS84
    result = _transform_geometry(buffered_projected, to_wgs84)
    
    report_progress(0.9, "Validating geometry...")
    
    # Ensure valid geometry
    if not result.is_valid:
        result = result.buffer(0)
    
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
    if fix_antimeridian and geometry.geom_type in ("Polygon", "MultiPolygon"):
        geometry = fix_antimeridian_crossing(geometry)
    
    return mapping(geometry)


def fix_antimeridian_crossing(geometry: BaseGeometry) -> BaseGeometry:
    """
    Fix geometries that cross the antimeridian (180° longitude).
    
    Uses the 'antimeridian' package to properly split polygons at the 180° line.
    
    Args:
        geometry: Input geometry
        
    Returns:
        Fixed geometry (may be MultiPolygon if split was needed)
    """
    try:
        import antimeridian
        
        if geometry.is_empty:
            return geometry
        
        # Use the antimeridian package's fix_polygon function
        if geometry.geom_type == "Polygon":
            fixed = antimeridian.fix_polygon(geometry)
            return fixed
        elif geometry.geom_type == "MultiPolygon":
            fixed_parts = []
            for poly in geometry.geoms:
                fixed = antimeridian.fix_polygon(poly)
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
