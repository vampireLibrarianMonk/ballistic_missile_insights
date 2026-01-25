"""
Geometry services for ORRG.
High-level services for generating range rings and analytical outputs.
"""

import time
from typing import Optional
from uuid import uuid4

from shapely.geometry import MultiPolygon, Point, mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from typing import Callable

from app.geometry.utils import (
    create_geodesic_buffer,
    create_geodesic_circle,
    create_geodesic_donut,
    find_closest_points,
    geodesic_distance,
    geodesic_line,
    get_geometry_bounds,
    get_geometry_centroid,
    count_vertices,
    geometry_to_geojson,
    make_geometry_valid,
)

# Type alias for progress callback
ProgressCallback = Optional[Callable[[float, str], None]]
from app.models.inputs import (
    SingleRangeRingInput,
    MultipleRangeRingInput,
    ReverseRangeRingInput,
    MinimumRangeRingInput,
    CustomPOIRangeRingInput,
    DistanceUnit,
    convert_to_km,
    classify_range,
)
from app.models.outputs import (
    RangeRingOutput,
    RangeRingLayer,
    ExportMetadata,
    OutputType,
    GeometryType,
    MinimumDistanceResult,
)


# Color palette for range rings (from shortest to longest range)
RANGE_COLORS = [
    "#3366CC",  # Blue - CRBM/SRBM
    "#33CC33",  # Green - MRBM
    "#FFCC00",  # Yellow - IRBM
    "#FF6600",  # Orange - Long IRBM
    "#CC0000",  # Red - ICBM
]


def _get_color_for_range(range_km: float) -> str:
    """Get a color based on range classification."""
    if range_km < 300:
        return RANGE_COLORS[0]
    elif range_km < 1000:
        return RANGE_COLORS[0]
    elif range_km < 3000:
        return RANGE_COLORS[1]
    elif range_km < 5500:
        return RANGE_COLORS[2]
    else:
        return RANGE_COLORS[4]


class RangeRingService:
    """
    Service class for generating range ring outputs.
    Provides methods for all five analytical tools.
    """
    
    def __init__(self, data_service=None):
        """
        Initialize the service.
        
        Args:
            data_service: Optional data service for loading country/city data
        """
        self._data_service = data_service
    
    def get_country_geometry(self, country_code: str) -> Optional[BaseGeometry]:
        """Get the geometry for a country by ISO3 code."""
        if self._data_service:
            return self._data_service.get_country_geometry(country_code)
        return None
    
    def get_country_name(self, country_code: str) -> str:
        """Get the name of a country by ISO3 code."""
        if self._data_service:
            return self._data_service.get_country_name(country_code)
        return country_code
    
    def get_city_coordinates(self, city_name: str) -> Optional[tuple[float, float]]:
        """Get coordinates for a city by name."""
        if self._data_service:
            return self._data_service.get_city_coordinates(city_name)
        return None


