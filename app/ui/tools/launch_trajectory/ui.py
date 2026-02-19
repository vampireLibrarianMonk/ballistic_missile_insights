"""
UI components for Launch Trajectory Visualization Tool.
Renders trajectory input, visualization, and export controls.
"""

import streamlit as st
import json
import csv
import io
from typing import Optional
from datetime import datetime

from app.ui.tools.launch_trajectory.state import (
    init_launch_trajectory_state,
    get_trajectory_state,
    get_trajectory_mode,
    get_trajectory_points,
    get_sensor_sources,
    set_trajectory_mode,
    add_trajectory_point,
    remove_trajectory_point,
    add_sensor_source,
    remove_sensor_source,
    clear_trajectory_state,
    clear_trajectory_outputs,
    add_trajectory_output,
    load_trajectory_from_data,
    validate_trajectory_for_mode,
    has_sensor_attribution,
    TrajectoryMode,
    FlightPhase,
    SensorClass,
)
from app.ui.layout.global_state import is_analyst_mode, get_map_style


# =============================================================================
# Sensor Color Palette
# =============================================================================
SENSOR_COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Blue
    "#96CEB4",  # Green
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Gold
]

PHASE_COLORS = {
    "boost": "#FF4444",
    "midcourse": "#44FF44",
    "terminal": "#4444FF",
    "unknown": "#888888",
}


# =============================================================================
# File Parsing Utilities
# =============================================================================

def parse_json_trajectory(content: str) -> tuple[list[dict], list[dict], dict, list[str]]:
    """
    Parse JSON trajectory data.
    
    Expected format:
    {
        "metadata": {...},
        "points": [...],
        "sensors": [...] (optional)
    }
    or just an array of points.
    
    Returns:
        Tuple of (points_list, sensors_list, metadata_dict, errors_list)
    """
    errors = []
    points = []
    sensors = []
    metadata = {}
    
    try:
        data = json.loads(content)
        
        if isinstance(data, list):
            # Direct array of points
            points = data
        elif isinstance(data, dict):
            points = data.get("points", data.get("trajectory", []))
            sensors = data.get("sensors", [])
            metadata = data.get("metadata", {})
        else:
            errors.append("Invalid JSON structure: expected array or object")
            return [], [], {}, errors
        
        # Validate points have required fields
        for i, point in enumerate(points):
            if "latitude" not in point and "lat" not in point:
                errors.append(f"Point {i+1}: Missing latitude field")
            if "longitude" not in point and "lon" not in point and "lng" not in point:
                errors.append(f"Point {i+1}: Missing longitude field")
            
            # Normalize field names
            if "lat" in point and "latitude" not in point:
                point["latitude"] = point["lat"]
            if "lon" in point and "longitude" not in point:
                point["longitude"] = point["lon"]
            if "lng" in point and "longitude" not in point:
                point["longitude"] = point["lng"]
                
    except json.JSONDecodeError as e:
        errors.append(f"JSON parse error: {str(e)}")
    
    return points, sensors, metadata, errors


def parse_csv_trajectory(content: str) -> tuple[list[dict], list[str]]:
    """
    Parse CSV trajectory data.
    
    Expected columns: latitude, longitude, timestamp/sequence_index, altitude (optional)
    
    Returns:
        Tuple of (points_list, errors_list)
    """
    errors = []
    points = []
    
    try:
        reader = csv.DictReader(io.StringIO(content))
        
        # Check for required columns
        fieldnames = reader.fieldnames or []
        has_lat = any(f.lower() in ["latitude", "lat"] for f in fieldnames)
        has_lon = any(f.lower() in ["longitude", "lon", "lng"] for f in fieldnames)
        
        if not has_lat:
            errors.append("CSV missing latitude column (expected: latitude or lat)")
        if not has_lon:
            errors.append("CSV missing longitude column (expected: longitude or lon)")
        
        if errors:
            return [], errors
        
        for i, row in enumerate(reader):
            point = {}
            
            # Extract latitude
            for key in ["latitude", "lat", "Latitude", "Lat"]:
                if key in row:
                    try:
                        point["latitude"] = float(row[key])
                    except ValueError:
                        errors.append(f"Row {i+2}: Invalid latitude value")
                    break
            
            # Extract longitude
            for key in ["longitude", "lon", "lng", "Longitude", "Lon", "Lng"]:
                if key in row:
                    try:
                        point["longitude"] = float(row[key])
                    except ValueError:
                        errors.append(f"Row {i+2}: Invalid longitude value")
                    break
            
            # Extract optional fields
            for key in ["timestamp", "time", "Timestamp", "Time"]:
                if key in row and row[key]:
                    point["timestamp"] = row[key]
                    break
            
            for key in ["sequence_index", "index", "seq", "Sequence", "Index"]:
                if key in row and row[key]:
                    try:
                        point["sequence_index"] = int(row[key])
                    except ValueError:
                        point["sequence_index"] = i
                    break
            
            for key in ["altitude", "alt", "Altitude", "Alt"]:
                if key in row and row[key]:
                    try:
                        point["altitude"] = float(row[key])
                    except ValueError:
                        pass
                    break
            
            for key in ["velocity", "vel", "speed", "Velocity", "Speed"]:
                if key in row and row[key]:
                    try:
                        point["velocity"] = float(row[key])
                    except ValueError:
                        pass
                    break
            
            for key in ["phase", "Phase", "flight_phase"]:
                if key in row and row[key]:
                    point["phase"] = row[key].lower()
                    break
            
            for key in ["sensor_id", "sensor", "Sensor"]:
                if key in row and row[key]:
                    point["sensor_id"] = row[key]
                    break
            
            if "latitude" in point and "longitude" in point:
                if "sequence_index" not in point:
                    point["sequence_index"] = i
                points.append(point)
                
    except Exception as e:
        errors.append(f"CSV parse error: {str(e)}")
    
    return points, errors


def extract_unique_sensors_from_points(points: list[dict]) -> list[dict]:
    """
    Extract unique sensor IDs from trajectory points.
    
    Args:
        points: List of trajectory point dictionaries
        
    Returns:
        List of sensor dictionaries with sensor_id and default values
    """
    seen_sensors = set()
    sensors = []
    
    for point in points:
        sensor_id = point.get("sensor_id")
        if sensor_id and sensor_id not in seen_sensors:
            seen_sensors.add(sensor_id)
            sensors.append({
                "sensor_id": sensor_id,
                "name": sensor_id,  # Will be updated if sensor metadata exists
                "sensor_class": "unknown",
                "detection_phase": point.get("phase"),
            })
    
    return sensors


# =============================================================================
# Sensor Color Assignment Component
# =============================================================================

def render_sensor_color_assignment() -> None:
    """
    Render the sensor color assignment panel.
    Only shown after trajectory data with sensors is loaded.
    Updates sensor colors directly in session state.
    """
    if "launch_trajectory_sensors" not in st.session_state:
        return
    
    sensors = st.session_state.launch_trajectory_sensors
    
    if not sensors:
        return
    
    st.markdown("**Assign Colors to Sensors:**")
    st.caption("Each sensor's trajectory segments will be rendered in the assigned color.")
    
    for i, sensor in enumerate(sensors):
        sensor_id = sensor.get("sensor_id", f"sensor_{i}")
        name = sensor.get("name", sensor_id)
        sensor_class = sensor.get("sensor_class", "unknown")
        detection_phase = sensor.get("detection_phase", "")
        # Handle None or missing color - must provide valid hex
        current_color = sensor.get("color") or SENSOR_COLORS[i % len(SENSOR_COLORS)]
        
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            # Sensor name and details
            phase_badge = f" [{detection_phase}]" if detection_phase else ""
            st.markdown(f"**{name}**{phase_badge}")
            st.caption(f"Class: {sensor_class}")
        
        with col2:
            # Color picker - directly update session state on change
            new_color = st.color_picker(
                f"Color",
                value=current_color,
                key=f"sensor_color_{sensor_id}_{st.session_state.launch_trajectory_form_version}",
                label_visibility="collapsed"
            )
            # Update the sensor color directly in session state
            st.session_state.launch_trajectory_sensors[i]["color"] = new_color
        
        with col3:
            # Color preview swatch
            st.markdown(
                f'<div style="background-color:{new_color};width:30px;height:30px;'
                f'border-radius:4px;border:2px solid #333;margin-top:5px;"></div>',
                unsafe_allow_html=True
            )


def render_sensor_legend_readonly() -> None:
    """Render a read-only sensor legend showing loaded sensors."""
    sensors = get_sensor_sources()
    
    if not sensors:
        return
    
    st.markdown("**Sensor Legend:**")
    
    for sensor in sensors:
        color = sensor.get("color", "#888888")
        name = sensor.get("name", "Unknown")
        sensor_class = sensor.get("sensor_class", "unknown")
        detection_phase = sensor.get("detection_phase", "")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(
                f'<div style="background-color:{color};width:20px;height:20px;'
                f'border-radius:3px;display:inline-block;border:1px solid #333;"></div>',
                unsafe_allow_html=True
            )
        with col2:
            phase_str = f" ({detection_phase})" if detection_phase else ""
            st.markdown(f"**{name}**{phase_str} - {sensor_class}")


# =============================================================================
# Trajectory Point List Component
# =============================================================================

def render_trajectory_points_list() -> None:
    """Render the list of trajectory points with edit/delete controls."""
    points = get_trajectory_points()
    
    if not points:
        st.info("No trajectory points. Upload a file or add points manually.")
        return
    
    st.markdown(f"**Trajectory Points ({len(points)}):**")
    
    # Show summary in collapsed view
    with st.expander("View/Edit Points", expanded=False):
        for i, point in enumerate(points):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                st.text(f"#{i+1}: ({point.get('latitude', 0):.4f}, {point.get('longitude', 0):.4f})")
            
            with col2:
                alt = point.get("altitude")
                if alt is not None:
                    st.text(f"Alt: {alt:.0f}m")
                else:
                    st.text("Alt: N/A")
            
            with col3:
                phase = point.get("phase", "unknown")
                sensor = point.get("sensor_id", "N/A")
                st.text(f"{phase} | {sensor}")
            
            with col4:
                if st.button("🗑️", key=f"del_point_{point.get('point_id', i)}"):
                    remove_trajectory_point(point.get("point_id"))
                    st.rerun()


# =============================================================================
# PyDeck Map Rendering
# =============================================================================

