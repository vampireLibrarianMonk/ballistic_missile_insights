"""
State management for Launch Trajectory Visualization Tool.
Manages trajectory data, sensor attribution, and visualization settings.
"""

import streamlit as st
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class TrajectoryMode(str, Enum):
    """Trajectory visualization mode."""
    MODE_2D = "2D"
    MODE_3D = "3D"


class FlightPhase(str, Enum):
    """Flight phase classification."""
    BOOST = "boost"
    MIDCOURSE = "midcourse"
    TERMINAL = "terminal"
    UNKNOWN = "unknown"


class SensorClass(str, Enum):
    """Sensor classification type."""
    SPACE_BASED = "space-based"
    GROUND_BASED = "ground-based"
    MARITIME = "maritime"
    AIRBORNE = "airborne"
    UNKNOWN = "unknown"


@dataclass
class TrajectoryPoint:
    """
    Represents a single point along a trajectory path.
    
    Required Fields:
        latitude: Decimal degrees
        longitude: Decimal degrees
        timestamp or sequence_index: Time or ordering
    
    Optional Fields:
        altitude: Meters above mean sea level
        velocity: Speed (informational)
        phase: Flight phase (boost/midcourse/terminal)
        sensor_id: Associated sensor source
    """
    latitude: float
    longitude: float
    timestamp: Optional[str] = None
    sequence_index: Optional[int] = None
    altitude: Optional[float] = None  # meters above MSL
    velocity: Optional[float] = None  # m/s, informational
    phase: FlightPhase = FlightPhase.UNKNOWN
    sensor_id: Optional[str] = None
    point_id: str = field(default_factory=lambda: str(uuid4())[:8])


@dataclass
class SensorSource:
    """
    Represents a sensor source for trajectory attribution.
    
    Each trajectory segment or point must be attributable to a sensor.
    """
    sensor_id: str
    name: str
    sensor_class: SensorClass = SensorClass.UNKNOWN
    detection_phase: Optional[FlightPhase] = None
    color: str = "#FF6B6B"  # Default color for visualization
    line_style: str = "solid"  # solid, dashed, dotted


@dataclass
class TrajectoryState:
    """
    Complete state for a trajectory visualization.
    """
    trajectory_id: str = field(default_factory=lambda: str(uuid4())[:8])
    mode: TrajectoryMode = TrajectoryMode.MODE_2D
    points: list[TrajectoryPoint] = field(default_factory=list)
    sensors: list[SensorSource] = field(default_factory=list)
    
    # Visualization toggles
    show_launch_marker: bool = True
    show_impact_marker: bool = True
    show_apogee_marker: bool = True
    show_phase_boundaries: bool = False
    show_sensor_coverage: bool = False
    
    # 3D-specific settings
    elevation_scale: float = 1.0
    pitch: float = 45.0
    bearing: float = 0.0
    
    # Data source info
    data_source_name: Optional[str] = None
    data_source_type: Optional[str] = None  # "file" or "manual"


# =============================================================================
# State Initialization
# =============================================================================