def generate_single_range_ring(
    input_data: SingleRangeRingInput,
    origin_geometry: Optional[BaseGeometry] = None,
    origin_name: str = "Origin",
    progress_callback: ProgressCallback = None,
) -> RangeRingOutput:
    """
    Generate a single range ring from a point or country boundary.
    
    Args:
        input_data: Input parameters for the range ring
        origin_geometry: Optional Shapely geometry for the origin (country boundary)
        origin_name: Name of the origin for display
        progress_callback: Optional callback for progress updates (progress: float 0-1, status: str)
        
    Returns:
        RangeRingOutput containing the generated range ring
    """
    def report_progress(pct: float, status: str):
        if progress_callback:
            progress_callback(pct, status)
    
    start_time = time.time()
    report_progress(0.0, "Starting range ring generation...")
    
    # Convert range to kilometers
    range_km = convert_to_km(input_data.range_value, input_data.range_unit)
    report_progress(0.05, f"Range: {range_km:.0f} km")
    
    # Get the range classification
    range_class = classify_range(range_km)
    
    # Determine origin point
    if input_data.origin_point:
        center_lat = input_data.origin_point.latitude
        center_lon = input_data.origin_point.longitude
        origin_name = input_data.origin_point.name
        
        report_progress(0.1, "Creating geodesic circle from point...")
        # Create circle from point
        ring_geometry = create_geodesic_circle(
            center_lat, center_lon, range_km,
            num_points=360 if input_data.resolution == "high" else 180
        )
        report_progress(0.8, "Circle geometry created")
    elif origin_geometry:
        report_progress(0.1, "Buffering country boundary...")
        # Buffer the country geometry with progress callback
        ring_geometry = create_geodesic_buffer(
            origin_geometry, range_km, input_data.resolution,
            progress_callback=lambda p, s: report_progress(0.1 + p * 0.6, s)
        )
        center_lat, center_lon = get_geometry_centroid(origin_geometry)
        
        report_progress(0.75, "Cutting ring at country border...")
        # Subtract the origin country geometry so ring only shows area BEYOND the border
        # The country should appear as a hole (unshaded area) within the range ring
        try:
            origin_valid = make_geometry_valid(origin_geometry)
            
            # Debug: Print geometry info before subtraction
            print(f"DEBUG: Ring geometry type BEFORE subtraction: {ring_geometry.geom_type}")
            print(f"DEBUG: Ring has {len(list(ring_geometry.interiors)) if ring_geometry.geom_type == 'Polygon' else 'N/A'} interior rings before")
            print(f"DEBUG: Origin geometry type: {origin_valid.geom_type}")
            print(f"DEBUG: Origin geometry area: {origin_valid.area:.2f}")
            
            ring_before = ring_geometry
            
            # Use shapely's difference to create the hole
            ring_geometry = ring_geometry.difference(origin_valid)
            
            # Debug: Print geometry info after subtraction
            print(f"DEBUG: Ring geometry type AFTER subtraction: {ring_geometry.geom_type}")
            if ring_geometry.geom_type == "Polygon":
                print(f"DEBUG: Ring has {len(list(ring_geometry.interiors))} interior rings after")
            elif ring_geometry.geom_type == "MultiPolygon":
                for i, poly in enumerate(ring_geometry.geoms):
                    print(f"DEBUG: MultiPolygon part {i} has {len(list(poly.interiors))} interior rings")
            
            # Validate the result
            if ring_geometry.is_empty:
                print(f"Warning: Subtraction resulted in empty geometry, using original")
                ring_geometry = ring_before
            elif not ring_geometry.is_valid:
                print(f"DEBUG: Geometry invalid after subtraction, fixing...")
                ring_geometry = make_geometry_valid(ring_geometry)
            
            # Check if subtraction worked by comparing areas
            area_before = ring_before.area
            area_after = ring_geometry.area
            print(f"DEBUG: Area before: {area_before:.2f}, Area after: {area_after:.2f}")
            
            if abs(area_before - area_after) < 0.01:  # Areas essentially identical
                print(f"Warning: Country subtraction may have failed - areas nearly identical")
                print(f"DEBUG: Trying alternative subtraction approach...")
                
                # Alternative approach: explicitly create a polygon with the country as a hole
                from shapely.geometry import Polygon, MultiPolygon
                
                if ring_before.geom_type == "Polygon":
                    # Get the exterior of the ring
                    exterior_coords = list(ring_before.exterior.coords)
                    # Get existing interior rings (holes)
                    existing_holes = [list(interior.coords) for interior in ring_before.interiors]
                    # Add the country boundary as another hole
                    if origin_valid.geom_type == "Polygon":
                        country_hole = list(origin_valid.exterior.coords)
                        existing_holes.append(country_hole)
                    elif origin_valid.geom_type == "MultiPolygon":
                        for poly in origin_valid.geoms:
                            country_hole = list(poly.exterior.coords)
                            existing_holes.append(country_hole)
                    
                    # Create new polygon with country as hole
                    try:
                        ring_geometry = Polygon(exterior_coords, holes=existing_holes)
                        ring_geometry = make_geometry_valid(ring_geometry)
                        print(f"DEBUG: Created polygon with explicit holes. Interior count: {len(list(ring_geometry.interiors))}")
                    except Exception as e:
                        print(f"DEBUG: Explicit hole creation failed: {e}")
                        ring_geometry = ring_before
                        
        except Exception as e:
            print(f"Could not subtract country geometry: {e}")
            import traceback
            traceback.print_exc()
    else:
        raise ValueError("Either origin_point or origin_geometry must be provided")
    
    # Make geometry valid if needed
    ring_geometry = make_geometry_valid(ring_geometry)
    
    # Get bounds
    bounds = get_geometry_bounds(ring_geometry)
    
    # Create layer - use weapon system name if provided
    if input_data.weapon_system:
        layer_name = input_data.weapon_system
        if range_class:
            layer_name = f"{layer_name} ({range_class.value})"
    else:
        layer_name = f"{range_km:.0f} km Range"
        if range_class:
            layer_name = f"{layer_name} ({range_class.value})"
    
    layer = RangeRingLayer(
        name=layer_name,
        geometry_type=GeometryType.POLYGON if ring_geometry.geom_type == "Polygon" else GeometryType.MULTI_POLYGON,
        geometry_geojson=geometry_to_geojson(ring_geometry),
        fill_color=_get_color_for_range(range_km),
        stroke_color=_get_color_for_range(range_km),
        fill_opacity=0.2,
        stroke_width=2.0,
        range_km=range_km,
        label=f"{input_data.range_value:,.0f} {input_data.range_unit.value}",
    )
    
    # Calculate processing time
    processing_time = (time.time() - start_time) * 1000
    
    # Create metadata
    metadata = ExportMetadata(
        tool_type=OutputType.SINGLE_RANGE_RING,
        point_count=1 if input_data.origin_point else None,
        vertex_count=count_vertices(ring_geometry),
        processing_time_ms=processing_time,
        resolution=input_data.resolution,
        geodesic_method="geographiclib",
        range_km=range_km,
        range_classification=range_class.value if range_class else None,
        origin_name=origin_name,
        origin_type=input_data.origin_type.value,
        weapon_name=input_data.weapon_system,
        weapon_source=getattr(input_data, 'weapon_source', None),
    )
    
    # Create title
    title = input_data.weapon_system or "Range Ring"
    if range_class:
        title = f"{title} {range_class.value}"
    
    return RangeRingOutput(
        output_type=OutputType.SINGLE_RANGE_RING,
        title=title,
        subtitle=origin_name,
        description=f"Range: {input_data.range_value:,.0f} {input_data.range_unit.value}",
        layers=[layer],
        center_latitude=center_lat,
        center_longitude=center_lon,
        bbox=bounds,
        metadata=metadata,
    )