def hex_to_rgb(hex_color: str) -> list[int]:
    """Convert hex color to RGB list."""
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]


def _calculate_bearing_deg(start_point: dict, end_point: dict) -> float:
    """Calculate bearing in degrees from start to end point."""
    import math

    lat1 = math.radians(start_point.get("latitude", 0.0))
    lon1 = math.radians(start_point.get("longitude", 0.0))
    lat2 = math.radians(end_point.get("latitude", 0.0))
    lon2 = math.radians(end_point.get("longitude", 0.0))

    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def _rotate_trajectory_points(points: list[dict], rotation_degrees: float) -> list[dict]:
    """Rotate trajectory points around the trajectory center by rotation_degrees."""
    import math

    if not points or abs(rotation_degrees) < 1e-6:
        return [dict(point) for point in points]

    center_lat = sum(p.get("latitude", 0) for p in points) / len(points)
    center_lon = sum(p.get("longitude", 0) for p in points) / len(points)
    center_lat_rad = math.radians(center_lat)
    cos_lat = math.cos(center_lat_rad) or 1.0

    angle = math.radians(rotation_degrees)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    rotated = []
    for point in points:
        lon = point.get("longitude", 0.0)
        lat = point.get("latitude", 0.0)
        x = (lon - center_lon) * cos_lat
        y = lat - center_lat

        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a

        rotated_lon = (x_rot / cos_lat) + center_lon
        rotated_lat = y_rot + center_lat

        rotated_point = dict(point)
        rotated_point["longitude"] = rotated_lon
        rotated_point["latitude"] = rotated_lat
        rotated.append(rotated_point)

    return rotated


def _get_phase_boundary_points(points: list[dict]) -> list[dict]:
    """Return points where the flight phase changes between consecutive samples."""
    if not points:
        return []

    boundaries = []
    last_phase = (points[0].get("phase") or "unknown").lower()
    for point in points[1:]:
        current_phase = (point.get("phase") or "unknown").lower()
        if current_phase != last_phase:
            boundary = dict(point)
            boundary["from_phase"] = last_phase
            boundary["to_phase"] = current_phase
            boundaries.append(boundary)
            last_phase = current_phase
        else:
            last_phase = current_phase

    return boundaries


def _render_orientation_dial(base_bearing: float, rotation_offset: float) -> None:
    """Render a circular dial showing launch/impact orientation relative to cardinals."""
    import math
    import streamlit.components.v1 as components

    effective_bearing = (base_bearing + rotation_offset) % 360
    radius = 80
    center = 100

    def _marker_position(angle_deg: float) -> tuple[float, float]:
        angle_rad = math.radians(angle_deg)
        x = center + radius * math.sin(angle_rad)
        y = center - radius * math.cos(angle_rad)
        return x, y

    launch_x, launch_y = _marker_position(effective_bearing)
    impact_x, impact_y = _marker_position((effective_bearing + 180) % 360)

    dial_html = f"""
    <div style="display:flex;justify-content:center;align-items:center;">
      <svg width="200" height="200" viewBox="0 0 200 200">
        <circle cx="100" cy="100" r="80" fill="#f8f8f8" stroke="#333" stroke-width="2" />
        <text x="100" y="20" text-anchor="middle" font-size="12" fill="#333">N</text>
        <text x="185" y="105" text-anchor="middle" font-size="12" fill="#333">E</text>
        <text x="100" y="195" text-anchor="middle" font-size="12" fill="#333">S</text>
        <text x="15" y="105" text-anchor="middle" font-size="12" fill="#333">W</text>
        <line x1="100" y1="20" x2="100" y2="180" stroke="#ddd" stroke-width="1" />
        <line x1="20" y1="100" x2="180" y2="100" stroke="#ddd" stroke-width="1" />
        <circle cx="{launch_x:.1f}" cy="{launch_y:.1f}" r="6" fill="#00FF00" stroke="#333" stroke-width="1" />
        <circle cx="{impact_x:.1f}" cy="{impact_y:.1f}" r="6" fill="#FF0000" stroke="#333" stroke-width="1" />
        <text x="{launch_x:.1f}" y="{launch_y - 10:.1f}" text-anchor="middle" font-size="10" fill="#333">L</text>
        <text x="{impact_x:.1f}" y="{impact_y - 10:.1f}" text-anchor="middle" font-size="10" fill="#333">I</text>
      </svg>
    </div>
    """
    components.html(dial_html, height=220)