def init_launch_trajectory_state() -> None:
    """
    Initialize session state for the Launch Trajectory Visualization Tool.
    Called once when the tool is first accessed.
    """
    if "launch_trajectory_state" not in st.session_state:
        st.session_state.launch_trajectory_state = TrajectoryState()
    
    if "launch_trajectory_points" not in st.session_state:
        st.session_state.launch_trajectory_points = []
    
    if "launch_trajectory_sensors" not in st.session_state:
        st.session_state.launch_trajectory_sensors = []
    
    if "launch_trajectory_mode" not in st.session_state:
        st.session_state.launch_trajectory_mode = TrajectoryMode.MODE_2D
    
    if "launch_trajectory_outputs" not in st.session_state:
        st.session_state.launch_trajectory_outputs = []
    
    # Form versioning for widget key management
    if "launch_trajectory_form_version" not in st.session_state:
        st.session_state.launch_trajectory_form_version = 0
    
    # Uploaded file tracking
    if "launch_trajectory_uploaded_file" not in st.session_state:
        st.session_state.launch_trajectory_uploaded_file = None
    
    # Selected point for editing
    if "launch_trajectory_selected_idx" not in st.session_state:
        st.session_state.launch_trajectory_selected_idx = None
    
    # Display toggles
    if "launch_trajectory_show_launch_marker" not in st.session_state:
        st.session_state.launch_trajectory_show_launch_marker = True
    
    if "launch_trajectory_show_impact_marker" not in st.session_state:
        st.session_state.launch_trajectory_show_impact_marker = True
    
    if "launch_trajectory_show_apogee_marker" not in st.session_state:
        st.session_state.launch_trajectory_show_apogee_marker = True
    
    if "launch_trajectory_show_phase_boundaries" not in st.session_state:
        st.session_state.launch_trajectory_show_phase_boundaries = False
    
    if "launch_trajectory_show_sensor_coverage" not in st.session_state:
        st.session_state.launch_trajectory_show_sensor_coverage = False
    
    # 3D view settings
    if "launch_trajectory_elevation_scale" not in st.session_state:
        st.session_state.launch_trajectory_elevation_scale = 1.0
    
    if "launch_trajectory_pitch" not in st.session_state:
        st.session_state.launch_trajectory_pitch = 45.0
    
    if "launch_trajectory_bearing" not in st.session_state:
        st.session_state.launch_trajectory_bearing = 0.0


# =============================================================================
# State Getters
# =============================================================================

def get_trajectory_state() -> dict[str, Any]:
    """
    Get the current trajectory state as a dictionary.
    
    Returns:
        Dictionary containing all trajectory state values.
    """
    init_launch_trajectory_state()
    return {
        "mode": st.session_state.launch_trajectory_mode,
        "points": st.session_state.launch_trajectory_points,
        "sensors": st.session_state.launch_trajectory_sensors,
        "outputs": st.session_state.launch_trajectory_outputs,
        "show_launch_marker": st.session_state.launch_trajectory_show_launch_marker,
        "show_impact_marker": st.session_state.launch_trajectory_show_impact_marker,
        "show_apogee_marker": st.session_state.launch_trajectory_show_apogee_marker,
        "show_phase_boundaries": st.session_state.launch_trajectory_show_phase_boundaries,
        "show_sensor_coverage": st.session_state.launch_trajectory_show_sensor_coverage,
        "elevation_scale": st.session_state.launch_trajectory_elevation_scale,
        "pitch": st.session_state.launch_trajectory_pitch,
        "bearing": st.session_state.launch_trajectory_bearing,
    }


def get_trajectory_mode() -> TrajectoryMode:
    """Get the current trajectory visualization mode."""
    init_launch_trajectory_state()
    return st.session_state.launch_trajectory_mode


def get_trajectory_points() -> list[dict]:
    """Get the list of trajectory points."""
    init_launch_trajectory_state()
    return st.session_state.launch_trajectory_points


def get_sensor_sources() -> list[dict]:
    """Get the list of sensor sources."""
    init_launch_trajectory_state()
    return st.session_state.launch_trajectory_sensors


# =============================================================================
# State Setters
# =============================================================================

def set_trajectory_mode(mode: TrajectoryMode) -> None:
    """
    Set the trajectory visualization mode.
    
    Args:
        mode: TrajectoryMode.MODE_2D or TrajectoryMode.MODE_3D
    """
    init_launch_trajectory_state()
    st.session_state.launch_trajectory_mode = mode


def add_trajectory_point(
    latitude: float,
    longitude: float,
    timestamp: Optional[str] = None,
    sequence_index: Optional[int] = None,
    altitude: Optional[float] = None,
    velocity: Optional[float] = None,
    phase: str = "unknown",
    sensor_id: Optional[str] = None,
) -> None:
    """
    Add a trajectory point to the state.
    
    Args:
        latitude: Decimal degrees
        longitude: Decimal degrees
        timestamp: ISO timestamp or time string
        sequence_index: Sequential order index
        altitude: Meters above MSL (required for 3D mode)
        velocity: Speed in m/s (informational)
        phase: Flight phase (boost/midcourse/terminal/unknown)
        sensor_id: Associated sensor source ID
    """
    init_launch_trajectory_state()
    point = {
        "point_id": str(uuid4())[:8],
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp,
        "sequence_index": sequence_index if sequence_index is not None else len(st.session_state.launch_trajectory_points),
        "altitude": altitude,
        "velocity": velocity,
        "phase": phase,
        "sensor_id": sensor_id,
    }
    st.session_state.launch_trajectory_points.append(point)


