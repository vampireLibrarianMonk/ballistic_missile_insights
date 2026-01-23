"""
Open Range Ring Generator (ORRG)
A fully open-source, web-based geodesic range ring analysis platform.

This is the main Streamlit application entry point.
"""

import sys
from pathlib import Path

# Add the project root to the Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

# Page configuration must be first Streamlit command
st.set_page_config(
    page_title="Open Range Ring Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Now import app modules
from app.ui.layout.global_state import init_session_state, get_map_style
from app.ui.layout.header import render_header, render_sidebar_header
from app.ui.layout.mode_toggle import render_settings_panel
from app.ui.tools.tool_components import render_all_tools
from app.rendering.pydeck_adapter import render_world_map


def render_world_map_section() -> None:
    """Render the world map for situational awareness."""
    st.header("🌍 World Map")
    st.markdown("""
    *Situational awareness view - displays global context and news events.*
    *Note: Analytical outputs are rendered within their respective tools below.*
    """)
    
    # Placeholder for news events - in production this would come from a news service
    sample_events = [
        {
            "title": "Sample Event 1",
            "latitude": 39.0,
            "longitude": 125.7,
            "source": "Example Source",
            "date": "2026-01-21",
            "event_type": "test",
        },
        {
            "title": "Sample Event 2",
            "latitude": 35.6,
            "longitude": 51.4,
            "source": "Example Source",
            "date": "2026-01-20",
            "event_type": "statement",
        },
    ]
    
    # Render the world map
    map_style = get_map_style()
    deck = render_world_map(news_events=sample_events, map_style=map_style)
    st.pydeck_chart(deck, width="stretch")


def render_news_feed_placeholder() -> None:
    """Render a placeholder for the news feed."""
    st.sidebar.markdown("### 📰 News Feed")
    st.sidebar.markdown("*News integration coming soon.*")
    st.sidebar.markdown("""
    The news feed will provide:
    - Missile launch reports
    - Strategic event monitoring
    - Filterable by country, weapon type, and time
    """)
    st.sidebar.divider()


def main() -> None:
    """Main application entry point."""
    # Initialize session state
    init_session_state()
    
    # Render sidebar components
    render_sidebar_header()
    render_settings_panel()
    render_news_feed_placeholder()
    
    # Render main content
    render_header()
    
    # Create tabs for different sections
    tab1, tab2 = st.tabs(["🌍 Situational Awareness", "📊 Analytical Tools"])
    
    with tab1:
        render_world_map_section()
    
    with tab2:
        render_all_tools()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 12px;">
        Open Range Ring Generator (ORRG) | Open Source Geodesic Analysis Platform<br>
        All geometry calculations use true geodesic methods on WGS84 ellipsoid.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
