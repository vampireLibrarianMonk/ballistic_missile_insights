"""
Shared UI components and helpers for range ring tools.

This module contains utilities that are reused across multiple tool UIs,
preventing circular imports between tool_components.py and individual tool modules.
"""

from __future__ import annotations

import streamlit as st
from typing import Optional

from app.ui.layout.global_state import is_analyst_mode
from app.rendering.pydeck_adapter import render_range_ring_output
from app.models.outputs import GeometryType


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


# =============================================================================
# Lazy Export Module Loading
# =============================================================================
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


# =============================================================================
# Cached Export Functions
# =============================================================================
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
def _cached_svg_export(output_id: str, _output, classification: str) -> bytes:
    """Generate SVG once for reuse by PNG and PDF exports."""
    _load_export_modules()
    from app.exports.png import render_svg_with_template

    svg_content = render_svg_with_template(_output, classification=classification)
    return svg_content.encode("utf-8")


@st.cache_data(show_spinner=False)
def _cached_png_export(output_id: str, _output, svg_bytes: bytes | None = None) -> bytes:
    """Generate PNG with caching, reusing pre-rendered SVG when provided."""
    _load_export_modules()
    if svg_bytes is not None:
        import cairosvg
        png_bytes = cairosvg.svg2png(
            bytestring=svg_bytes,
            output_width=1400,
            output_height=900,
            dpi=100,
            background_color="white",
        )
        return png_bytes

    return _export_to_png_bytes(_output)


@st.cache_data(show_spinner=False)
def _cached_pdf_export(output_id: str, _output, include_metadata: bool, svg_bytes: bytes | None = None) -> bytes:
    """Generate PDF with caching, reusing pre-rendered SVG when provided."""
    _load_export_modules()
    if svg_bytes is not None:
        import cairosvg
        return cairosvg.svg2pdf(bytestring=svg_bytes)

    return _export_to_pdf_bytes(_output, include_metadata=include_metadata)


# =============================================================================
# Map and Legend Rendering
# =============================================================================
def render_map_with_legend(deck, output, height: int = 500) -> None:
    """
    Render a pydeck map with an integrated legend inside the map container.
    
    Args:
        deck: PyDeck Deck object
        output: RangeRingOutput containing layers for legend
        height: Height of the map in pixels
    """
    import streamlit.components.v1 as components
    
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


# =============================================================================
# Export Controls Rendering
# =============================================================================
def render_export_controls(output, tool_key: str) -> None:
    """Render export controls for a tool output using cached exports."""
    include_metadata = is_analyst_mode()
    output_id = str(output.output_id)
    classification = "UNCLASSIFIED"  # UI tools currently use unclassified marking
    
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
                svg_bytes = _cached_svg_export(output_id, output, classification)
                png_data = _cached_png_export(output_id, output, svg_bytes)
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
                svg_bytes = _cached_svg_export(output_id, output, classification)
                pdf_data = _cached_pdf_export(output_id, output, include_metadata, svg_bytes)
            st.download_button(
                "📥 PDF",
                data=pdf_data,
                file_name=f"{tool_key}_{output.output_id}.pdf",
                mime="application/pdf",
                key=f"pdf_{tool_key}_{output.output_id}",
            )


__all__ = [
    "get_weapon_selection_and_range",
    "render_range_input_with_weapon_key",
    "render_map_with_legend",
    "render_export_controls",
    "render_output_panel",
    "build_progress_callback",
]


# =============================================================================
# Shared Output / Progress Helpers
# =============================================================================
def build_progress_callback(label: str = "Initializing..."):
    """
    Create a Streamlit progress bar and return (bar, callback).

    Callback signature matches existing services: (pct: float, status: str).
    """
    progress_bar = st.progress(0.0, text=label)

    def update_progress(pct: float, status: str):
        progress_bar.progress(min(pct, 1.0), text=f"{int(min(pct,1.0)*100)}% - {status}")

    return progress_bar, update_progress


def render_output_panel(
    output,
    tool_key: str,
    map_style,
    show_metadata: bool = True,
    extra_metadata: dict | None = None,
    classification: str = "UNCLASSIFIED",
):
    """
    Standardized rendering for tool outputs: title/subtitle, map+legend, metadata, exports.
    """
    st.success("Output ready!")

    st.subheader(output.title)
    if getattr(output, "subtitle", None):
        st.caption(output.subtitle)
    if getattr(output, "description", None):
        st.markdown(f"*{output.description}*")

    deck = render_range_ring_output(output, map_style)
    render_map_with_legend(deck, output)

    if show_metadata and is_analyst_mode():
        metadata = {
            "output_id": str(output.output_id),
            "vertex_count": getattr(output.metadata, "vertex_count", None),
            "processing_time_ms": getattr(output.metadata, "processing_time_ms", None),
            "range_km": getattr(output.metadata, "range_km", None),
            "range_classification": getattr(output.metadata, "range_classification", None),
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        with st.expander("📊 Technical Metadata"):
            st.json(metadata)

    render_export_controls(output, tool_key)
