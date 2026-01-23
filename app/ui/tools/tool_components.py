"""
Tool UI components for ORRG.
Renders all five analytical tools with their inputs, outputs, and export controls.
"""

import streamlit as st
from typing import Optional

from app.data.loaders import get_data_service
from app.models.inputs import (
    OriginType,
    DistanceUnit,
    PointOfInterest,
    SingleRangeRingInput,
    MultipleRangeRingInput,
    ReverseRangeRingInput,
    MinimumRangeRingInput,
    CustomPOIRangeRingInput,
)
from app.geometry.services import (
    generate_single_range_ring,
    generate_multiple_range_rings,
    generate_reverse_range_ring,
    calculate_minimum_distance,
    generate_custom_poi_range_ring,
)
from app.rendering.pydeck_adapter import render_range_ring_output
from app.ui.layout.global_state import (
    is_analyst_mode,
    get_map_style,
    add_tool_output,
    get_tool_state,
    clear_tool_outputs,
)
from app.exports.geojson import export_to_geojson_string
from app.exports.kmz import export_to_kmz_bytes
from app.exports.png import export_to_png_bytes
from app.exports.pdf import export_to_pdf_bytes


def render_map_with_legend(deck, output, height: int = 500) -> None:
    """
    Render a pydeck map with an integrated legend inside the map container.
    
    Args:
        deck: PyDeck Deck object
        output: RangeRingOutput containing layers for legend
        height: Height of the map in pixels
    """
    import streamlit.components.v1 as components
    from app.models.outputs import GeometryType
    
    # Build legend items from layers
    legend_items = []
    for layer in output.layers:
        if layer.fill_color and layer.range_km:
            # Range ring layers with range_km
            legend_items.append({
                "name": layer.name,
                "color": layer.fill_color,
                "range_km": layer.range_km,
                "is_point": False,
            })
        elif layer.fill_color and layer.geometry_type == GeometryType.POINT:
            # Point layers (like target cities)
            legend_items.append({
                "name": layer.name,
                "color": layer.fill_color,
                "range_km": None,
                "is_point": True,
            })
    
    # Build legend HTML
    legend_items_html = ""
    for item in legend_items:
        if item["is_point"]:
            # Point marker (circle)
            legend_items_html += f'''
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <div style="width: 14px; height: 14px; background-color: {item["color"]}; 
                     border: 2px solid #333; border-radius: 50%; 
                     margin-right: 8px; flex-shrink: 0;"></div>
                <div style="font-size: 11px; line-height: 1.3;">
                    <strong>{item["name"]}</strong>
                </div>
            </div>'''
        else:
            # Range ring (square)
            legend_items_html += f'''
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <div style="width: 14px; height: 14px; background-color: {item["color"]}; 
                     opacity: 0.8; border: 2px solid {item["color"]}; border-radius: 3px; 
                     margin-right: 8px; flex-shrink: 0;"></div>
                <div style="font-size: 11px; line-height: 1.3;">
                    <strong>{item["name"]}</strong><br/>
                    <span style="color: #555;">({item["range_km"]:,.0f} km)</span>
                </div>
            </div>'''
    
    # Get the deck HTML
    deck_html = deck.to_html(as_string=True)
    
    # Add CSS to enable touch/trackpad interactions
    touch_css = '''
    <style>
        html, body, canvas, #deck-container, #deckgl-wrapper, .deck-tooltip {
            touch-action: manipulation !important;
        }
        canvas {
            touch-action: none !important;
        }
    </style>
    '''
    deck_html = deck_html.replace('<head>', f'<head>{touch_css}')
    
    # Map controls help overlay
    zoom_control = '''
    <div id="zoom-help" style="
        position: absolute;
        top: 10px;
        right: 10px;
        background-color: rgba(255, 255, 255, 0.9);
        border: 1px solid #999;
        border-radius: 4px;
        padding: 6px 10px;
        box-shadow: 1px 1px 4px rgba(0,0,0,0.2);
        z-index: 1000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 10px;
        color: #333;
        line-height: 1.5;
    ">
        <strong>🗺️ Controls:</strong><br/>
        Mouse wheel: Zoom<br/>
        Click + Drag: Pan<br/>
        Double-click: Zoom in
    </div>
    '''
    
    # Create legend overlay HTML to inject
    legend_overlay = f'''
    <div id="legend-overlay" style="
        position: absolute;
        bottom: 20px;
        right: 20px;
        background-color: rgba(255, 255, 255, 0.92);
        border: 2px solid #333;
        border-radius: 6px;
        padding: 8px 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        max-width: 260px;
        z-index: 1000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    ">
        {legend_items_html}
    </div>
    '''
    
    # Inject zoom control and legend into deck HTML
    deck_html = deck_html.replace('</body>', f'{zoom_control}</body>')
    if legend_items:
        deck_html = deck_html.replace('</body>', f'{legend_overlay}</body>')
    
    # Render using components.html for proper integration
    components.html(deck_html, height=height, scrolling=False)