def render_trajectory_map_with_legend(
    points: list[dict],
    sensors: list[dict],
    height: int = 500,
    mode: TrajectoryMode = TrajectoryMode.MODE_2D,
) -> None:
    """
    Render trajectory points on a pydeck map with sensor-based coloring and integrated legend.
    Mirrors the render_map_with_legend pattern from tool_components.py.
    
    Args:
        points: List of trajectory point dictionaries
        sensors: List of sensor dictionaries with colors
        height: Map height in pixels
    """
    import pydeck as pdk
    import streamlit.components.v1 as components
    
    if not points:
        return
    
    # Build sensor color lookup - handle None colors
    sensor_colors = {}
    for i, sensor in enumerate(sensors):
        sensor_id = sensor.get("sensor_id")
        color_hex = sensor.get("color") or SENSOR_COLORS[i % len(SENSOR_COLORS)]
        sensor_colors[sensor_id] = hex_to_rgb(color_hex)
    
    # Default color for points without sensor
    default_color = [136, 136, 136]  # Gray
    
    is_3d = mode == TrajectoryMode.MODE_3D
    elevation_scale = st.session_state.launch_trajectory_elevation_scale if is_3d else 1.0

    # Build path data - group consecutive points by sensor for line segments
    path_data = []
    current_sensor = None
    current_path = []
    
    sorted_points = sorted(points, key=lambda p: p.get("sequence_index", 0))
    show_phase_boundaries = bool(st.session_state.launch_trajectory_show_phase_boundaries)
    boundary_points = _get_phase_boundary_points(sorted_points) if show_phase_boundaries else []
    
    for i, point in enumerate(sorted_points):
        sensor_id = point.get("sensor_id")
        altitude = (point.get("altitude") or 0) * elevation_scale if is_3d else 0
        coord = [point.get("longitude", 0), point.get("latitude", 0)]
        if is_3d:
            coord.append(altitude)
        
        if sensor_id != current_sensor and current_path:
            # Save current path and start new one
            color = sensor_colors.get(current_sensor, default_color)
            if len(current_path) >= 2:
                path_data.append({
                    "path": current_path,
                    "color": color + [200],  # Add alpha
                    "sensor_id": current_sensor,
                })
            # Start new path with last point of previous (for continuity)
            current_path = [current_path[-1]] if current_path else []
        
        current_path.append(coord)
        current_sensor = sensor_id
    
    # Add final path segment
    if len(current_path) >= 2:
        color = sensor_colors.get(current_sensor, default_color)
        path_data.append({
            "path": current_path,
            "color": color + [200],
            "sensor_id": current_sensor,
        })
    
    # Build point data for scatter plot - ALL points
    # Using pixel-based sizing for consistent appearance across zoom levels
    point_data = []
    for point in sorted_points:
        sensor_id = point.get("sensor_id")
        color = sensor_colors.get(sensor_id, default_color)
        altitude = (point.get("altitude") or 0) * elevation_scale if is_3d else 0
        position = [point.get("longitude", 0), point.get("latitude", 0)]
        if is_3d:
            position.append(altitude)
        point_data.append({
            "position": position,
            "color": color + [255],
            "phase": point.get("phase", "unknown"),
            "sensor_id": sensor_id or "N/A",
            "altitude": point.get("altitude") or 0,
            "name": f"Point {point.get('sequence_index', 0)}",
        })
    
    # Add special markers for launch (first point) and impact (last point)
    launch_point = sorted_points[0] if sorted_points else None
    impact_point = sorted_points[-1] if sorted_points else None
    
    marker_data = []
    if launch_point:
        launch_altitude = (launch_point.get("altitude") or 0) * elevation_scale if is_3d else 0
        launch_position = [launch_point.get("longitude", 0), launch_point.get("latitude", 0)]
        if is_3d:
            launch_position.append(launch_altitude)
        marker_data.append({
            "position": launch_position,
            "color": [0, 255, 0, 255],  # Green for launch
            "name": "Launch Point",
            "phase": launch_point.get("phase", "boost"),
            "sensor_id": launch_point.get("sensor_id", "N/A"),
            "altitude": launch_point.get("altitude") or 0,
        })
    if impact_point:
        impact_altitude = (impact_point.get("altitude") or 0) * elevation_scale if is_3d else 0
        impact_position = [impact_point.get("longitude", 0), impact_point.get("latitude", 0)]
        if is_3d:
            impact_position.append(impact_altitude)
        marker_data.append({
            "position": impact_position,
            "color": [255, 0, 0, 255],  # Red for impact
            "name": "Impact Point",
            "phase": impact_point.get("phase", "terminal"),
            "sensor_id": impact_point.get("sensor_id", "N/A"),
            "altitude": impact_point.get("altitude") or 0,
        })
    
    # Find apogee (highest altitude point)
    if sorted_points:
        apogee_point = max(sorted_points, key=lambda p: p.get("altitude", 0) or 0)
        apogee_altitude_value = apogee_point.get("altitude") or 0
        if apogee_altitude_value > 0:
            apogee_altitude = apogee_altitude_value * elevation_scale if is_3d else 0
            apogee_position = [apogee_point.get("longitude", 0), apogee_point.get("latitude", 0)]
            if is_3d:
                apogee_position.append(apogee_altitude)
            marker_data.append({
                "position": apogee_position,
                "color": [255, 165, 0, 255],  # Orange for apogee
                "name": f"Apogee ({apogee_altitude_value:,.0f}m)",
                "phase": apogee_point.get("phase", "midcourse"),
                "sensor_id": apogee_point.get("sensor_id", "N/A"),
                "altitude": apogee_altitude_value,
            })

    boundary_data = []
    for boundary in boundary_points:
        altitude = (boundary.get("altitude") or 0) * elevation_scale if is_3d else 0
        position = [boundary.get("longitude", 0), boundary.get("latitude", 0)]
        if is_3d:
            position.append(altitude)
        boundary_data.append({
            "position": position,
            "color": [255, 215, 0, 220],  # Gold for phase boundary
            "name": f"Phase Boundary ({boundary.get('from_phase')}→{boundary.get('to_phase')})",
            "phase": boundary.get("to_phase", "unknown"),
            "sensor_id": boundary.get("sensor_id", "N/A"),
            "altitude": boundary.get("altitude") or 0,
        })
    
    # Calculate view center
    avg_lat = sum(p.get("latitude", 0) for p in sorted_points) / len(sorted_points)
    avg_lon = sum(p.get("longitude", 0) for p in sorted_points) / len(sorted_points)
    
    # Create pydeck layers
    layers = []
    
    # Path layer for trajectory lines (rendered first, below points)
    if path_data:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=path_data,
                get_path="path",
                get_color="color",
                width_min_pixels=4,
                width_max_pixels=10,
                pickable=True,
                billboard=not is_3d,
            )
        )
    
    # Scatter layer for trajectory points - use pixel-based sizing for consistent appearance
    if point_data:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=point_data,
                get_position="position",
                get_color="color",
                get_radius=100,  # Base radius in meters (will be overridden by min/max pixels)
                radius_min_pixels=6,  # Minimum size in pixels
                radius_max_pixels=6,  # Maximum size in pixels (same = constant size)
                pickable=True,
                opacity=0.9,
            )
        )
    
    # Marker layer for launch/impact/apogee (rendered last, on top) - larger constant pixel size
    if marker_data:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=marker_data,
                get_position="position",
                get_color="color",
                get_radius=100,  # Base radius in meters (will be overridden by min/max pixels)
                radius_min_pixels=12,  # Larger constant pixel size for special markers
                radius_max_pixels=12,  # Same min/max = constant size regardless of zoom
                pickable=True,
            )
        )

    if boundary_data:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=boundary_data,
                get_position="position",
                get_color="color",
                get_radius=80,
                radius_min_pixels=10,
                radius_max_pixels=10,
                pickable=True,
            )
        )
    
    # Create deck
    view_state = pdk.ViewState(
        latitude=avg_lat,
        longitude=avg_lon,
        zoom=5,
        pitch=st.session_state.launch_trajectory_pitch if is_3d else 0,
        bearing=st.session_state.launch_trajectory_bearing if is_3d else 0,
    )
    
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=get_map_style(),
        tooltip={
            "html": "<b>{name}</b><br/>Phase: {phase}<br/>Sensor: {sensor_id}<br/>Alt: {altitude}m",
            "style": {"backgroundColor": "steelblue", "color": "white"},
        },
    )
    
    # Build legend HTML (mirrors tool_components.py render_map_with_legend pattern)
    legend_items_html = ""
    
    # Add sensor entries to legend
    for sensor in sensors:
        color = sensor.get("color", "#888888")
        name = sensor.get("name", "Unknown Sensor")
        phase = sensor.get("detection_phase", "")
        sensor_class = sensor.get("sensor_class", "unknown")
        phase_str = f" ({phase})" if phase else ""
        legend_items_html += f'''
        <div style="display: flex; align-items: center; margin: 4px 0;">
            <div style="width: 14px; height: 14px; background-color: {color}; 
                 opacity: 0.8; border: 2px solid {color}; border-radius: 3px; 
                 margin-right: 8px; flex-shrink: 0;"></div>
            <div style="font-size: 11px; line-height: 1.3;">
                <strong>{name}</strong>{phase_str}<br/>
                <span style="color: #555;">{sensor_class}</span>
            </div>
        </div>'''
    
    # Add special markers to legend
    legend_items_html += '''
    <div style="margin-top: 8px; border-top: 1px solid #ccc; padding-top: 8px;">
        <div style="display: flex; align-items: center; margin: 4px 0;">
            <div style="width: 14px; height: 14px; background-color: #00FF00; 
                 border: 2px solid #333; border-radius: 50%; 
                 margin-right: 8px; flex-shrink: 0;"></div>
            <div style="font-size: 11px;"><strong>Launch Point</strong></div>
        </div>
        <div style="display: flex; align-items: center; margin: 4px 0;">
            <div style="width: 14px; height: 14px; background-color: #FFA500; 
                 border: 2px solid #333; border-radius: 50%; 
                 margin-right: 8px; flex-shrink: 0;"></div>
            <div style="font-size: 11px;"><strong>Apogee</strong></div>
        </div>
        <div style="display: flex; align-items: center; margin: 4px 0;">
            <div style="width: 14px; height: 14px; background-color: #FF0000; 
                 border: 2px solid #333; border-radius: 50%; 
                 margin-right: 8px; flex-shrink: 0;"></div>
            <div style="font-size: 11px;"><strong>Impact Point</strong></div>
        </div>
    </div>'''

    if show_phase_boundaries:
        legend_items_html += '''
        <div style="margin-top: 6px;">
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <div style="width: 14px; height: 14px; background-color: #FFD700;
                     border: 2px solid #333; border-radius: 3px;
                     margin-right: 8px; flex-shrink: 0;"></div>
                <div style="font-size: 11px;"><strong>Phase Boundary</strong></div>
            </div>
        </div>'''
    
    # Get deck HTML and inject legend
    deck_html = deck.to_html(as_string=True)
    
    # Add CSS for touch interactions
    touch_css = '''
    <style>
        html, body, canvas, #deck-container, #deckgl-wrapper, .deck-tooltip {
            touch-action: manipulation !important;
        }
        canvas {
            touch-action: none !important;
        }
    </style>
    '''
    deck_html = deck_html.replace('<head>', f'<head>{touch_css}')
    
    # Map controls help overlay
    zoom_control = '''
    <div id="zoom-help" style="
        position: absolute;
        top: 10px;
        right: 10px;
        background-color: rgba(255, 255, 255, 0.9);
        border: 1px solid #999;
        border-radius: 4px;
        padding: 6px 10px;
        box-shadow: 1px 1px 4px rgba(0,0,0,0.2);
        z-index: 1000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 10px;
        color: #333;
        line-height: 1.5;
    ">
        <strong>🗺️ Controls:</strong><br/>
        Mouse wheel: Zoom<br/>
        Click + Drag: Pan<br/>
        Double-click: Zoom in
    </div>
    '''
    
    # Legend overlay
    legend_overlay = f'''
    <div id="legend-overlay" style="
        position: absolute;
        bottom: 20px;
        right: 20px;
        background-color: rgba(255, 255, 255, 0.92);
        border: 2px solid #333;
        border-radius: 6px;
        padding: 8px 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        max-width: 280px;
        max-height: calc(100% - 125px);
        overflow-y: auto;
        z-index: 1000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    ">
        <div style="font-weight: bold; margin-bottom: 6px; font-size: 12px;">🛰️ Sensor Attribution</div>
        {legend_items_html}
    </div>
    '''
    
    # Inject controls and legend
    deck_html = deck_html.replace('</body>', f'{zoom_control}</body>')
    if sensors:
        deck_html = deck_html.replace('</body>', f'{legend_overlay}</body>')
    
    # Render
    components.html(deck_html, height=height, scrolling=False)


# =============================================================================
# Export Controls (mirrors tool_components.py render_export_controls pattern)
# =============================================================================

def render_trajectory_export_controls() -> None:
    """Render export options for trajectory visualization - matches custom_poi tool pattern."""
    state = get_trajectory_state()
    points = state.get("points", [])
    # Get current sensors from session state with updated colors
    sensors = st.session_state.launch_trajectory_sensors if "launch_trajectory_sensors" in st.session_state else []
    
    # Unique ID for widget keys
    output_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Show expander with export buttons - matches custom_poi pattern
    with st.expander("📥 Download Options", expanded=False):
        projection_options = {
            "Azimuthal Equidistant (EPSG:990001)": "EPSG:990001",
            "Eckert IV (EPSG:990002)": "EPSG:990002",
        }
        selected_projection = st.selectbox(
            "Basemap Projection",
            options=list(projection_options.keys()),
            index=0,
            key="traj_export_projection",
        )
        selected_srs = projection_options[selected_projection]

        zoom_factor = st.slider(
            "Export Zoom",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
            key="traj_export_zoom",
            help="Zoom in (>1.0) or out (<1.0) for the exported map image.",
        )
        show_phase_boundaries = bool(st.session_state.launch_trajectory_show_phase_boundaries)

        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # JSON Export (replaces GeoJSON for trajectory data)
            export_data = {
                "type": "TrajectoryVisualization",
                "disclaimer": "Illustrative and analytical visualization only",
                "export_timestamp": datetime.now().isoformat(),
                "points": points,
                "sensors": sensors,
                "metadata": {
                    "point_count": len(points),
                    "sensor_count": len(sensors),
                    "has_sensor_attribution": has_sensor_attribution(),
                    "zoom_factor": zoom_factor,
                    "show_phase_boundaries": show_phase_boundaries,
                }
            }
            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                "📥 JSON",
                data=json_str,
                file_name=f"trajectory_{output_id}.json",
                mime="application/json",
                key=f"json_traj_{output_id}",
            )
        
        with col2:
            # KMZ Export
            if points:
                kmz_data = generate_trajectory_kmz(
                    points,
                    sensors,
                    rotation_degrees=0.0,
                    show_phase_boundaries=show_phase_boundaries,
                )
                st.download_button(
                    "📥 KMZ",
                    data=kmz_data,
                    file_name=f"trajectory_{output_id}.kmz",
                    mime="application/vnd.google-earth.kmz",
                    key=f"kmz_traj_{output_id}",
                )
            else:
                st.button("📥 KMZ", disabled=True, key="kmz_disabled")
        
        with col3:
            # PNG Export
            if points:
                png_data = generate_trajectory_png(
                    points,
                    sensors,
                    srs=selected_srs,
                    rotation_degrees=0.0,
                    rotate_image=False,
                    zoom_factor=zoom_factor,
                    show_phase_boundaries=show_phase_boundaries,
                )
                st.download_button(
                    "📥 PNG",
                    data=png_data,
                    file_name=f"trajectory_{output_id}.png",
                    mime="image/png",
                    key=f"png_traj_{output_id}",
                )
            else:
                st.button("📥 PNG", disabled=True, key="png_disabled")
        
        with col4:
            # PDF Export
            if points:
                pdf_data = generate_trajectory_pdf(
                    points,
                    sensors,
                    srs=selected_srs,
                    rotation_degrees=0.0,
                    rotate_image=False,
                    zoom_factor=zoom_factor,
                    show_phase_boundaries=show_phase_boundaries,
                )
                st.download_button(
                    "📥 PDF",
                    data=pdf_data,
                    file_name=f"trajectory_{output_id}.pdf",
                    mime="application/pdf",
                    key=f"pdf_traj_{output_id}",
                )
            else:
                st.button("📥 PDF", disabled=True, key="pdf_disabled")


