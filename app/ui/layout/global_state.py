"""
Global session state management for ORRG.
Manages user mode, session data, and application state.
"""

from typing import Any, Optional
from uuid import UUID, uuid4

import streamlit as st

from app.models.outputs import AnalyticalResult


# Session state keys
SESSION_ID_KEY = "session_id"
USER_MODE_KEY = "user_mode"
MAP_STYLE_KEY = "map_style"
ANALYTICAL_RESULTS_KEY = "analytical_results"
SELECTED_NEWS_EVENT_KEY = "selected_news_event"
NEWS_FILTERS_KEY = "news_filters"

COMMAND_HISTORY_KEY = "command_history"
COMMAND_OUTPUT_KEY = "command_output"
COMMAND_REVERSE_PENDING_KEY = "command_reverse_pending"
COMMAND_SINGLE_PENDING_KEY = "command_single_pending"
COMMAND_MINIMUM_PENDING_KEY = "command_minimum_pending"

def init_session_state() -> None:
    """
    Initialize all session state variables.
    Should be called at the start of the application.
    """
    # Session ID
    if SESSION_ID_KEY not in st.session_state:
        st.session_state[SESSION_ID_KEY] = uuid4()
    
    # User mode: "general" or "analyst"
    if USER_MODE_KEY not in st.session_state:
        st.session_state[USER_MODE_KEY] = "general"
    
    # Map style
    if MAP_STYLE_KEY not in st.session_state:
        st.session_state[MAP_STYLE_KEY] = "light"
    
    # Analytical results container
    if ANALYTICAL_RESULTS_KEY not in st.session_state:
        st.session_state[ANALYTICAL_RESULTS_KEY] = AnalyticalResult(
            session_id=st.session_state[SESSION_ID_KEY]
        )
    
    # Selected news event (for world map highlighting)
    if SELECTED_NEWS_EVENT_KEY not in st.session_state:
        st.session_state[SELECTED_NEWS_EVENT_KEY] = None
    
    # News filters
    if NEWS_FILTERS_KEY not in st.session_state:
        st.session_state[NEWS_FILTERS_KEY] = {
            "countries": [],
            "weapon_systems": [],
            "range_classifications": [],
            "time_window": None,
        }

    # Command center state
    if COMMAND_HISTORY_KEY not in st.session_state:
        st.session_state[COMMAND_HISTORY_KEY] = []
    if COMMAND_OUTPUT_KEY not in st.session_state:
        st.session_state[COMMAND_OUTPUT_KEY] = None
    if COMMAND_REVERSE_PENDING_KEY not in st.session_state:
        st.session_state[COMMAND_REVERSE_PENDING_KEY] = None
    if COMMAND_MINIMUM_PENDING_KEY not in st.session_state:
        st.session_state[COMMAND_MINIMUM_PENDING_KEY] = None
    
    # Tool-specific state initialization
    _init_tool_states()


def _init_tool_states() -> None:
    """Initialize state for each analytical tool."""
    tool_keys = [
        "single_range_ring",
        "multiple_range_ring",
        "reverse_range_ring",
        "minimum_range_ring",
        "custom_poi_range_ring",
    ]
    
    for tool_key in tool_keys:
        state_key = f"{tool_key}_state"
        if state_key not in st.session_state:
            st.session_state[state_key] = {
                "outputs": [],
                "expanded": False,
            }


# User Mode Functions
def get_user_mode() -> str:
    """Get the current user mode."""
    return st.session_state.get(USER_MODE_KEY, "general")


def set_user_mode(mode: str) -> None:
    """Set the user mode ('general' or 'analyst')."""
    if mode in ["general", "analyst"]:
        st.session_state[USER_MODE_KEY] = mode
        # Update analytical results user mode
        if ANALYTICAL_RESULTS_KEY in st.session_state:
            st.session_state[ANALYTICAL_RESULTS_KEY].user_mode = mode


def is_analyst_mode() -> bool:
    """Check if the application is in analyst mode."""
    return get_user_mode() == "analyst"


def toggle_user_mode() -> None:
    """Toggle between general and analyst modes."""
    current = get_user_mode()
    set_user_mode("analyst" if current == "general" else "general")


# Map Style Functions
def get_map_style() -> str:
    """Get the current map style."""
    return st.session_state.get(MAP_STYLE_KEY, "light")


def set_map_style(style: str) -> None:
    """Set the map style."""
    st.session_state[MAP_STYLE_KEY] = style


# Analytical Results Functions
def get_analytical_results() -> AnalyticalResult:
    """Get the current analytical results container."""
    return st.session_state.get(ANALYTICAL_RESULTS_KEY, AnalyticalResult())


def add_output_to_results(output) -> None:
    """Add an output to the analytical results."""
    results = get_analytical_results()
    results.add_output(output)
    st.session_state[ANALYTICAL_RESULTS_KEY] = results


def remove_output_from_results(output_id: UUID) -> bool:
    """Remove an output from the analytical results."""
    results = get_analytical_results()
    success = results.remove_output(output_id)
    st.session_state[ANALYTICAL_RESULTS_KEY] = results
    return success


