"""
Tool UI components for ORRG.
Renders all analytical tools by importing from their respective modules.
"""

import streamlit as st

from app.ui.tools.launch_trajectory.ui import render_launch_trajectory_tool
from app.ui.tools.single.ui import render_single_range_ring_tool
from app.ui.tools.reverse.ui import render_reverse_range_ring_tool
from app.ui.tools.minimum.ui import render_minimum_range_ring_tool
from app.ui.tools.multiple.ui import render_multiple_range_ring_tool
from app.ui.tools.custom_poi.ui import render_custom_poi_tool

# Re-export shared utilities for backward compatibility
from app.ui.tools.shared import (
    get_weapon_selection_and_range,
    render_range_input_with_weapon_key,
    render_map_with_legend,
    render_export_controls,
)


def render_all_tools() -> None:
    """Render all analytical tools."""
    st.header("📊 Analytical Tools")
    st.markdown("Select a tool below to generate range ring analyses.")
    
    render_single_range_ring_tool()
    render_multiple_range_ring_tool()
    render_reverse_range_ring_tool()
    render_minimum_range_ring_tool()
    render_custom_poi_tool()
    render_launch_trajectory_tool()


__all__ = [
    "render_all_tools",
    "render_single_range_ring_tool",
    "render_multiple_range_ring_tool",
    "render_reverse_range_ring_tool",
    "render_minimum_range_ring_tool",
    "render_custom_poi_tool",
    "render_launch_trajectory_tool",
    # Shared utilities
    "get_weapon_selection_and_range",
    "render_range_input_with_weapon_key",
    "render_map_with_legend",
    "render_export_controls",
]
