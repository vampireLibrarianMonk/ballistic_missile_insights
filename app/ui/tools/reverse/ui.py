"""
UI rendering for the Reverse Range Ring tool.

This module was split out from app.ui.tools.tool_components to align with the
per-tool folder structure used elsewhere (e.g., single, multiple, minimum).
"""

from __future__ import annotations

import streamlit as st

from app.data.loaders import get_data_service
from app.geometry.services import generate_reverse_range_ring
from app.geometry.utils import geodesic_distance, _extract_all_coordinates
from app.models.inputs import (
    DistanceUnit,
    PointOfInterest,
    ReverseRangeRingInput,
)
from app.ui.layout.global_state import (
    get_map_style,
    add_tool_output,
    get_tool_state,
    clear_tool_outputs,
    bump_tool_viz_version,
)
from app.ui.tools.reverse.state import (
    get_reverse_available_systems,
    set_reverse_available_systems,
    get_reverse_min_distance,
    set_reverse_min_distance,
    is_reverse_calculated,
    set_reverse_calculated,
    reset_reverse_range_ring_state,
)
from app.ui.tools.shared import (
    render_output_panel,
    build_progress_callback,
)


def render_reverse_range_ring_tool() -> None:
    """Render the Reverse Range Ring Generator tool."""
    with st.expander("🔄 Reverse Range Ring Generator", expanded=False):
        st.markdown("""
        Identifies the geographic region from which a weapon system could reach a specified target.
        
        **Step 1:** Select target city and shooter country, then calculate which systems can reach the target.
        **Step 2:** Select an available system and generate the launch envelope map.
        """)
        
        data_service = get_data_service()
        
        # Initialize session state for reverse tool
        if "reverse_available_systems" not in st.session_state:
            st.session_state.reverse_available_systems = []
        if "reverse_min_distance" not in st.session_state:
            st.session_state.reverse_min_distance = None
        if "reverse_calculated" not in st.session_state:
            st.session_state.reverse_calculated = False
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**City Name (Target):**")
            cities = data_service.get_city_list()
            city_name = st.selectbox("Select Target City", options=cities, key="reverse_city")
            coords = data_service.get_city_coordinates(city_name)
            if coords:
                target_lat, target_lon = coords
                st.caption(f"📍 {target_lat:.4f}, {target_lon:.4f}")
            else:
                target_lat, target_lon = 0.0, 0.0
        
        with col2:
            st.markdown("**Country Name (Shooter):**")
            countries = data_service.get_country_list()
            shooter_country_name = st.selectbox("Select Shooter Country", options=countries, key="reverse_shooter_country")
            shooter_country_code = data_service.get_country_code(shooter_country_name) if shooter_country_name else None
        
        st.divider()
        
        # Step 1: Calculate available systems
        col_calc, col_status = st.columns([1, 2])
        
        with col_calc:
            if st.button("🔍 Calculate Availability", key="reverse_calculate"):
                if shooter_country_code and city_name:
                    with st.spinner("Calculating minimum distance and available systems..."):
                        try:
                            # Get shooter country geometry
                            shooter_geom = data_service.get_country_geometry(shooter_country_code)
                            
                            if shooter_geom:
                                # Calculate minimum distance from shooter country to target
                                # Sample boundary points to find closest point
                                coords_list = _extract_all_coordinates(shooter_geom)
                                
                                min_dist = float('inf')
                                for lon, lat in coords_list[:500]:  # Sample up to 500 points
                                    dist = geodesic_distance(lat, lon, target_lat, target_lon)
                                    if dist < min_dist:
                                        min_dist = dist
                                
                                set_reverse_min_distance(min_dist)
                                
                                # Get all weapon systems for this country
                                all_weapons = data_service.get_weapon_systems(shooter_country_code)
                                
                                # Filter to systems that can reach the target
                                available = [w for w in all_weapons if w["range_km"] >= min_dist]
                                available = sorted(available, key=lambda x: x["range_km"])
                                
                                set_reverse_available_systems(available)
                                set_reverse_calculated(True)
                                
                        except Exception as e:
                            st.error(f"Error calculating: {e}")
        
        with col_status:
            if is_reverse_calculated():
                min_dist = get_reverse_min_distance()
                if min_dist:
                    st.metric("Minimum Distance to Target", f"{min_dist:,.0f} km")
        
        # Display calculation results
        if is_reverse_calculated():
            available_systems = get_reverse_available_systems()
            
            if not available_systems:
                st.warning(f"⚠️ No weapon systems from **{shooter_country_name}** can reach **{city_name}**.")
                st.info(f"The minimum distance is **{get_reverse_min_distance():,.0f} km**, but no available systems have sufficient range.")
            else:
                st.success(f"✅ **{len(available_systems)}** system(s) from **{shooter_country_name}** can reach **{city_name}**")
                
                st.divider()
                
                # Step 2: Select system and generate map
                st.markdown("**Threat System(s) Availability:**")
                
                system_options = [f"{w['name']} ({w['range_km']:,.0f} km)" for w in available_systems]
                selected_system_str = st.selectbox(
                    "Select Weapon System",
                    options=system_options,
                    key="reverse_selected_system"
                )
                
                # Get the selected system details
                selected_idx = system_options.index(selected_system_str) if selected_system_str else 0
                selected_system = available_systems[selected_idx]
                selected_weapon_source = selected_system.get("source")
                
                resolution = st.selectbox("Resolution", options=["low", "normal", "high"], index=1, key="reverse_resolution")
                
                if st.button("🚀 Generate Launch Envelope", key="reverse_generate"):
                    progress_bar, update_progress = build_progress_callback("Initializing...")

                    try:
                        target = PointOfInterest(name=city_name, latitude=target_lat, longitude=target_lon)
                        input_data = ReverseRangeRingInput(
                            target_point=target,
                            range_value=selected_system["range_km"],
                            range_unit=DistanceUnit("km"),
                            weapon_system=selected_system["name"],
                            resolution=resolution,
                        )
                        # Attach weapon source for export attribution when present
                        setattr(input_data, "weapon_source", selected_weapon_source)

                        # Get shooter country geometry for intersection
                        shooter_geometry = data_service.get_country_geometry(shooter_country_code)

                        # Generate with progress callback - all updates come from the service
                        output = generate_reverse_range_ring(
                            input_data, 
                            threat_country_geometry=shooter_geometry,
                            threat_country_name=shooter_country_name,
                            progress_callback=update_progress
                        )

                        # Clear previous outputs and add new one
                        clear_tool_outputs("reverse_range_ring")
                        add_tool_output("reverse_range_ring", output)
                        bump_tool_viz_version("reverse_range_ring")

                        # Complete progress and rerun to render from session state
                        progress_bar.progress(1.0, text="100% - Complete!")
                        st.rerun()

                    except Exception as e:
                        progress_bar.progress(1.0, text="Error!")
                        st.error(f"Error generating range ring: {e}")
                
                # Render output from session state (persists across reruns including downloads)
                tool_state = get_tool_state("reverse_range_ring")
                if tool_state.get("outputs"):
                    output = tool_state["outputs"][-1]  # Get latest output
                    
                    st.success("Launch envelope generated!")

                    render_output_panel(
                        output,
                        tool_key="reverse_range_ring",
                        map_style=get_map_style(),
                        extra_metadata={
                            "vertex_count": getattr(output.metadata, "vertex_count", None),
                            "processing_time_ms": getattr(output.metadata, "processing_time_ms", None),
                            "range_km": getattr(output.metadata, "range_km", None),
                            "weapon_source": getattr(output.metadata, "weapon_source", None),
                        },
                    )
        else:
            st.info("👆 Select a target city and shooter country, then click **Calculate Availability** to see which systems can reach the target.")

        # Utility control for resetting the tool UI + visualization back to the initial state
        if st.button("🔄 Reset Tool", key="reverse_reset_tool", use_container_width=True):
            # Clear persisted computation + outputs
            reset_reverse_range_ring_state()
            bump_tool_viz_version("reverse_range_ring")

            # Clear Streamlit widget state so selectboxes return to defaults
            widget_keys = [
                "reverse_city",
                "reverse_shooter_country",
                "reverse_selected_system",
                "reverse_resolution",
            ]
            for k in widget_keys:
                if k in st.session_state:
                    del st.session_state[k]

            st.rerun()


__all__ = ["render_reverse_range_ring_tool"]
