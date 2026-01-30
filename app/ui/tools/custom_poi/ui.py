"""
UI rendering for the Custom POI Range Ring tool.

This module was split out from app.ui.tools.tool_components to align with the
per-tool folder structure used elsewhere (e.g., single, reverse, minimum, multiple).
"""

from __future__ import annotations

import streamlit as st

from app.models.inputs import (
    DistanceUnit,
    PointOfInterest,
)
from app.rendering.pydeck_adapter import render_range_ring_output
from app.ui.layout.global_state import (
    is_analyst_mode,
    get_map_style,
    add_tool_output,
    get_tool_state,
    clear_tool_outputs,
)
from app.ui.tools.custom_poi.state import (
    get_custom_pois,
    add_custom_poi,
    update_custom_poi,
    remove_custom_poi,
    get_selected_poi_idx,
    set_selected_poi_idx,
    get_form_version,
    increment_form_version,
    get_prefill_data,
    set_prefill_data,
)
from app.ui.tools.shared import (
    render_map_with_legend,
    render_export_controls,
)


def render_custom_poi_tool() -> None:
    """Render the Custom POI Range Ring Generator tool."""
    with st.expander("📍 Custom POI Range Ring Generator", expanded=False):
        st.markdown("""
        Generate minimum/maximum "donut" range rings from one or more user-defined points of interest.
        Each POI has its own range settings.
        """)
        
        # Generate unique key prefix based on form version
        form_key = f"cpoi_v{get_form_version()}"
        
        # Get prefill values (either from edit mode or defaults for add mode)
        prefill = get_prefill_data() or {}
        default_name = prefill.get("name", "")
        default_lat = prefill.get("lat", 0.0)
        default_lon = prefill.get("lon", 0.0)
        default_min_range = prefill.get("min_range", 0.0)
        default_max_range = prefill.get("max_range", 1.0)
        default_unit = prefill.get("unit", "km")
        
        st.markdown("**Points of Interest:**")
        
        # Get custom POIs using state management
        custom_pois = get_custom_pois()
        selected_idx = get_selected_poi_idx()
        
        # Display existing POIs with radio buttons for selection
        if custom_pois:
            # Build display labels with range info
            poi_options = ["➕ Add New POI"]
            for poi in custom_pois:
                min_r = poi.get('min_range', 0)
                max_r = poi.get('max_range', 1000)
                unit = poi.get('unit', 'km')
                if min_r > 0:
                    range_str = f"{min_r:,.0f}-{max_r:,.0f} {unit}"
                else:
                    range_str = f"{max_r:,.0f} {unit}"
                poi_options.append(f"📍 {poi['name']} | {range_str} | (Lat: {poi['lat']:.4f}, Long: {poi['lon']:.4f})")
            
            # Determine current selection index (0 = new, 1+ = edit existing)
            current_selection = 0 if selected_idx is None else selected_idx + 1
            
            selected_option = st.radio(
                "Select POI to edit or add new:",
                options=poi_options,
                index=current_selection,
                key="custom_poi_radio",
                horizontal=False,
            )
            
            # Determine which POI is selected
            option_idx = poi_options.index(selected_option)
            if option_idx == 0:
                # Add new mode
                if selected_idx is not None:
                    # Switched from edit to add mode - increment version to get fresh widgets
                    set_selected_poi_idx(None)
                    set_prefill_data(None)  # Clear prefill for add mode
                    increment_form_version()
                    st.rerun()
                edit_mode = False
                edit_idx = None
            else:
                # Edit existing mode
                edit_idx = option_idx - 1
                if selected_idx != edit_idx:
                    # Switched to different POI - load its values and increment version
                    set_selected_poi_idx(edit_idx)
                    poi = custom_pois[edit_idx]
                    set_prefill_data({
                        "name": poi["name"],
                        "lat": poi["lat"],
                        "lon": poi["lon"],
                        "min_range": poi.get("min_range", 0.0),
                        "max_range": poi.get("max_range", 1000.0),
                        "unit": poi.get("unit", "km"),
                    })
                    increment_form_version()
                    st.rerun()
                edit_mode = True
        else:
            st.info("No POIs added yet. Add your first point of interest below.")
            edit_mode = False
            edit_idx = None
        
        st.divider()
        
        # Input form for adding/editing - use version-based keys to force clearing
        if edit_mode:
            st.markdown(f"**Editing: {custom_pois[edit_idx]['name']}**")
        else:
            st.markdown("**Add New POI:**")
        
        # Row 1: Name
        poi_name = st.text_input(
            "POI Name",
            value=default_name,
            key=f"{form_key}_name",
        )
        
        # Row 2: Location
        col1, col2 = st.columns(2)
        with col1:
            poi_lat = st.number_input(
                "Latitude",
                value=default_lat,
                min_value=-90.0,
                max_value=90.0,
                key=f"{form_key}_lat",
            )
        with col2:
            poi_lon = st.number_input(
                "Longitude",
                value=default_lon,
                min_value=-180.0,
                max_value=180.0,
                key=f"{form_key}_lon",
            )
        
        # Row 3: Range settings (per POI)
        st.markdown("**Range Settings for this POI:**")
        col3, col4, col5 = st.columns([2, 2, 1])
        with col3:
            poi_min_range = st.number_input(
                "Min Range (0 for solid)",
                value=default_min_range,
                min_value=0.0,
                key=f"{form_key}_min_range",
            )
        with col4:
            poi_max_range = st.number_input(
                "Max Range",
                value=default_max_range,
                min_value=1.0,
                key=f"{form_key}_max_range",
            )
        with col5:
            unit_options = [u.value for u in DistanceUnit]
            unit_idx = unit_options.index(default_unit) if default_unit in unit_options else 0
            poi_unit = st.selectbox(
                "Unit",
                options=unit_options,
                index=unit_idx,
                key=f"{form_key}_unit",
            )
        
        # Action buttons
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if edit_mode:
                # Finalize (update) button when editing
                if st.button("✅ Finalize", key="custom_finalize_poi", use_container_width=True):
                    if poi_name:
                        if poi_max_range <= poi_min_range and poi_min_range > 0:
                            st.warning("Max range must be greater than min range.")
                        else:
                            update_custom_poi(edit_idx, {
                                "name": poi_name,
                                "lat": poi_lat,
                                "lon": poi_lon,
                                "min_range": poi_min_range,
                                "max_range": poi_max_range,
                                "unit": poi_unit,
                            })
                            # Reset to add mode after finalizing - increment version for fresh widgets
                            set_selected_poi_idx(None)
                            set_prefill_data(None)  # Clear prefill
                            increment_form_version()
                            st.rerun()
                    else:
                        st.warning("Please enter a POI name.")
            else:
                # Add button when adding new
                if st.button("➕ Add POI", key="custom_add_poi", use_container_width=True):
                    if poi_name:
                        if poi_max_range <= poi_min_range and poi_min_range > 0:
                            st.warning("Max range must be greater than min range.")
                        else:
                            add_custom_poi({
                                "name": poi_name,
                                "lat": poi_lat,
                                "lon": poi_lon,
                                "min_range": poi_min_range,
                                "max_range": poi_max_range,
                                "unit": poi_unit,
                            })
                            # Clear form after adding - increment version for fresh widgets
                            set_prefill_data(None)  # Clear prefill
                            increment_form_version()
                            st.rerun()
                    else:
                        st.warning("Please enter a POI name.")
        
        with col_btn2:
            if edit_mode:
                # Delete button when editing
                if st.button("🗑️ Delete", key="custom_delete_poi", use_container_width=True, type="secondary"):
                    remove_custom_poi(edit_idx)
                    # Reset to add mode after deleting - increment version for fresh widgets
                    set_selected_poi_idx(None)
                    set_prefill_data(None)  # Clear prefill
                    increment_form_version()
                    st.rerun()
        
        st.divider()
        
        # Global settings
        st.markdown("**Generation Settings:**")
        resolution = st.selectbox("Resolution", options=["low", "normal", "high"], index=1, key="custom_resolution")
        
        if st.button("🚀 Generate POI Rings", key="custom_generate"):
            if not custom_pois:
                st.warning("Please add at least one POI.")
                return
            
            with st.spinner("Generating..."):
                try:
                    from app.geometry.services import generate_custom_poi_range_ring_multi
                    
                    # Build list of POIs with their individual ranges
                    poi_data_list = []
                    for p in custom_pois:
                        poi_data_list.append({
                            "poi": PointOfInterest(name=p["name"], latitude=p["lat"], longitude=p["lon"]),
                            "min_range": p.get("min_range", 0.0),
                            "max_range": p.get("max_range", 1000.0),
                            "unit": DistanceUnit(p.get("unit", "km")),
                        })
                    
                    output = generate_custom_poi_range_ring_multi(
                        poi_data_list=poi_data_list,
                        resolution=resolution,
                    )
                    
                    clear_tool_outputs("custom_poi_range_ring")
                    add_tool_output("custom_poi_range_ring", output)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Render output from session state (persists across reruns)
        tool_state = get_tool_state("custom_poi_range_ring")
        if tool_state.get("outputs"):
            output = tool_state["outputs"][-1]
            
            st.success("POI rings generated!")
            st.subheader(output.title)
            st.caption(output.subtitle)
            
            deck = render_range_ring_output(output, get_map_style())
            render_map_with_legend(deck, output)
            
            if is_analyst_mode():
                with st.expander("📊 Technical Metadata"):
                    st.json({
                        "output_id": str(output.output_id),
                        "processing_time_ms": output.metadata.processing_time_ms if output.metadata else None,
                        "poi_count": output.metadata.point_count if output.metadata else None,
                    })
            
            render_export_controls(output, "custom_poi_range_ring")


__all__ = ["render_custom_poi_tool"]