def generate_multiple_range_rings(
    input_data: MultipleRangeRingInput,
    origin_geometry: Optional[BaseGeometry] = None,
    origin_name: str = "Origin",
    progress_callback: ProgressCallback = None,
) -> RangeRingOutput:
    """
    Generate multiple concentric range rings.
    
    Args:
        input_data: Input parameters including multiple ranges
        origin_geometry: Optional Shapely geometry for the origin
        origin_name: Name of the origin
        progress_callback: Optional callback for progress updates (progress: float 0-1, status: str)
        
    Returns:
        RangeRingOutput containing multiple layers
    """
    def report_progress(pct: float, status: str):
        if progress_callback:
            progress_callback(pct, status)
    
    start_time = time.time()
    report_progress(0.0, "Initializing multiple range ring generation...")
    
    layers = []
    all_geometries = []
    
    # Determine center point
    report_progress(0.02, "Determining origin center point...")
    if input_data.origin_point:
        center_lat = input_data.origin_point.latitude
        center_lon = input_data.origin_point.longitude
        origin_name = input_data.origin_point.name
        report_progress(0.05, f"Using point origin: {origin_name}")
    elif origin_geometry:
        center_lat, center_lon = get_geometry_centroid(origin_geometry)
        report_progress(0.05, f"Calculated centroid for {origin_name}")
    else:
        raise ValueError("Either origin_point or origin_geometry must be provided")
    
    # Sort ranges from largest to smallest (for proper layering)
    report_progress(0.08, "Sorting ranges for proper layering...")
    sorted_ranges = sorted(
        input_data.ranges,
        key=lambda r: convert_to_km(r[0], r[1]),
        reverse=True
    )
    num_ranges = len(sorted_ranges)
    report_progress(0.10, f"Processing {num_ranges} range ring(s)...")
    
    # Make origin geometry valid for subtraction
    origin_valid = None
    if origin_geometry:
        report_progress(0.12, "Validating origin geometry...")
        origin_valid = make_geometry_valid(origin_geometry)
        report_progress(0.15, "Origin geometry validated")
    
    # Process each range - this is the main work (15% - 85%)
    for ring_idx, (range_value, range_unit, label) in enumerate(sorted_ranges):
        range_km = convert_to_km(range_value, range_unit)
        range_class = classify_range(range_km)
        ring_label = label or f"{range_km:.0f} km"
        
        # Calculate progress for this ring (each ring gets equal share of 15%-85% = 70%)
        ring_start_pct = 0.15 + (ring_idx / num_ranges) * 0.70
        ring_end_pct = 0.15 + ((ring_idx + 1) / num_ranges) * 0.70
        ring_progress_range = ring_end_pct - ring_start_pct
        
        report_progress(ring_start_pct, f"Ring {ring_idx + 1}/{num_ranges}: {ring_label} - Starting...")
        
        # Generate ring geometry
        if input_data.origin_point:
            report_progress(ring_start_pct + ring_progress_range * 0.1, 
                          f"Ring {ring_idx + 1}/{num_ranges}: Creating geodesic circle ({range_km:.0f} km)...")
            ring_geometry = create_geodesic_circle(
                center_lat, center_lon, range_km,
                num_points=180 if input_data.resolution == "normal" else 72
            )
            report_progress(ring_start_pct + ring_progress_range * 0.8, 
                          f"Ring {ring_idx + 1}/{num_ranges}: Circle created")
        elif origin_geometry:
            # Define a nested progress callback for the buffer operation
            def buffer_progress(buffer_pct: float, buffer_status: str):
                # Map buffer progress (0-1) to our ring's progress range (10%-70% of ring's allocation)
                mapped_pct = ring_start_pct + ring_progress_range * (0.1 + buffer_pct * 0.6)
                report_progress(mapped_pct, f"Ring {ring_idx + 1}/{num_ranges}: {buffer_status}")
            
            report_progress(ring_start_pct + ring_progress_range * 0.1, 
                          f"Ring {ring_idx + 1}/{num_ranges}: Buffering boundary ({range_km:.0f} km)...")
            ring_geometry = create_geodesic_buffer(
                origin_geometry, range_km, input_data.resolution,
                progress_callback=buffer_progress
            )
            
            # Subtract the origin country geometry so ring only shows area BEYOND the border
            report_progress(ring_start_pct + ring_progress_range * 0.75, 
                          f"Ring {ring_idx + 1}/{num_ranges}: Subtracting origin from ring...")
            try:
                ring_geometry = ring_geometry.difference(origin_valid)
            except Exception as e:
                print(f"Could not subtract country geometry: {e}")
        
        report_progress(ring_start_pct + ring_progress_range * 0.85, 
                      f"Ring {ring_idx + 1}/{num_ranges}: Validating geometry...")
        ring_geometry = make_geometry_valid(ring_geometry)
        all_geometries.append(ring_geometry)
        
        # Create layer
        layer_name = label or f"{range_km:.0f} km"
        
        report_progress(ring_start_pct + ring_progress_range * 0.95, 
                      f"Ring {ring_idx + 1}/{num_ranges}: Creating layer...")
        layer = RangeRingLayer(
            name=layer_name,
            geometry_type=GeometryType.POLYGON if ring_geometry.geom_type == "Polygon" else GeometryType.MULTI_POLYGON,
            geometry_geojson=geometry_to_geojson(ring_geometry),
            fill_color=_get_color_for_range(range_km),
            stroke_color=_get_color_for_range(range_km),
            fill_opacity=0.15,
            stroke_width=2.0,
            range_km=range_km,
            label=f"{range_value:,.0f} {range_unit.value}",
        )
        layers.append(layer)
        
        report_progress(ring_end_pct, f"Ring {ring_idx + 1}/{num_ranges}: Complete")
    
    # Finalize (85% - 100%)
    report_progress(0.86, "Calculating combined bounds...")
    combined = unary_union(all_geometries)
    bounds = get_geometry_bounds(combined)
    
    report_progress(0.90, "Computing processing statistics...")
    # Calculate processing time
    processing_time = (time.time() - start_time) * 1000
    
    report_progress(0.94, "Building metadata...")
    # Create metadata
    metadata = ExportMetadata(
        tool_type=OutputType.MULTIPLE_RANGE_RING,
        ring_count=len(layers),
        vertex_count=sum(count_vertices(g) for g in all_geometries),
        processing_time_ms=processing_time,
        resolution=input_data.resolution,
        geodesic_method="geographiclib",
        origin_name=origin_name,
        origin_type=input_data.origin_type.value,
    )
    
    report_progress(0.98, "Creating output object...")
    
    output = RangeRingOutput(
        output_type=OutputType.MULTIPLE_RANGE_RING,
        title="Multiple Range Rings",
        subtitle=origin_name,
        description=f"{len(layers)} range rings",
        layers=layers,
        center_latitude=center_lat,
        center_longitude=center_lon,
        bbox=bounds,
        metadata=metadata,
    )
    
    report_progress(1.0, "Complete!")
    return output


