"""
Output models for ORRG analytical tools.
Standard output objects for all range ring generators.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry


class OutputType(str, Enum):
    """Type of analytical output."""
    SINGLE_RANGE_RING = "single_range_ring"
    MULTIPLE_RANGE_RING = "multiple_range_ring"
    REVERSE_RANGE_RING = "reverse_range_ring"
    MINIMUM_RANGE_RING = "minimum_range_ring"
    CUSTOM_POI_RANGE_RING = "custom_poi_range_ring"


class GeometryType(str, Enum):
    """GeoJSON geometry types."""
    POINT = "Point"
    LINE_STRING = "LineString"
    POLYGON = "Polygon"
    MULTI_POINT = "MultiPoint"
    MULTI_LINE_STRING = "MultiLineString"
    MULTI_POLYGON = "MultiPolygon"
    GEOMETRY_COLLECTION = "GeometryCollection"


class ExportMetadata(BaseModel):
    """Metadata attached to exports, especially for analyst mode."""
    output_id: UUID = Field(default_factory=uuid4, description="Unique output identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    tool_type: OutputType = Field(..., description="Type of tool that generated this output")
    crs: str = Field("EPSG:4326", description="Coordinate reference system")
    
    # Geometry metrics (analyst mode)
    point_count: Optional[int] = Field(None, description="Number of points in geometry")
    vertex_count: Optional[int] = Field(None, description="Number of vertices")
    ring_count: Optional[int] = Field(None, description="Number of rings (for polygons)")
    
    # Processing metrics (analyst mode)
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    resolution: Optional[str] = Field(None, description="Resolution setting used")
    geodesic_method: Optional[str] = Field(None, description="Geodesic calculation method")
    
    # Range information
    range_km: Optional[float] = Field(None, description="Range in kilometers")
    range_classification: Optional[str] = Field(None, description="Missile range classification")
    
    # Origin information
    origin_name: Optional[str] = Field(None, description="Name of origin (country, city, or POI)")
    origin_type: Optional[str] = Field(None, description="Type of origin")


class RangeRingLayer(BaseModel):
    """A single layer within a range ring output (e.g., one ring in a multi-ring output)."""
    layer_id: UUID = Field(default_factory=uuid4, description="Unique layer identifier")
    name: str = Field(..., description="Display name for this layer")
    geometry_type: GeometryType = Field(..., description="Type of geometry")
    geometry_geojson: dict[str, Any] = Field(..., description="GeoJSON geometry object")
    
    # Styling hints
    fill_color: Optional[str] = Field(None, description="Fill color (hex or rgba)")
    stroke_color: Optional[str] = Field(None, description="Stroke color (hex or rgba)")
    fill_opacity: float = Field(0.3, ge=0, le=1, description="Fill opacity")
    stroke_width: float = Field(2.0, ge=0, description="Stroke width in pixels")
    
    # Metadata
    range_km: Optional[float] = Field(None, description="Range in km for this layer")
    label: Optional[str] = Field(None, description="Label text for legend")

    class Config:
        arbitrary_types_allowed = True

    def to_shapely(self) -> BaseGeometry:
        """Convert the GeoJSON geometry to a Shapely geometry object."""
        return shape(self.geometry_geojson)


class RangeRingOutput(BaseModel):
    """
    Standard output object for all range ring generators.
    Contains one or more layers of geometry with associated metadata.
    """
    output_id: UUID = Field(default_factory=uuid4, description="Unique output identifier")
    output_type: OutputType = Field(..., description="Type of analytical output")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    # Title and description
    title: str = Field(..., description="Display title for the output")
    subtitle: Optional[str] = Field(None, description="Subtitle (e.g., country name)")
    description: Optional[str] = Field(None, description="Detailed description")
    
    # Geometry layers
    layers: list[RangeRingLayer] = Field(
        default_factory=list, 
        description="List of geometry layers"
    )
    
    # Origin point for map centering
    center_latitude: float = Field(..., description="Center latitude for map display")
    center_longitude: float = Field(..., description="Center longitude for map display")
    
    # Bounding box for zoom fitting [min_lon, min_lat, max_lon, max_lat]
    bbox: Optional[tuple[float, float, float, float]] = Field(
        None, description="Bounding box [min_lon, min_lat, max_lon, max_lat]"
    )
    
    # Metadata
    metadata: ExportMetadata = Field(..., description="Export and processing metadata")

    class Config:
        arbitrary_types_allowed = True

    def get_combined_geometry(self) -> Optional[BaseGeometry]:
        """Get a combined Shapely geometry of all layers."""
        from shapely.ops import unary_union
        
        geometries = [layer.to_shapely() for layer in self.layers if layer.geometry_geojson]
        if not geometries:
            return None
        return unary_union(geometries)

    def to_geojson_feature_collection(self) -> dict[str, Any]:
        """Convert output to a GeoJSON FeatureCollection."""
        features = []
        for layer in self.layers:
            feature = {
                "type": "Feature",
                "id": str(layer.layer_id),
                "properties": {
                    "name": layer.name,
                    "label": layer.label,
                    "range_km": layer.range_km,
                    "fill_color": layer.fill_color,
                    "stroke_color": layer.stroke_color,
                    "fill_opacity": layer.fill_opacity,
                    "stroke_width": layer.stroke_width,
                },
                "geometry": layer.geometry_geojson,
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "output_id": str(self.output_id),
                "output_type": self.output_type.value,
                "title": self.title,
                "subtitle": self.subtitle,
                "created_at": self.created_at.isoformat(),
                "crs": self.metadata.crs,
            },
        }


class MinimumDistanceResult(BaseModel):
    """Result from minimum distance calculation between two countries."""
    country_a_code: str = Field(..., description="ISO3 code for first country")
    country_b_code: str = Field(..., description="ISO3 code for second country")
    country_a_name: str = Field(..., description="Name of first country")
    country_b_name: str = Field(..., description="Name of second country")
    
    # Minimum distance
    distance_km: float = Field(..., description="Minimum distance in kilometers")
    
    # Closest points
    point_a_lat: float = Field(..., description="Latitude of closest point on country A")
    point_a_lon: float = Field(..., description="Longitude of closest point on country A")
    point_b_lat: float = Field(..., description="Latitude of closest point on country B")
    point_b_lon: float = Field(..., description="Longitude of closest point on country B")


class AnalyticalResult(BaseModel):
    """
    Container for analytical results that may include multiple outputs.
    Used for stacking outputs from the same or different tools.
    """
    result_id: UUID = Field(default_factory=uuid4, description="Unique result identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    # Outputs
    outputs: list[RangeRingOutput] = Field(
        default_factory=list,
        description="List of range ring outputs"
    )
    
    # Session information
    session_id: Optional[UUID] = Field(None, description="Session identifier")
    user_mode: str = Field("general", description="User mode: 'general' or 'analyst'")

    def add_output(self, output: RangeRingOutput) -> None:
        """Add an output to the result stack."""
        self.outputs.append(output)

    def remove_output(self, output_id: UUID) -> bool:
        """Remove an output by ID. Returns True if found and removed."""
        for i, output in enumerate(self.outputs):
            if output.output_id == output_id:
                self.outputs.pop(i)
                return True
        return False

    def clear_outputs(self) -> None:
        """Clear all outputs."""
        self.outputs.clear()

    def get_combined_bbox(self) -> Optional[tuple[float, float, float, float]]:
        """Get the combined bounding box of all outputs."""
        if not self.outputs:
            return None
        
        min_lon = float('inf')
        min_lat = float('inf')
        max_lon = float('-inf')
        max_lat = float('-inf')
        
        for output in self.outputs:
            if output.bbox:
                min_lon = min(min_lon, output.bbox[0])
                min_lat = min(min_lat, output.bbox[1])
                max_lon = max(max_lon, output.bbox[2])
                max_lat = max(max_lat, output.bbox[3])
        
        if min_lon == float('inf'):
            return None
        
        return (min_lon, min_lat, max_lon, max_lat)
