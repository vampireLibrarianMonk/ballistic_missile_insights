"""
UI rendering for the Single Range Ring tool.

This module was split out from app.ui.tools.tool_components to align with the
per-tool folder structure used elsewhere (e.g., custom_poi, multiple, reverse).
"""

from __future__ import annotations

import streamlit as st
from shapely.geometry import Point

from app.data.loaders import get_data_service
from app.geometry.services import generate_single_range_ring
from app.models.inputs import (
    OriginType,
    DistanceUnit,
    PointOfInterest,
    SingleRangeRingInput,
)
from app.rendering.pydeck_adapter import render_range_ring_output
from app.ui.layout.global_state import (
    is_analyst_mode,
    get_map_style,
    add_tool_output,
    get_tool_state,
    clear_tool_outputs,
)
from app.ui.tools.single.state import reset_single_range_ring_state
from app.ui.tools.shared import (
    get_weapon_selection_and_range,
    render_range_input_with_weapon_key,
    render_map_with_legend,
    render_export_controls,
)


def render_single_range_ring_tool() -> None:
    """Render the Single Range Ring Generator tool."""
    with st.expander("🎯 Single Range Ring Generator", expanded=False):
        st.markdown(
            """
            Generate a single geodesic range ring from a country boundary or point of origin.
            """
        )

        data_service = get_data_service()

        col1, col2 = st.columns(2)

        with col1:
            origin_type = st.selectbox(
                "Origin Type",
                options=["country", "point"],
                format_func=lambda x: "Country Boundary" if x == "country" else "Custom Point",
                key="single_origin_type",
            )

            if origin_type == "country":
                countries = data_service.get_country_list()
                country_name = st.selectbox(
                    "Select Country",
                    options=countries,
                    key="single_country",
                )
                country_code = data_service.get_country_code(country_name) if country_name else None

                if country_code:
                    weapons = data_service.get_weapon_systems(country_code)
                    weapon_names = ["Manual Entry"] + [w["name"] for w in weapons]
                    selected_weapon = st.selectbox(
                        "Weapon System",
                        options=weapon_names,
                        key="single_weapon",
                    )

                    range_value, label_for_legend = get_weapon_selection_and_range(
                        data_service, country_code, selected_weapon
                    )
                else:
                    selected_weapon = "Manual Entry"
                    range_value = None
                    label_for_legend = ""
            else:
                lat = st.number_input(
                    "Latitude", value=39.0, min_value=-90.0, max_value=90.0, key="single_lat"
                )
                lon = st.number_input(
                    "Longitude", value=125.0, min_value=-180.0, max_value=180.0, key="single_lon"
                )
                poi_name = st.text_input("Point Name", value="Custom Point", key="single_poi_name")
                country_code = None
                selected_weapon = "Manual Entry"
                range_value = None
                label_for_legend = ""

        with col2:
            # Use shared range input function with weapon-based key
            range_value = render_range_input_with_weapon_key(
                db_range_value=range_value,
                stored_range_value=1000.0,
                selected_weapon_name=selected_weapon,
                key_prefix="single",
                label_base="Range Value",
            )

            range_unit = st.selectbox(
                "Distance Unit",
                options=[u.value for u in DistanceUnit],
                index=0,
                key="single_unit",
            )

            resolution = st.selectbox(
                "Resolution",
                options=["low", "normal", "high"],
                index=1,
                key="single_resolution",
            )

        if st.button("🚀 Generate Range Ring", key="single_generate"):
            progress_bar = st.progress(0, text="Initializing...")

            def update_progress(pct: float, status: str):
                progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")

            try:
                if origin_type == "country" and country_code:
                    weapon_source = None
                    if selected_weapon != "Manual Entry":
                        weapon_info = data_service.get_weapon_info(selected_weapon, country_code)
                        if weapon_info:
                            weapon_source = weapon_info.get("source")

                    input_data = SingleRangeRingInput(
                        origin_type=OriginType.COUNTRY,
                        country_code=country_code,
                        range_value=range_value,
                        range_unit=DistanceUnit(range_unit),
                        weapon_system=selected_weapon if selected_weapon != "Manual Entry" else None,
                        weapon_source=weapon_source,
                        resolution=resolution,
                    )
                    origin_geom = data_service.get_country_geometry(country_code)
                    output = generate_single_range_ring(
                        input_data, origin_geom, country_name, progress_callback=update_progress
                    )
                else:
                    poi = PointOfInterest(name=poi_name, latitude=lat, longitude=lon)
                    input_data = SingleRangeRingInput(
                        origin_type=OriginType.POINT,
                        origin_point=poi,
                        range_value=range_value,
                        range_unit=DistanceUnit(range_unit),
                        resolution=resolution,
                    )
                    output = generate_single_range_ring(
                        input_data, progress_callback=update_progress
                    )

                progress_bar.progress(1.0, text="100% - Complete!")

                reset_single_range_ring_state()
                add_tool_output("single_range_ring", output)
                st.rerun()

            except Exception as e:
                progress_bar.progress(1.0, text="Error!")
                st.error(f"Error generating range ring: {e}")

        tool_state = get_tool_state("single_range_ring")
        if tool_state.get("outputs"):
            output = tool_state["outputs"][-1]

            st.success("Range ring generated!")

            st.subheader(output.title)
            if output.subtitle:
                st.caption(output.subtitle)

            deck = render_range_ring_output(output, get_map_style())
            render_map_with_legend(deck, output)

            if is_analyst_mode():
                with st.expander("📊 Technical Metadata"):
                    st.json(
                        {
                            "output_id": str(output.output_id),
                            "vertex_count": output.metadata.vertex_count,
                            "processing_time_ms": output.metadata.processing_time_ms,
                            "range_km": output.metadata.range_km,
                            "range_classification": output.metadata.range_classification,
                        }
                    )

            render_export_controls(output, "single_range_ring")


__all__ = ["render_single_range_ring_tool"]