def generate_reverse_range_ring(
    input_data: ReverseRangeRingInput,
    threat_country_geometry: Optional[BaseGeometry] = None,
    threat_country_name: Optional[str] = None,
    progress_callback: ProgressCallback = None,
) -> RangeRingOutput:
    """
    Generate a reverse range ring showing potential launch areas within a threat country.
    
    This identifies the portion of the shooter country that is within weapon range of the target.
    
    The process (matching original ArcGIS implementation):
    1. Creates a geodesic buffer (circle) around the TARGET point using the weapon range
    2. Clips (intersects) that buffer with the SHOOTER COUNTRY boundary
    3. The result shows the areas within the shooter country from which the target can be reached
    
    Args:
        input_data: Input parameters including target point and range
        threat_country_geometry: Geometry of the shooter/threat country
        threat_country_name: Name of the shooter/threat country
        progress_callback: Optional callback for progress updates (progress: float 0-1, status: str)
        
    Returns:
        RangeRingOutput showing potential launch areas within the shooter country
    """
    def report_progress(pct: float, status: str):
        if progress_callback:
            progress_callback(pct, status)
    
    start_time = time.time()
    report_progress(0.0, "Initializing reverse range ring analysis...")
    
    report_progress(0.02, "Loading target coordinates...")
    target_lat = input_data.target_point.latitude
    target_lon = input_data.target_point.longitude
    
    report_progress(0.05, "Converting range to kilometers...")
    range_km = convert_to_km(input_data.range_value, input_data.range_unit)
    range_class = classify_range(range_km)
    report_progress(0.08, f"Weapon range: {range_km:,.0f} km ({range_class.value if range_class else 'Unknown'})")
    
    layers = []
    
    # Step 1: Create geodesic buffer around the TARGET (reach envelope)
    report_progress(0.10, f"Creating reach envelope around target ({range_km:,.0f} km radius)...")
    reach_envelope = create_geodesic_circle(
        target_lat, target_lon, range_km,
        num_points=360 if input_data.resolution == "high" else 180
    )
    report_progress(0.18, "Validating reach envelope geometry...")
    reach_envelope = make_geometry_valid(reach_envelope)
    report_progress(0.20, "Reach envelope created successfully")
    
    if threat_country_geometry is not None:
        # Make shooter country geometry valid
        report_progress(0.22, f"Loading shooter country geometry ({threat_country_name})...")
        shooter_geom = make_geometry_valid(threat_country_geometry)
        report_progress(0.25, "Shooter country geometry validated")
        
        # First, calculate the minimum and maximum distances from the shooter country to the target
        # This helps us determine if we need intersection at all
        report_progress(0.28, "Extracting shooter country boundary coordinates...")
        from app.geometry.utils import _extract_all_coordinates
        shooter_coords = _extract_all_coordinates(shooter_geom)
        
        report_progress(0.32, f"Calculating distances from {len(shooter_coords[:2000])} boundary points to target...")
        min_dist_to_target = float('inf')
        max_dist_to_target = 0
        
        sample_count = min(2000, len(shooter_coords))
        for i, (lon, lat) in enumerate(shooter_coords[:2000]):
            dist = geodesic_distance(lat, lon, target_lat, target_lon)
            if dist < min_dist_to_target:
                min_dist_to_target = dist
            if dist > max_dist_to_target:
                max_dist_to_target = dist
            
            # Progress update every 500 points
            if i % 500 == 0:
                pct = 0.32 + 0.15 * (i / sample_count)
                report_progress(pct, f"Measuring distances: {i}/{sample_count} points...")
        
        report_progress(0.48, f"Distance analysis complete: {min_dist_to_target:,.0f} km (min) to {max_dist_to_target:,.0f} km (max)")
        
        # If the ENTIRE shooter country is within range (max distance < range),
        # then the launch region IS the shooter country
        if max_dist_to_target <= range_km:
            report_progress(0.50, f"All of {threat_country_name} is within {range_km:,.0f} km range")
            # All of shooter country is within range
            launch_region = shooter_geom
            description = f"All of {threat_country_name} can reach {input_data.target_point.name}"
            report_progress(0.55, "Using entire shooter country as launch region")
        elif min_dist_to_target <= range_km:
            report_progress(0.50, f"Partial coverage: {min_dist_to_target:,.0f} km to {max_dist_to_target:,.0f} km")
            report_progress(0.52, "Computing intersection of reach envelope with shooter country...")
            # Part of shooter country is within range - need intersection
            # Fix antimeridian crossing before intersection
            try:
                report_progress(0.54, "Fixing antimeridian crossing for reach envelope...")
                import antimeridian
                reach_envelope_fixed = antimeridian.fix_polygon(reach_envelope)
                
                report_progress(0.56, "Fixing antimeridian crossing for shooter country...")
                # Also fix shooter geometry if needed
                if shooter_geom.geom_type == "Polygon":
                    shooter_geom_fixed = antimeridian.fix_polygon(shooter_geom)
                elif shooter_geom.geom_type == "MultiPolygon":
                    fixed_parts = []
                    for poly in shooter_geom.geoms:
                        fixed = antimeridian.fix_polygon(poly)
                        if fixed.geom_type == "MultiPolygon":
                            fixed_parts.extend(fixed.geoms)
                        else:
                            fixed_parts.append(fixed)
                    shooter_geom_fixed = MultiPolygon(fixed_parts) if len(fixed_parts) > 1 else fixed_parts[0]
                else:
                    shooter_geom_fixed = shooter_geom
            except Exception as e:
                print(f"Antimeridian fix failed: {e}")
                reach_envelope_fixed = reach_envelope
                shooter_geom_fixed = shooter_geom
            
            # Try the intersection
            report_progress(0.60, "Computing geometry intersection...")
            launch_region = reach_envelope_fixed.intersection(shooter_geom_fixed)
            report_progress(0.65, "Validating intersection result...")
            launch_region = make_geometry_valid(launch_region)
            
            # If intersection fails (empty), fall back to using entire shooter country
            # since we already verified part of it is in range
            if launch_region.is_empty:
                report_progress(0.68, "Intersection empty - using simplified geometry")
                launch_region = shooter_geom
                description = f"Launch region within {threat_country_name} (geometry simplified due to antimeridian)"
            else:
                report_progress(0.68, "Intersection computed successfully")
                description = f"Potential launch areas within {threat_country_name} that can reach {input_data.target_point.name}"
        else:
            # Target is out of range
            report_progress(0.50, f"Target OUT OF RANGE (minimum distance: {min_dist_to_target:,.0f} km)")
            launch_region = None
            description = f"Target {input_data.target_point.name} is OUT OF RANGE from {threat_country_name} (minimum distance: {min_dist_to_target:,.0f} km)"
        
        # Check if we have a valid launch region
        report_progress(0.70, "Validating launch region...")
        if launch_region is None or launch_region.is_empty:
            # Verify with geodesic distance calculation
            report_progress(0.72, "Re-verifying distances for validation...")
            from app.geometry.utils import _extract_all_coordinates
            shooter_coords = _extract_all_coordinates(shooter_geom)
            
            min_dist_to_target = float('inf')
            for lon, lat in shooter_coords[:1000]:
                dist = geodesic_distance(lat, lon, target_lat, target_lon)
                if dist < min_dist_to_target:
                    min_dist_to_target = dist
            
            if min_dist_to_target <= range_km:
                # Target should be in range but intersection failed (likely antimeridian issue)
                # Fall back to showing the full envelope with a message
                report_progress(0.75, "Intersection failed but target in range - showing full envelope")
                description = f"Target is within range ({min_dist_to_target:,.0f} km), but geometry intersection failed. Showing full envelope."
                launch_region = None
            else:
                report_progress(0.75, "Confirmed: target is out of range")
                description = f"Target {input_data.target_point.name} is OUT OF RANGE from {threat_country_name} (minimum distance: {min_dist_to_target:,.0f} km)"
                launch_region = None
        else:
            report_progress(0.75, "Launch region validated successfully")
            description = f"Potential launch areas within {threat_country_name} that can reach {input_data.target_point.name}"
        
        # Create launch region layer if we have one
        report_progress(0.78, "Creating output layers...")
        if launch_region is not None and not launch_region.is_empty:
            report_progress(0.80, "Building launch region layer...")
            layer_name = f"Launch Region for {input_data.weapon_system or 'Weapon'}"
            
            launch_layer = RangeRingLayer(
                name=layer_name,
                geometry_type=GeometryType.POLYGON if launch_region.geom_type == "Polygon" else GeometryType.MULTI_POLYGON,
                geometry_geojson=geometry_to_geojson(launch_region, fix_antimeridian=True),
                fill_color="#FF4444",
                stroke_color="#CC0000",
                fill_opacity=0.4,
                stroke_width=2.5,
                range_km=range_km,
                label=f"Within {range_km:,.0f} km of target",
            )
            layers.append(launch_layer)
            
            # Get bounds from launch region
            bounds = get_geometry_bounds(launch_region)
        else:
            # No intersection - show full envelope as reference
            envelope_layer = RangeRingLayer(
                name=f"Reach Envelope ({range_km:.0f} km)",
                geometry_type=GeometryType.POLYGON,
                geometry_geojson=geometry_to_geojson(reach_envelope, fix_antimeridian=True),
                fill_color="#888888",
                stroke_color="#666666",
                fill_opacity=0.15,
                stroke_width=1.5,
                range_km=range_km,
                label=f"Full {range_km:,.0f} km envelope",
            )
            layers.append(envelope_layer)
            bounds = get_geometry_bounds(reach_envelope)
        
        # Calculate center - use target location
        center_lat = target_lat
        center_lon = target_lon
    else:
        # No shooter country - just show the reach envelope
        layer_name = input_data.weapon_system or f"Reach Envelope ({range_km:.0f} km)"
        
        envelope_layer = RangeRingLayer(
            name=layer_name,
            geometry_type=GeometryType.POLYGON,
            geometry_geojson=geometry_to_geojson(reach_envelope, fix_antimeridian=True),
            fill_color="#FF4444",
            stroke_color="#CC0000",
            fill_opacity=0.2,
            stroke_width=2.5,
            range_km=range_km,
            label=f"Within {range_km:,.0f} km of target",
        )
        layers.append(envelope_layer)
        
        bounds = get_geometry_bounds(reach_envelope)
        center_lat = target_lat
        center_lon = target_lon
        description = f"Area within {range_km:,.0f} km of target"
    
    # Create target point layer
    report_progress(0.85, "Adding target marker layer...")
    target_point = Point(target_lon, target_lat)
    target_layer = RangeRingLayer(
        name=f"Target: {input_data.target_point.name}",
        geometry_type=GeometryType.POINT,
        geometry_geojson=geometry_to_geojson(target_point, fix_antimeridian=False),
        fill_color="#FFFF00",  # Yellow for visibility
        stroke_color="#FF0000",
        fill_opacity=1.0,
        stroke_width=4.0,
        label=input_data.target_point.name,
    )
    layers.append(target_layer)
    
    # Calculate processing time
    report_progress(0.90, "Computing processing statistics...")
    processing_time = (time.time() - start_time) * 1000
    
    # Create metadata
    report_progress(0.93, "Building export metadata...")
    metadata = ExportMetadata(
        tool_type=OutputType.REVERSE_RANGE_RING,
        vertex_count=count_vertices(reach_envelope),
        processing_time_ms=processing_time,
        resolution=input_data.resolution,
        geodesic_method="geographiclib",
        range_km=range_km,
        range_classification=range_class.value if range_class else None,
        origin_name=input_data.target_point.name,
        origin_type="target_point",
    )
    
    report_progress(0.96, "Creating output object...")
    title = "Reverse Range Ring"
    if input_data.weapon_system:
        title = f"{input_data.weapon_system} Launch Envelope"
    
    subtitle = f"Target: {input_data.target_point.name}"
    if threat_country_name:
        subtitle = f"Target: {input_data.target_point.name} | Shooter: {threat_country_name}"
    
    report_progress(1.0, "Complete!")
    return RangeRingOutput(
        output_type=OutputType.REVERSE_RANGE_RING,
        title=title,
        subtitle=subtitle,
        description=description,
        layers=layers,
        center_latitude=center_lat,
        center_longitude=center_lon,
        bbox=bounds,
        metadata=metadata,
    )


