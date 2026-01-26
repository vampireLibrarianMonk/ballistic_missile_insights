"""
Tool UI components for ORRG.
Renders all five analytical tools with their inputs, outputs, and export controls.
"""

import streamlit as st
from typing import Optional
from shapely.geometry import Point

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
# =============================================================================
# Shared Weapon System / Range Selection Helpers
# =============================================================================
def get_weapon_selection_and_range(
    data_service,
    country_code: str,
    selected_weapon_name: str,
) -> tuple[float | None, str]:
    """
    Get range value and legend label based on weapon selection.

    This is the core shared logic between Single and Multiple range ring tools.
    Uses the working pattern from the Multiple Range Ring tool.
    
    Args:
        data_service: Data service for weapon lookup
        country_code: Country code for weapon systems lookup
        selected_weapon_name: Currently selected weapon name from dropdown
    
    Returns:
        Tuple of (range_value or None for manual, label_for_legend)
        - range_value: float if weapon selected, None if manual entry
        - label_for_legend: weapon name if selected, empty string if manual
    """
    if selected_weapon_name != "Manual Entry" and country_code:
        weapon_range = data_service.get_weapon_range(selected_weapon_name, country_code)
        range_value = weapon_range or 1000.0
        label_for_legend = selected_weapon_name
    else:
        range_value = None  # Indicates manual entry
        label_for_legend = ""
    
    return range_value, label_for_legend


def render_range_input_with_weapon_key(
    db_range_value: float | None,
    stored_range_value: float,
    selected_weapon_name: str,
    key_prefix: str,
    label_base: str = "Range Value",
) -> float:
    """
    Render range input with unique key based on weapon selection.
    
    Uses unique keys including weapon name to force Streamlit to refresh
    the value when switching between weapons. This is the working pattern
    from the Multiple Range Ring tool.
    
    Args:
        db_range_value: Range from database (None if manual entry)
        stored_range_value: Previously stored manual value
        selected_weapon_name: Currently selected weapon name
        key_prefix: Unique prefix for widget key (e.g., "single", "multi_0")
        label_base: Base label for the input (e.g., "Range Value", "Range 1")
    
    Returns:
        The range value (either from database or user input)
    """
    if db_range_value is None:
        # Manual entry - show stored value
        return st.number_input(
            label_base,
            value=float(stored_range_value),
            min_value=1.0,
            step=100.0,
            key=f"{key_prefix}_range_manual",
        )
    else:
        # Weapon selected - key includes weapon name to force refresh on change
        weapon_key = selected_weapon_name.replace(" ", "_").replace("-", "_")
        return st.number_input(
            f"{label_base} (override)",
            value=float(db_range_value),
            min_value=1.0,
            step=100.0,
            key=f"{key_prefix}_range_{weapon_key}",
        )


# Lazy import exports - will be loaded on demand, not at module load
# This makes the UI load instantly
_export_modules_loaded = False
_export_to_geojson_string = None
_export_to_kmz_bytes = None
_export_to_png_bytes = None
_export_to_pdf_bytes = None


def _load_export_modules():
    """Lazy load export modules only when needed."""
    global _export_modules_loaded
    global _export_to_geojson_string, _export_to_kmz_bytes
    global _export_to_png_bytes, _export_to_pdf_bytes
    
    if not _export_modules_loaded:
        from app.exports.geojson import export_to_geojson_string
        from app.exports.kmz import export_to_kmz_bytes
        from app.exports.png import export_to_png_bytes
        from app.exports.pdf import export_to_pdf_bytes
        
        _export_to_geojson_string = export_to_geojson_string
        _export_to_kmz_bytes = export_to_kmz_bytes
        _export_to_png_bytes = export_to_png_bytes
        _export_to_pdf_bytes = export_to_pdf_bytes
        _export_modules_loaded = True


