"""
Geometry package for ORRG.
Provides geodesic geometry operations using open-source libraries.
"""

from app.geometry.utils import (
    geodesic_distance,
    geodesic_point_at_distance,
    create_geodesic_circle,
    create_geodesic_buffer,
    simplify_geometry,
    get_geometry_centroid,
    get_geometry_bounds,
    count_vertices,
)

from app.geometry.services import (
    RangeRingService,
    generate_single_range_ring,
    generate_multiple_range_rings,
    generate_reverse_range_ring,
    calculate_minimum_distance,
    generate_custom_poi_range_ring,
)

__all__ = [
    # Utils
    "geodesic_distance",
    "geodesic_point_at_distance",
    "create_geodesic_circle",
    "create_geodesic_buffer",
    "simplify_geometry",
    "get_geometry_centroid",
    "get_geometry_bounds",
    "count_vertices",
    # Services
    "RangeRingService",
    "generate_single_range_ring",
    "generate_multiple_range_rings",
    "generate_reverse_range_ring",
    "calculate_minimum_distance",
    "generate_custom_poi_range_ring",
]
