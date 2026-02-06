"""Shared helpers for Command Center task modules."""

from __future__ import annotations

import base64
import os
import re
from typing import Optional
from difflib import get_close_matches

import streamlit as st
import streamlit.components.v1 as components

from app.data.loaders import get_data_service
from app.ui.layout.global_state import set_command_output


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def fuzzy_match(name: str, options: list[str], cutoff: float = 0.75) -> Optional[str]:
    if not name or not options:
        return None
    normalized_options = {opt.lower(): opt for opt in options}
    matches = get_close_matches(name.lower(), normalized_options.keys(), n=1, cutoff=cutoff)
    if matches:
        return normalized_options[matches[0]]
    return None


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

_validation_js_cache: Optional[str] = None
_validation_js_mtime: Optional[int] = None
_html_template_cache: dict[str, str] = {}
_html_template_mtime: dict[str, int] = {}


def _load_validation_js_template() -> str:
    global _validation_js_cache, _validation_js_mtime
    js_path = os.path.join(os.path.dirname(__file__), "validation.js")
    try:
        current_mtime = os.stat(js_path).st_mtime_ns
    except OSError:
        current_mtime = None
    if _validation_js_cache is None or current_mtime != _validation_js_mtime:
        with open(js_path, "r", encoding="utf-8") as f:
            _validation_js_cache = f.read()
        _validation_js_mtime = current_mtime
    return _validation_js_cache


def _load_html_template(template_name: str) -> str:
    template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "html", "command")
    )
    template_path = os.path.join(template_dir, template_name)
    try:
        current_mtime = os.stat(template_path).st_mtime_ns
    except OSError:
        current_mtime = None
    cached_mtime = _html_template_mtime.get(template_name)
    if template_name not in _html_template_cache or current_mtime != cached_mtime:
        with open(template_path, "r", encoding="utf-8") as f:
            _html_template_cache[template_name] = f.read()
        _html_template_mtime[template_name] = current_mtime
    return _html_template_cache[template_name]


def render_html_template(template_name: str, replacements: Optional[dict[str, str]] = None) -> str:
    html = _load_html_template(template_name)
    for placeholder, value in (replacements or {}).items():
        html = html.replace(placeholder, value)
    return html


def get_shared_validation_js() -> str:
    import json

    js_template = _load_validation_js_template()
    data_service = get_data_service()
    countries = data_service.get_country_list()
    country_codes = data_service.get_country_codes()
    cities = data_service.get_city_list()

    countries_json = json.dumps([c.lower() for c in countries])
    country_codes_json = json.dumps([c.lower() for c in country_codes])
    cities_json = json.dumps([c.lower() for c in cities])
    countries_display_json = json.dumps(sorted(countries))
    cities_display_json = json.dumps(sorted(cities))

    js_code = js_template.replace("{{COUNTRIES_JSON}}", countries_json)
    js_code = js_code.replace("{{COUNTRY_CODES_JSON}}", country_codes_json)
    js_code = js_code.replace("{{CITIES_JSON}}", cities_json)
    js_code = js_code.replace("{{COUNTRIES_DISPLAY_JSON}}", countries_display_json)
    js_code = js_code.replace("{{CITIES_DISPLAY_JSON}}", cities_display_json)
    return js_code


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def render_cached_export_links(output, tool_key: str) -> None:
    """Render export download links from cache (HTML template-based)."""
    output_id = str(output.output_id)
    cache_key = f"command_exports_{output_id}"

    if cache_key not in st.session_state:
        st.warning("Cache not found. Please regenerate exports.")
        return

    cached = st.session_state[cache_key]
    base_name = f"{tool_key}_{output_id}"

    export_html = render_html_template(
        "export_cached.html",
        replacements={
            "{{GEOJSON_B64}}": cached["geojson_b64"],
            "{{KMZ_B64}}": cached["kmz_b64"],
            "{{PNG_B64}}": cached["png_b64"],
            "{{PDF_B64}}": cached["pdf_b64"],
            "{{BASE_NAME}}": base_name,
        },
    )

    components.html(export_html, height=100)


def render_js_export_controls(output, tool_key: str) -> None:
    """Render JavaScript-based export controls that don't cause page refresh."""
    from app.ui.layout.global_state import is_analyst_mode

    # Lazy load export modules
    from app.exports.geojson import export_to_geojson_string
    from app.exports.kmz import export_to_kmz_bytes
    from app.exports.png import export_to_png_bytes
    from app.exports.pdf import export_to_pdf_bytes

    include_metadata = is_analyst_mode()
    output_id = str(output.output_id)

    cache_key = f"command_exports_{output_id}"

    if cache_key in st.session_state:
        cached = st.session_state[cache_key]
        geojson_b64 = cached["geojson_b64"]
        kmz_b64 = cached["kmz_b64"]
        png_b64 = cached["png_b64"]
        pdf_b64 = cached["pdf_b64"]
    else:
        status_placeholder = st.empty()

        loading_html = render_html_template("export_loading.html")
        status_placeholder.markdown(loading_html, unsafe_allow_html=True)

        geojson_data = export_to_geojson_string(output, include_metadata=include_metadata)
        kmz_data = export_to_kmz_bytes(output, include_metadata=include_metadata)

        from app.exports.png import render_svg_with_template
        import cairosvg

        svg_content = render_svg_with_template(output, classification="UNCLASSIFIED")
        svg_bytes = svg_content.encode("utf-8")

        png_data = cairosvg.svg2png(
            bytestring=svg_bytes,
            output_width=1400,
            output_height=900,
            dpi=100,
            background_color="white",
        )

        pdf_data = cairosvg.svg2pdf(bytestring=svg_bytes)

        geojson_b64 = base64.b64encode(geojson_data.encode("utf-8")).decode("utf-8")
        kmz_b64 = base64.b64encode(kmz_data).decode("utf-8")
        png_b64 = base64.b64encode(png_data).decode("utf-8")
        pdf_b64 = base64.b64encode(pdf_data).decode("utf-8")

        st.session_state[cache_key] = {
            "geojson_b64": geojson_b64,
            "kmz_b64": kmz_b64,
            "png_b64": png_b64,
            "pdf_b64": pdf_b64,
        }

        status_placeholder.empty()

    base_name = f"{tool_key}_{output_id}"

    export_html = render_html_template(
        "export_options.html",
        replacements={
            "{{GEOJSON_B64}}": geojson_b64,
            "{{KMZ_B64}}": kmz_b64,
            "{{PNG_B64}}": png_b64,
            "{{PDF_B64}}": pdf_b64,
            "{{BASE_NAME}}": base_name,
        },
    )

    components.html(export_html, height=100)


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def clear_product_viewer() -> None:
    """Clear the product viewer back to its original state."""
    set_command_output(None)