def calculate_minimum_distance(
    input_data: MinimumRangeRingInput,
    geometry_a: BaseGeometry,
    geometry_b: BaseGeometry,
    location_a_name: str = "Location A",
    location_b_name: str = "Location B",
    progress_callback: ProgressCallback = None,
) -> tuple[RangeRingOutput, MinimumDistanceResult]:
    """
    Calculate the minimum distance between two locations (countries or cities).
    
    Args:
        input_data: Input parameters
        geometry_a: Geometry of first location (country polygon or city point)
        geometry_b: Geometry of second location (country polygon or city point)
        location_a_name: Name of first location
        location_b_name: Name of second location
        progress_callback: Optional callback for progress updates (progress: float 0-1, status: str)
        
    Returns:
        Tuple of (RangeRingOutput, MinimumDistanceResult)
    """
    def report_progress(pct: float, status: str):
        if progress_callback:
            progress_callback(pct, status)
    
    start_time = time.time()
    report_progress(0.0, "Initializing minimum distance calculation...")
    
    report_progress(0.05, f"Loading geometry for {location_a_name}...")
    report_progress(0.10, f"Loading geometry for {location_b_name}...")
    
    # Find closest points
    report_progress(0.15, "Sampling boundary coordinates...")
    report_progress(0.25, "Computing geodesic distances between all point pairs...")
    point_a, point_b, distance_km = find_closest_points(geometry_a, geometry_b)
    report_progress(0.50, f"Minimum distance found: {distance_km:,.1f} km")
    
    layers = []
    
    # Create minimum distance line
    report_progress(0.55, "Creating geodesic line between closest points...")
    if input_data.show_minimum_line:
        line = geodesic_line(
            point_a[0], point_a[1],
            point_b[0], point_b[1],
            num_points=100
        )
        
        line_layer = RangeRingLayer(
            name=f"Minimum Distance: {distance_km:,.1f} km",
            geometry_type=GeometryType.LINE_STRING,
            geometry_geojson=geometry_to_geojson(line),
            fill_color=None,
            stroke_color="#FF0000",
            fill_opacity=0,
            stroke_width=3.0,
            range_km=distance_km,
            label=f"{distance_km:,.1f} km",
        )
        layers.append(line_layer)
    report_progress(0.65, "Geodesic line created")
    
    # Create point markers
    report_progress(0.70, f"Creating marker for closest point on {location_a_name}...")
    point_a_geom = Point(point_a[1], point_a[0])
    point_b_geom = Point(point_b[1], point_b[0])
    
    point_a_layer = RangeRingLayer(
        name=f"Closest point on {location_a_name}",
        geometry_type=GeometryType.POINT,
        geometry_geojson=geometry_to_geojson(point_a_geom),
        fill_color="#3366CC",
        stroke_color="#000066",
        fill_opacity=1.0,
        stroke_width=2.0,
    )
    
    report_progress(0.75, f"Creating marker for closest point on {location_b_name}...")
    point_b_layer = RangeRingLayer(
        name=f"Closest point on {location_b_name}",
        geometry_type=GeometryType.POINT,
        geometry_geojson=geometry_to_geojson(point_b_geom),
        fill_color="#CC3366",
        stroke_color="#660033",
        fill_opacity=1.0,
        stroke_width=2.0,
    )
    
    layers.extend([point_a_layer, point_b_layer])
    report_progress(0.80, "Point markers created")
    
    # Calculate center and bounds
    report_progress(0.85, "Calculating map bounds...")
    combined = unary_union([geometry_a, geometry_b])
    bounds = get_geometry_bounds(combined)
    center_lat = (point_a[0] + point_b[0]) / 2
    center_lon = (point_a[1] + point_b[1]) / 2
    
    # Calculate processing time
    report_progress(0.90, "Computing processing statistics...")
    processing_time = (time.time() - start_time) * 1000
    
    # Create metadata
    report_progress(0.93, "Building export metadata...")
    metadata = ExportMetadata(
        tool_type=OutputType.MINIMUM_RANGE_RING,
        processing_time_ms=processing_time,
        geodesic_method="geographiclib",
        range_km=distance_km,
        origin_name=location_a_name,
    )
    
    report_progress(0.96, "Creating output object...")
    output = RangeRingOutput(
        output_type=OutputType.MINIMUM_RANGE_RING,
        title="Minimum Distance Analysis",
        subtitle=f"{location_a_name} to {location_b_name}",
        description=f"Minimum geodesic distance: {distance_km:,.1f} km",
        layers=layers,
        center_latitude=center_lat,
        center_longitude=center_lon,
        bbox=bounds,
        metadata=metadata,
    )
    
    result = MinimumDistanceResult(
        country_a_code=input_data.country_code_a or "",
        country_b_code=input_data.country_code_b or "",
        country_a_name=location_a_name,
        country_b_name=location_b_name,
        distance_km=distance_km,
        point_a_lat=point_a[0],
        point_a_lon=point_a[1],
        point_b_lat=point_b[0],
        point_b_lon=point_b[1],
    )
    
    report_progress(1.0, "Complete!")
    return output, result