def generate_trajectory_kmz(
    points: list[dict],
    sensors: list[dict],
    rotation_degrees: float = 0.0,
    show_phase_boundaries: bool = False,
) -> bytes:
    """
    Generate a KMZ file for the trajectory.
    
    Args:
        points: List of trajectory point dictionaries
        sensors: List of sensor dictionaries with colors
        
    Returns:
        KMZ file as bytes
    """
    import zipfile
    from io import BytesIO
    
    # Build sensor color lookup
    sensor_colors = {}
    for sensor in sensors:
        sensor_id = sensor.get("sensor_id")
        color_hex = sensor.get("color", "#888888")
        # KML uses AABBGGRR format
        hex_clean = color_hex.lstrip('#')
        r, g, b = int(hex_clean[0:2], 16), int(hex_clean[2:4], 16), int(hex_clean[4:6], 16)
        sensor_colors[sensor_id] = f"ff{b:02x}{g:02x}{r:02x}"
    
    default_color = "ff888888"
    
    # Sort points
    sorted_points = sorted(points, key=lambda p: p.get("sequence_index", 0))
    if rotation_degrees:
        sorted_points = _rotate_trajectory_points(sorted_points, rotation_degrees)
    boundary_points = _get_phase_boundary_points(sorted_points) if show_phase_boundaries else []
    
    # Build KML content
    kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>Launch Trajectory Visualization</name>
    <description>Illustrative and analytical visualization only. Does not calculate or infer launch capability.</description>
'''
    
    # Add styles for each sensor
    for sensor in sensors:
        sensor_id = sensor.get("sensor_id", "unknown")
        color = sensor_colors.get(sensor_id, default_color)
        kml_content += f'''
    <Style id="sensor_{sensor_id}">
        <LineStyle><color>{color}</color><width>4</width></LineStyle>
        <IconStyle><color>{color}</color><scale>0.8</scale></IconStyle>
    </Style>'''
    
    # Add special marker styles
    kml_content += '''
    <Style id="launch"><IconStyle><color>ff00ff00</color><scale>1.2</scale></IconStyle></Style>
    <Style id="apogee"><IconStyle><color>ff00a5ff</color><scale>1.0</scale></IconStyle></Style>
    <Style id="impact"><IconStyle><color>ff0000ff</color><scale>1.2</scale></IconStyle></Style>
    <Style id="phase_boundary"><IconStyle><color>ff00d7ff</color><scale>1.0</scale></IconStyle></Style>
'''
    
    # Build path segments by sensor
    current_sensor = None
    segment_coords = []
    segment_num = 0
    
    for point in sorted_points:
        sensor_id = point.get("sensor_id")
        coord = f"{point.get('longitude', 0)},{point.get('latitude', 0)},{point.get('altitude', 0) or 0}"
        
        if sensor_id != current_sensor and segment_coords:
            # Output previous segment
            sensor_name = current_sensor or "Unknown"
            style_id = f"sensor_{current_sensor}" if current_sensor else "sensor_unknown"
            kml_content += f'''
    <Placemark>
        <name>Segment {segment_num + 1} ({sensor_name})</name>
        <styleUrl>#{style_id}</styleUrl>
        <LineString>
            <altitudeMode>absolute</altitudeMode>
            <coordinates>{' '.join(segment_coords)}</coordinates>
        </LineString>
    </Placemark>'''
            segment_num += 1
            segment_coords = [segment_coords[-1]] if segment_coords else []
        
        segment_coords.append(coord)
        current_sensor = sensor_id
    
    # Output final segment
    if segment_coords:
        sensor_name = current_sensor or "Unknown"
        style_id = f"sensor_{current_sensor}" if current_sensor else "sensor_unknown"
        kml_content += f'''
    <Placemark>
        <name>Segment {segment_num + 1} ({sensor_name})</name>
        <styleUrl>#{style_id}</styleUrl>
        <LineString>
            <altitudeMode>absolute</altitudeMode>
            <coordinates>{' '.join(segment_coords)}</coordinates>
        </LineString>
    </Placemark>'''
    
    # Add special markers
    if sorted_points:
        launch = sorted_points[0]
        kml_content += f'''
    <Placemark>
        <name>Launch Point</name>
        <styleUrl>#launch</styleUrl>
        <Point><coordinates>{launch.get('longitude', 0)},{launch.get('latitude', 0)},{launch.get('altitude', 0) or 0}</coordinates></Point>
    </Placemark>'''
        
        impact = sorted_points[-1]
        kml_content += f'''
    <Placemark>
        <name>Impact Point</name>
        <styleUrl>#impact</styleUrl>
        <Point><coordinates>{impact.get('longitude', 0)},{impact.get('latitude', 0)},{impact.get('altitude', 0) or 0}</coordinates></Point>
    </Placemark>'''
        
        apogee = max(sorted_points, key=lambda p: p.get("altitude", 0) or 0)
        apogee_altitude_value = apogee.get("altitude") or 0
        if apogee_altitude_value > 0:
            kml_content += f'''
    <Placemark>
        <name>Apogee ({apogee_altitude_value:,.0f}m)</name>
        <styleUrl>#apogee</styleUrl>
        <Point><coordinates>{apogee.get('longitude', 0)},{apogee.get('latitude', 0)},{apogee_altitude_value}</coordinates></Point>
    </Placemark>'''

        if boundary_points:
            for boundary in boundary_points:
                kml_content += f'''
    <Placemark>
        <name>Phase Boundary ({boundary.get('from_phase')}→{boundary.get('to_phase')})</name>
        <styleUrl>#phase_boundary</styleUrl>
        <Point><coordinates>{boundary.get('longitude', 0)},{boundary.get('latitude', 0)},{boundary.get('altitude', 0) or 0}</coordinates></Point>
    </Placemark>'''
    
    kml_content += '''