# Cached export functions to avoid recomputation on every render
@st.cache_data(show_spinner=False)
def _cached_geojson_export(output_id: str, _output, include_metadata: bool) -> str:
    """Generate GeoJSON with caching."""
    _load_export_modules()
    return _export_to_geojson_string(_output, include_metadata=include_metadata)


@st.cache_data(show_spinner=False)
def _cached_kmz_export(output_id: str, _output, include_metadata: bool) -> bytes:
    """Generate KMZ with caching."""
    _load_export_modules()
    return _export_to_kmz_bytes(_output, include_metadata=include_metadata)


@st.cache_data(show_spinner=False)
def _cached_png_export(output_id: str, _output) -> bytes:
    """Generate PNG with caching."""
    _load_export_modules()
    return _export_to_png_bytes(_output)


@st.cache_data(show_spinner=False)
def _cached_pdf_export(output_id: str, _output, include_metadata: bool) -> bytes:
    """Generate PDF with caching."""
    _load_export_modules()
    return _export_to_pdf_bytes(_output, include_metadata=include_metadata)


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
    # Legend expands upward from bottom-right corner and scrolls if too tall
    # Max height leaves room for the Controls box (approx 70px) at top + margins
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
        max-height: calc(100% - 125px);
        overflow-y: auto;
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
    """Render export controls for a tool output using cached exports."""
    include_metadata = is_analyst_mode()
    output_id = str(output.output_id)
    
    # Show expander with export buttons - exports are generated on-demand and cached
    with st.expander("📥 Download Options", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # GeoJSON is fast, generate immediately
            with st.spinner("Preparing GeoJSON..."):
                geojson_data = _cached_geojson_export(output_id, output, include_metadata)
            st.download_button(
                "📥 GeoJSON",
                data=geojson_data,
                file_name=f"{tool_key}_{output.output_id}.geojson",
                mime="application/geo+json",
                key=f"geojson_{tool_key}_{output.output_id}",
            )
        
        with col2:
            # KMZ is fast, generate immediately
            with st.spinner("Preparing KMZ..."):
                kmz_data = _cached_kmz_export(output_id, output, include_metadata)
            st.download_button(
                "📥 KMZ",
                data=kmz_data,
                file_name=f"{tool_key}_{output.output_id}.kmz",
                mime="application/vnd.google-earth.kmz",
                key=f"kmz_{tool_key}_{output.output_id}",
            )
        
        with col3:
            # PNG - show status while preparing (no blocking delays)
            with st.spinner("Preparing PNG..."):
                png_data = _cached_png_export(output_id, output)
            st.download_button(
                "📥 PNG",
                data=png_data,
                file_name=f"{tool_key}_{output.output_id}.png",
                mime="image/png",
                key=f"png_{tool_key}_{output.output_id}",
            )
        
        with col4:
            # PDF - show status while preparing (no blocking delays)
            with st.spinner("Preparing PDF..."):
                pdf_data = _cached_pdf_export(output_id, output, include_metadata)
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
            # Create progress bar container
            progress_bar = st.progress(0, text="Initializing...")
            status_text = st.empty()
            
            def update_progress(pct: float, status: str):
                """Callback to update progress bar."""
                progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")
            
            try:
                if origin_type == "country" and country_code:
                    # Get weapon source if a weapon is selected
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
                
                # Clear previous outputs and add new one
                clear_tool_outputs("single_range_ring")
                add_tool_output("single_range_ring", output)
                st.rerun()  # Rerun to render from session state
                
            except Exception as e:
                progress_bar.progress(1.0, text="Error!")
                st.error(f"Error generating range ring: {e}")
        
        # Render output from session state (persists across reruns)
        tool_state = get_tool_state("single_range_ring")
        if tool_state.get("outputs"):
            output = tool_state["outputs"][-1]  # Get latest output
            
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
        
        # Dynamic range inputs
        if "multi_ranges" not in st.session_state:
            st.session_state.multi_ranges = [{"value": 1000, "unit": "km", "weapon_name": "Manual Entry"}]
        
        ranges_to_remove = []
        for i, range_item in enumerate(st.session_state.multi_ranges):
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
            st.session_state.multi_ranges.pop(i)
        
        if st.button("➕ Add Range", key="multi_add_range"):
            st.session_state.multi_ranges.append({"value": 1000, "unit": "km", "weapon_name": "Manual Entry"})
            st.rerun()
        
        resolution = st.selectbox("Resolution", options=["low", "normal", "high"], index=1, key="multi_resolution")
        
        if st.button("🚀 Generate Multiple Rings", key="multi_generate"):
            if not st.session_state.multi_ranges:
                st.warning("Please add at least one range.")
                return
            
            # Create progress bar - updates come from the service
            progress_bar = st.progress(0, text="0% - Initializing...")
            
            def update_progress(pct: float, msg: str):
                """Callback to update progress bar from generate_multiple_range_rings."""
                progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {msg}")
            
            try:
                # Build range tuples
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
                    
                    # Generate with progress callback - all updates come from the service
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
                        resolution=resolution,
                    )
                    
                    # Generate with progress callback - all updates come from the service
                    output = generate_multiple_range_rings(
                        input_data,
                        progress_callback=update_progress
                    )
                
                # Clear previous outputs and add new one
                clear_tool_outputs("multiple_range_ring")
                add_tool_output("multiple_range_ring", output)
                st.rerun()  # Rerun to render from session state
                
            except Exception as e:
                progress_bar.progress(1.0, text="Error!")
                st.error(f"Error: {e}")
        
        # Render output from session state (persists across reruns)
        tool_state = get_tool_state("multiple_range_ring")
        if tool_state.get("outputs"):
            output = tool_state["outputs"][-1]  # Get latest output
            
            st.success("Range rings generated!")
            
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
                        "layer_count": len(output.layers),
                        "processing_time_ms": output.metadata.processing_time_ms if output.metadata else None,
                    })
            
            # Export controls
            render_export_controls(output, "multiple_range_ring")


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
                    # Create progress bar - updates come from the service
                    progress_bar = st.progress(0, text="0% - Initializing...")
                    
                    def update_progress(pct: float, status: str):
                        """Callback to update progress bar from generate_reverse_range_ring."""
                        progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")
                    
                    try:
                        target = PointOfInterest(name=city_name, latitude=target_lat, longitude=target_lon)
                        input_data = ReverseRangeRingInput(
                            target_point=target,
                            range_value=selected_system["range_km"],
                            range_unit=DistanceUnit("km"),
                            weapon_system=selected_system["name"],
                            resolution=resolution,
                        )
                        
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
                    
                    st.subheader(output.title)
                    st.caption(output.subtitle)
                    st.markdown(f"*{output.description}*")
                    
                    deck = render_range_ring_output(output, get_map_style())
                    render_map_with_legend(deck, output)
                    
                    # Analyst mode metadata
                    if is_analyst_mode():
                        with st.expander("📊 Technical Metadata"):
                            st.json({
                                "output_id": str(output.output_id),
                                "vertex_count": output.metadata.vertex_count if output.metadata else None,
                                "processing_time_ms": output.metadata.processing_time_ms if output.metadata else None,
                                "range_km": output.metadata.range_km if output.metadata else None,
                            })
                    
                    render_export_controls(output, "reverse_range_ring")
        else:
            st.info("👆 Select a target city and shooter country, then click **Calculate Availability** to see which systems can reach the target.")


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
        
        show_line = st.checkbox("Show minimum distance line", value=True, key="min_show_line")
        
        if st.button("🚀 Calculate Minimum Distance", key="min_generate"):
            if geom_a is not None and geom_b is not None:
                # Create progress bar - updates come from the service
                progress_bar = st.progress(0, text="0% - Initializing...")
                
                def update_progress(pct: float, status: str):
                    """Callback to update progress bar from calculate_minimum_distance."""
                    progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")
                
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
                    st.session_state.min_distance_result = result
                    
                    # Clear previous outputs and add new one
                    clear_tool_outputs("minimum_range_ring")
                    add_tool_output("minimum_range_ring", output)
                    
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
            result = st.session_state.get("min_distance_result")
            if result:
                st.success(f"Minimum distance: **{result.distance_km:,.1f} km**")
            
            st.subheader(output.title)
            st.caption(output.subtitle)
            st.markdown(f"*{output.description}*")
            
            deck = render_range_ring_output(output, get_map_style())
            render_map_with_legend(deck, output)
            
            # Analyst mode metadata
            if is_analyst_mode():
                with st.expander("📊 Technical Metadata"):
                    st.json({
                        "output_id": str(output.output_id),
                        "processing_time_ms": output.metadata.processing_time_ms if output.metadata else None,
                        "range_km": output.metadata.range_km if output.metadata else None,
                    })
            
            render_export_controls(output, "minimum_range_ring")


