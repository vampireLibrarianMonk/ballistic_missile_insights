"""
UI rendering for the Minimum Range Ring tool.

This module was split out from app.ui.tools.tool_components to align with the
per-tool folder structure used elsewhere (e.g., single, reverse, multiple).
"""

from __future__ import annotations

import streamlit as st
from shapely.geometry import Point

from app.data.loaders import get_data_service
from app.geometry.services import calculate_minimum_distance
from app.models.inputs import MinimumRangeRingInput
from app.ui.layout.global_state import (
    get_map_style,
    add_tool_output,
    get_tool_state,
    clear_tool_outputs,
    bump_tool_viz_version,
)
from app.ui.tools.minimum.state import (
    get_min_distance_result,
    set_min_distance_result,
)
from app.ui.tools.shared import (
    render_output_panel,
    build_progress_callback,
)


def render_minimum_range_ring_tool() -> None:
    """Render the Minimum Range Ring Generator tool."""
    with st.expander("📏 Minimum Range Ring Generator", expanded=False):
        st.markdown("""
        Calculate and visualize the minimum geodesic distance between two locations.
        """)
        
        data_service = get_data_service()
        
        # Location type selection
        location_type = st.radio(
            "Select Location Type",
            options=["Countries", "Cities"],
            horizontal=True,
            key="min_location_type",
        )
        
        col1, col2 = st.columns(2)
        
        if location_type == "Countries":
            countries = data_service.get_country_list()
            
            with col1:
                st.markdown("**Location A**")
                location_a_name = st.selectbox("Select Country A", options=countries, key="min_country_a")
                country_code_a = data_service.get_country_code(location_a_name) if location_a_name else None
                geom_a = data_service.get_country_geometry(country_code_a) if country_code_a else None
            
            with col2:
                st.markdown("**Location B**")
                location_b_name = st.selectbox("Select Country B", options=countries, index=1 if len(countries) > 1 else 0, key="min_country_b")
                country_code_b = data_service.get_country_code(location_b_name) if location_b_name else None
                geom_b = data_service.get_country_geometry(country_code_b) if country_code_b else None
        else:
            # Cities mode
            cities = data_service.get_city_list()
            
            with col1:
                st.markdown("**Location A**")
                location_a_name = st.selectbox("Select City A", options=cities, key="min_city_a")
                coords_a = data_service.get_city_coordinates(location_a_name)
                if coords_a:
                    lat_a, lon_a = coords_a
                    st.caption(f"📍 {lat_a:.4f}, {lon_a:.4f}")
                    geom_a = Point(lon_a, lat_a)
                else:
                    geom_a = None
                country_code_a = None
            
            with col2:
                st.markdown("**Location B**")
                # Get a different default city for B
                default_idx_b = 1 if len(cities) > 1 else 0
                location_b_name = st.selectbox("Select City B", options=cities, index=default_idx_b, key="min_city_b")
                coords_b = data_service.get_city_coordinates(location_b_name)
                if coords_b:
                    lat_b, lon_b = coords_b
                    st.caption(f"📍 {lat_b:.4f}, {lon_b:.4f}")
                    geom_b = Point(lon_b, lat_b)
                else:
                    geom_b = None
                country_code_b = None
        
        # Weapon System Reference Section
        st.divider()
        st.markdown("**Weapon System Reference (Optional):**")
        st.caption("Select a country and weapon system to see its range for comparison.")
        
        col_ws1, col_ws2 = st.columns(2)
        
        with col_ws1:
            # Country selection for weapon systems
            ws_countries = data_service.get_country_list()
            ws_country_name = st.selectbox(
                "Country",
                options=["-- Select Country --"] + ws_countries,
                key="min_ws_country",
            )
            ws_country_code = data_service.get_country_code(ws_country_name) if ws_country_name != "-- Select Country --" else None
        
        with col_ws2:
            # Weapon system selection with Name | Class | Range format
            if ws_country_code:
                weapons = data_service.get_weapon_systems(ws_country_code)
                if weapons:
                    # Build display options: "Name | Classification | Range km"
                    weapon_options = []
                    weapon_map = {}  # Map display string to weapon data
                    for w in weapons:
                        weapon_class = w.get("classification", "Unknown")
                        weapon_range = w.get("range_km", 0)
                        display_str = f"{w['name']} | {weapon_class} | {weapon_range:,.0f} km"
                        weapon_options.append(display_str)
                        weapon_map[display_str] = w
                    
                    selected_ws = st.selectbox(
                        "Weapon System",
                        options=weapon_options,
                        key="min_ws_weapon",
                    )
                    
                    # Show selected weapon details
                    if selected_ws and selected_ws in weapon_map:
                        ws_data = weapon_map[selected_ws]
                        st.info(f"🎯 **{ws_data['name']}**: {ws_data.get('range_km', 0):,.0f} km range")
                else:
                    st.selectbox("Weapon System", options=["No weapons available"], key="min_ws_weapon_empty", disabled=True)
            else:
                st.selectbox("Weapon System", options=["Select a country first"], key="min_ws_weapon_placeholder", disabled=True)
        
        st.divider()
        
        show_line = st.checkbox("Show minimum distance line", value=True, key="min_show_line")
        
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            generate_clicked = st.button("🚀 Calculate Minimum Distance", key="min_generate", use_container_width=True)
        with action_col2:
            if st.button("🧹 Clear Visualization", key="min_clear_viz", use_container_width=True):
                clear_tool_outputs("minimum_range_ring")
                bump_tool_viz_version("minimum_range_ring")
                # Also clear computed distance text so the panel truly resets
                set_min_distance_result(None)
                st.rerun()

        if generate_clicked:
            if geom_a is not None and geom_b is not None:
                progress_bar, update_progress = build_progress_callback("Initializing...")

                try:
                    input_data = MinimumRangeRingInput(
                        country_code_a=country_code_a,
                        country_code_b=country_code_b,
                        show_minimum_line=show_line,
                        show_buffer_rings=False,
                    )

                    output, result = calculate_minimum_distance(
                        input_data, geom_a, geom_b, location_a_name, location_b_name,
                        progress_callback=update_progress
                    )

                    # Store result in session state for persistence
                    set_min_distance_result(result)

                    # Clear previous outputs and add new one
                    clear_tool_outputs("minimum_range_ring")
                    add_tool_output("minimum_range_ring", output)
                    bump_tool_viz_version("minimum_range_ring")

                    # Complete progress and rerun to render from session state
                    progress_bar.progress(1.0, text="100% - Complete!")
                    st.rerun()

                except Exception as e:
                    progress_bar.progress(1.0, text="Error!")
                    st.error(f"Error calculating minimum distance: {e}")
            else:
                st.warning("Please select valid locations for both A and B.")
        
        # Render output from session state (persists across reruns including downloads)
        tool_state = get_tool_state("minimum_range_ring")
        if tool_state.get("outputs"):
            output = tool_state["outputs"][-1]  # Get latest output

            # Get result from session state
            result = get_min_distance_result()
            if result:
                st.success(f"Minimum distance: **{result.distance_km:,.1f} km**")

            render_output_panel(
                output,
                tool_key="minimum_range_ring",
                map_style=get_map_style(),
                extra_metadata={
                    "processing_time_ms": getattr(output.metadata, "processing_time_ms", None),
                    "range_km": getattr(output.metadata, "range_km", None),
                    "weapon_source": getattr(output.metadata, "weapon_source", None),
                },
            )


__all__ = ["render_minimum_range_ring_tool"]
