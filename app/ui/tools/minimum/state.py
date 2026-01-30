"""
State management for the Minimum Range Ring tool.

Manages session state for minimum distance calculations between two locations.
"""

import streamlit as st
from app.ui.layout.global_state import clear_tool_outputs


def reset_minimum_range_ring_state() -> None:
    """Clear all persisted state for the minimum range ring tool."""
    clear_tool_outputs("minimum_range_ring")
    
    # Clear minimum tool session state
    if "min_distance_result" in st.session_state:
        del st.session_state.min_distance_result


def get_min_distance_result():
    """Get the stored minimum distance calculation result."""
    return st.session_state.get("min_distance_result")


def set_min_distance_result(result) -> None:
    """Store the minimum distance calculation result."""
    st.session_state.min_distance_result = result


__all__ = [
    "reset_minimum_range_ring_state",
    "get_min_distance_result",
    "set_min_distance_result",
]
