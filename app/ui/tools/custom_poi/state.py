"""
State management for the Custom POI Range Ring tool.

Manages session state for custom POI range ring generation with dynamic POI inputs.
"""

import streamlit as st
from app.ui.layout.global_state import clear_tool_outputs


def reset_custom_poi_state() -> None:
    """Clear all persisted state for the custom POI tool."""
    clear_tool_outputs("custom_poi_range_ring")
    
    # Clear custom POI session state
    if "custom_pois" in st.session_state:
        del st.session_state.custom_pois
    if "custom_poi_selected_idx" in st.session_state:
        del st.session_state.custom_poi_selected_idx
    if "custom_poi_form_version" in st.session_state:
        del st.session_state.custom_poi_form_version
    if "custom_poi_load_poi" in st.session_state:
        del st.session_state.custom_poi_load_poi
    if "custom_poi_prefill" in st.session_state:
        del st.session_state.custom_poi_prefill


def get_custom_pois() -> list:
    """Get the list of custom POIs."""
    if "custom_pois" not in st.session_state:
        st.session_state.custom_pois = []
    return st.session_state.custom_pois


def add_custom_poi(poi_data: dict) -> None:
    """Add a new POI configuration."""
    pois = get_custom_pois()
    pois.append(poi_data)


def update_custom_poi(index: int, poi_data: dict) -> None:
    """Update a POI configuration by index."""
    pois = get_custom_pois()
    if 0 <= index < len(pois):
        pois[index] = poi_data


def remove_custom_poi(index: int) -> None:
    """Remove a POI configuration by index."""
    pois = get_custom_pois()
    if 0 <= index < len(pois):
        pois.pop(index)


def get_selected_poi_idx() -> int | None:
    """Get the currently selected POI index (None for add mode)."""
    return st.session_state.get("custom_poi_selected_idx")


def set_selected_poi_idx(idx: int | None) -> None:
    """Set the currently selected POI index."""
    st.session_state.custom_poi_selected_idx = idx


def get_form_version() -> int:
    """Get the form version number for unique widget keys."""
    if "custom_poi_form_version" not in st.session_state:
        st.session_state.custom_poi_form_version = 0
    return st.session_state.custom_poi_form_version


def increment_form_version() -> None:
    """Increment form version to force widget refresh."""
    st.session_state.custom_poi_form_version = get_form_version() + 1


def get_prefill_data() -> dict | None:
    """Get prefill data for the form."""
    return st.session_state.get("custom_poi_prefill")


def set_prefill_data(data: dict | None) -> None:
    """Set prefill data for the form."""
    st.session_state.custom_poi_prefill = data


__all__ = [
    "reset_custom_poi_state",
    "get_custom_pois",
    "add_custom_poi",
    "update_custom_poi",
    "remove_custom_poi",
    "get_selected_poi_idx",
    "set_selected_poi_idx",
    "get_form_version",
    "increment_form_version",
    "get_prefill_data",
    "set_prefill_data",
]