def render_custom_poi_tool() -> None:
    """Render the Custom POI Range Ring Generator tool."""
    with st.expander("📍 Custom POI Range Ring Generator", expanded=False):
        st.markdown("""
        Generate minimum/maximum "donut" range rings from one or more user-defined points of interest.
        Each POI has its own range settings.
        """)
        
        # Initialize session state for POI list
        if "custom_pois" not in st.session_state:
            st.session_state.custom_pois = []  # Each entry: {name, lat, lon, min_range, max_range, unit}
        if "custom_poi_selected_idx" not in st.session_state:
            st.session_state.custom_poi_selected_idx = None  # None = new entry mode
        if "custom_poi_form_version" not in st.session_state:
            st.session_state.custom_poi_form_version = 0  # Incremented to force new widgets
        if "custom_poi_load_poi" not in st.session_state:
            st.session_state.custom_poi_load_poi = None
        if "custom_poi_prefill" not in st.session_state:
            st.session_state.custom_poi_prefill = None  # Pre-fill values for edit mode
        
        # Generate unique key prefix based on form version
        form_key = f"cpoi_v{st.session_state.custom_poi_form_version}"
        
        # Get prefill values (either from edit mode or defaults for add mode)
        prefill = st.session_state.custom_poi_prefill or {}
        default_name = prefill.get("name", "")
        default_lat = prefill.get("lat", 0.0)
        default_lon = prefill.get("lon", 0.0)
        default_min_range = prefill.get("min_range", 0.0)
        default_max_range = prefill.get("max_range", 1.0)
        default_unit = prefill.get("unit", "km")
        
        st.markdown("**Points of Interest:**")
        
        # Display existing POIs with radio buttons for selection
        if st.session_state.custom_pois:
            # Build display labels with range info
            poi_options = ["➕ Add New POI"]
            for poi in st.session_state.custom_pois:
                min_r = poi.get('min_range', 0)
                max_r = poi.get('max_range', 1000)
                unit = poi.get('unit', 'km')
                if min_r > 0:
                    range_str = f"{min_r:,.0f}-{max_r:,.0f} {unit}"
                else:
                    range_str = f"{max_r:,.0f} {unit}"
                poi_options.append(f"📍 {poi['name']} | {range_str} | (Lat: {poi['lat']:.4f}, Long: {poi['lon']:.4f})")
            
            # Determine current selection index (0 = new, 1+ = edit existing)
            current_selection = 0 if st.session_state.custom_poi_selected_idx is None else st.session_state.custom_poi_selected_idx + 1
            
            selected_option = st.radio(
                "Select POI to edit or add new:",
                options=poi_options,
                index=current_selection,
                key="custom_poi_radio",
                horizontal=False,
            )
            
            # Determine which POI is selected
            selected_idx = poi_options.index(selected_option)
            if selected_idx == 0:
                # Add new mode
                if st.session_state.custom_poi_selected_idx is not None:
                    # Switched from edit to add mode - increment version to get fresh widgets
                    st.session_state.custom_poi_selected_idx = None
                    st.session_state.custom_poi_prefill = None  # Clear prefill for add mode
                    st.session_state.custom_poi_form_version += 1
                    st.rerun()
                edit_mode = False
                edit_idx = None
            else:
                # Edit existing mode
                edit_idx = selected_idx - 1
                if st.session_state.custom_poi_selected_idx != edit_idx:
                    # Switched to different POI - load its values and increment version
                    st.session_state.custom_poi_selected_idx = edit_idx
                    poi = st.session_state.custom_pois[edit_idx]
                    st.session_state.custom_poi_prefill = {
                        "name": poi["name"],
                        "lat": poi["lat"],
                        "lon": poi["lon"],
                        "min_range": poi.get("min_range", 0.0),
                        "max_range": poi.get("max_range", 1000.0),
                        "unit": poi.get("unit", "km"),
                    }
                    st.session_state.custom_poi_form_version += 1
                    st.rerun()
                edit_mode = True
        else:
            st.info("No POIs added yet. Add your first point of interest below.")
            edit_mode = False
            edit_idx = None
        
        st.divider()
        
        # Input form for adding/editing - use version-based keys to force clearing
        if edit_mode:
            st.markdown(f"**Editing: {st.session_state.custom_pois[edit_idx]['name']}**")
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
                            st.session_state.custom_pois[edit_idx] = {
                                "name": poi_name,
                                "lat": poi_lat,
                                "lon": poi_lon,
                                "min_range": poi_min_range,
                                "max_range": poi_max_range,
                                "unit": poi_unit,
                            }
                            # Reset to add mode after finalizing - increment version for fresh widgets
                            st.session_state.custom_poi_selected_idx = None
                            st.session_state.custom_poi_prefill = None  # Clear prefill
                            st.session_state.custom_poi_form_version += 1
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
                            st.session_state.custom_pois.append({
                                "name": poi_name,
                                "lat": poi_lat,
                                "lon": poi_lon,
                                "min_range": poi_min_range,
                                "max_range": poi_max_range,
                                "unit": poi_unit,
                            })
                            # Clear form after adding - increment version for fresh widgets
                            st.session_state.custom_poi_prefill = None  # Clear prefill
                            st.session_state.custom_poi_form_version += 1
                            st.rerun()
                    else:
                        st.warning("Please enter a POI name.")
        
        with col_btn2:
            if edit_mode:
                # Delete button when editing
                if st.button("🗑️ Delete", key="custom_delete_poi", use_container_width=True, type="secondary"):
                    st.session_state.custom_pois.pop(edit_idx)
                    # Reset to add mode after deleting - increment version for fresh widgets
                    st.session_state.custom_poi_selected_idx = None
                    st.session_state.custom_poi_prefill = None  # Clear prefill
                    st.session_state.custom_poi_form_version += 1
                    st.rerun()
        
        st.divider()
        
        # Global settings
        st.markdown("**Generation Settings:**")
        resolution = st.selectbox("Resolution", options=["low", "normal", "high"], index=1, key="custom_resolution")
        
        if st.button("🚀 Generate POI Rings", key="custom_generate"):
            if not st.session_state.custom_pois:
                st.warning("Please add at least one POI.")
                return
            
            with st.spinner("Generating..."):
                try:
                    from app.geometry.services import generate_custom_poi_range_ring_multi
                    
                    # Build list of POIs with their individual ranges
                    poi_data_list = []
                    for p in st.session_state.custom_pois:
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


def render_all_tools() -> None:
    """Render all analytical tools."""
    st.header("📊 Analytical Tools")
    st.markdown("Select a tool below to generate range ring analyses.")
    
    render_single_range_ring_tool()
    render_multiple_range_ring_tool()
    render_reverse_range_ring_tool()
    render_minimum_range_ring_tool()
    render_custom_poi_tool()