def render_export_controls(output, tool_key: str) -> None:
    """Render export controls for a tool output."""
    col1, col2, col3, col4 = st.columns(4)
    
    include_metadata = is_analyst_mode()
    
    with col1:
        geojson_data = export_to_geojson_string(output, include_metadata=include_metadata)
        st.download_button(
            "📥 GeoJSON",
            data=geojson_data,
            file_name=f"{tool_key}_{output.output_id}.geojson",
            mime="application/geo+json",
            key=f"geojson_{tool_key}_{output.output_id}",
        )
    
    with col2:
        kmz_data = export_to_kmz_bytes(output, include_metadata=include_metadata)
        st.download_button(
            "📥 KMZ",
            data=kmz_data,
            file_name=f"{tool_key}_{output.output_id}.kmz",
            mime="application/vnd.google-earth.kmz",
            key=f"kmz_{tool_key}_{output.output_id}",
        )
    
    with col3:
        png_data = export_to_png_bytes(output)
        st.download_button(
            "📥 PNG",
            data=png_data,
            file_name=f"{tool_key}_{output.output_id}.png",
            mime="image/png",
            key=f"png_{tool_key}_{output.output_id}",
        )
    
    with col4:
        pdf_data = export_to_pdf_bytes(output, include_metadata=include_metadata)
        st.download_button(
            "📥 PDF",
            data=pdf_data,
            file_name=f"{tool_key}_{output.output_id}.pdf",
            mime="application/pdf",
            key=f"pdf_{tool_key}_{output.output_id}",
        )


