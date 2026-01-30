"""
PyDeck adapter for ORRG.
Provides map rendering using pydeck for interactive visualization.
"""

from typing import Any, Optional

import pydeck as pdk

from app.models.outputs import (
    RangeRingOutput,
    RangeRingLayer,
    GeometryType,
    OutputType,
)


# Map style options
MAP_STYLES = {
    "light": "mapbox://styles/mapbox/light-v10",
    "dark": "mapbox://styles/mapbox/dark-v10",
    "satellite": "mapbox://styles/mapbox/satellite-v9",
    "streets": "mapbox://styles/mapbox/streets-v11",
    "outdoors": "mapbox://styles/mapbox/outdoors-v11",
}

# Default style (works without Mapbox token)
DEFAULT_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
DARK_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"


def hex_to_rgba(hex_color: str, opacity: float = 1.0) -> list[int]:
    """
    Convert hex color to RGBA list.
    
    Args:
        hex_color: Hex color string (e.g., "#FF0000")
        opacity: Opacity value (0-1)
        
    Returns:
        List of [R, G, B, A] values (0-255)
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    a = int(opacity * 255)
    
    return [r, g, b, a]


# Minimum zoom level to prevent world repetition (1.0 shows ~one full world)
MIN_ZOOM_LEVEL = 1.0
MAX_ZOOM_LEVEL = 18.0


def get_initial_view_state(
    latitude: float = 0,
    longitude: float = 0,
    zoom: float = 2,
    bbox: Optional[tuple[float, float, float, float]] = None,
    min_zoom: float = MIN_ZOOM_LEVEL,
    max_zoom: float = MAX_ZOOM_LEVEL,
) -> pdk.ViewState:
    """
    Create an initial view state for the map.
    
    Args:
        latitude: Center latitude
        longitude: Center longitude
        zoom: Zoom level (0-20)
        bbox: Optional bounding box to fit [min_lon, min_lat, max_lon, max_lat]
        min_zoom: Minimum zoom level (prevents world repetition)
        max_zoom: Maximum zoom level
        
    Returns:
        PyDeck ViewState object
    """
    if bbox:
        # Calculate center and zoom from bounding box
        min_lon, min_lat, max_lon, max_lat = bbox
        latitude = (min_lat + max_lat) / 2
        longitude = (min_lon + max_lon) / 2
        
        # Calculate zoom based on bbox size
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        max_range = max(lat_range, lon_range)
        
        # Rough zoom calculation - enforce minimum zoom to prevent world repetition
        if max_range > 180:
            zoom = min_zoom  # Use minimum zoom instead of 0
        elif max_range > 90:
            zoom = max(1.2, min_zoom)
        elif max_range > 45:
            zoom = max(2, min_zoom)
        elif max_range > 22:
            zoom = 3
        elif max_range > 11:
            zoom = 4
        elif max_range > 5:
            zoom = 5
        elif max_range > 2.5:
            zoom = 6
        elif max_range > 1:
            zoom = 7
        else:
            zoom = 8
    
    # Ensure zoom is within bounds
    zoom = max(min_zoom, min(zoom, max_zoom))
    
    return pdk.ViewState(
        latitude=latitude,
        longitude=longitude,
        zoom=zoom,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        pitch=0,
        bearing=0,
    )


def create_polygon_layer(
    layer: RangeRingLayer,
    layer_id: str,
) -> pdk.Layer:
    """
    Create a PyDeck polygon layer from a RangeRingLayer.
    
    Args:
        layer: RangeRingLayer containing polygon geometry
        layer_id: Unique identifier for the layer
        
    Returns:
        PyDeck GeoJsonLayer
    """
    geojson_data = {
        "type": "Feature",
        "properties": {
            "name": layer.name,
            "range_km": layer.range_km,
        },
        "geometry": layer.geometry_geojson,
    }
    
    fill_color = hex_to_rgba(layer.fill_color or "#3366CC", layer.fill_opacity)
    line_color = hex_to_rgba(layer.stroke_color or "#3366CC", 1.0)
    
    return pdk.Layer(
        "GeoJsonLayer",
        id=layer_id,
        data=geojson_data,
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False,
        get_fill_color=fill_color,
        get_line_color=line_color,
        get_line_width=layer.stroke_width * 500,  # Convert to meters
        line_width_min_pixels=1,
        line_width_max_pixels=5,
    )


def create_line_layer(
    layer: RangeRingLayer,
    layer_id: str,
) -> pdk.Layer:
    """
    Create a PyDeck line layer from a RangeRingLayer.
    
    Args:
        layer: RangeRingLayer containing line geometry
        layer_id: Unique identifier for the layer
        
    Returns:
        PyDeck GeoJsonLayer configured for lines
    """
    geojson_data = {
        "type": "Feature",
        "properties": {
            "name": layer.name,
            "range_km": layer.range_km,
        },
        "geometry": layer.geometry_geojson,
    }
    
    line_color = hex_to_rgba(layer.stroke_color or "#FF0000", 1.0)
    
    return pdk.Layer(
        "GeoJsonLayer",
        id=layer_id,
        data=geojson_data,
        pickable=True,
        stroked=True,
        filled=False,
        get_line_color=line_color,
        get_line_width=layer.stroke_width * 500,
        line_width_min_pixels=2,
        line_width_max_pixels=8,
    )


def create_point_layer(
    layer: RangeRingLayer,
    layer_id: str,
) -> pdk.Layer:
    """
    Create a PyDeck point layer from a RangeRingLayer.
    
    Args:
        layer: RangeRingLayer containing point geometry
        layer_id: Unique identifier for the layer
        
    Returns:
        PyDeck ScatterplotLayer
    """
    coords = layer.geometry_geojson.get("coordinates", [0, 0])
    
    data = [{
        "position": coords,
        "name": layer.name,
        "label": layer.label or layer.name,
    }]
    
    fill_color = hex_to_rgba(layer.fill_color or "#000000", layer.fill_opacity)
    
    return pdk.Layer(
        "ScatterplotLayer",
        id=layer_id,
        data=data,
        pickable=True,
        get_position="position",
        get_fill_color=fill_color,
        get_radius=8000,  # Radius in meters
        radius_min_pixels=5,
        radius_max_pixels=15,
    )


def create_layer_from_output(
    layer: RangeRingLayer,
    layer_index: int = 0,
) -> Optional[pdk.Layer]:
    """
    Create a PyDeck layer from a RangeRingLayer based on geometry type.
    
    Args:
        layer: RangeRingLayer to convert
        layer_index: Index for unique layer ID
        
    Returns:
        PyDeck Layer or None if geometry type is not supported
    """
    layer_id = f"layer_{layer_index}_{layer.layer_id}"
    
    if layer.geometry_type in [GeometryType.POLYGON, GeometryType.MULTI_POLYGON]:
        return create_polygon_layer(layer, layer_id)
    elif layer.geometry_type in [GeometryType.LINE_STRING, GeometryType.MULTI_LINE_STRING]:
        return create_line_layer(layer, layer_id)
    elif layer.geometry_type in [GeometryType.POINT, GeometryType.MULTI_POINT]:
        return create_point_layer(layer, layer_id)
    
    return None


def render_range_ring_output(
    output: RangeRingOutput,
    map_style: str = "light",
    height: int = 500,
) -> pdk.Deck:
    """
    Render a RangeRingOutput as a PyDeck map.
    
    Args:
        output: RangeRingOutput to render
        map_style: Map style name ('light', 'dark', 'satellite', 'streets')
        height: Map height in pixels
        
    Returns:
        PyDeck Deck object ready for display
    """
    # Create layers
    pdk_layers = []
    for i, layer in enumerate(output.layers):
        pdk_layer = create_layer_from_output(layer, i)
        if pdk_layer:
            pdk_layers.append(pdk_layer)
    
    # Get view state
    view_state = get_initial_view_state(
        latitude=output.center_latitude,
        longitude=output.center_longitude,
        bbox=output.bbox,
    )
    
    # Get map style
    style = DARK_STYLE if map_style == "dark" else DEFAULT_STYLE
    
    # Tooltip configuration (minimum-distance tool should not show a "Range" line)
    tooltip = {
        "html": "<b>{name}</b>",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white",
        },
    }
    if output.output_type != OutputType.MINIMUM_RANGE_RING:
        tooltip = {
            "html": "<b>{name}</b><br/>Range: {range_km} km",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white",
            },
        }
    
    return pdk.Deck(
        layers=pdk_layers,
        initial_view_state=view_state,
        map_style=style,
        tooltip=tooltip,
    )


def render_world_map(
    news_events: Optional[list[dict[str, Any]]] = None,
    map_style: str = "light",
    height: int = 400,
) -> pdk.Deck:
    """
    Render the world map for situational awareness with optional news events.
    
    Args:
        news_events: Optional list of news event dicts with lat, lon, title, etc.
        map_style: Map style name
        height: Map height in pixels
        
    Returns:
        PyDeck Deck object
    """
    layers = []
    
    # Add news event markers if provided
    if news_events:
        event_data = []
        for event in news_events:
            event_data.append({
                "position": [event.get("longitude", 0), event.get("latitude", 0)],
                "title": event.get("title", "Unknown Event"),
                "source": event.get("source", ""),
                "date": event.get("date", ""),
                "event_type": event.get("event_type", ""),
                "color": _get_event_color(event.get("event_type", "")),
            })
        
        if event_data:
            event_layer = pdk.Layer(
                "ScatterplotLayer",
                id="news_events",
                data=event_data,
                pickable=True,
                get_position="position",
                get_fill_color="color",
                get_radius=50000,
                radius_min_pixels=5,
                radius_max_pixels=20,
            )
            layers.append(event_layer)
    
    # Create view state (world view)
    view_state = get_initial_view_state(
        latitude=20,
        longitude=0,
        zoom=1.5,
    )
    
    # Get map style
    style = DARK_STYLE if map_style == "dark" else DEFAULT_STYLE
    
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=style,
        tooltip={
            "html": "<b>{title}</b><br/>{source}<br/>{date}",
            "style": {
                "backgroundColor": "#333",
                "color": "white",
            },
        },
    )


def _get_event_color(event_type: str) -> list[int]:
    """Get color for a news event based on type."""
    event_colors = {
        "launch": [255, 0, 0, 200],      # Red for launches
        "test": [255, 165, 0, 200],       # Orange for tests
        "exercise": [255, 255, 0, 200],   # Yellow for exercises
        "statement": [0, 100, 255, 200],  # Blue for statements
        "incident": [255, 0, 255, 200],   # Magenta for incidents
    }
    return event_colors.get(event_type.lower(), [128, 128, 128, 200])


def create_pydeck_map(
    layers: list[pdk.Layer],
    view_state: Optional[pdk.ViewState] = None,
    map_style: str = "light",
    tooltip: Optional[dict] = None,
) -> pdk.Deck:
    """
    Create a custom PyDeck map with provided layers.
    
    Args:
        layers: List of PyDeck layers
        view_state: Optional ViewState (defaults to world view)
        map_style: Map style name
        tooltip: Optional tooltip configuration
        
    Returns:
        PyDeck Deck object
    """
    if view_state is None:
        view_state = get_initial_view_state()
    
    style = DARK_STYLE if map_style == "dark" else DEFAULT_STYLE
    
    default_tooltip = {
        "html": "<b>{name}</b>",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white",
        },
    }
    
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=style,
        tooltip=tooltip or default_tooltip,
    )


def render_multiple_outputs(
    outputs: list[RangeRingOutput],
    map_style: str = "light",
) -> pdk.Deck:
    """
    Render multiple RangeRingOutputs on a single map.
    
    Args:
        outputs: List of RangeRingOutput objects
        map_style: Map style name
        
    Returns:
        PyDeck Deck object with all layers
    """
    all_layers = []
    all_bboxes = []
    
    for output_idx, output in enumerate(outputs):
        for layer_idx, layer in enumerate(output.layers):
            pdk_layer = create_layer_from_output(layer, output_idx * 100 + layer_idx)
            if pdk_layer:
                all_layers.append(pdk_layer)
        
        if output.bbox:
            all_bboxes.append(output.bbox)
    
    # Calculate combined bbox
    if all_bboxes:
        combined_bbox = (
            min(b[0] for b in all_bboxes),
            min(b[1] for b in all_bboxes),
            max(b[2] for b in all_bboxes),
            max(b[3] for b in all_bboxes),
        )
    else:
        combined_bbox = None
    
    view_state = get_initial_view_state(bbox=combined_bbox)
    
    style = DARK_STYLE if map_style == "dark" else DEFAULT_STYLE
    
    return pdk.Deck(
        layers=all_layers,
        initial_view_state=view_state,
        map_style=style,
        tooltip={
            "html": "<b>{name}</b><br/>Range: {range_km} km",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white",
            },
        },
    )
