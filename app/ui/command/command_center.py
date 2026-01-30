"""
Command Center UI orchestrator.
Delegates per-task flows to dedicated modules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

import streamlit as st

from app.models.outputs import RangeRingOutput
from app.rendering.pydeck_adapter import render_range_ring_output
from app.ui.layout.global_state import (
    get_map_style,
    get_command_history,
    add_command_history_entry,
    clear_command_history,
    get_command_output,
    set_command_output,
    get_command_reverse_pending,
    get_command_single_pending,
    get_command_minimum_pending,
    get_command_multiple_pending,
    get_command_custom_poi_pending,
)
from app.ui.tools.tool_components import render_map_with_legend
from app.ui.command.shared_command_utils import (
    get_shared_validation_js,
    render_html_template,
    render_js_export_controls,
    render_cached_export_links,
    clear_product_viewer,
)
from app.ui.command import (
    reverse_command,
    single_command,
    multiple_command,
    minimum_command,
    custom_poi_command,
    trajectory_command,
)


CommandOutput = Union[RangeRingOutput, str, None]


def _render_command_input_status_bar() -> None:
    """Render a JavaScript-based status bar using the HTML template."""
    shared_js = get_shared_validation_js()

    # Extract the default empty message once (same behavior as before)
    empty_message = (
        shared_js
        .split("messages:")[1]
        .split("empty:")[1]
        .split("'")[1]
    )

    status_html = render_html_template(
        "status_bar.html",
        replacements={
            "{{SHARED_JS}}": shared_js,
            "{{EMPTY_MESSAGE}}": empty_message,
        },
    )

    st.components.v1.html(status_html, height=55)


def _render_input_panel() -> Optional[str]:
    """Render the user input panel and return the submitted text if any."""
    # If a pending synthetic query was enqueued by a Step 2 confirm, route it immediately
    pending_query = st.session_state.pop("command_pending_query", None)
    if pending_query:
        return pending_query

    # Multiple flow uses a dedicated pending query as well
    multiple_pending_query = st.session_state.pop("command_multiple_pending_query", None)
    if multiple_pending_query:
        return multiple_pending_query

    # Pending flows get priority
    for pending_panel in (
        multiple_command.render_pending_panel,
        reverse_command.render_pending_panel,
        single_command.render_pending_panel,
        minimum_command.render_pending_panel,
        custom_poi_command.render_pending_panel,
    ):
        result = pending_panel()
        if result is not None:
            return result

    # Step 1: Normal input panel using a form for Ctrl+Enter submission
    st.markdown("### 📝 Step 1: Enter Command")

    with st.form(key="command_form", clear_on_submit=True):
        query_text = st.text_area(
            "Command input",
            placeholder="Type a question or task... (Ctrl+Enter to submit)",
            height=120,
            key="command_input_text",
            label_visibility="collapsed",
        )

        _render_command_input_status_bar()

        executed = st.form_submit_button("⚙️ Execute Command", use_container_width=True)

    if executed and query_text and query_text.strip():
        return query_text.strip()

    if executed:
        st.warning("Please enter a question or task before submitting.")
    return None


def _render_product_output_viewer() -> None:
    """Render the product output viewer (collapsible) with clear functionality."""
    output = get_command_output()

    with st.expander("🗺️ Product Output Viewer", expanded=output is not None):
        if output is None:
            st.info("No output generated yet. Run a query or task to see results here.")
            return

        if isinstance(output, RangeRingOutput):
            st.subheader(output.title)
            if output.subtitle:
                st.caption(output.subtitle)
            if output.description:
                st.markdown(f"*{output.description}*")

            deck = render_range_ring_output(output, get_map_style())
            render_map_with_legend(deck, output)
            render_js_export_controls(output, "command_output")
        else:
            st.markdown("### Answer")
            st.markdown(output)

        st.divider()
        if st.button("🔄 Reset Execution Query", key="reset_execution_query", use_container_width=True):
            clear_product_viewer()
            st.rerun()


def _render_help_section() -> None:
    """Render the Command Center help section with tabbed tool help."""
    with st.expander("❓ Help", expanded=False):
        tab_rrr, tab_single, tab_multi, tab_min, tab_poi, tab_traj = st.tabs([
            "🔄 Reverse Range Ring",
            "🎯 Single Range Ring",
            "📊 Multiple Range Ring",
            "📏 Minimum Range Ring",
            "📍 Custom POI",
            "🚀 Launch Trajectory",
        ])

        reverse_command.help_tab(tab_rrr)
        single_command.help_tab(tab_single)
        multiple_command.help_tab(tab_multi)
        minimum_command.help_tab(tab_min)
        custom_poi_command.help_tab(tab_poi)
        trajectory_command.help_tab(tab_traj)


def _render_history() -> None:
    """Render command query/task history in reverse chronological order."""
    history = get_command_history()
    with st.expander("📜 Query & Task History", expanded=False):
        if not history:
            st.info("No command history yet.")
            return

        if st.button("🗑️ Clear History", key="clear_history_btn", use_container_width=True):
            clear_command_history()
            st.rerun()

        st.divider()

        for idx, entry in enumerate(history):
            timestamp = entry.get("timestamp", "Unknown time")
            entry_type = entry.get("type", "Query")
            text = entry.get("text", "")
            resolution = entry.get("resolution", "Pending")
            status = entry.get("status", "Pending")
            entry_output = entry.get("output")

            display_status = status.replace(" (Updated)", "")

            st.markdown(f"**{timestamp} | {entry_type}**")
            st.markdown(f"\"{text}\"")

            if resolution == "Reverse Range Ring":
                weapon_name = entry.get("weapon_name")
                weapon_range = entry.get("weapon_range_km")
                shooter = entry.get("shooter_country")
                target = entry.get("target_city")
                if weapon_name and shooter and target:
                    st.caption(f"🎯 {shooter} → {target}")
                    st.caption(f"🚀 {weapon_name} ({weapon_range:,.0f} km)")

            if resolution == "Minimum Range Ring":
                location_a = entry.get("location_a")
                location_b = entry.get("location_b")
                distance_km = entry.get("minimum_distance_km")
                location_type = entry.get("location_type", "")
                if location_a and location_b:
                    st.caption(
                        f"📏 {location_a} ↔ {location_b}"
                        + (f" • {distance_km:,.1f} km" if distance_km is not None else "")
                    )
                    if location_type:
                        st.caption(f"🗂️ Mode: {location_type.title()}")

            st.caption(f"Resolution: {resolution}")
            st.caption(f"Status: {display_status}")

            if entry_output is not None and isinstance(entry_output, RangeRingOutput):
                output_id = str(entry_output.output_id)
                cache_key = f"command_exports_{output_id}"
                is_cached = cache_key in st.session_state

                with st.expander(f"📥 Export Options {'(cached)' if is_cached else ''}", expanded=False):
                    if is_cached:
                        render_cached_export_links(entry_output, f"history_{idx}")
                    else:
                        st.caption("Exports not yet generated for this entry.")
                        if st.button("⚡ Generate Exports", key=f"gen_exports_{idx}", use_container_width=True):
                            render_js_export_controls(entry_output, f"history_{idx}")

            st.divider()


def _mock_intent_response(query: str) -> tuple[CommandOutput, str, str]:
    """Route query through pending handlers then initial parsers; fallback placeholder."""

    # Pending flows first
    for handler in (
        multiple_command.handle_pending,
        minimum_command.handle_pending,
        single_command.handle_pending,
        reverse_command.handle_pending,
        custom_poi_command.handle_pending,
    ):
        handled = handler(query)
        if handled:
            return handled

    # Initial parse flows (priority order mirrors previous behavior)
    for parser in (
        reverse_command.parse_initial,
        single_command.parse_initial,
        minimum_command.parse_initial,
        multiple_command.parse_initial,
        custom_poi_command.parse_initial,
        trajectory_command.parse_initial,
    ):
        parsed = parser(query)
        if parsed:
            return parsed

    response = (
        "**Answer Summary (Placeholder)**\n\n"
        f"You asked: **{query}**.\n\n"
        "The Command Center is ready to route this request to the appropriate analytical tool or summary "
        "pipeline once intent classification is connected."
    )
    return response, "Command Center Placeholder", "Answered"


def render_command_center() -> None:
    """Render the Command tab page layout."""
    st.header("⚡ ORRG – Command Center")

    query = _render_input_panel()
    if query:
        output, resolution, status = _mock_intent_response(query)

        if status != "Pending":
            set_command_output(output)

        if status != "Completed (Updated)":
            is_task = resolution in (
                "Reverse Range Ring",
                "Single Range Ring",
                "Minimum Range Ring",
                "Multiple Range Ring",
            )
            add_command_history_entry(
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "Task" if is_task else "Query",
                    "text": query,
                    "resolution": resolution,
                    "status": status,
                }
            )

        if status == "Pending" and (
            get_command_reverse_pending() is not None
            or get_command_single_pending() is not None
            or get_command_minimum_pending() is not None
            or get_command_multiple_pending() is not None
            or get_command_custom_poi_pending() is not None
        ):
            st.rerun()

    _render_help_section()
    _render_product_output_viewer()
    _render_history()