def render_single_range_ring_tool() -> None:
    """Render the Single Range Ring Generator tool."""
    with st.expander("🎯 Single Range Ring Generator", expanded=False):
        st.markdown("""
        Generate a single geodesic range ring from a country boundary or point of origin.
        """)
        
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
                
                # Weapon system selection
                if country_code:
                    weapons = data_service.get_weapon_systems(country_code)
                    weapon_names = ["Manual Entry"] + [w["name"] for w in weapons]
                    selected_weapon = st.selectbox(
                        "Weapon System",
                        options=weapon_names,
                        key="single_weapon",
                    )
                    
                    if selected_weapon != "Manual Entry":
                        weapon_range = data_service.get_weapon_range(selected_weapon, country_code)
                        range_value = weapon_range or 1000.0
                    else:
                        range_value = None
            else:
                lat = st.number_input("Latitude", value=39.0, min_value=-90.0, max_value=90.0, key="single_lat")
                lon = st.number_input("Longitude", value=125.0, min_value=-180.0, max_value=180.0, key="single_lon")
                poi_name = st.text_input("Point Name", value="Custom Point", key="single_poi_name")
                country_code = None
                selected_weapon = "Manual Entry"
                range_value = None
        
        with col2:
            if range_value is None:
                range_value = st.number_input(
                    "Range Value",
                    value=1000.0,
                    min_value=1.0,
                    step=100.0,
                    key="single_range_value",
                )
            else:
                range_value = st.number_input(
                    "Range Value (override)",
                    value=float(range_value),
                    min_value=1.0,
                    step=100.0,
                    key="single_range_override",
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
            # Create progress bar container
            progress_bar = st.progress(0, text="Initializing...")
            status_text = st.empty()
            
            def update_progress(pct: float, status: str):
                """Callback to update progress bar."""
                progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")
            
            try:
                if origin_type == "country" and country_code:
                    input_data = SingleRangeRingInput(
                        origin_type=OriginType.COUNTRY,
                        country_code=country_code,
                        range_value=range_value,
                        range_unit=DistanceUnit(range_unit),
                        weapon_system=selected_weapon if selected_weapon != "Manual Entry" else None,
                        resolution=resolution,
                    )
                    origin_geom = data_service.get_country_geometry(country_code)
                    output = generate_single_range_ring(
                        input_data, origin_geom, country_name,
                        progress_callback=update_progress
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
                        input_data,
                        progress_callback=update_progress
                    )
                
                # Complete progress
                progress_bar.progress(1.0, text="100% - Complete!")
                
                add_tool_output("single_range_ring", output)
                st.success("Range ring generated!")
                
                # Display result
                st.subheader(output.title)
                if output.subtitle:
                    st.caption(output.subtitle)
                
                # Render map with legend overlay
                deck = render_range_ring_output(output, get_map_style())
                render_map_with_legend(deck, output)
                
                # Analyst mode metadata
                if is_analyst_mode():
                    with st.expander("📊 Technical Metadata"):
                        st.json({
                            "output_id": str(output.output_id),
                            "vertex_count": output.metadata.vertex_count,
                            "processing_time_ms": output.metadata.processing_time_ms,
                            "range_km": output.metadata.range_km,
                            "range_classification": output.metadata.range_classification,
                        })
                
                # Export controls
                render_export_controls(output, "single_range_ring")
                
            except Exception as e:
                progress_bar.progress(1.0, text="Error!")
                st.error(f"Error generating range ring: {e}")


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
        
        # Dynamic range inputs
        if "multi_ranges" not in st.session_state:
            st.session_state.multi_ranges = [{"value": 500, "unit": "km", "label": "SRBM"}]
        
        ranges_to_remove = []
        for i, range_item in enumerate(st.session_state.multi_ranges):
            col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
            with col1:
                range_item["value"] = st.number_input(f"Range {i+1}", value=range_item["value"], key=f"multi_range_{i}")
            with col2:
                range_item["unit"] = st.selectbox(f"Unit {i+1}", options=["km", "mi", "nm"], key=f"multi_unit_{i}")
            with col3:
                range_item["label"] = st.text_input(f"Label {i+1}", value=range_item.get("label", ""), key=f"multi_label_{i}")
            with col4:
                if st.button("❌", key=f"multi_remove_{i}"):
                    ranges_to_remove.append(i)
        
        for i in sorted(ranges_to_remove, reverse=True):
            st.session_state.multi_ranges.pop(i)
        
        if st.button("➕ Add Range", key="multi_add_range"):
            st.session_state.multi_ranges.append({"value": 1000, "unit": "km", "label": ""})
            st.rerun()
        
        resolution = st.selectbox("Resolution", options=["low", "normal", "high"], index=1, key="multi_resolution")
        
        if st.button("🚀 Generate Multiple Rings", key="multi_generate"):
            if not st.session_state.multi_ranges:
                st.warning("Please add at least one range.")
                return
            
            with st.spinner("Generating range rings..."):
                try:
                    ranges = [
                        (r["value"], DistanceUnit(r["unit"]), r.get("label"))
                        for r in st.session_state.multi_ranges
                    ]
                    
                    if origin_type == "country" and country_code:
                        input_data = MultipleRangeRingInput(
                            origin_type=OriginType.COUNTRY,
                            country_code=country_code,
                            ranges=ranges,
                            resolution=resolution,
                        )
                        origin_geom = data_service.get_country_geometry(country_code)
                        output = generate_multiple_range_rings(input_data, origin_geom, country_name)
                    else:
                        poi = PointOfInterest(name=poi_name, latitude=lat, longitude=lon)
                        input_data = MultipleRangeRingInput(
                            origin_type=OriginType.POINT,
                            origin_point=poi,
                            ranges=ranges,
                            resolution=resolution,
                        )
                        output = generate_multiple_range_rings(input_data)
                    
                    add_tool_output("multiple_range_ring", output)
                    st.success("Range rings generated!")
                    
                    st.subheader(output.title)
                    deck = render_range_ring_output(output, get_map_style())
                    render_map_with_legend(deck, output)
                    render_export_controls(output, "multiple_range_ring")
                    
                except Exception as e:
                    st.error(f"Error: {e}")


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
                            from app.geometry.utils import geodesic_distance
                            
                            # Get shooter country geometry
                            shooter_geom = data_service.get_country_geometry(shooter_country_code)
                            
                            if shooter_geom:
                                # Calculate minimum distance from shooter country to target
                                # Sample boundary points to find closest point
                                from app.geometry.utils import _extract_all_coordinates
                                coords_list = _extract_all_coordinates(shooter_geom)
                                
                                min_dist = float('inf')
                                for lon, lat in coords_list[:500]:  # Sample up to 500 points
                                    dist = geodesic_distance(lat, lon, target_lat, target_lon)
                                    if dist < min_dist:
                                        min_dist = dist
                                
                                st.session_state.reverse_min_distance = min_dist
                                
                                # Get all weapon systems for this country
                                all_weapons = data_service.get_weapon_systems(shooter_country_code)
                                
                                # Filter to systems that can reach the target
                                available = [w for w in all_weapons if w["range_km"] >= min_dist]
                                available = sorted(available, key=lambda x: x["range_km"])
                                
                                st.session_state.reverse_available_systems = available
                                st.session_state.reverse_calculated = True
                                
                        except Exception as e:
                            st.error(f"Error calculating: {e}")
        
        with col_status:
            if st.session_state.reverse_calculated:
                min_dist = st.session_state.reverse_min_distance
                if min_dist:
                    st.metric("Minimum Distance to Target", f"{min_dist:,.0f} km")
        
        # Display calculation results
        if st.session_state.reverse_calculated:
            available_systems = st.session_state.reverse_available_systems
            
            if not available_systems:
                st.warning(f"⚠️ No weapon systems from **{shooter_country_name}** can reach **{city_name}**.")
                st.info(f"The minimum distance is **{st.session_state.reverse_min_distance:,.0f} km**, but no available systems have sufficient range.")
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
                
                resolution = st.selectbox("Resolution", options=["low", "normal", "high"], index=1, key="reverse_resolution")
                
                if st.button("🚀 Generate Launch Envelope", key="reverse_generate"):
                    # Create progress bar container
                    progress_bar = st.progress(0, text="Initializing...")
                    
                    def update_progress(pct: float, status: str):
                        """Callback to update progress bar."""
                        progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")
                    
                    try:
                        update_progress(0.1, "Loading target coordinates...")
                        
                        target = PointOfInterest(name=city_name, latitude=target_lat, longitude=target_lon)
                        input_data = ReverseRangeRingInput(
                            target_point=target,
                            range_value=selected_system["range_km"],
                            range_unit=DistanceUnit("km"),
                            weapon_system=selected_system["name"],
                            resolution=resolution,
                        )
                        
                        update_progress(0.2, "Loading shooter country geometry...")
                        
                        # Get shooter country geometry for intersection
                        shooter_geometry = data_service.get_country_geometry(shooter_country_code)
                        
                        update_progress(0.3, "Calculating reach envelope...")
                        update_progress(0.5, "Computing distance ranges...")
                        update_progress(0.7, "Generating launch region...")
                        
                        output = generate_reverse_range_ring(
                            input_data, 
                            threat_country_geometry=shooter_geometry,
                            threat_country_name=shooter_country_name
                        )
                        
                        update_progress(0.9, "Rendering output...")
                        
                        add_tool_output("reverse_range_ring", output)
                        
                        # Complete progress
                        progress_bar.progress(1.0, text="100% - Complete!")
                        
                        st.success("Launch envelope generated!")
                        
                        st.subheader(output.title)
                        st.caption(output.subtitle)
                        st.markdown(f"*{output.description}*")
                        
                        deck = render_range_ring_output(output, get_map_style())
                        render_map_with_legend(deck, output)
                        render_export_controls(output, "reverse_range_ring")
                        
                    except Exception as e:
                        progress_bar.progress(1.0, text="Error!")
                        st.error(f"Error: {e}")
        else:
            st.info("👆 Select a target city and shooter country, then click **Calculate Availability** to see which systems can reach the target.")


def render_minimum_range_ring_tool() -> None:
    """Render the Minimum Range Ring Generator tool."""
    with st.expander("📏 Minimum Range Ring Generator", expanded=False):
        st.markdown("""
        Calculate and visualize the minimum geodesic distance between two countries.
        """)
        
        data_service = get_data_service()
        countries = data_service.get_country_list()
        
        col1, col2 = st.columns(2)
        
        with col1:
            country_a = st.selectbox("Country A (Origin)", options=countries, key="min_country_a")
            country_code_a = data_service.get_country_code(country_a) if country_a else None
        
        with col2:
            country_b = st.selectbox("Country B (Target)", options=countries, index=1 if len(countries) > 1 else 0, key="min_country_b")
            country_code_b = data_service.get_country_code(country_b) if country_b else None
        
        show_line = st.checkbox("Show minimum distance line", value=True, key="min_show_line")
        
        # Weapon system buffer selection
        st.markdown("**Show Weapon System Ranges:**")
        st.caption("Select weapon systems to display as range rings from Country A")
        
        if country_code_a:
            weapons = data_service.get_weapon_systems(country_code_a)
            if weapons:
                # Create columns for weapon checkboxes
                selected_weapons = []
                cols = st.columns(2)
                for i, weapon in enumerate(weapons[:8]):  # Limit to 8 weapons
                    with cols[i % 2]:
                        if st.checkbox(f"{weapon['name']} ({weapon['range_km']:,.0f} km)", 
                                      key=f"min_weapon_{i}", value=False):
                            selected_weapons.append(weapon)
            else:
                selected_weapons = []
                st.info(f"No weapon systems available for {country_a}")
        else:
            selected_weapons = []
        
        if st.button("🚀 Calculate Minimum Distance", key="min_generate"):
            if country_code_a and country_code_b:
                with st.spinner("Calculating..."):
                    try:
                        input_data = MinimumRangeRingInput(
                            country_code_a=country_code_a,
                            country_code_b=country_code_b,
                            show_minimum_line=show_line,
                            show_buffer_rings=len(selected_weapons) > 0,
                        )
                        geom_a = data_service.get_country_geometry(country_code_a)
                        geom_b = data_service.get_country_geometry(country_code_b)
                        
                        output, result = calculate_minimum_distance(
                            input_data, geom_a, geom_b, country_a, country_b,
                            weapon_systems=selected_weapons
                        )
                        
                        add_tool_output("minimum_range_ring", output)
                        
                        st.success(f"Minimum distance: **{result.distance_km:,.1f} km**")
                        st.subheader(output.title)
                        st.markdown(f"*Buffer rings show weapon system ranges from **{country_a}** that could potentially reach **{country_b}**. "
                                   f"Rings are clipped to {country_a}'s border.*")
                        
                        deck = render_range_ring_output(output, get_map_style())
                        render_map_with_legend(deck, output)
                        render_export_controls(output, "minimum_range_ring")
                        
                    except Exception as e:
                        st.error(f"Error: {e}")


def render_custom_poi_tool() -> None:
    """Render the Custom POI Range Ring Generator tool."""
    with st.expander("📍 Custom POI Range Ring Generator", expanded=False):
        st.markdown("""
        Generate minimum/maximum "donut" range rings from one or more user-defined points of interest.
        """)
        
        if "custom_pois" not in st.session_state:
            st.session_state.custom_pois = []
        
        st.markdown("**Points of Interest:**")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_name = st.text_input("POI Name", key="custom_new_name")
        with col2:
            new_lat = st.number_input("Lat", value=39.0, key="custom_new_lat")
            new_lon = st.number_input("Lon", value=125.0, key="custom_new_lon")
        with col3:
            st.write("")
            st.write("")
            if st.button("➕ Add", key="custom_add_poi"):
                if new_name:
                    st.session_state.custom_pois.append({
                        "name": new_name, "lat": new_lat, "lon": new_lon
                    })
                    st.rerun()
        
        for i, poi in enumerate(st.session_state.custom_pois):
            st.text(f"📍 {poi['name']} ({poi['lat']:.4f}, {poi['lon']:.4f})")
        
        col1, col2 = st.columns(2)
        with col1:
            min_range = st.number_input("Min Range (0 for solid)", value=0.0, min_value=0.0, key="custom_min")
        with col2:
            max_range = st.number_input("Max Range", value=1000.0, min_value=1.0, key="custom_max")
        
        range_unit = st.selectbox("Unit", options=[u.value for u in DistanceUnit], key="custom_unit")
        resolution = st.selectbox("Resolution", options=["low", "normal", "high"], index=1, key="custom_resolution")
        
        if st.button("🚀 Generate POI Rings", key="custom_generate"):
            if not st.session_state.custom_pois:
                st.warning("Please add at least one POI.")
                return
            
            with st.spinner("Generating..."):
                try:
                    pois = [
                        PointOfInterest(name=p["name"], latitude=p["lat"], longitude=p["lon"])
                        for p in st.session_state.custom_pois
                    ]
                    input_data = CustomPOIRangeRingInput(
                        points_of_interest=pois,
                        min_range_value=min_range if min_range > 0 else None,
                        max_range_value=max_range,
                        range_unit=DistanceUnit(range_unit),
                        resolution=resolution,
                    )
                    output = generate_custom_poi_range_ring(input_data)
                    
                    add_tool_output("custom_poi_range_ring", output)
                    st.success("POI rings generated!")
                    
                    st.subheader(output.title)
                    deck = render_range_ring_output(output, get_map_style())
                    st.pydeck_chart(deck)
                    render_export_controls(output, "custom_poi_range_ring")
                    
                except Exception as e:
                    st.error(f"Error: {e}")


def render_all_tools() -> None:
    """Render all analytical tools."""
    st.header("📊 Analytical Tools")
    st.markdown("Select a tool below to generate range ring analyses.")
    
    render_single_range_ring_tool()
    render_multiple_range_ring_tool()
    render_reverse_range_ring_tool()
    render_minimum_range_ring_tool()
    render_custom_poi_tool()
