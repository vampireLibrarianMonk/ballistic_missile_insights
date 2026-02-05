"""
UI rendering for the Multiple Range Ring tool.

This module was split out from app.ui.tools.tool_components to align with the
per-tool folder structure used elsewhere (e.g., single, reverse, minimum).
"""

from __future__ import annotations

import streamlit as st

from app.data.loaders import get_data_service
from app.geometry.services import generate_multiple_range_rings
from app.models.inputs import (
    OriginType,
    DistanceUnit,
    PointOfInterest,
    MultipleRangeRingInput,
)
from app.ui.layout.global_state import (
    get_map_style,
    add_tool_output,
    get_tool_state,
    clear_tool_outputs,
    bump_tool_viz_version,
)
from app.ui.tools.multiple.state import get_multi_ranges, add_multi_range, remove_multi_range
from app.ui.tools.shared import (
    render_output_panel,
    build_progress_callback,
)


def render_multiple_range_ring_tool() -> None:
    """Render the Multiple Range Ring Generator tool."""
    with st.expander("🎯 Multiple Range Ring Generator", expanded=False):
        st.markdown("""
        Generate multiple concentric range rings representing different weapon systems or ranges.
        """)
        
        data_service = get_data_service()
        
        origin_type = st.selectbox(
            "Origin Type",
            options=["country", "point"],
            format_func=lambda x: "Country Boundary" if x == "country" else "Custom Point",
            key="multi_origin_type",
        )
        
        if origin_type == "country":
            countries = data_service.get_country_list()
            country_name = st.selectbox("Select Country", options=countries, key="multi_country")
            country_code = data_service.get_country_code(country_name) if country_name else None
        else:
            lat = st.number_input("Latitude", value=39.0, key="multi_lat")
            lon = st.number_input("Longitude", value=125.0, key="multi_lon")
            poi_name = st.text_input("Point Name", value="Custom Point", key="multi_poi_name")
            country_code = None
        
        st.markdown("**Add Ranges:**")
        
        # Get available weapon systems for selected country (if country origin)
        available_weapons = []
        weapon_names = ["Manual Entry"]
        if origin_type == "country" and country_code:
            available_weapons = data_service.get_weapon_systems(country_code)
            weapon_names = ["Manual Entry"] + [w['name'] for w in available_weapons]
        
        # Dynamic range inputs using state management
        multi_ranges = get_multi_ranges()
        
        ranges_to_remove = []
        for i, range_item in enumerate(multi_ranges):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                # Weapon system selection - same pattern as single range ring
                selected_weapon_name = st.selectbox(
                    f"Weapon System {i+1}",
                    options=weapon_names,
                    index=weapon_names.index(range_item.get("weapon_name", "Manual Entry")) if range_item.get("weapon_name", "Manual Entry") in weapon_names else 0,
                    key=f"multi_weapon_{i}",
                )
                range_item["weapon_name"] = selected_weapon_name
                
                # If weapon selected from database, get its range
                if selected_weapon_name != "Manual Entry":
                    weapon_range = data_service.get_weapon_range(selected_weapon_name, country_code)
                    range_value = weapon_range or 1000.0
                    range_item["label"] = selected_weapon_name
                else:
                    range_value = None
                    range_item["label"] = ""
            
            with col2:
                # Range value - mirrors single range ring behavior exactly
                # Key includes weapon name so switching weapons refreshes the value
                if range_value is None:
                    # Manual entry - show default or stored value
                    range_item["value"] = st.number_input(
                        f"Range {i+1}",
                        value=float(range_item.get("value", 1000)),
                        min_value=1.0,
                        step=100.0,
                        key=f"multi_range_manual_{i}",
                    )
                else:
                    # Weapon selected - key includes weapon name to force refresh on change
                    # Sanitize weapon name for key (remove spaces and special chars)
                    weapon_key = selected_weapon_name.replace(" ", "_").replace("-", "_")
                    range_item["value"] = st.number_input(
                        f"Range {i+1} (override)",
                        value=float(range_value),
                        min_value=1.0,
                        step=100.0,
                        key=f"multi_range_{i}_{weapon_key}",
                    )
            
            with col3:
                range_item["unit"] = st.selectbox(
                    f"Unit {i+1}",
                    options=["km", "mi", "nm"],
                    index=["km", "mi", "nm"].index(range_item.get("unit", "km")),
                    key=f"multi_unit_{i}",
                )
            
            with col4:
                st.write("")  # Spacing
                if st.button("❌", key=f"multi_remove_{i}"):
                    ranges_to_remove.append(i)
        
        for i in sorted(ranges_to_remove, reverse=True):
            remove_multi_range(i)
        
        if st.button("➕ Add Range", key="multi_add_range"):
            add_multi_range()
            st.rerun()
        
        resolution = st.selectbox("Resolution", options=["low", "normal", "high"], index=1, key="multi_resolution")
        
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            generate_clicked = st.button("🚀 Generate Multiple Rings", key="multi_generate", use_container_width=True)
        with action_col2:
            if st.button("🧹 Clear Visualization", key="multi_clear_viz", use_container_width=True):
                clear_tool_outputs("multiple_range_ring")
                bump_tool_viz_version("multiple_range_ring")
                st.rerun()

        if generate_clicked:
            if not multi_ranges:
                st.warning("Please add at least one range.")
                return

            progress_bar, update_progress = build_progress_callback("Initializing...")

            try:
                # Build range tuples and capture a single weapon_source (first non-empty from selected weapons)
                ranges = []
                weapon_source = None
                for r in multi_ranges:
                    ranges.append((r["value"], DistanceUnit(r["unit"]), r.get("label")))
                    if not weapon_source and r.get("weapon_name") and r.get("weapon_name") != "Manual Entry":
                        # Look up source from the weapon info
                        info = next((w for w in available_weapons if w.get("name") == r.get("weapon_name")), None)
                        if info and info.get("source"):
                            weapon_source = info.get("source")

                if origin_type == "country" and country_code:
                    input_data = MultipleRangeRingInput(
                        origin_type=OriginType.COUNTRY,
                        country_code=country_code,
                        ranges=ranges,
                        weapon_source=weapon_source,
                        resolution=resolution,
                    )
                    origin_geom = data_service.get_country_geometry(country_code)

                    output = generate_multiple_range_rings(
                        input_data, origin_geom, country_name,
                        progress_callback=update_progress
                    )
                else:
                    poi = PointOfInterest(name=poi_name, latitude=lat, longitude=lon)

                    input_data = MultipleRangeRingInput(
                        origin_type=OriginType.POINT,
                        origin_point=poi,
                        ranges=ranges,
                        weapon_source=weapon_source,
                        resolution=resolution,
                    )

                    output = generate_multiple_range_rings(
                        input_data,
                        progress_callback=update_progress
                    )

                # Clear previous outputs and add new one
                clear_tool_outputs("multiple_range_ring")
                add_tool_output("multiple_range_ring", output)
                bump_tool_viz_version("multiple_range_ring")
                st.rerun()  # Rerun to render from session state

            except Exception as e:
                progress_bar.progress(1.0, text="Error!")
                st.error(f"Error: {e}")
        
        # Render output from session state (persists across reruns)
        tool_state = get_tool_state("multiple_range_ring")
        if tool_state.get("outputs"):
            output = tool_state["outputs"][-1]  # Get latest output

            render_output_panel(
                output,
                tool_key="multiple_range_ring",
                map_style=get_map_style(),
                extra_metadata={
                    "layer_count": len(output.layers),
                    "processing_time_ms": getattr(output.metadata, "processing_time_ms", None),
                    "weapon_source": getattr(output.metadata, "weapon_source", None),
                },
            )


__all__ = ["render_multiple_range_ring_tool"]