def clear_all_outputs() -> None:
    """Clear all outputs from the analytical results."""
    results = get_analytical_results()
    results.clear_outputs()
    st.session_state[ANALYTICAL_RESULTS_KEY] = results


# News Event Functions
def get_selected_news_event() -> Optional[dict]:
    """Get the currently selected news event."""
    return st.session_state.get(SELECTED_NEWS_EVENT_KEY)


def set_selected_news_event(event: Optional[dict]) -> None:
    """Set the selected news event."""
    st.session_state[SELECTED_NEWS_EVENT_KEY] = event


# News Filter Functions
def get_news_filters() -> dict:
    """Get the current news filters."""
    return st.session_state.get(NEWS_FILTERS_KEY, {})


def set_news_filters(filters: dict) -> None:
    """Set the news filters."""
    st.session_state[NEWS_FILTERS_KEY] = filters


def update_news_filter(key: str, value: Any) -> None:
    """Update a specific news filter."""
    filters = get_news_filters()
    filters[key] = value
    st.session_state[NEWS_FILTERS_KEY] = filters


# Command Center State Functions
def get_command_history() -> list[dict]:
    """Get the current command history list."""
    return st.session_state.get(COMMAND_HISTORY_KEY, [])


def add_command_history_entry(entry: dict) -> None:
    """Add an entry to the command history (latest first)."""
    history = get_command_history()
    history.insert(0, entry)
    st.session_state[COMMAND_HISTORY_KEY] = history


def clear_command_history() -> None:
    """Clear all command history entries."""
    st.session_state[COMMAND_HISTORY_KEY] = []


def update_command_history_entry(match_criteria: dict, updates: dict) -> bool:
    """
    Update an existing command history entry that matches the criteria.
    Returns True if an entry was updated, False otherwise.
    """
    history = get_command_history()
    for entry in history:
        # Check if entry matches all criteria
        matches = all(entry.get(k) == v for k, v in match_criteria.items())
        if matches:
            entry.update(updates)
            st.session_state[COMMAND_HISTORY_KEY] = history
            return True
    return False


def get_command_output():
    """Get the current command output (RangeRingOutput or string response)."""
    return st.session_state.get(COMMAND_OUTPUT_KEY)


def set_command_output(output) -> None:
    """Set the current command output."""
    st.session_state[COMMAND_OUTPUT_KEY] = output


def get_command_reverse_pending() -> Optional[dict]:
    """Get the pending reverse range ring selection data."""
    return st.session_state.get(COMMAND_REVERSE_PENDING_KEY)


def set_command_reverse_pending(data: Optional[dict]) -> None:
    """Set or clear the pending reverse range ring selection data."""
    st.session_state[COMMAND_REVERSE_PENDING_KEY] = data


def get_command_single_pending() -> Optional[dict]:
    """Get the pending single range ring selection data."""
    return st.session_state.get(COMMAND_SINGLE_PENDING_KEY)


def set_command_single_pending(data: Optional[dict]) -> None:
    """Set or clear the pending single range ring selection data."""
    st.session_state[COMMAND_SINGLE_PENDING_KEY] = data


def get_command_minimum_pending() -> Optional[dict]:
    """Get the pending minimum range ring selection data."""
    return st.session_state.get(COMMAND_MINIMUM_PENDING_KEY)


def set_command_minimum_pending(data: Optional[dict]) -> None:
    """Set or clear the pending minimum range ring selection data."""
    st.session_state[COMMAND_MINIMUM_PENDING_KEY] = data


# Tool State Functions
def get_tool_state(tool_key: str) -> dict:
    """Get the state for a specific tool."""
    state_key = f"{tool_key}_state"
    return st.session_state.get(state_key, {"outputs": [], "expanded": False})


def set_tool_state(tool_key: str, state: dict) -> None:
    """Set the state for a specific tool."""
    state_key = f"{tool_key}_state"
    st.session_state[state_key] = state


def add_tool_output(tool_key: str, output) -> None:
    """Add an output to a specific tool's state."""
    state = get_tool_state(tool_key)
    state["outputs"].append(output)
    set_tool_state(tool_key, state)
    
    # Also add to global analytical results
    add_output_to_results(output)


def clear_tool_outputs(tool_key: str) -> None:
    """Clear all outputs for a specific tool."""
    state = get_tool_state(tool_key)
    
    # Remove from global results
    results = get_analytical_results()
    for output in state.get("outputs", []):
        results.remove_output(output.output_id)
    st.session_state[ANALYTICAL_RESULTS_KEY] = results
    
    # Clear tool state
    state["outputs"] = []
    set_tool_state(tool_key, state)


def toggle_tool_expanded(tool_key: str) -> None:
    """Toggle the expanded state of a tool."""
    state = get_tool_state(tool_key)
    state["expanded"] = not state.get("expanded", False)
    set_tool_state(tool_key, state)


# Session Functions
def get_session_id() -> UUID:
    """Get the current session ID."""
    return st.session_state.get(SESSION_ID_KEY, uuid4())


def reset_session() -> None:
    """Reset all session state to defaults."""
    # Clear all session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Re-initialize
    init_session_state()
