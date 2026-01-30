"""
State management for the Reverse Range Ring tool.

Manages session state for the two-step reverse range ring workflow:
1. Calculate available weapon systems that can reach the target
2. Generate the launch envelope for a selected system
"""

import streamlit as st
from app.ui.layout.global_state import clear_tool_outputs


def reset_reverse_range_ring_state() -> None:
    """Clear all persisted state for the reverse range ring tool."""
    clear_tool_outputs("reverse_range_ring")
    
    # Clear reverse tool session state
    if "reverse_available_systems" in st.session_state:
        del st.session_state.reverse_available_systems
    if "reverse_min_distance" in st.session_state:
        del st.session_state.reverse_min_distance
    if "reverse_calculated" in st.session_state:
        del st.session_state.reverse_calculated


def get_reverse_available_systems() -> list:
    """Get the list of available weapon systems that can reach the target."""
    return st.session_state.get("reverse_available_systems", [])


def set_reverse_available_systems(systems: list) -> None:
    """Set the list of available weapon systems."""
    st.session_state.reverse_available_systems = systems


def get_reverse_min_distance() -> float | None:
    """Get the minimum distance from shooter country to target."""
    return st.session_state.get("reverse_min_distance")


def set_reverse_min_distance(distance: float) -> None:
    """Set the minimum distance from shooter country to target."""
    st.session_state.reverse_min_distance = distance


def is_reverse_calculated() -> bool:
    """Check if the availability calculation has been performed."""
    return st.session_state.get("reverse_calculated", False)


def set_reverse_calculated(calculated: bool) -> None:
    """Set the calculated flag."""
    st.session_state.reverse_calculated = calculated


__all__ = [
    "reset_reverse_range_ring_state",
    "get_reverse_available_systems",
    "set_reverse_available_systems",
    "get_reverse_min_distance",
    "set_reverse_min_distance",
    "is_reverse_calculated",
    "set_reverse_calculated",
]
