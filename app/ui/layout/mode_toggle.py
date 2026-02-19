"""
Mode toggle component for ORRG.
Provides UI for switching between General User and Analyst modes.
"""

import streamlit as st

from app.ui.layout.global_state import (
    get_user_mode,
    set_user_mode,
    is_analyst_mode,
    get_map_style,
    set_map_style,
)


def render_mode_toggle() -> None:
    """
    Render the mode toggle in the sidebar.
    Allows switching between General User and Analyst modes.
    """
    st.sidebar.markdown("### ⚙️ Settings")
    
    # Mode toggle
    current_mode = get_user_mode()
    
    mode_options = {
        "general": "👤 General User",
        "analyst": "🔬 Analyst",
    }
    
    selected = st.sidebar.radio(
        "User Mode",
        options=list(mode_options.keys()),
        format_func=lambda x: mode_options[x],
        index=0 if current_mode == "general" else 1,
        key="mode_toggle_radio",
        help="Analyst mode shows additional technical details and diagnostics.",
    )
    
    if selected != current_mode:
        set_user_mode(selected)
        st.rerun()
    
    # Mode description
    if is_analyst_mode():
        st.sidebar.info(
            "**Analyst Mode** provides full access to:\n"
            "- Command Center\n"
            "- Situational Awareness\n"
            "- Analytical Tools\n\n"
            "Additional diagnostic information includes:\n"
            "- Geometry resolution and point density\n"
            "- Processing metrics\n"
            "- Export metadata\n"
            "- Technical details"
        )
    else:
        st.sidebar.info(
            "**General User Mode** provides access to:\n"
            "- Command Center\n\n"
            "This mode hides Situational Awareness and Analytical Tools."
        )
    
    st.sidebar.divider()


def render_map_style_selector() -> None:
    """
    Render the map style selector in the sidebar.
    """
    st.sidebar.markdown("### 🗺️ Map Style")
    
    current_style = get_map_style()
    
    style_options = {
        "light": "☀️ Light",
        "dark": "🌙 Dark",
    }
    
    selected = st.sidebar.selectbox(
        "Map Style",
        options=list(style_options.keys()),
        format_func=lambda x: style_options[x],
        index=0 if current_style == "light" else 1,
        key="map_style_selector",
    )
    
    if selected != current_style:
        set_map_style(selected)
        st.rerun()


def render_settings_panel() -> None:
    """
    Render the complete settings panel in the sidebar.
    Combines mode toggle and other settings.
    """
    render_mode_toggle()
    render_map_style_selector()
    st.sidebar.divider()
