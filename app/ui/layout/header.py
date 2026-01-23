"""
Header component for ORRG.
Renders the application header with title and mode indicator.
"""

import streamlit as st

from app.ui.layout.global_state import get_user_mode, is_analyst_mode


def render_header() -> None:
    """
    Render the application header.
    Includes the title, tagline, and current mode indicator.
    """
    # Create header container
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        st.title("🎯 Open Range Ring Generator")
        st.caption("*A fully open-source, web-based geodesic range ring analysis platform.*")
    
    with header_col2:
        # Mode indicator
        mode = get_user_mode()
        if is_analyst_mode():
            st.markdown(
                """
                <div style="
                    background-color: #1f77b4;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    text-align: center;
                    font-weight: bold;
                    margin-top: 20px;
                ">
                    🔬 ANALYST MODE
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="
                    background-color: #2ca02c;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    text-align: center;
                    font-weight: bold;
                    margin-top: 20px;
                ">
                    👤 GENERAL USER
                </div>
                """,
                unsafe_allow_html=True,
            )
    
    # Horizontal divider
    st.divider()


def render_sidebar_header() -> None:
    """
    Render a compact header in the sidebar.
    """
    st.sidebar.markdown("## 🎯 ORRG")
    
    # Mode indicator in sidebar
    mode = get_user_mode()
    mode_label = "🔬 Analyst" if is_analyst_mode() else "👤 General"
    mode_color = "#1f77b4" if is_analyst_mode() else "#2ca02c"
    
    st.sidebar.markdown(
        f"""
        <div style="
            background-color: {mode_color};
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            text-align: center;
            font-size: 12px;
            margin-bottom: 10px;
        ">
            {mode_label}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.divider()