def remove_trajectory_point(point_id: str) -> bool:
    """
    Remove a trajectory point by its ID.
    
    Args:
        point_id: The unique point identifier
        
    Returns:
        True if point was removed, False if not found
    """
    init_launch_trajectory_state()
    points = st.session_state.launch_trajectory_points
    for i, point in enumerate(points):
        if point.get("point_id") == point_id:
            points.pop(i)
            return True
    return False


def update_trajectory_point(point_id: str, **kwargs) -> bool:
    """
    Update a trajectory point by its ID.
    
    Args:
        point_id: The unique point identifier
        **kwargs: Fields to update
        
    Returns:
        True if point was updated, False if not found
    """
    init_launch_trajectory_state()
    for point in st.session_state.launch_trajectory_points:
        if point.get("point_id") == point_id:
            point.update(kwargs)
            return True
    return False


def add_sensor_source(
    name: str,
    sensor_class: str = "unknown",
    detection_phase: Optional[str] = None,
    color: str = "#FF6B6B",
    line_style: str = "solid",
) -> str:
    """
    Add a sensor source for trajectory attribution.
    
    Args:
        name: Sensor name or identifier
        sensor_class: Classification (space-based, ground-based, maritime, airborne)
        detection_phase: Phase detected (boost/midcourse/terminal)
        color: Hex color for visualization
        line_style: Line style (solid, dashed, dotted)
        
    Returns:
        The generated sensor_id
    """
    init_launch_trajectory_state()
    sensor_id = str(uuid4())[:8]
    sensor = {
        "sensor_id": sensor_id,
        "name": name,
        "sensor_class": sensor_class,
        "detection_phase": detection_phase,
        "color": color,
        "line_style": line_style,
    }
    st.session_state.launch_trajectory_sensors.append(sensor)
    return sensor_id


def remove_sensor_source(sensor_id: str) -> bool:
    """
    Remove a sensor source by its ID.
    
    Args:
        sensor_id: The unique sensor identifier
        
    Returns:
        True if sensor was removed, False if not found
    """
    init_launch_trajectory_state()
    sensors = st.session_state.launch_trajectory_sensors
    for i, sensor in enumerate(sensors):
        if sensor.get("sensor_id") == sensor_id:
            sensors.pop(i)
            return True
    return False


# =============================================================================
# State Clear/Reset
# =============================================================================

def clear_trajectory_state() -> None:
    """Clear all trajectory state, resetting to defaults."""
    init_launch_trajectory_state()
    st.session_state.launch_trajectory_points = []
    st.session_state.launch_trajectory_sensors = []
    st.session_state.launch_trajectory_outputs = []
    st.session_state.launch_trajectory_mode = TrajectoryMode.MODE_2D
    st.session_state.launch_trajectory_form_version += 1
    st.session_state.launch_trajectory_selected_idx = None
    st.session_state.launch_trajectory_uploaded_file = None
    
    # Reset display toggles
    st.session_state.launch_trajectory_show_launch_marker = True
    st.session_state.launch_trajectory_show_impact_marker = True
    st.session_state.launch_trajectory_show_apogee_marker = True
    st.session_state.launch_trajectory_show_phase_boundaries = False
    st.session_state.launch_trajectory_show_sensor_coverage = False
    
    # Reset 3D settings
    st.session_state.launch_trajectory_elevation_scale = 1.0
    st.session_state.launch_trajectory_pitch = 45.0
    st.session_state.launch_trajectory_bearing = 0.0

    # Reset tool-local metadata (used by export titles and UI banners)
    st.session_state.launch_trajectory_data_loaded = False
    st.session_state.launch_trajectory_file_metadata = {}
    # Clear file-level metadata caches
    if "launch_trajectory_uploaded_file" in st.session_state:
        st.session_state.launch_trajectory_uploaded_file = None
    if "launch_trajectory_file_metadata" in st.session_state:
        st.session_state.launch_trajectory_file_metadata = {}

    # Bump a visualization render version so embedded pydeck map fully resets.
    if "launch_trajectory_viz_version" not in st.session_state:
        st.session_state.launch_trajectory_viz_version = 0
    st.session_state.launch_trajectory_viz_version += 1


