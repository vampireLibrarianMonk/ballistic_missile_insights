"""
State management for the Multiple Range Ring tool.

Manages session state for multiple range ring generation with dynamic range inputs.
"""

import streamlit as st
from app.ui.layout.global_state import clear_tool_outputs


def reset_multiple_range_ring_state() -> None:
    """Clear all persisted state for the multiple range ring tool."""
    clear_tool_outputs("multiple_range_ring")
    
    # Clear multi ranges session state
    if "multi_ranges" in st.session_state:
        del st.session_state.multi_ranges


def get_multi_ranges() -> list:
    """Get the list of range configurations."""
    if "multi_ranges" not in st.session_state:
        st.session_state.multi_ranges = [{"value": 1000, "unit": "km", "weapon_name": "Manual Entry"}]
    return st.session_state.multi_ranges


def add_multi_range(value: float = 1000, unit: str = "km", weapon_name: str = "Manual Entry") -> None:
    """Add a new range configuration."""
    ranges = get_multi_ranges()
    ranges.append({"value": value, "unit": unit, "weapon_name": weapon_name})


def remove_multi_range(index: int) -> None:
    """Remove a range configuration by index."""
    ranges = get_multi_ranges()
    if 0 <= index < len(ranges):
        ranges.pop(index)


__all__ = [
    "reset_multiple_range_ring_state",
    "get_multi_ranges",
    "add_multi_range",
    "remove_multi_range",
]