</Document>
</kml>'''
    
    # Create KMZ (zipped KML)
    kmz_buffer = BytesIO()
    with zipfile.ZipFile(kmz_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', kml_content)
    kmz_buffer.seek(0)
    
    return kmz_buffer.getvalue()


ORRG_AEQD_WKT = (
    'PROJCS["ORRG Azimuthal Equidistant",'
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],' 
    'PROJECTION["Azimuthal_Equidistant"],'
    'PARAMETER["latitude_of_center",0.0],PARAMETER["longitude_of_center",0.0],'
    'PARAMETER["false_easting",0.0],PARAMETER["false_northing",0.0],'
    'UNIT["metre",1.0],AUTHORITY["EPSG","990001"]]'
)
ORRG_ECKERT_IV_WKT = (
    'PROJCS["ORRG Eckert IV",'
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],' 
    'PROJECTION["Eckert_IV"],PARAMETER["Central_Meridian",0.0],'
    'UNIT["metre",1.0],AUTHORITY["EPSG","990002"]]'
)


def _get_projection_crs(srs: str):
    from pyproj import CRS

    if srs == "EPSG:990001":
        return CRS.from_wkt(ORRG_AEQD_WKT)
    if srs == "EPSG:990002":
        return CRS.from_wkt(ORRG_ECKERT_IV_WKT)
    return CRS.from_user_input(srs)


def _project_trajectory_points(points: list[dict], srs: str) -> list[dict]:
    from pyproj import Transformer

    if srs == "EPSG:4326":
        return [{**point, "x": point.get("longitude", 0), "y": point.get("latitude", 0)} for point in points]

    transformer = Transformer.from_crs("EPSG:4326", _get_projection_crs(srs), always_xy=True)
    projected = []
    for point in points:
        lon = point.get("longitude", 0)
        lat = point.get("latitude", 0)
        x, y = transformer.transform(lon, lat)
        projected.append({**point, "x": x, "y": y})
    return projected


def _format_projection_label(srs: str) -> str:
    if srs == "EPSG:990001":
        return "ORRG Azimuthal Equidistant (EPSG:990001)"
    if srs == "EPSG:990002":
        return "ORRG Eckert IV (EPSG:990002)"
    return srs


def _fetch_trajectory_basemap(
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    width: int,
    height: int,
    srs: str = "EPSG:990001",
) -> 'PILImage.Image':
    """
    Fetch basemap from GeoServer WMS (same as custom POI tool).
    
    Args:
        min_x, min_y, max_x, max_y: Bounding box in the target SRS units
        width, height: Image dimensions in pixels
        
    Returns:
        PIL Image of the basemap
    """
    import requests
    from PIL import Image as PILImage
    from io import BytesIO
    
    GEOSERVER_WMS_URL = "http://localhost:8080/geoserver/ows"
    GEOSERVER_BASEMAP_LAYER = "ne:world"
    
    # Use custom ORRG CRS (EPSG:990001 AEQD or EPSG:990002 Eckert IV)
    params = {
        "service": "WMS",
        "version": "1.1.1",
        "request": "GetMap",
        "layers": GEOSERVER_BASEMAP_LAYER,
        "format": "image/png",
        "width": width,
        "height": height,
        "srs": srs,
        "bbox": f"{min_x},{min_y},{max_x},{max_y}",
    }
    
    try:
        r = requests.get(GEOSERVER_WMS_URL, params=params, timeout=30)
        r.raise_for_status()
        
        # Check if response is an image
        content_type = r.headers.get('Content-Type', '')
        if 'image' in content_type:
            return PILImage.open(BytesIO(r.content)).convert('RGB')
        else:
            raise Exception(f"GeoServer returned non-image: {content_type}")
    except Exception as e:
        # Fallback to light blue background
        print(f"GeoServer basemap fetch failed: {e}")
        return PILImage.new('RGB', (width, height), (212, 228, 247))


def _render_trajectory_map_image(
    points: list[dict],
    sensors: list[dict],
    width: int = 1336,
    height: int = 676,
    srs: str = "EPSG:990001",
    rotation_degrees: float = 0.0,
    rotate_image: bool = False,
    zoom_factor: float = 1.0,
    show_phase_boundaries: bool = False,
) -> bytes:
    """
    Render just the trajectory map image for embedding in SVG template.
    Uses GeoServer WMS basemap (same as custom POI tool).
    
    Args:
        points: List of trajectory point dictionaries
        sensors: List of sensor dictionaries with colors
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        PNG image as bytes
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.image import imread
    from io import BytesIO
    import numpy as np
    
    # Build sensor color lookup - handle None colors
    sensor_colors = {}
    for i, sensor in enumerate(sensors):
        sensor_id = sensor.get("sensor_id")
        color_hex = sensor.get("color") or SENSOR_COLORS[i % len(SENSOR_COLORS)]
        sensor_colors[sensor_id] = color_hex
    
    default_color = "#888888"
    
    # Sort points by sequence
    sorted_points = sorted(points, key=lambda p: p.get("sequence_index", 0))
    
    if not sorted_points:
        # Return empty image if no points
        from PIL import Image as PILImage
        img = PILImage.new('RGB', (width, height), (212, 228, 247))
        buf = BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    
    if rotation_degrees and not rotate_image:
        sorted_points = _rotate_trajectory_points(sorted_points, rotation_degrees)
    projected_points = _project_trajectory_points(sorted_points, srs)
    boundary_points = _get_phase_boundary_points(projected_points) if show_phase_boundaries else []

    # Calculate bounding box with padding to ensure entire trajectory is visible
    xs = [p.get("x", 0) for p in projected_points]
    ys = [p.get("y", 0) for p in projected_points]

    x_range = max(xs) - min(xs) if len(xs) > 1 else 1.0
    y_range = max(ys) - min(ys) if len(ys) > 1 else 1.0

    # Use larger padding to ensure all markers are visible
    pad_factor = 0.20  # 20% padding on each side
    min_pad = 0.5 if srs == "EPSG:4326" else 50000.0
    x_pad = max(x_range * pad_factor, min_pad)
    y_pad = max(y_range * pad_factor, min_pad)

    min_x = min(xs) - x_pad
    max_x = max(xs) + x_pad
    min_y = min(ys) - y_pad
    max_y = max(ys) + y_pad

    zoom_factor = max(0.1, float(zoom_factor or 1.0))
    if abs(zoom_factor - 1.0) > 1e-6:
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        half_width = (max_x - min_x) / 2 / zoom_factor
        half_height = (max_y - min_y) / 2 / zoom_factor
        min_x = center_x - half_width
        max_x = center_x + half_width
        min_y = center_y - half_height
        max_y = center_y + half_height
    
    # Adjust aspect ratio to match image dimensions
    target_ratio = width / height
    current_x_span = max_x - min_x
    current_y_span = max_y - min_y
    current_ratio = current_x_span / current_y_span
    
    if current_ratio < target_ratio:
        # Need to expand longitude range
        needed_x_span = current_y_span * target_ratio
        x_expansion = (needed_x_span - current_x_span) / 2
        min_x -= x_expansion
        max_x += x_expansion
    else:
        # Need to expand latitude range
        needed_y_span = current_x_span / target_ratio
        y_expansion = (needed_y_span - current_y_span) / 2
        min_y -= y_expansion
        max_y += y_expansion
    
    # Fetch GeoServer basemap (same as custom POI tool)
    basemap_img = _fetch_trajectory_basemap(min_x, min_y, max_x, max_y, width, height, srs=srs)
    
    # Create figure with exact dimensions for template
    dpi = 100
    fig, ax = plt.subplots(1, 1, figsize=(width/dpi, height/dpi), dpi=dpi)
    
    # Display basemap
    ax.imshow(basemap_img, extent=[min_x, max_x, min_y, max_y], aspect='auto', zorder=0)
    
    # Plot trajectory segments by sensor
    current_sensor = None
    segment_xs = []
    segment_ys = []
    
    for point in projected_points:
        sensor_id = point.get("sensor_id")
        x = point.get("x", 0)
        y = point.get("y", 0)
        
        if sensor_id != current_sensor and segment_xs:
            color = sensor_colors.get(current_sensor, default_color)
            ax.plot(segment_xs, segment_ys, color=color, linewidth=4, alpha=0.85, solid_capstyle='round', zorder=3)
            segment_xs = [segment_xs[-1]]
            segment_ys = [segment_ys[-1]]
        
        segment_xs.append(x)
        segment_ys.append(y)
        current_sensor = sensor_id
    
    if segment_xs:
        color = sensor_colors.get(current_sensor, default_color)
        ax.plot(segment_xs, segment_ys, color=color, linewidth=4, alpha=0.85, solid_capstyle='round', zorder=3)
    
    # Plot all points with sensor colors
    for point in projected_points:
        sensor_id = point.get("sensor_id")
        color = sensor_colors.get(sensor_id, default_color)
        ax.scatter(point.get("x", 0), point.get("y", 0), 
                   c=color, s=50, zorder=5, edgecolors='black', linewidth=0.5)
    
    # Plot special markers as circles with current fill colors
    if sorted_points:
        launch = projected_points[0]
        ax.scatter(launch.get("x", 0), launch.get("y", 0), 
                   c='#00FF00', s=300, marker='o', zorder=10, edgecolors='black', linewidth=2)
        
        impact = projected_points[-1]
        ax.scatter(impact.get("x", 0), impact.get("y", 0), 
                   c='#FF0000', s=300, marker='o', zorder=10, edgecolors='black', linewidth=2)
        
        apogee = max(projected_points, key=lambda p: p.get("altitude", 0) or 0)
        apogee_altitude_value = apogee.get("altitude") or 0
        if apogee_altitude_value > 0:
            ax.scatter(apogee.get("x", 0), apogee.get("y", 0), 
                       c='#FFA500', s=250, marker='o', zorder=10, edgecolors='black', linewidth=2)

    if boundary_points:
        for boundary in boundary_points:
            ax.scatter(boundary.get("x", 0), boundary.get("y", 0),
                       c='#FFD700', s=140, marker='s', zorder=9, edgecolors='black', linewidth=1.5)
    
    # Set axis limits to match basemap extent
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    
    # Remove axes for clean map image
    ax.set_axis_off()
    
    plt.tight_layout(pad=0)
    
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    
    if rotate_image and abs(rotation_degrees) > 1e-6:
        from PIL import Image as PILImage
        img = PILImage.open(buf).convert('RGBA')
        rotated = img.rotate(-rotation_degrees, resample=PILImage.BICUBIC, expand=False)
        rotated_rgb = PILImage.new('RGB', rotated.size, (255, 255, 255))
        rotated_rgb.paste(rotated, mask=rotated.split()[3])
        output_buf = BytesIO()
        rotated_rgb.save(output_buf, format='PNG')
        return output_buf.getvalue()

    return buf.getvalue()


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def _render_trajectory_svg_with_template(
    points: list[dict],
    sensors: list[dict],
    title: str = "(U) Launch Trajectory Visualization",
    subtitle: str = "",
    classification: str = "UNCLASSIFIED",
    created_by: str = "ORRG",
    srs: str = "EPSG:990001",
    rotation_degrees: float = 0.0,
    rotate_image: bool = False,
    zoom_factor: float = 1.0,
    show_phase_boundaries: bool = False,
) -> str:
    """
    Render trajectory using the professional IC-style SVG template.
    Uses ElementTree for proper legend positioning (expands upward like custom POI tool).
    
    Args:
        points: List of trajectory point dictionaries
        sensors: List of sensor dictionaries with colors
        title: Title line 1
        subtitle: Title line 2
        classification: Classification marking
        created_by: Creator attribution
        
    Returns:
        SVG string with substituted values
    """
    import base64
    from pathlib import Path
    from xml.etree import ElementTree as ET
    
    # Legend layout constants (matching png.py)
    LEGEND_X = 40
    LEGEND_BOTTOM_Y = 780  # Fixed bottom edge position
    LEGEND_PADDING_TOP = 12
    LEGEND_ITEM_HEIGHT = 22
    LEGEND_SWATCH_SIZE = 14
    LEGEND_TEXT_X = 40
    LEGEND_RIGHT_PADDING = 15
    
    # Template path
    template_path = Path(__file__).parent.parent.parent.parent / "templates" / "output-template.svg"
    
    with open(template_path, "r") as f:
        svg_content = f.read()
    
    # Render the map image and encode as base64
    map_bytes = _render_trajectory_map_image(
        points,
        sensors,
        srs=srs,
        rotation_degrees=rotation_degrees,
        rotate_image=rotate_image,
        zoom_factor=zoom_factor,
        show_phase_boundaries=show_phase_boundaries,
    )
    map_base64 = base64.b64encode(map_bytes).decode("utf-8")
    map_data_uri = f"data:image/png;base64,{map_base64}"
    
    # Perform text substitutions first (before ElementTree parsing)
    # Title block
    svg_content = svg_content.replace(
        '>(U) Threat to United States</text>',
        f'>{_escape_xml(title)}</text>'
    )
    svg_content = svg_content.replace(
        '>CSS-10 Mod 2 ICBM (11,200 km)</text>',
        f'>{_escape_xml(subtitle)}</text>'
    )
    
    # Classification
    svg_content = svg_content.replace('>UNCLASSIFIED</text>', f'>{_escape_xml(classification)}</text>')
    
    # Map image
    svg_content = svg_content.replace(
        'xlink:href="data:image/png;base64,REPLACE_WITH_BASE64_OR_SET_HREF"',
        f'xlink:href="{map_data_uri}"'
    )
    
    # Created by
    svg_content = svg_content.replace(
        '>Created By: Mr. P</text>',
        f'>Created By: {_escape_xml(created_by)}</text>'
    )
    
    # Source lines
    svg_content = svg_content.replace(
        '>Source: DOD, 2015 Annual Report to Congress: China, 07 April 2015</text>',
        f'>Source: Illustrative and Analytical Visualization Only</text>'
    )
    svg_content = svg_content.replace(
        '>DoS, Simplified World Polygons, March 2013</text>',
        f'>Points: {len(points)} | Sensors: {len(sensors)} | {datetime.now().strftime("%Y-%m-%d %H:%M")}</text>'
    )
    
    # Coordinate system
    projection_label = _format_projection_label(srs)
    svg_content = svg_content.replace(
        '>Coordinate System: Eckert III (world) (Central Meridian 104.0)</text>',
        f'>Coordinate System: {projection_label}</text>'
    )
    
    # Attribution
    svg_content = svg_content.replace(
        '>Sources: Esri, HERE, DeLorme, Intermap, increment P Corp, GEBCO, USGS, FAO, NPS, NRCan, ...</text>',
        '>DISCLAIMER: This visualization is illustrative and analytical only. It does not calculate or infer launch capability.</text>'
    )
    
    # Build legend items list (sensors + special markers)
    legend_items = []
    
    # Add sensor entries
    for i, sensor in enumerate(sensors):
        color = sensor.get("color") or SENSOR_COLORS[i % len(SENSOR_COLORS)]
        name = sensor.get("name", "Unknown")
        phase = sensor.get("detection_phase", "")
        label = f"{name} ({phase})" if phase else name
        legend_items.append({
            "name": label,
            "color": color,
            "is_point": False,  # Use rectangle swatch
        })
    
    # Add special markers
    legend_items.append({"name": "Launch Point", "color": "#00FF00", "is_point": True})
    legend_items.append({"name": "Apogee", "color": "#FFA500", "is_point": True})
    legend_items.append({"name": "Impact Point", "color": "#FF0000", "is_point": True})
    if show_phase_boundaries:
        legend_items.append({"name": "Phase Boundary", "color": "#FFD700", "is_point": False})
    
    # Calculate legend dimensions
    num_items = len(legend_items)
    legend_height = LEGEND_PADDING_TOP + (num_items * LEGEND_ITEM_HEIGHT) + 10
    
    # Calculate max text width (estimate)
    max_text_width = max(len(item["name"]) * 7 for item in legend_items) if legend_items else 100
    legend_width = int(LEGEND_TEXT_X + max_text_width + LEGEND_RIGHT_PADDING)
    legend_width = max(legend_width, 150)
    
    # Calculate Y position so bottom edge stays fixed (expands upward)
    MAX_LEGEND_HEIGHT = 600
    legend_height = min(legend_height, MAX_LEGEND_HEIGHT)
    legend_top_y = LEGEND_BOTTOM_Y - legend_height
    
    # Parse SVG and update legend positioning using ElementTree
    root = ET.fromstring(svg_content)
    
    # Update the legend group's transform to expand upward
    legend_group = root.find(".//*[@id='lower_left_callout']")
    if legend_group is not None:
        legend_group.set("transform", f"translate({LEGEND_X},{legend_top_y})")
    
    # Update callout box dimensions
    callout_box = root.find(".//*[@id='callout_box']")
    if callout_box is not None:
        callout_box.set("width", str(legend_width))
        callout_box.set("height", str(legend_height))

    # Update coordinate system box to expand left and stay within map frame
    coordinate_group = root.find(".//*[@id='coordinate_box_group']")
    coordinate_box = root.find(".//*[@id='coordinate_box']")
    coordinate_line1 = root.find(".//*[@id='coordinate_line1']")
    coordinate_line2 = root.find(".//*[@id='coordinate_line2']")
    if coordinate_group is not None and coordinate_box is not None:
        coord_line1_text = f"Coordinate System: {projection_label}"
        coord_line2_text = "Datum: D WGS 1984"
        coord_text_width = max(len(coord_line1_text), len(coord_line2_text)) * 7 + 24
        coord_box_width = max(coord_text_width, 300)
        coord_right_edge = 1370
        coord_x = coord_right_edge - coord_box_width
        coordinate_group.set("transform", f"translate({coord_x},710)")
        coordinate_box.set("width", str(coord_box_width))
        if coordinate_line1 is not None:
            coordinate_line1.set("x", str(coord_box_width - 12))
            coordinate_line1.set("text-anchor", "end")
            coordinate_line1.text = coord_line1_text
        if coordinate_line2 is not None:
            coordinate_line2.set("x", str(coord_box_width - 12))
            coordinate_line2.set("text-anchor", "end")
            coordinate_line2.text = coord_line2_text
    
    # Replace legend items container with new content
    legend_container = root.find(".//*[@id='legend_items_container']")
    if legend_container is not None:
        # Clear existing children
        for child in list(legend_container):
            legend_container.remove(child)
        
        # Add new legend items
        for i, item in enumerate(legend_items):
            y_offset = LEGEND_PADDING_TOP + i * LEGEND_ITEM_HEIGHT
            
            if item["is_point"]:
                # Circle for point markers (launch/apogee/impact)
                swatch = ET.SubElement(legend_container, "circle")
                swatch.set("cx", "25")
                swatch.set("cy", str(y_offset + 7))
                swatch.set("r", "7")
                swatch.set("fill", item["color"])
                swatch.set("stroke", "#333")
                swatch.set("stroke-width", "1.5")
            else:
                # Rectangle for sensor swatches
                swatch = ET.SubElement(legend_container, "rect")
                swatch.set("x", "18")
                swatch.set("y", str(y_offset))
                swatch.set("width", str(LEGEND_SWATCH_SIZE))
                swatch.set("height", str(LEGEND_SWATCH_SIZE))
                swatch.set("fill", item["color"])
                swatch.set("stroke", "#333")
                swatch.set("stroke-width", "1")
                swatch.set("rx", "2")
                swatch.set("opacity", "0.9")
            
            text_el = ET.SubElement(legend_container, "text")
            text_el.set("x", str(LEGEND_TEXT_X))
            text_el.set("y", str(y_offset + 11))
            text_el.set("class", "header-text box-text")
            text_el.text = item["name"]
    
    svg_content = ET.tostring(root, encoding="unicode")
    
    # Re-add XML declaration
    if not svg_content.startswith('<?xml'):
        svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content
    
    return svg_content


def generate_trajectory_pdf(
    points: list[dict],
    sensors: list[dict],
    srs: str = "EPSG:990001",
    rotation_degrees: float = 0.0,
    rotate_image: bool = False,
    zoom_factor: float = 1.0,
    show_phase_boundaries: bool = False,
) -> bytes:
    """
    Generate a PDF of the trajectory using the SVG template (matches other tools' style).
    
    Args:
        points: List of trajectory point dictionaries
        sensors: List of sensor dictionaries with colors
        
    Returns:
        PDF file as bytes
    """
    from io import BytesIO
    
    # Get metadata for title
    metadata = st.session_state.get("launch_trajectory_file_metadata", {})
    title = metadata.get("name", "(U) Launch Trajectory Visualization")
    missile_class = metadata.get("missile_class", "")
    range_km = metadata.get("estimated_range_km", "")
    subtitle = f"{missile_class} ({range_km} km)" if missile_class and range_km else missile_class or ""
    
    try:
        import cairosvg
        from PIL import Image
        
        # Render SVG with template
        svg_content = _render_trajectory_svg_with_template(
            points,
            sensors,
            title=title,
            subtitle=subtitle,
            srs=srs,
            rotation_degrees=rotation_degrees,
            rotate_image=rotate_image,
            zoom_factor=zoom_factor,
            show_phase_boundaries=show_phase_boundaries,
        )
        
        # Convert SVG to PDF
        pdf_bytes = cairosvg.svg2pdf(
            bytestring=svg_content.encode("utf-8"),
            output_width=1400,
            output_height=900,
        )
        
        return pdf_bytes
        
    except ImportError:
        # Fallback to matplotlib PDF if cairosvg not available
        return _fallback_trajectory_pdf(
            points,
            sensors,
            title,
            subtitle,
            rotation_degrees=rotation_degrees,
            show_phase_boundaries=show_phase_boundaries,
        )


def _fallback_trajectory_pdf(
    points: list[dict],
    sensors: list[dict],
    title: str,
    subtitle: str,
    rotation_degrees: float = 0.0,
    show_phase_boundaries: bool = False,
) -> bytes:
    """Fallback PDF generation using matplotlib."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.backends.backend_pdf import PdfPages
    from io import BytesIO
    
    sensor_colors = {s.get("sensor_id"): s.get("color", "#888888") for s in sensors}
    default_color = "#888888"
    sorted_points = sorted(points, key=lambda p: p.get("sequence_index", 0))
    boundary_points = _get_phase_boundary_points(sorted_points) if show_phase_boundaries else []
    if rotation_degrees:
        sorted_points = _rotate_trajectory_points(sorted_points, rotation_degrees)
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 9))
    ax.set_facecolor("#e8f4f8")
    
    # Plot trajectory
    current_sensor = None
    segment_lons, segment_lats = [], []
    
    for point in sorted_points:
        sensor_id = point.get("sensor_id")
        lon, lat = point.get("longitude", 0), point.get("latitude", 0)
        
        if sensor_id != current_sensor and segment_lons:
            color = sensor_colors.get(current_sensor, default_color)
            ax.plot(segment_lons, segment_lats, color=color, linewidth=3, alpha=0.8)
            segment_lons, segment_lats = [segment_lons[-1]], [segment_lats[-1]]
        
        segment_lons.append(lon)
        segment_lats.append(lat)
        current_sensor = sensor_id
    
    if segment_lons:
        color = sensor_colors.get(current_sensor, default_color)
        ax.plot(segment_lons, segment_lats, color=color, linewidth=3, alpha=0.8)
    
    for point in sorted_points:
        sensor_id = point.get("sensor_id")
        color = sensor_colors.get(sensor_id, default_color)
        ax.scatter(point.get("longitude", 0), point.get("latitude", 0), 
                   c=color, s=40, zorder=5, edgecolors='black', linewidth=0.5)
    
    if sorted_points:
        launch = sorted_points[0]
        ax.scatter(launch.get("longitude", 0), launch.get("latitude", 0), 
                   c='#00FF00', s=250, marker='^', zorder=10, edgecolors='black', linewidth=2)
        impact = sorted_points[-1]
        ax.scatter(impact.get("longitude", 0), impact.get("latitude", 0), 
                   c='#FF0000', s=250, marker='v', zorder=10, edgecolors='black', linewidth=2)
        apogee = max(sorted_points, key=lambda p: p.get("altitude", 0) or 0)
        if apogee.get("altitude", 0) > 0:
            ax.scatter(apogee.get("longitude", 0), apogee.get("latitude", 0), 
                       c='#FFA500', s=180, marker='D', zorder=10, edgecolors='black', linewidth=2)

    if boundary_points:
        for boundary in boundary_points:
            ax.scatter(boundary.get("longitude", 0), boundary.get("latitude", 0),
                       c='#FFD700', s=120, marker='s', zorder=9, edgecolors='black', linewidth=1.5)
    
    legend_handles = []
    for sensor in sensors:
        patch = mpatches.Patch(color=sensor.get("color", "#888888"), 
                               label=f"{sensor.get('name', 'Unknown')} ({sensor.get('detection_phase', '')})")
        legend_handles.append(patch)
    legend_handles.append(plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#00FF00', 
                                      markersize=12, markeredgecolor='black', label='Launch Point'))
    legend_handles.append(plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='#FFA500', 
                                      markersize=10, markeredgecolor='black', label='Apogee'))
    legend_handles.append(plt.Line2D([0], [0], marker='v', color='w', markerfacecolor='#FF0000', 
                                      markersize=12, markeredgecolor='black', label='Impact Point'))
    if boundary_points:
        legend_handles.append(plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#FFD700',
                                          markersize=10, markeredgecolor='black', label='Phase Boundary'))
    
    ax.legend(handles=legend_handles, loc='upper left', fontsize=9, framealpha=0.9)
    ax.set_xlabel('Longitude', fontsize=11)
    ax.set_ylabel('Latitude', fontsize=11)
    ax.set_title(f'{title}\n{subtitle}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    fig.text(0.5, 0.02, 'DISCLAIMER: This visualization is illustrative and analytical only.', 
             ha='center', fontsize=9, style='italic', color='gray')
    
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    
    buf = BytesIO()
    with PdfPages(buf) as pdf:
        pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    return buf.getvalue()


def generate_trajectory_png(
    points: list[dict],
    sensors: list[dict],
    srs: str = "EPSG:990001",
    rotation_degrees: float = 0.0,
    rotate_image: bool = False,
    zoom_factor: float = 1.0,
    show_phase_boundaries: bool = False,
) -> bytes:
    """
    Generate a PNG image of the trajectory using the SVG template (matches other tools' style).
    
    Args:
        points: List of trajectory point dictionaries
        sensors: List of sensor dictionaries with colors
        
    Returns:
        PNG image as bytes
    """
    from io import BytesIO
    
    # Get metadata for title
    metadata = st.session_state.get("launch_trajectory_file_metadata", {})
    title = metadata.get("name", "(U) Launch Trajectory Visualization")
    missile_class = metadata.get("missile_class", "")
    range_km = metadata.get("estimated_range_km", "")
    subtitle = f"{missile_class} ({range_km} km)" if missile_class and range_km else missile_class or ""
    
    try:
        import cairosvg
        from PIL import Image
        
        # Render SVG with template
        svg_content = _render_trajectory_svg_with_template(
            points,
            sensors,
            title=title,
            subtitle=subtitle,
            srs=srs,
            rotation_degrees=rotation_degrees,
            rotate_image=rotate_image,
            zoom_factor=zoom_factor,
            show_phase_boundaries=show_phase_boundaries,
        )
        
        # Convert SVG to PNG with white background
        png_bytes = cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            output_width=1400,
            output_height=900,
            dpi=100,
            background_color="white",
        )
        
        # Ensure no alpha channel in final output
        buffer = BytesIO(png_bytes)
        img = Image.open(buffer)
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        output_buffer = BytesIO()
        img.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
        
    except ImportError:
        # Fallback to matplotlib if cairosvg not available
        return _fallback_trajectory_png(
            points,
            sensors,
            title,
            subtitle,
            rotation_degrees=rotation_degrees,
            show_phase_boundaries=show_phase_boundaries,
        )


def _fallback_trajectory_png(
    points: list[dict],
    sensors: list[dict],
    title: str,
    subtitle: str,
    rotation_degrees: float = 0.0,
    show_phase_boundaries: bool = False,
) -> bytes:
    """Fallback PNG generation using matplotlib."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from io import BytesIO
    
    sensor_colors = {s.get("sensor_id"): s.get("color", "#888888") for s in sensors}
    default_color = "#888888"
    sorted_points = sorted(points, key=lambda p: p.get("sequence_index", 0))
    boundary_points = _get_phase_boundary_points(sorted_points) if show_phase_boundaries else []
    if rotation_degrees:
        sorted_points = _rotate_trajectory_points(sorted_points, rotation_degrees)
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 9))
    ax.set_facecolor("#e8f4f8")
    
    # Plot trajectory
    current_sensor = None
    segment_lons, segment_lats = [], []
    
    for point in sorted_points:
        sensor_id = point.get("sensor_id")
        lon, lat = point.get("longitude", 0), point.get("latitude", 0)
        
        if sensor_id != current_sensor and segment_lons:
            color = sensor_colors.get(current_sensor, default_color)
            ax.plot(segment_lons, segment_lats, color=color, linewidth=3, alpha=0.8)
            segment_lons, segment_lats = [segment_lons[-1]], [segment_lats[-1]]
        
        segment_lons.append(lon)
        segment_lats.append(lat)
        current_sensor = sensor_id
    
    if segment_lons:
        color = sensor_colors.get(current_sensor, default_color)
        ax.plot(segment_lons, segment_lats, color=color, linewidth=3, alpha=0.8)
    
    for point in sorted_points:
        sensor_id = point.get("sensor_id")
        color = sensor_colors.get(sensor_id, default_color)
        ax.scatter(point.get("longitude", 0), point.get("latitude", 0), 
                   c=color, s=40, zorder=5, edgecolors='black', linewidth=0.5)
    
    if sorted_points:
        launch = sorted_points[0]
        ax.scatter(launch.get("longitude", 0), launch.get("latitude", 0), 
                   c='#00FF00', s=250, marker='^', zorder=10, edgecolors='black', linewidth=2)
        impact = sorted_points[-1]
        ax.scatter(impact.get("longitude", 0), impact.get("latitude", 0), 
                   c='#FF0000', s=250, marker='v', zorder=10, edgecolors='black', linewidth=2)
        apogee = max(sorted_points, key=lambda p: p.get("altitude", 0) or 0)
        if apogee.get("altitude", 0) > 0:
            ax.scatter(apogee.get("longitude", 0), apogee.get("latitude", 0), 
                       c='#FFA500', s=180, marker='D', zorder=10, edgecolors='black', linewidth=2)

    if boundary_points:
        for boundary in boundary_points:
            ax.scatter(boundary.get("longitude", 0), boundary.get("latitude", 0),
                       c='#FFD700', s=120, marker='s', zorder=9, edgecolors='black', linewidth=1.5)
    
    legend_handles = []
    for sensor in sensors:
        patch = mpatches.Patch(color=sensor.get("color", "#888888"), 
                               label=f"{sensor.get('name', 'Unknown')} ({sensor.get('detection_phase', '')})")
        legend_handles.append(patch)
    legend_handles.append(plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#00FF00', 
                                      markersize=12, markeredgecolor='black', label='Launch Point'))
    legend_handles.append(plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='#FFA500', 
                                      markersize=10, markeredgecolor='black', label='Apogee'))
    legend_handles.append(plt.Line2D([0], [0], marker='v', color='w', markerfacecolor='#FF0000', 
                                      markersize=12, markeredgecolor='black', label='Impact Point'))
    if boundary_points:
        legend_handles.append(plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#FFD700',
                                          markersize=10, markeredgecolor='black', label='Phase Boundary'))
    
    ax.legend(handles=legend_handles, loc='upper left', fontsize=9, framealpha=0.9)
    ax.set_xlabel('Longitude', fontsize=11)
    ax.set_ylabel('Latitude', fontsize=11)
    ax.set_title(f'{title}\n{subtitle}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    fig.text(0.5, 0.02, 'DISCLAIMER: This visualization is illustrative and analytical only.', 
             ha='center', fontsize=9, style='italic', color='gray')
    
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    return buf.getvalue()


# =============================================================================
# Main Tool Renderer
# =============================================================================

def render_launch_trajectory_tool() -> None:
    """
    Render the complete Launch Trajectory Visualization Tool.
    
    Appears as an expandable section below the Custom POI tool,
    following the same visual language and interaction patterns.
    """
    init_launch_trajectory_state()

    # Track if data has been loaded
    if "launch_trajectory_data_loaded" not in st.session_state:
        st.session_state.launch_trajectory_data_loaded = False
    if "launch_trajectory_file_metadata" not in st.session_state:
        st.session_state.launch_trajectory_file_metadata = {}
    if "launch_trajectory_viz_version" not in st.session_state:
        st.session_state.launch_trajectory_viz_version = 0
    
    with st.expander("🚀 Launch Trajectory Visualization", expanded=False):
        st.markdown("""
        *Visualize launch and flight profiles with spatial and temporal context.*  
        **Note:** This tool is illustrative and analytical, not predictive.
        """)
        
        # =================================================================
        # Mode Selector
        # =================================================================
        st.markdown("### Trajectory Mode")
        
        mode_col1, mode_col2 = st.columns(2)
        
        current_mode = get_trajectory_mode()
        
        with mode_col1:
            if st.button(
                "📊 2D Mode",
                key="traj_mode_2d",
                type="primary" if current_mode == TrajectoryMode.MODE_2D else "secondary",
                use_container_width=True,
                help="Ground-projected trajectory path"
            ):
                set_trajectory_mode(TrajectoryMode.MODE_2D)
                st.rerun()
        
        with mode_col2:
            if st.button(
                "🌐 3D Mode",
                key="traj_mode_3d",
                type="primary" if current_mode == TrajectoryMode.MODE_3D else "secondary",
                use_container_width=True,
                help="Altitude-aware trajectory arcs"
            ):
                set_trajectory_mode(TrajectoryMode.MODE_3D)
                st.rerun()
        
        if current_mode == TrajectoryMode.MODE_2D:
            st.info("**2D Mode:** Displays ground-projected trajectory path. Altitude shown as metadata only.")
        else:
            st.info("**3D Mode:** Displays altitude-aware trajectory arcs with perspective controls. Requires altitude data.")
        
        st.divider()
        
        # =================================================================
        # Data Source Input
        # =================================================================
        st.markdown("### Trajectory Data Source")
        
        data_source_tab, manual_tab = st.tabs(["📁 File Upload", "✏️ Manual Entry"])
        
        with data_source_tab:
            uploaded_file = st.file_uploader(
                "Upload Trajectory Data",
                type=["json", "csv"],
                key=f"traj_file_upload_{st.session_state.launch_trajectory_form_version}",
                help="JSON (preferred) or CSV with latitude, longitude, timestamp/sequence_index"
            )
            
            if uploaded_file is not None:
                content = uploaded_file.read().decode("utf-8")
                file_ext = uploaded_file.name.split(".")[-1].lower()
                
                if file_ext == "json":
                    points, sensors, metadata, errors = parse_json_trajectory(content)
                elif file_ext == "csv":
                    points, errors = parse_csv_trajectory(content)
                    sensors = extract_unique_sensors_from_points(points)
                    metadata = {}
                else:
                    points, sensors, metadata, errors = [], [], {}, ["Unsupported file format"]
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Show metadata if available
                    if metadata:
                        st.success(f"**{metadata.get('name', 'Trajectory')}** - {len(points)} points")
                        if metadata.get('description'):
                            st.caption(metadata.get('description'))
                        if metadata.get('missile_class'):
                            st.caption(f"Missile Class: {metadata.get('missile_class')} | Est. Range: {metadata.get('estimated_range_km', 'N/A')} km")
                    else:
                        st.success(f"Parsed {len(points)} trajectory points from {uploaded_file.name}")
                    
                    # Show detected sensors
                    if sensors:
                        st.info(f"🛰️ Detected **{len(sensors)}** sensor sources in the data")
                    
                    if st.button("✅ Load Trajectory Data", key="traj_load_file"):
                        loaded = load_trajectory_from_data(points, sensors, uploaded_file.name)
                        st.session_state.launch_trajectory_data_loaded = True
                        st.session_state.launch_trajectory_file_metadata = metadata
                        
                        # Assign default colors to sensors
                        for i, sensor in enumerate(st.session_state.launch_trajectory_sensors):
                            if "color" not in sensor:
                                sensor["color"] = SENSOR_COLORS[i % len(SENSOR_COLORS)]
                        
                        st.success(f"Loaded {loaded} points into trajectory")
                        st.rerun()
                    
                    # Preview first few points
                    with st.expander("Preview Data"):
                        st.json(points[:5] if len(points) > 5 else points)
        
        with manual_tab:
            st.markdown("**Add Trajectory Point:**")
            
            form_version = st.session_state.launch_trajectory_form_version
            
            col1, col2 = st.columns(2)
            with col1:
                manual_lat = st.number_input(
                    "Latitude",
                    value=0.0,
                    min_value=-90.0,
                    max_value=90.0,
                    format="%.6f",
                    key=f"traj_manual_lat_{form_version}"
                )
            with col2:
                manual_lon = st.number_input(
                    "Longitude",
                    value=0.0,
                    min_value=-180.0,
                    max_value=180.0,
                    format="%.6f",
                    key=f"traj_manual_lon_{form_version}"
                )
            
            col3, col4 = st.columns(2)
            with col3:
                manual_alt = st.number_input(
                    "Altitude (m)",
                    value=0.0,
                    min_value=0.0,
                    max_value=1000000.0,
                    help="Meters above mean sea level (required for 3D mode)",
                    key=f"traj_manual_alt_{form_version}"
                )
            with col4:
                manual_phase = st.selectbox(
                    "Flight Phase",
                    options=["unknown", "boost", "midcourse", "terminal"],
                    index=0,
                    key=f"traj_manual_phase_{form_version}"
                )
            
            # Sensor selection for manual entry (only if sensors exist)
            sensors = get_sensor_sources()
            if sensors:
                sensor_options = ["None"] + [s.get("name", s.get("sensor_id", "Unknown")) for s in sensors]
                manual_sensor = st.selectbox(
                    "Sensor Attribution",
                    options=sensor_options,
                    index=0,
                    key=f"traj_manual_sensor_{form_version}"
                )
            else:
                manual_sensor = "None"
                st.caption("💡 Load trajectory data with sensors to enable sensor attribution")
            
            if st.button("➕ Add Point", key="traj_add_manual_point"):
                sensor_id = None
                if manual_sensor != "None" and sensors:
                    for s in sensors:
                        if s.get("name") == manual_sensor or s.get("sensor_id") == manual_sensor:
                            sensor_id = s.get("sensor_id")
                            break
                
                add_trajectory_point(
                    latitude=manual_lat,
                    longitude=manual_lon,
                    altitude=manual_alt if manual_alt > 0 else None,
                    phase=manual_phase,
                    sensor_id=sensor_id,
                )
                st.success("Point added to trajectory")
                st.rerun()
        
        st.divider()
        
        # =================================================================
        # Sensor Attribution Section - Only shown after data is loaded
        # =================================================================
        sensors = get_sensor_sources()
        points = get_trajectory_points()
        
        if sensors and points:
            st.markdown("### Sensor Attribution")
            st.caption("Assign colors to each sensor to differentiate trajectory segments.")
            
            with st.expander("🛰️ Sensor Color Assignment", expanded=True):
                render_sensor_color_assignment()
            
            st.divider()
        
        # =================================================================
        # Trajectory Points List
        # =================================================================
        render_trajectory_points_list()
        
        if points:
            st.divider()
        
        # =================================================================
        # Visualization Controls
        # =================================================================
        if points:
            st.markdown("### Visualization Settings")
            
            vis_col1, vis_col2 = st.columns(2)
            
            with vis_col1:
                st.session_state.launch_trajectory_show_launch_marker = st.checkbox(
                    "Show Launch Point Marker",
                    value=st.session_state.launch_trajectory_show_launch_marker,
                    key="traj_show_launch"
                )
                st.session_state.launch_trajectory_show_impact_marker = st.checkbox(
                    "Show Impact Marker",
                    value=st.session_state.launch_trajectory_show_impact_marker,
                    key="traj_show_impact"
                )
                st.session_state.launch_trajectory_show_apogee_marker = st.checkbox(
                    "Show Apogee Marker",
                    value=st.session_state.launch_trajectory_show_apogee_marker,
                    key="traj_show_apogee"
                )
            
            with vis_col2:
                st.session_state.launch_trajectory_show_phase_boundaries = st.checkbox(
                    "Show Phase Boundaries",
                    value=st.session_state.launch_trajectory_show_phase_boundaries,
                    key="traj_show_phases"
                )
                if is_analyst_mode():
                    st.session_state.launch_trajectory_show_sensor_coverage = st.checkbox(
                        "Show Sensor Coverage",
                        value=st.session_state.launch_trajectory_show_sensor_coverage,
                        key="traj_show_sensor_coverage"
                    )
            
            # 3D-specific controls
            if current_mode == TrajectoryMode.MODE_3D:
                st.markdown("**3D View Controls:**")
                
                view_col1, view_col2, view_col3 = st.columns(3)
                
                with view_col1:
                    st.session_state.launch_trajectory_elevation_scale = st.slider(
                        "Elevation Scale",
                        min_value=0.1,
                        max_value=10.0,
                        value=st.session_state.launch_trajectory_elevation_scale,
                        step=0.1,
                        key="traj_elev_scale"
                    )
                
                with view_col2:
                    st.session_state.launch_trajectory_pitch = st.slider(
                        "Pitch (°)",
                        min_value=0.0,
                        max_value=85.0,
                        value=st.session_state.launch_trajectory_pitch,
                        step=5.0,
                        key="traj_pitch"
                    )
                
                with view_col3:
                    st.session_state.launch_trajectory_bearing = st.slider(
                        "Bearing (°)",
                        min_value=0.0,
                        max_value=360.0,
                        value=st.session_state.launch_trajectory_bearing,
                        step=15.0,
                        key="traj_bearing"
                    )
            
            st.divider()
        
        # =================================================================
        # Generate Visualization + Clear controls
        # =================================================================
        btn_col1, btn_col2, btn_col3 = st.columns(3)

        with btn_col1:
            generate_disabled = not bool(points)
            if st.button(
                "🚀 Generate Visualization",
                key="traj_generate",
                type="primary",
                use_container_width=True,
                disabled=generate_disabled,
            ):
                # Validate for mode
                is_valid, errors = validate_trajectory_for_mode(current_mode)
                
                if not is_valid:
                    for error in errors:
                        st.error(error)
                else:
                    with st.spinner("Generating trajectory visualization..."):
                        # Build visualization output
                        st.success(f"Trajectory visualization generated with {len(points)} points!")
                        
                        # Store output for rendering
                        output_data = {
                            "mode": current_mode,
                            "points": points,
                            "sensors": get_sensor_sources(),
                            "settings": {
                                "show_launch_marker": st.session_state.launch_trajectory_show_launch_marker,
                                "show_impact_marker": st.session_state.launch_trajectory_show_impact_marker,
                                "show_apogee_marker": st.session_state.launch_trajectory_show_apogee_marker,
                                "show_phase_boundaries": st.session_state.launch_trajectory_show_phase_boundaries,
                            }
                        }
                        add_trajectory_output(output_data)

        with btn_col2:
            if st.button("🧹 Clear Visualization", key="traj_clear_viz", use_container_width=True):
                # Preserve loaded points/sensors, but clear the rendered outputs and force a re-render.
                clear_trajectory_outputs()
                st.session_state.launch_trajectory_viz_version += 1
                st.rerun()

        with btn_col3:
            if st.button("🗑️ Clear All", key="traj_clear", use_container_width=True):
                clear_trajectory_state()
                st.success("Trajectory data cleared")
                st.rerun()
        
        # =================================================================
        # Output Map Slot
        # =================================================================
        state = get_trajectory_state()
        outputs = state.get("outputs", [])
        
        if outputs:
            st.markdown("---")
            st.markdown("### Trajectory Output Map")
            
            latest_output = outputs[-1]
            output_points = latest_output.get("points", [])
            # Get CURRENT sensors from session state (with updated colors)
            output_sensors = st.session_state.launch_trajectory_sensors if "launch_trajectory_sensors" in st.session_state else []
            
            # Render with pydeck for color support (legend is integrated in the map)
            if output_points:
                # Force a full re-render when the viz version changes.
                # (components.html may otherwise retain client-side state)
                render_trajectory_map_with_legend(
                    output_points,
                    output_sensors,
                    height=500 + (int(st.session_state.launch_trajectory_viz_version) % 2),
                    mode=latest_output.get("mode", TrajectoryMode.MODE_2D),
                )
                
                # Attribution notice
                st.caption("⚠️ **Disclaimer:** This visualization is illustrative and analytical only. It does not calculate or infer launch capability.")
            
            # Render export controls
            render_trajectory_export_controls()
        
        # =================================================================
        # Analyst Mode: Technical Metadata
        # =================================================================
        if is_analyst_mode() and outputs:
            with st.expander("📊 Technical Metadata"):
                latest = outputs[-1]
                st.json({
                    "mode": str(latest.get("mode")),
                    "point_count": len(latest.get("points", [])),
                    "sensor_count": len(latest.get("sensors", [])),
                    "has_full_attribution": has_sensor_attribution(),
                    "settings": latest.get("settings", {}),
                })