def generate_custom_poi_range_ring(
    input_data: CustomPOIRangeRingInput,
) -> RangeRingOutput:
    """
    Generate range rings from custom points of interest.
    Supports donut (ring with hole) for min/max ranges.
    
    Args:
        input_data: Input parameters including POIs and ranges
        
    Returns:
        RangeRingOutput containing the generated range ring(s)
    """
    start_time = time.time()
    
    # Convert ranges to kilometers
    max_range_km = convert_to_km(input_data.max_range_value, input_data.range_unit)
    min_range_km = convert_to_km(input_data.min_range_value, input_data.range_unit) if input_data.min_range_value else 0
    
    range_class = classify_range(max_range_km)
    
    layers = []
    all_geometries = []
    
    # Generate rings for each POI
    for poi in input_data.points_of_interest:
        if min_range_km > 0:
            # Create donut
            ring_geometry = create_geodesic_donut(
                poi.latitude, poi.longitude,
                min_range_km, max_range_km,
                num_points=360 if input_data.resolution == "high" else 180
            )
        else:
            # Create solid circle
            ring_geometry = create_geodesic_circle(
                poi.latitude, poi.longitude, max_range_km,
                num_points=360 if input_data.resolution == "high" else 180
            )
        
        ring_geometry = make_geometry_valid(ring_geometry)
        all_geometries.append(ring_geometry)
        
        # Create layer for this POI
        layer_name = f"{poi.name}"
        if min_range_km > 0:
            layer_name = f"{layer_name} ({min_range_km:.0f}-{max_range_km:.0f} km)"
        else:
            layer_name = f"{layer_name} ({max_range_km:.0f} km)"
        
        layer = RangeRingLayer(
            name=layer_name,
            geometry_type=GeometryType.POLYGON,
            geometry_geojson=geometry_to_geojson(ring_geometry),
            fill_color=_get_color_for_range(max_range_km),
            stroke_color=_get_color_for_range(max_range_km),
            fill_opacity=0.2,
            stroke_width=2.0,
            range_km=max_range_km,
            label=f"{input_data.max_range_value:,.0f} {input_data.range_unit.value}",
        )
        layers.append(layer)
        
        # Add POI marker
        poi_point = Point(poi.longitude, poi.latitude)
        poi_layer = RangeRingLayer(
            name=poi.name,
            geometry_type=GeometryType.POINT,
            geometry_geojson=geometry_to_geojson(poi_point),
            fill_color="#000000",
            stroke_color="#FFFFFF",
            fill_opacity=1.0,
            stroke_width=2.0,
            label=poi.name,
        )
        layers.append(poi_layer)
    
    # Calculate center and bounds
    if len(input_data.points_of_interest) == 1:
        center_lat = input_data.points_of_interest[0].latitude
        center_lon = input_data.points_of_interest[0].longitude
    else:
        # Use centroid of all POIs
        center_lat = sum(p.latitude for p in input_data.points_of_interest) / len(input_data.points_of_interest)
        center_lon = sum(p.longitude for p in input_data.points_of_interest) / len(input_data.points_of_interest)
    
    combined = unary_union(all_geometries)
    bounds = get_geometry_bounds(combined)
    
    # Calculate processing time
    processing_time = (time.time() - start_time) * 1000
    
    # Create metadata
    metadata = ExportMetadata(
        tool_type=OutputType.CUSTOM_POI_RANGE_RING,
        point_count=len(input_data.points_of_interest),
        vertex_count=sum(count_vertices(g) for g in all_geometries),
        processing_time_ms=processing_time,
        resolution=input_data.resolution,
        geodesic_method="geographiclib",
        range_km=max_range_km,
        range_classification=range_class.value if range_class else None,
    )
    
    # Create title
    title = input_data.weapon_system or "Custom POI Range Ring"
    if min_range_km > 0:
        description = f"Range: {input_data.min_range_value:,.0f} - {input_data.max_range_value:,.0f} {input_data.range_unit.value}"
    else:
        description = f"Range: {input_data.max_range_value:,.0f} {input_data.range_unit.value}"
    
    return RangeRingOutput(
        output_type=OutputType.CUSTOM_POI_RANGE_RING,
        title=title,
        subtitle=f"{len(input_data.points_of_interest)} POI(s)",
        description=description,
        layers=layers,
        center_latitude=center_lat,
        center_longitude=center_lon,
        bbox=bounds,
        metadata=metadata,
    )
