"""Launch Trajectory command stub (placeholder)."""

from __future__ import annotations

import streamlit as st


def parse_initial(query: str):
    return None


def handle_pending(query: str):
    return None


def render_pending_panel():
    return None


def help_tab(tab):
    with tab:
        st.markdown("**Launch Trajectory**")
        st.markdown("*Coming Soon*")
        st.markdown("Visualize ballistic missile launch trajectories.")
        st.markdown("**Example:**")
        st.code("Show launch trajectory from Pyongyang to Tokyo")