def clear_trajectory_outputs() -> None:
    """Clear only the trajectory outputs, preserving input state."""
    init_launch_trajectory_state()
    st.session_state.launch_trajectory_outputs = []


def add_trajectory_output(output: Any) -> None:
    """
    Add a trajectory visualization output.
    
    Args:
        output: The generated trajectory output object
    """
    init_launch_trajectory_state()
    st.session_state.launch_trajectory_outputs.append(output)


# =============================================================================
# Bulk Data Loading
# =============================================================================

def load_trajectory_from_data(
    points_data: list[dict],
    sensors_data: Optional[list[dict]] = None,
    source_name: Optional[str] = None,
) -> int:
    """
    Load trajectory data from parsed file or external source.
    
    Args:
        points_data: List of point dictionaries with required fields
        sensors_data: Optional list of sensor source dictionaries
        source_name: Name of the data source (e.g., filename)
        
    Returns:
        Number of points loaded
    """
    init_launch_trajectory_state()
    
    # Clear existing points
    st.session_state.launch_trajectory_points = []
    
    # Load points with validation
    for i, point in enumerate(points_data):
        if "latitude" in point and "longitude" in point:
            add_trajectory_point(
                latitude=float(point["latitude"]),
                longitude=float(point["longitude"]),
                timestamp=point.get("timestamp"),
                sequence_index=point.get("sequence_index", i),
                altitude=point.get("altitude"),
                velocity=point.get("velocity"),
                phase=point.get("phase", "unknown"),
                sensor_id=point.get("sensor_id"),
            )
    
    # Load sensors if provided - PRESERVE original sensor_id from file
    if sensors_data:
        st.session_state.launch_trajectory_sensors = []
        for sensor in sensors_data:
            # Directly add sensor dict preserving original sensor_id
            sensor_entry = {
                "sensor_id": sensor.get("sensor_id", str(uuid4())[:8]),  # Keep original ID!
                "name": sensor.get("name", "Unknown Sensor"),
                "sensor_class": sensor.get("sensor_class", "unknown"),
                "detection_phase": sensor.get("detection_phase"),
                "line_style": sensor.get("line_style", "solid"),
            }
            # Only set color if explicitly provided in file (not None)
            if sensor.get("color"):
                sensor_entry["color"] = sensor["color"]
            st.session_state.launch_trajectory_sensors.append(sensor_entry)
    
    return len(st.session_state.launch_trajectory_points)


# =============================================================================
# Validation Helpers
# =============================================================================

def validate_trajectory_for_mode(mode: TrajectoryMode) -> tuple[bool, list[str]]:
    """
    Validate that trajectory data meets requirements for the selected mode.
    
    Args:
        mode: The visualization mode to validate against
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    init_launch_trajectory_state()
    errors = []
    points = st.session_state.launch_trajectory_points
    
    if not points:
        errors.append("No trajectory points defined")
        return False, errors
    
    for i, point in enumerate(points):
        # Required fields
        if point.get("latitude") is None or point.get("longitude") is None:
            errors.append(f"Point {i+1}: Missing latitude or longitude")
        
        # Timestamp or sequence_index required
        if point.get("timestamp") is None and point.get("sequence_index") is None:
            errors.append(f"Point {i+1}: Missing timestamp or sequence_index")
        
        # 3D mode requires altitude
        if mode == TrajectoryMode.MODE_3D and point.get("altitude") is None:
            errors.append(f"Point {i+1}: 3D mode requires altitude")
    
    return len(errors) == 0, errors


def has_sensor_attribution() -> bool:
    """Check if all trajectory points have sensor attribution."""
    init_launch_trajectory_state()
    points = st.session_state.launch_trajectory_points
    sensors = st.session_state.launch_trajectory_sensors
    
    if not sensors:
        return False
    
    sensor_ids = {s.get("sensor_id") for s in sensors}
    for point in points:
        if point.get("sensor_id") not in sensor_ids:
            return False
    
    return True
