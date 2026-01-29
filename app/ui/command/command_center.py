"""
Command Center UI for ORRG.
Provides a Google-like intent-driven interface for queries and taskings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union
import os
import re

from difflib import get_close_matches

import streamlit as st

from app.models.outputs import RangeRingOutput
from shapely.geometry import Point

from app.models.inputs import (
    PointOfInterest,
    ReverseRangeRingInput,
    SingleRangeRingInput,
    MinimumRangeRingInput,
    DistanceUnit,
    OriginType,
)
from app.geometry.services import (
    generate_reverse_range_ring,
    generate_single_range_ring,
    calculate_minimum_distance,
)
from app.geometry.utils import geodesic_distance
from app.data.loaders import get_data_service
from app.rendering.pydeck_adapter import render_range_ring_output
from app.ui.layout.global_state import (
    get_map_style,
    get_command_history,
    add_command_history_entry,
    update_command_history_entry,
    clear_command_history,
    get_command_output,
    set_command_output,
    get_command_reverse_pending,
    set_command_reverse_pending,
    get_command_single_pending,
    set_command_single_pending,
    get_command_minimum_pending,
    set_command_minimum_pending,
)
from app.ui.tools.tool_components import render_map_with_legend
import streamlit.components.v1 as components
import base64


CommandOutput = Union[RangeRingOutput, str, None]


class CommandParsingError(Exception):
    """Raised when command parsing fails."""


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _fuzzy_match(name: str, options: list[str], cutoff: float = 0.75) -> Optional[str]:
    if not name or not options:
        return None
    normalized_options = {opt.lower(): opt for opt in options}
    matches = get_close_matches(name.lower(), normalized_options.keys(), n=1, cutoff=cutoff)
    if matches:
        return normalized_options[matches[0]]
    return None


def _extract_reverse_range_request(text: str) -> Optional[tuple[str, str]]:
    """Extract shooter country and target city from a reverse range ring command."""
    normalized = _normalize_text(text)
    synonyms = r"reverse range ring|reverse ring|launch envelope|reverse range"
    prepositions = r"from|within|inside"
    target_words = r"against|to|toward|towards"
    pattern = (
        rf"(?:generate|create|build|show)?\s*(?:a\s+)?"
        rf"(?:{synonyms})\s+"
        rf"(?:{prepositions})\s+(?P<country>.+?)\s+"
        rf"(?:{target_words})\s+(?P<city>.+?)\.?$"
    )
    match = re.search(pattern, normalized)
    if not match:
        return None
    country_raw = match.group("country")
    city_raw = match.group("city")
    if not country_raw or not city_raw:
        return None
    return country_raw.strip(), city_raw.strip()


def _generate_reverse_range_output(country_name: str, city_name: str) -> RangeRingOutput:
    data_service = get_data_service()

    countries = data_service.get_country_list()
    cities = data_service.get_city_list()

    matched_country = _fuzzy_match(country_name, countries, cutoff=0.6)
    matched_city = _fuzzy_match(city_name, cities, cutoff=0.6)

    if not matched_country:
        raise CommandParsingError(f"Unable to match shooter country '{country_name}'.")
    if not matched_city:
        raise CommandParsingError(f"Unable to match target city '{city_name}'.")

    country_code = data_service.get_country_code(matched_country)
    if not country_code:
        raise CommandParsingError(f"Could not resolve ISO code for '{matched_country}'.")

    target_coords = data_service.get_city_coordinates(matched_city)
    if not target_coords:
        raise CommandParsingError(f"Could not resolve coordinates for '{matched_city}'.")

    return _generate_reverse_range_output_with_weapon(matched_country, matched_city, country_code, target_coords)


def _generate_reverse_range_output_with_weapon(
    country_name: str,
    city_name: str,
    country_code: str,
    target_coords: tuple[float, float],
    weapon: Optional[dict] = None,
    progress_callback: Optional[callable] = None,
) -> RangeRingOutput:
    data_service = get_data_service()
    weapons = data_service.get_weapon_systems(country_code)
    if not weapons:
        raise CommandParsingError(f"No weapon systems found for {country_name}.")

    selected_weapon = weapon or max(weapons, key=lambda w: w.get("range_km", 0))
    range_km = selected_weapon.get("range_km", 0)
    if range_km <= 0:
        raise CommandParsingError(f"Weapon range data unavailable for {country_name}.")

    target_poi = PointOfInterest(name=city_name, latitude=target_coords[0], longitude=target_coords[1])

    input_data = ReverseRangeRingInput(
        target_point=target_poi,
        range_value=range_km,
        range_unit=DistanceUnit.KILOMETERS,
        weapon_system=selected_weapon.get("name"),
        resolution="normal",
    )

    threat_geometry = data_service.get_country_geometry(country_code)
    if threat_geometry is None:
        raise CommandParsingError(f"Could not load geometry for {country_name}.")

    return generate_reverse_range_ring(
        input_data,
        threat_country_geometry=threat_geometry,
        threat_country_name=country_name,
        progress_callback=progress_callback,
    )


def _build_weapon_selection_message(country_name: str, weapons: list[dict]) -> str:
    lines = [
        f"**Weapon systems available for {country_name}:**",
        "Select a system by replying with: `Select reverse weapon #`.",
        "",
    ]

    for idx, weapon in enumerate(weapons, start=1):
        name = weapon.get("name", "Unknown")
        range_km = weapon.get("range_km", 0)
        classification = weapon.get("classification", "")
        label = f"{idx}. {name} — {range_km:,.0f} km"
        if classification:
            label += f" ({classification})"
        lines.append(label)

    return "\n".join(lines)


def _extract_reverse_weapon_selection(text: str) -> Optional[int]:
    normalized = _normalize_text(text)
    match = re.search(r"select reverse weapon\s*(?P<index>\d+)", normalized)
    if match:
        return int(match.group("index"))
    return None


# ============================================================================
# Minimum Range Ring Functions
# ============================================================================

def _extract_minimum_range_request(text: str) -> Optional[tuple[str, str]]:
    """Extract two location names from a minimum range ring command."""
    normalized = _normalize_text(text)
    synonyms = r"minimum range ring|minimum distance|min distance|min range"
    prepositions = r"between|from"
    target_words = r"and|to"
    pattern = (
        rf"(?:calculate|compute|generate|show)?\s*(?:a\s+)?"
        rf"(?:{synonyms})\s+"
        rf"(?:{prepositions})\s+(?P<location_a>.+?)\s+"
        rf"(?:{target_words})\s+(?P<location_b>.+?)\.?$"
    )
    match = re.search(pattern, normalized)
    if not match:
        return None
    location_a = match.group("location_a")
    location_b = match.group("location_b")
    if not location_a or not location_b:
        return None
    return location_a.strip(), location_b.strip()


def _extract_minimum_location_type(text: str) -> Optional[str]:
    """Extract the minimum range ring location type selection."""
    normalized = _normalize_text(text)
    match = re.search(r"select minimum type\s*(countries|cities)", normalized)
    if match:
        return match.group(1).lower()
    return None


def _build_minimum_location_type_message() -> str:
    """Build the minimum range ring location type selection message."""
    return "\n".join(
        [
            "**Minimum Range Ring setup**",
            "Select the location type to analyze by replying with:",
            "- `Select minimum type countries`",
            "- `Select minimum type cities`",
        ]
    )


def _build_minimum_location_selection_message(location_type: str, locations: list[str]) -> str:
    """Build a numbered selection list for minimum range ring locations."""
    label = "Countries" if location_type == "countries" else "Cities"
    lines = [
        f"**{label} available:**",
        "Select the two locations by replying with:",
        "`Select minimum locations # and #`",
        "",
    ]
    for idx, location in enumerate(locations, start=1):
        lines.append(f"{idx}. {location}")
    return "\n".join(lines)


def _extract_minimum_location_selection(text: str) -> Optional[tuple[int, int]]:
    """Extract two selection indexes from minimum location selection command."""
    normalized = _normalize_text(text)
    match = re.search(
        r"select minimum locations\s*(?P<first>\d+)\s*(?:and|,)\s*(?P<second>\d+)",
        normalized,
    )
    if match:
        return int(match.group("first")), int(match.group("second"))
    return None


def _generate_minimum_range_output(
    location_type: str,
    location_a: str,
    location_b: str,
    progress_callback: Optional[callable] = None,
) -> tuple[RangeRingOutput, float]:
    """Generate Minimum Range Ring output for the selected locations."""
    data_service = get_data_service()

    if location_type == "countries":
        country_code_a = data_service.get_country_code(location_a)
        country_code_b = data_service.get_country_code(location_b)
        if not country_code_a or not country_code_b:
            raise CommandParsingError("Could not resolve ISO codes for selected countries.")
        geometry_a = data_service.get_country_geometry(country_code_a)
        geometry_b = data_service.get_country_geometry(country_code_b)
        if geometry_a is None or geometry_b is None:
            raise CommandParsingError("Could not load geometry for one or more countries.")
    else:
        coords_a = data_service.get_city_coordinates(location_a)
        coords_b = data_service.get_city_coordinates(location_b)
        if not coords_a or not coords_b:
            raise CommandParsingError("Could not resolve coordinates for one or more cities.")
        geometry_a = Point(coords_a[1], coords_a[0])
        geometry_b = Point(coords_b[1], coords_b[0])
        country_code_a = None
        country_code_b = None

    input_data = MinimumRangeRingInput(
        country_code_a=country_code_a,
        country_code_b=country_code_b,
        show_minimum_line=True,
        show_buffer_rings=False,
    )

    output, result = calculate_minimum_distance(
        input_data,
        geometry_a,
        geometry_b,
        location_a,
        location_b,
        progress_callback=progress_callback,
    )
    return output, result.distance_km


def _update_minimum_pending_history_entry(
    location_type: str,
    location_a: str,
    location_b: str,
    distance_km: float,
    final_status: str,
    output: Optional[RangeRingOutput] = None,
) -> None:
    """Update the pending minimum range ring history entry with completion details."""
    display_type = "Countries" if location_type == "countries" else "Cities"
    updates = {
        "status": final_status,
        "text": (
            f"Minimum range ring ({display_type}): {location_a} ↔ {location_b} "
            f"({distance_km:,.1f} km)"
        ),
        "minimum_distance_km": distance_km,
        "location_type": location_type,
        "location_a": location_a,
        "location_b": location_b,
    }

    if output is not None:
        updates["output"] = output

    update_command_history_entry(
        match_criteria={
            "resolution": "Minimum Range Ring",
            "status": "Pending",
        },
        updates=updates,
    )

# ============================================================================
# Single Range Ring Functions
# ============================================================================

def _extract_single_range_request(text: str) -> Optional[str]:
    """Extract country from a single range ring command.
    
    Returns the country name if matched, None otherwise.
    Note: Must NOT match reverse range ring commands.
    """
    normalized = _normalize_text(text)
    
    # First, check if this is actually a reverse range ring command
    # Reverse commands take priority - do not match them as single
    reverse_indicators = ["reverse", "launch envelope"]
    if any(indicator in normalized for indicator in reverse_indicators):
        return None
    
    synonyms = r"single range ring|single ring|range ring"
    prepositions = r"from|for"
    pattern = (
        rf"(?:generate|create|build|show)?\s*(?:a\s+)?"
        rf"(?:{synonyms})\s+"
        rf"(?:{prepositions})\s+(?P<country>.+?)\.?$"
    )
    match = re.search(pattern, normalized)
    if not match:
        return None
    country_raw = match.group("country")
    if not country_raw:
        return None
    return country_raw.strip()


def _build_single_weapon_selection_message(country_name: str, weapons: list[dict]) -> str:
    """Build the weapon selection message for single range ring."""
    lines = [
        f"**Weapon systems available for {country_name}:**",
        "Select a system by replying with: `Select single weapon #`.",
        "",
    ]

    for idx, weapon in enumerate(weapons, start=1):
        name = weapon.get("name", "Unknown")
        range_km = weapon.get("range_km", 0)
        classification = weapon.get("classification", "")
        label = f"{idx}. {name} — {range_km:,.0f} km"
        if classification:
            label += f" ({classification})"
        lines.append(label)

    return "\n".join(lines)


def _extract_single_weapon_selection(text: str) -> Optional[int]:
    """Extract weapon selection index from 'select single weapon #' command."""
    normalized = _normalize_text(text)
    match = re.search(r"select single weapon\s*(?P<index>\d+)", normalized)
    if match:
        return int(match.group("index"))
    return None


def _generate_single_range_output_with_weapon(
    country_name: str,
    country_code: str,
    weapon: dict,
    progress_callback: Optional[callable] = None,
) -> RangeRingOutput:
    """Generate Single Range Ring output with selected weapon."""
    data_service = get_data_service()
    
    range_km = weapon.get("range_km", 0)
    if range_km <= 0:
        raise CommandParsingError(f"Weapon range data unavailable for {weapon.get('name', 'Unknown')}.")

    input_data = SingleRangeRingInput(
        origin_type=OriginType.COUNTRY,
        country_code=country_code,
        range_value=range_km,
        range_unit=DistanceUnit.KILOMETERS,
        weapon_system=weapon.get("name"),
        resolution="normal",
    )

    country_geometry = data_service.get_country_geometry(country_code)
    if country_geometry is None:
        raise CommandParsingError(f"Could not load geometry for {country_name}.")

    return generate_single_range_ring(
        input_data,
        origin_geometry=country_geometry,
        origin_name=country_name,
        progress_callback=progress_callback,
    )


def _update_single_pending_history_entry(
    country_name: str,
    weapon_name: str,
    weapon_range: float,
    final_status: str,
    output: Optional[RangeRingOutput] = None,
) -> None:
    """Update the pending single range ring history entry with completion details."""
    updates = {
        "status": final_status,
        "text": f"Single range ring: {country_name} using {weapon_name} ({weapon_range:,.0f} km)",
        "weapon_name": weapon_name,
        "weapon_range_km": weapon_range,
        "origin_country": country_name,
    }
    
    if output is not None:
        updates["output"] = output
    
    update_command_history_entry(
        match_criteria={
            "resolution": "Single Range Ring",
            "status": "Pending",
        },
        updates=updates
    )


def _clear_export_cache() -> None:
    """Clear any cached export data from session state."""
    keys_to_remove = [k for k in st.session_state.keys() if k.startswith("command_exports_")]
    for key in keys_to_remove:
        del st.session_state[key]


def _clear_product_viewer() -> None:
    """
    Clear the product viewer back to its original state.
    Export cache is preserved so history entries can still use cached exports.
    """
    set_command_output(None)


def _update_pending_history_entry(
    country_name: str,
    city_name: str,
    weapon_name: str,
    weapon_range: float,
    final_status: str,
    output: Optional[RangeRingOutput] = None,
) -> None:
    """
    Update the pending reverse range ring history entry with completion details.
    Consolidates both steps into one history entry with full context.
    """
    updates = {
        "status": final_status,
        "text": f"Reverse range ring: {country_name} → {city_name} using {weapon_name} ({weapon_range:,.0f} km)",
        "weapon_name": weapon_name,
        "weapon_range_km": weapon_range,
        "shooter_country": country_name,
        "target_city": city_name,
    }
    
    # Store the output for later export generation
    if output is not None:
        updates["output"] = output
    
    # Find and update the pending entry for this reverse range ring task
    update_command_history_entry(
        match_criteria={
            "resolution": "Reverse Range Ring",
            "status": "Pending",
        },
        updates=updates
    )


def _render_cached_export_links(output, tool_key: str) -> None:
    """Render export download links from cache (HTML template-based)."""
    output_id = str(output.output_id)
    cache_key = f"command_exports_{output_id}"

    if cache_key not in st.session_state:
        st.warning("Cache not found. Please regenerate exports.")
        return

    cached = st.session_state[cache_key]
    base_name = f"{tool_key}_{output_id}"

    export_html = _render_html_template(
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


def _render_rrr_validator() -> None:
    """Render the Reverse Range Ring real-time validator widget."""
    import json

    data_service = get_data_service()

    countries = data_service.get_country_list()
    cities = data_service.get_city_list()

    html = _render_html_template(
        "rrr_validator.html",
        replacements={
            "{{COUNTRIES_JSON}}": json.dumps([c.lower() for c in countries]),
            "{{CITIES_JSON}}": json.dumps([c.lower() for c in cities]),
            "{{COUNTRIES_DISPLAY_JSON}}": json.dumps(sorted(countries)),
            "{{CITIES_DISPLAY_JSON}}": json.dumps(sorted(cities)),
        },
    )

    components.html(html, height=420)


def _render_js_export_controls(output, tool_key: str) -> None:
    """Render JavaScript-based export controls that don't cause page refresh."""
    from app.ui.layout.global_state import is_analyst_mode
    
    # Lazy load export modules
    from app.exports.geojson import export_to_geojson_string
    from app.exports.kmz import export_to_kmz_bytes
    from app.exports.png import export_to_png_bytes
    from app.exports.pdf import export_to_pdf_bytes
    
    include_metadata = is_analyst_mode()
    output_id = str(output.output_id)
    
    # Cache key for this output's exports
    cache_key = f"command_exports_{output_id}"
    
    # Check if we already have cached export data for this output
    if cache_key in st.session_state:
        cached = st.session_state[cache_key]
        geojson_b64 = cached["geojson_b64"]
        kmz_b64 = cached["kmz_b64"]
        png_b64 = cached["png_b64"]
        pdf_b64 = cached["pdf_b64"]
    else:
        # Show loading status while generating exports
        status_placeholder = st.empty()

        # Load loading spinner HTML from template
        loading_html = _render_html_template("export_loading.html")

        status_placeholder.markdown(loading_html, unsafe_allow_html=True)

        # Generate export data without artificial delays for faster performance
        # GeoJSON and KMZ are fast (no map rendering)
        geojson_data = export_to_geojson_string(output, include_metadata=include_metadata)
        kmz_data = export_to_kmz_bytes(output, include_metadata=include_metadata)
        
        # PNG and PDF share the same SVG rendering - import optimized function
        from app.exports.png import render_svg_with_template
        import cairosvg
        
        # Render SVG once and reuse for both PNG and PDF
        svg_content = render_svg_with_template(output, classification="UNCLASSIFIED")
        svg_bytes = svg_content.encode("utf-8")
        
        # Generate PNG from cached SVG
        png_data = cairosvg.svg2png(
            bytestring=svg_bytes,
            output_width=1400,
            output_height=900,
            dpi=100,
            background_color="white",
        )
        
        # Generate PDF from cached SVG
        pdf_data = cairosvg.svg2pdf(bytestring=svg_bytes)
        
        # Base64 encode
        geojson_b64 = base64.b64encode(geojson_data.encode('utf-8')).decode('utf-8')
        kmz_b64 = base64.b64encode(kmz_data).decode('utf-8')
        png_b64 = base64.b64encode(png_data).decode('utf-8')
        pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
        
        # Cache the encoded data
        st.session_state[cache_key] = {
            "geojson_b64": geojson_b64,
            "kmz_b64": kmz_b64,
            "png_b64": png_b64,
            "pdf_b64": pdf_b64,
        }
        
        # Clear the loading placeholder
        status_placeholder.empty()

    # File names
    base_name = f"{tool_key}_{output_id}"

    export_html = _render_html_template(
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


def _render_input_panel() -> Optional[str]:
    """Render the user input panel and return the submitted text if any."""
    reverse_pending = get_command_reverse_pending()
    single_pending = get_command_single_pending()
    minimum_pending = get_command_minimum_pending()
    
    # Check if we're currently processing a task (to disable confirm button)
    is_processing = st.session_state.get("command_processing", False)
    pending_query = st.session_state.pop("command_pending_query", None)
    if pending_query:
        return pending_query

    st.caption("Ask a question • Issue a task • Generate analysis • Get answers")

    # If there's a pending reverse range ring selection, show Step 2 UI
    if reverse_pending:
        st.markdown("### 🔄 Step 2: Select Weapon System")
        st.info(
            f"**Reverse Range Ring in progress**\n\n"
            f"Shooter: **{reverse_pending.get('country_name')}** → Target: **{reverse_pending.get('city_name')}**"
        )

        weapons = reverse_pending.get("weapons", [])
        weapon_labels = [
            f"{idx}. {w.get('name', 'Unknown')} — {w.get('range_km', 0):,.0f} km"
            for idx, w in enumerate(weapons, start=1)
        ]

        selected_label = st.selectbox(
            "Choose a weapon system:",
            options=weapon_labels,
            index=0,
            key="weapon_select_dropdown",
            disabled=is_processing,
        )

        # Hide the confirm button while processing to match Execute Command behavior
        confirm_btn = False
        if not is_processing:
            confirm_btn = st.button(
                "✅ Confirm Selection",
                key="confirm_weapon",
                use_container_width=True,
            )

        # Reset Execution Query button - only show when there's output to clear
        if get_command_output() is not None and not is_processing:
            st.divider()
            if st.button("🔄 Reset Execution Query", key="reset_execution_query_step2", use_container_width=True):
                _clear_product_viewer()
                st.rerun()

        if confirm_btn and selected_label and not is_processing:
            # Set processing state to prevent duplicate clicks
            st.session_state["command_processing"] = True
            # Extract selection index from label
            sel_idx = weapon_labels.index(selected_label) + 1
            st.session_state["command_pending_query"] = f"Select reverse weapon {sel_idx}"
            st.rerun()

        return None

    # If there's a pending single range ring selection, show Step 2 UI
    if single_pending:
        st.markdown("### 🎯 Step 2: Select Weapon System")
        st.info(
            f"**Single Range Ring in progress**\n\n"
            f"Origin: **{single_pending.get('country_name')}**"
        )

        weapons = single_pending.get("weapons", [])
        weapon_labels = [
            f"{idx}. {w.get('name', 'Unknown')} — {w.get('range_km', 0):,.0f} km"
            for idx, w in enumerate(weapons, start=1)
        ]

        selected_label = st.selectbox(
            "Choose a weapon system:",
            options=weapon_labels,
            index=0,
            key="single_weapon_select_dropdown",
            disabled=is_processing,
        )

        # Hide the confirm button while processing to match Execute Command behavior
        confirm_btn = False
        if not is_processing:
            confirm_btn = st.button(
                "✅ Confirm Selection",
                key="confirm_single_weapon",
                use_container_width=True,
            )

        # Reset Execution Query button
        if get_command_output() is not None and not is_processing:
            st.divider()
            if st.button("🔄 Reset Execution Query", key="reset_execution_query_single", use_container_width=True):
                _clear_product_viewer()
                st.rerun()

        if confirm_btn and selected_label and not is_processing:
            # Set processing state to prevent duplicate clicks
            st.session_state["command_processing"] = True
            sel_idx = weapon_labels.index(selected_label) + 1
            st.session_state["command_pending_query"] = f"Select single weapon {sel_idx}"
            st.rerun()

        return None

    # If there's a pending minimum range ring selection, show Step 2 UI
    if minimum_pending:
        selection_labels = minimum_pending.get("selection_labels")
        inferred_type = minimum_pending.get("location_type", "unknown")

        if not selection_labels:
            st.markdown("### 📏 Step 2: Select Location Type")
            st.info("**Minimum Range Ring in progress**\n\nSelect a location type to continue.")
            type_options = ["Countries", "Cities"]
            default_index = 0 if inferred_type == "countries" else 1
            selected_type = st.selectbox(
                "Choose location type:",
                options=type_options,
                index=default_index,
                key="minimum_type_select",
                disabled=is_processing,
            )

            confirm_btn = False
            if not is_processing:
                confirm_btn = st.button(
                    "✅ Confirm Selection",
                    key="confirm_minimum_type",
                    use_container_width=True,
                )

            if get_command_output() is not None and not is_processing:
                st.divider()
                if st.button(
                    "🔄 Reset Execution Query",
                    key="reset_execution_query_minimum_type",
                    use_container_width=True,
                ):
                    _clear_product_viewer()
                    st.rerun()

            if confirm_btn and selected_type and not is_processing:
                st.session_state["command_processing"] = True
                st.session_state["command_pending_query"] = (
                    f"Select minimum type {selected_type.lower()}"
                )
                st.rerun()

            return None

        st.markdown("### 📏 Step 2: Select Minimum Range Locations")
        st.info(
            "**Minimum Range Ring in progress**\n\n"
            f"Mode: **{inferred_type.title()}**"
        )

        selected_a = st.selectbox(
            "Select Location A:",
            options=selection_labels,
            index=0,
            key="minimum_location_a",
            disabled=is_processing,
        )
        selected_b = st.selectbox(
            "Select Location B:",
            options=selection_labels,
            index=1 if len(selection_labels) > 1 else 0,
            key="minimum_location_b",
            disabled=is_processing,
        )

        confirm_btn = False
        if not is_processing:
            confirm_btn = st.button(
                "✅ Confirm Selection",
                key="confirm_minimum_locations",
                use_container_width=True,
            )

        if get_command_output() is not None and not is_processing:
            st.divider()
            if st.button(
                "🔄 Reset Execution Query",
                key="reset_execution_query_minimum",
                use_container_width=True,
            ):
                _clear_product_viewer()
                st.rerun()

        if confirm_btn and selected_a and selected_b and not is_processing:
            st.session_state["command_processing"] = True
            sel_idx_a = selection_labels.index(selected_a) + 1
            sel_idx_b = selection_labels.index(selected_b) + 1
            st.session_state["command_pending_query"] = (
                f"Select minimum locations {sel_idx_a} and {sel_idx_b}"
            )
            st.rerun()

        return None

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

        # Inject JavaScript status bar for real-time input validation
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
            _render_js_export_controls(output, "command_output")
        else:
            st.markdown("### Answer")
            st.markdown(output)
        
        # Add reset button at the bottom of the viewer
        st.divider()
        if st.button("🔄 Reset Execution Query", key="reset_execution_query", use_container_width=True):
            _clear_product_viewer()
            st.rerun()


# Path to the shared JavaScript validation file
_VALIDATION_JS_PATH = "/home/flaniganp/PycharmProjects/range_ring_2016_05_12/app/ui/command/validation.js"

# Cache for the loaded JS template (loaded once per session)
_validation_js_cache: Optional[str] = None
_validation_js_mtime: Optional[int] = None
_html_template_cache: dict[str, str] = {}
_html_template_mtime: dict[str, int] = {}


def _load_validation_js_template() -> str:
    """Load the JavaScript validation template from file (cached)."""
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
    """Load an HTML template from app/html/command (cached)."""
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


def _render_html_template(template_name: str, replacements: Optional[dict[str, str]] = None) -> str:
    """Render a cached HTML template with placeholder replacements."""
    html = _load_html_template(template_name)
    for placeholder, value in (replacements or {}).items():
        html = html.replace(placeholder, value)
    return html


def _get_shared_validation_js() -> str:
    """
    Load and populate the shared JavaScript validation code.
    
    Reads from validation.js and replaces placeholders with actual data:
    - {{COUNTRIES_JSON}} -> list of lowercase country names
    - {{CITIES_JSON}} -> list of lowercase city names  
    - {{COUNTRIES_DISPLAY_JSON}} -> list of display country names
    - {{CITIES_DISPLAY_JSON}} -> list of display city names
    """
    import json
    
    # Load the JS template
    js_template = _load_validation_js_template()
    
    # Get data from the service
    data_service = get_data_service()
    countries = data_service.get_country_list()
    cities = data_service.get_city_list()
    
    # Create JSON strings for replacement
    countries_json = json.dumps([c.lower() for c in countries])
    cities_json = json.dumps([c.lower() for c in cities])
    countries_display_json = json.dumps(sorted(countries))
    cities_display_json = json.dumps(sorted(cities))
    
    # Replace placeholders with actual data
    js_code = js_template.replace("{{COUNTRIES_JSON}}", countries_json)
    js_code = js_code.replace("{{CITIES_JSON}}", cities_json)
    js_code = js_code.replace("{{COUNTRIES_DISPLAY_JSON}}", countries_display_json)
    js_code = js_code.replace("{{CITIES_DISPLAY_JSON}}", cities_display_json)
    
    return js_code


def _render_command_input_status_bar() -> None:
    """Render a JavaScript-based status bar using the HTML template."""
    shared_js = _get_shared_validation_js()

    # Extract the default empty message once (same behavior as before)
    empty_message = (
        shared_js
        .split("messages:")[1]
        .split("empty:")[1]
        .split("'")[1]
    )

    status_html = _render_html_template(
        "status_bar.html",
        replacements={
            "{{SHARED_JS}}": shared_js,
            "{{EMPTY_MESSAGE}}": empty_message,
        },
    )

    components.html(status_html, height=55)


def _render_single_range_ring_validator() -> None:
    """Render the Single Range Ring real-time validator widget."""
    import json

    data_service = get_data_service()
    countries = data_service.get_country_list()

    html = _render_html_template(
        "srr_validator.html",
        replacements={
            "{{COUNTRIES_JSON}}": json.dumps([c.lower() for c in countries]),
            "{{COUNTRIES_DISPLAY_JSON}}": json.dumps(sorted(countries)),
        },
    )

    components.html(html, height=320)


def _render_minimum_range_ring_validator() -> None:
    """Render the Minimum Range Ring real-time validator widget."""
    import json

    data_service = get_data_service()
    countries = data_service.get_country_list()
    cities = data_service.get_city_list()

    html = _render_html_template(
        "mrr_validator.html",
        replacements={
            "{{COUNTRIES_JSON}}": json.dumps([c.lower() for c in countries]),
            "{{CITIES_JSON}}": json.dumps([c.lower() for c in cities]),
            "{{COUNTRIES_DISPLAY_JSON}}": json.dumps(sorted(countries)),
            "{{CITIES_DISPLAY_JSON}}": json.dumps(sorted(cities)),
        },
    )

    components.html(html, height=420)


def _render_reverse_range_ring_validator() -> None:
    """Render JavaScript-based real-time validation widget for Reverse Range Ring commands."""
    import json
    
    # Get the country and city lists for validation
    data_service = get_data_service()
    countries = data_service.get_country_list()
    cities = data_service.get_city_list()
    
    # Keep original case for display, lowercase for matching
    countries_display_json = json.dumps(sorted(countries))
    cities_display_json = json.dumps(sorted(cities))
    countries_json = json.dumps([c.lower() for c in countries])
    cities_json = json.dumps([c.lower() for c in cities])
    
    validator_html = f"""
    <style>
        .rrr-validator {{
            font-family: "Source Sans Pro", sans-serif;
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 12px;
            margin: 10px 0;
        }}
        .rrr-validator-title {{
            font-size: 13px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }}
        .rrr-section {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
            font-size: 13px;
        }}
        .rrr-icon {{
            width: 18px;
            height: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }}
        .rrr-valid {{ color: #28a745; }}
        .rrr-invalid {{ color: #dc3545; }}
        .rrr-warning {{ color: #ffc107; }}
        .rrr-pending {{ color: #6c757d; }}
        .rrr-label {{
            color: #555;
            min-width: 100px;
        }}
        .rrr-value {{
            color: #333;
            font-weight: 500;
        }}
        .rrr-match {{
            color: #28a745;
            font-size: 11px;
            margin-left: 4px;
        }}
        .rrr-hint {{
            font-size: 11px;
            color: #888;
            font-style: italic;
            margin-top: 8px;
        }}
        /* Lookup section styles */
        .rrr-lookup-section {{
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid #e0e0e0;
        }}
        .rrr-lookup-title {{
            font-size: 12px;
            font-weight: 600;
            color: #555;
            margin-bottom: 8px;
        }}
        .rrr-lookup-row {{
            display: flex;
            gap: 12px;
            margin-bottom: 8px;
        }}
        .rrr-lookup-col {{
            flex: 1;
        }}
        .rrr-lookup-label {{
            font-size: 11px;
            color: #666;
            margin-bottom: 4px;
        }}
        .rrr-search-input {{
            width: 100%;
            padding: 6px 8px;
            font-size: 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
        }}
        .rrr-search-input:focus {{
            outline: none;
            border-color: #ff4b4b;
        }}
        .rrr-suggestions {{
            max-height: 150px;
            overflow-y: auto;
            overflow-x: hidden;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            margin-top: 4px;
            display: none;
            scrollbar-width: thin;
            scrollbar-color: #888 #f0f0f0;
        }}
        .rrr-suggestions::-webkit-scrollbar {{
            width: 8px;
        }}
        .rrr-suggestions::-webkit-scrollbar-track {{
            background: #f0f0f0;
            border-radius: 4px;
        }}
        .rrr-suggestions::-webkit-scrollbar-thumb {{
            background: #888;
            border-radius: 4px;
        }}
        .rrr-suggestions::-webkit-scrollbar-thumb:hover {{
            background: #666;
        }}
        .rrr-suggestions.active {{
            display: block;
        }}
        .rrr-suggestion {{
            padding: 6px 8px;
            font-size: 11px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
        }}
        .rrr-suggestion:last-child {{
            border-bottom: none;
        }}
        .rrr-suggestion:hover {{
            background: #f0f2f6;
        }}
        .rrr-suggestion-match {{
            background: #fff3cd;
        }}
        .rrr-no-results {{
            padding: 6px 8px;
            font-size: 11px;
            color: #888;
            font-style: italic;
        }}
    </style>
    <div class="rrr-validator" id="rrr-validator-widget">
        <div class="rrr-validator-title">📋 Query Validator</div>
        <div class="rrr-section" id="rrr-verb">
            <span class="rrr-icon rrr-pending" id="rrr-verb-icon">○</span>
            <span class="rrr-label">Action:</span>
            <span class="rrr-value" id="rrr-verb-value">—</span>
        </div>
        <div class="rrr-section" id="rrr-type">
            <span class="rrr-icon rrr-pending" id="rrr-type-icon">○</span>
            <span class="rrr-label">Ring Type:</span>
            <span class="rrr-value" id="rrr-type-value">—</span>
        </div>
        <div class="rrr-section" id="rrr-from">
            <span class="rrr-icon rrr-pending" id="rrr-from-icon">○</span>
            <span class="rrr-label">Preposition:</span>
            <span class="rrr-value" id="rrr-from-value">—</span>
        </div>
        <div class="rrr-section" id="rrr-country">
            <span class="rrr-icon rrr-pending" id="rrr-country-icon">○</span>
            <span class="rrr-label">Country:</span>
            <span class="rrr-value" id="rrr-country-value">—</span>
        </div>
        <div class="rrr-section" id="rrr-target">
            <span class="rrr-icon rrr-pending" id="rrr-target-icon">○</span>
            <span class="rrr-label">Target Prep:</span>
            <span class="rrr-value" id="rrr-target-value">—</span>
        </div>
        <div class="rrr-section" id="rrr-city">
            <span class="rrr-icon rrr-pending" id="rrr-city-icon">○</span>
            <span class="rrr-label">City:</span>
            <span class="rrr-value" id="rrr-city-value">—</span>
        </div>
        <div class="rrr-hint" id="rrr-hint">Type your command above to see validation...</div>
        
        <!-- Lookup Section -->
        <div class="rrr-lookup-section">
            <div class="rrr-lookup-title">🔍 Name Lookup (search to find exact format)</div>
            <div class="rrr-lookup-row">
                <div class="rrr-lookup-col">
                    <div class="rrr-lookup-label">Country Search:</div>
                    <input type="text" class="rrr-search-input" id="rrr-country-search" placeholder="Type to search countries..." autocomplete="off">
                    <div class="rrr-suggestions" id="rrr-country-suggestions"></div>
                </div>
                <div class="rrr-lookup-col">
                    <div class="rrr-lookup-label">City Search:</div>
                    <input type="text" class="rrr-search-input" id="rrr-city-search" placeholder="Type to search cities..." autocomplete="off">
                    <div class="rrr-suggestions" id="rrr-city-suggestions"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        (function() {{
            // Valid options
            const validVerbs = ['generate', 'create', 'build', 'show'];
            const validTypes = ['reverse range ring', 'reverse ring', 'launch envelope', 'reverse range'];
            const validFromPreps = ['from', 'within', 'inside'];
            const validTargetPreps = ['against', 'to', 'toward', 'towards'];
            const validCountries = {countries_json};
            const validCities = {cities_json};
            const countriesDisplay = {countries_display_json};
            const citiesDisplay = {cities_display_json};
            
            // Fuzzy match function with multiple match types
            function fuzzyMatch(input, options) {{
                if (!input) return null;
                const lower = input.toLowerCase().trim();
                // Exact match first
                if (options.includes(lower)) return lower;
                // Prefix match
                const prefixMatch = options.find(opt => opt.startsWith(lower));
                if (prefixMatch) return prefixMatch;
                // Contains match (also check if any word in option starts with input)
                for (const opt of options) {{
                    const words = opt.split(/[\\s,]+/);
                    for (const word of words) {{
                        if (word.startsWith(lower) || lower.startsWith(word)) {{
                            return opt;
                        }}
                    }}
                }}
                // General contains
                const containsMatch = options.find(opt => opt.includes(lower) || lower.includes(opt));
                return containsMatch || null;
            }}
            
            // Get fuzzy matches for suggestions (returns multiple)
            function getFuzzyMatches(input, displayOptions, maxResults = 10) {{
                if (!input || input.length < 1) return displayOptions.slice(0, maxResults);
                const lower = input.toLowerCase().trim();
                const results = [];
                
                // Score each option
                const scored = displayOptions.map(opt => {{
                    const optLower = opt.toLowerCase();
                    let score = 0;
                    
                    // Exact match = highest
                    if (optLower === lower) score = 100;
                    // Starts with = high
                    else if (optLower.startsWith(lower)) score = 80;
                    // Word in option starts with input
                    else {{
                        const words = optLower.split(/[\\s,]+/);
                        for (const word of words) {{
                            if (word.startsWith(lower)) {{
                                score = 70;
                                break;
                            }}
                        }}
                    }}
                    // Contains anywhere
                    if (score === 0 && optLower.includes(lower)) score = 50;
                    // Input contains option word
                    if (score === 0) {{
                        const words = optLower.split(/[\\s,]+/);
                        for (const word of words) {{
                            if (lower.includes(word) && word.length > 2) {{
                                score = 40;
                                break;
                            }}
                        }}
                    }}
                    
                    return {{ opt, score }};
                }});
                
                return scored
                    .filter(s => s.score > 0)
                    .sort((a, b) => b.score - a.score)
                    .slice(0, maxResults)
                    .map(s => s.opt);
            }}
            
            // valid: 'exact' | 'fuzzy' | false | null
            function setStatus(id, valid, value, matched) {{
                const icon = document.getElementById(id + '-icon');
                const valueEl = document.getElementById(id + '-value');
                if (!icon || !valueEl) return;
                
                if (valid === 'exact') {{
                    icon.textContent = '✓';
                    icon.className = 'rrr-icon rrr-valid';
                }} else if (valid === 'fuzzy') {{
                    icon.textContent = '⚠';
                    icon.className = 'rrr-icon rrr-warning';
                }} else if (valid === false) {{
                    icon.textContent = '✗';
                    icon.className = 'rrr-icon rrr-invalid';
                }} else {{
                    icon.textContent = '○';
                    icon.className = 'rrr-icon rrr-pending';
                }}
                
                if (value && matched && matched !== value.toLowerCase()) {{
                    valueEl.innerHTML = value + '<span class="rrr-match"> (use: ' + matched + ')</span>';
                }} else {{
                    valueEl.textContent = value || '—';
                }}
            }}
            
            function parseAndValidate(text) {{
                const hint = document.getElementById('rrr-hint');
                if (!text || text.trim().length < 3) {{
                    ['rrr-verb', 'rrr-type', 'rrr-from', 'rrr-country', 'rrr-target', 'rrr-city'].forEach(id => {{
                        setStatus(id, null, '—');
                    }});
                    if (hint) hint.textContent = 'Type your command above to see validation...';
                    return;
                }}
                
                const lower = text.toLowerCase().trim();

                if (lower.includes('minimum') || lower.includes('min distance') || lower.includes('minimum distance')) {{
                    ['rrr-verb', 'rrr-type', 'rrr-from', 'rrr-country', 'rrr-target', 'rrr-city'].forEach(id => {{
                        setStatus(id, null, '—');
                    }});
                    if (hint) hint.textContent = 'This looks like a Minimum Range Ring command. See Minimum Range Ring tab.';
                    return;
                }}

                if (lower.includes('single range ring') || lower.includes('single ring')) {{
                    ['rrr-verb', 'rrr-type', 'rrr-from', 'rrr-country', 'rrr-target', 'rrr-city'].forEach(id => {{
                        setStatus(id, null, '—');
                    }});
                    if (hint) hint.textContent = 'This looks like a Single Range Ring command. See Single Range Ring tab.';
                    return;
                }}
                
                // Verb validation
                let verbMatch = validVerbs.find(v => lower.startsWith(v));
                setStatus('rrr-verb', verbMatch ? 'exact' : false, verbMatch || (lower.split(' ')[0] || ''), verbMatch);
                
                // Type validation
                let typeMatch = validTypes.find(t => lower.includes(t));
                setStatus('rrr-type', typeMatch ? 'exact' : false, typeMatch || '—', typeMatch);
                
                // From preposition validation
                let fromMatch = validFromPreps.find(p => {{
                    const typeEnd = typeMatch ? lower.indexOf(typeMatch) + typeMatch.length : 0;
                    const afterType = lower.substring(typeEnd);
                    return afterType.includes(' ' + p + ' ') || afterType.endsWith(' ' + p);
                }});
                setStatus('rrr-from', fromMatch ? 'exact' : false, fromMatch || '—', fromMatch);
                
                let country = null;
                let city = null;
                let targetPrep = null;
                
                if (fromMatch) {{
                    const typeEnd = typeMatch ? lower.indexOf(typeMatch) + typeMatch.length : 0;
                    const fromToken = ' ' + fromMatch;
                    const fromIdx = lower.indexOf(fromToken + ' ', typeEnd);
                    let afterFrom = '';

                    if (fromIdx >= 0) {{
                        afterFrom = lower.substring(fromIdx + fromMatch.length + 2);
                    }} else if (lower.endsWith(fromToken)) {{
                        afterFrom = '';
                    }}

                    if (afterFrom !== '') {{
                        const targetMatch = validTargetPreps.find(tp => (
                            afterFrom.includes(' ' + tp + ' ') || afterFrom.endsWith(' ' + tp)
                        ));
                        if (targetMatch) {{
                            const tpIdx = afterFrom.indexOf(' ' + targetMatch + ' ');
                            targetPrep = targetMatch;
                            if (tpIdx >= 0) {{
                                country = afterFrom.substring(0, tpIdx).trim();
                                city = afterFrom.substring(tpIdx + targetMatch.length + 2).trim().replace(/\\.$/, '');
                            }} else {{
                                country = afterFrom.substring(0, afterFrom.length - targetMatch.length - 1).trim();
                                city = '';
                            }}
                        }} else {{
                            country = afterFrom.trim();
                        }}
                    }}
                }}
                
                // Country validation: exact vs fuzzy vs no match
                let countryStatus = false;
                let countryMatch = null;
                if (country) {{
                    const countryLower = country.toLowerCase();
                    if (validCountries.includes(countryLower)) {{
                        countryStatus = 'exact';
                        countryMatch = countryLower;
                    }} else {{
                        countryMatch = fuzzyMatch(country, validCountries);
                        if (countryMatch) {{
                            countryStatus = 'fuzzy';  // Found fuzzy match but not exact
                        }}
                    }}
                }}
                setStatus('rrr-country', countryStatus, country || '—', countryMatch);
                
                // Target prep validation
                setStatus('rrr-target', targetPrep ? 'exact' : false, targetPrep || '—', targetPrep);
                
                // City validation: exact vs fuzzy vs no match
                let cityStatus = false;
                let cityMatch = null;
                if (city) {{
                    const cityLower = city.toLowerCase();
                    if (validCities.includes(cityLower)) {{
                        cityStatus = 'exact';
                        cityMatch = cityLower;
                    }} else {{
                        cityMatch = fuzzyMatch(city, validCities);
                        if (cityMatch) {{
                            cityStatus = 'fuzzy';  // Found fuzzy match but not exact
                        }}
                    }}
                }}
                setStatus('rrr-city', cityStatus, city || '—', cityMatch);
                
                // Check overall validity
                const allExact = verbMatch && typeMatch && fromMatch && (countryStatus === 'exact') && targetPrep && (cityStatus === 'exact');
                const allValid = verbMatch && typeMatch && fromMatch && countryMatch && targetPrep && cityMatch;
                const hasFuzzy = (countryStatus === 'fuzzy') || (cityStatus === 'fuzzy');
                const partialValid = typeMatch || countryMatch || cityMatch;
                
                if (allExact) {{
                    if (hint) hint.textContent = '✅ Query looks valid! Click Execute to proceed.';
                }} else if (allValid && hasFuzzy) {{
                    if (hint) hint.textContent = '⚠️ Query may work, but check ⚠ items for exact format.';
                }} else if (partialValid) {{
                    if (hint) hint.textContent = '⚠️ Some fields need attention. Check the items marked with ✗ or ⚠';
                }} else {{
                    if (hint) hint.textContent = 'Format: Generate a reverse range ring from [Country] against [City]';
                }}
            }}
            
            // Setup lookup search boxes
            function setupLookup(inputId, suggestionsId, displayOptions) {{
                const input = document.getElementById(inputId);
                const suggestions = document.getElementById(suggestionsId);
                if (!input || !suggestions) return;
                
                input.addEventListener('input', function() {{
                    const val = this.value;
                    const matches = getFuzzyMatches(val, displayOptions, 10);
                    
                    if (matches.length > 0) {{
                        suggestions.innerHTML = matches.map(m => 
                            '<div class="rrr-suggestion">' + m + '</div>'
                        ).join('');
                        suggestions.classList.add('active');
                    }} else {{
                        suggestions.innerHTML = '<div class="rrr-no-results">No matches found</div>';
                        suggestions.classList.add('active');
                    }}
                }});
                
                input.addEventListener('focus', function() {{
                    if (this.value.length >= 1 || suggestions.innerHTML) {{
                        suggestions.classList.add('active');
                    }}
                }});
                
                input.addEventListener('blur', function() {{
                    setTimeout(() => suggestions.classList.remove('active'), 200);
                }});
                
                suggestions.addEventListener('click', function(e) {{
                    if (e.target.classList.contains('rrr-suggestion')) {{
                        input.value = e.target.textContent;
                        suggestions.classList.remove('active');
                    }}
                }});
            }}
            
            // Initialize lookup boxes
            setupLookup('rrr-country-search', 'rrr-country-suggestions', countriesDisplay);
            setupLookup('rrr-city-search', 'rrr-city-suggestions', citiesDisplay);
            
            function attachListener() {{
                const textareas = window.parent.document.querySelectorAll('textarea');
                for (const ta of textareas) {{
                    if (ta.placeholder && ta.placeholder.includes('Type a question')) {{
                        ta.addEventListener('input', function(e) {{
                            parseAndValidate(e.target.value);
                        }});
                        parseAndValidate(ta.value);
                        return true;
                    }}
                }}
                return false;
            }}
            
            let attempts = 0;
            const maxAttempts = 20;
            const tryAttach = setInterval(function() {{
                attempts++;
                if (attachListener() || attempts >= maxAttempts) {{
                    clearInterval(tryAttach);
                }}
            }}, 200);
        }})();
    </script>
    """
    
    components.html(validator_html, height=430)


def _render_help_section() -> None:
    """Render the Command Center help section with tabbed tool help."""
    with st.expander("❓ Help", expanded=False):
        # Create tabs for each tool
        tab_rrr, tab_single, tab_multi, tab_min, tab_poi, tab_traj = st.tabs([
            "🔄 Reverse Range Ring",
            "🎯 Single Range Ring",
            "📊 Multiple Range Ring",
            "📏 Minimum Range Ring",
            "📍 Custom POI",
            "🚀 Launch Trajectory"
        ])
        
        with tab_rrr:
            st.markdown("**Reverse Range Ring Task**")
            st.markdown(
                "Use the format: `Generate a {reverse range ring|reverse ring|launch envelope|reverse range} "
                "from {Country} {against|to|toward|towards} {City}.`"
            )
            st.markdown(
                "Then respond with `Select reverse weapon #` using the number from the returned list to generate "
                "the reverse range ring output and export options."
            )
            st.markdown("**Example:**")
            st.code("Generate a reverse range ring from Iran against Tel Aviv")
            # Add the real-time validator widget
            _render_reverse_range_ring_validator()
        
        with tab_single:
            st.markdown("**Single Range Ring Task**")
            st.markdown(
                "Use the format: `Generate a {single range ring|single ring|range ring} "
                "{from|for} {Country}.`"
            )
            st.markdown(
                "Then respond with `Select single weapon #` using the number from the returned list to generate "
                "the single range ring output and export options."
            )
            st.markdown("**Example:**")
            st.code("Generate a single range ring from Iran")
            # Add the real-time validator widget for Single Range Ring
            _render_single_range_ring_validator()
        
        with tab_multi:
            st.markdown("**Multiple Range Ring**")
            st.markdown("*Coming Soon*")
            st.markdown("Generate multiple concentric range rings from a country or point.")
            st.markdown("**Example:**")
            st.code("Generate multiple range rings from North Korea at 500, 1000, 1500 km")
        
        with tab_min:
            st.markdown("**Minimum Range Ring Task**")
            st.markdown(
                "Use the format: `Calculate {minimum range ring|min distance|minimum distance} "
                "between {Location A} and {Location B}.`"
            )
            st.markdown(
                "Then respond with `Select minimum type countries` or `Select minimum type cities`, followed by "
                "`Select minimum locations # and #` using the numbered list to generate the output and exports."
            )
            st.markdown("**Example:**")
            st.code("Calculate minimum distance between Korea, North and Japan")
            # Add the real-time validator widget for Minimum Range Ring
            _render_minimum_range_ring_validator()
        
        with tab_poi:
            st.markdown("**Custom POI Range Ring**")
            st.markdown("*Coming Soon*")
            st.markdown("Generate range rings from custom points of interest.")
            st.markdown("**Example:**")
            st.code("Generate range ring from lat 35.6762 lon 51.4241 with range 1000 km")
        
        with tab_traj:
            st.markdown("**Launch Trajectory**")
            st.markdown("*Coming Soon*")
            st.markdown("Visualize ballistic missile launch trajectories.")
            st.markdown("**Example:**")
            st.code("Show launch trajectory from Pyongyang to Tokyo")


def _render_history() -> None:
    """Render command query/task history in reverse chronological order."""
    history = get_command_history()
    with st.expander("📜 Query & Task History", expanded=False):
        if not history:
            st.info("No command history yet.")
            return

        # Clear history button at the top - direct clear without export cache iteration
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
            
            # Clean up status display
            display_status = status.replace(" (Updated)", "")

            st.markdown(f"**{timestamp} | {entry_type}**")
            st.markdown(f"\"{text}\"")
            
            # Show extra details for reverse range ring entries
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
            
            # Export section - uses expander (no rerun needed) with lazy generation
            if entry_output is not None and isinstance(entry_output, RangeRingOutput):
                output_id = str(entry_output.output_id)
                cache_key = f"command_exports_{output_id}"
                is_cached = cache_key in st.session_state
                
                with st.expander(f"📥 Export Options {'(cached)' if is_cached else ''}", expanded=False):
                    if is_cached:
                        # Cached - show downloads immediately (no generation needed)
                        _render_cached_export_links(entry_output, f"history_{idx}")
                    else:
                        # Not cached - show generate button
                        st.caption("Exports not yet generated for this entry.")
                        if st.button("⚡ Generate Exports", key=f"gen_exports_{idx}", use_container_width=True):
                            _render_js_export_controls(entry_output, f"history_{idx}")
            
            st.divider()


def _mock_intent_response(query: str) -> tuple[CommandOutput, str, str]:
    """Return a placeholder response until full intent routing is implemented."""
    
    # =========================================================================
    # Handle Minimum Range Ring location selection (Step 2)
    # =========================================================================
    minimum_pending = get_command_minimum_pending()
    minimum_selection = _extract_minimum_location_selection(query)
    if minimum_pending and minimum_selection:
        selection_labels = minimum_pending.get("selection_labels", [])
        selected_indices = [minimum_selection[0] - 1, minimum_selection[1] - 1]
        if all(0 <= idx < len(selection_labels) for idx in selected_indices):
            location_a = selection_labels[selected_indices[0]]
            location_b = selection_labels[selected_indices[1]]
            progress_bar = st.progress(0, text="0% - Initializing...")

            def update_progress(pct: float, status: str):
                progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")

            try:
                output, distance_km = _generate_minimum_range_output(
                    minimum_pending["location_type"],
                    location_a,
                    location_b,
                    progress_callback=update_progress,
                )
                progress_bar.progress(1.0, text="100% - Complete!")

                _update_minimum_pending_history_entry(
                    minimum_pending["location_type"],
                    location_a,
                    location_b,
                    distance_km,
                    "Completed",
                    output=output,
                )

                set_command_minimum_pending(None)
                st.session_state["command_processing"] = False
                return output, "Minimum Range Ring", "Completed (Updated)"
            except CommandParsingError as exc:
                progress_bar.progress(1.0, text="Error!")
                st.session_state["command_processing"] = False
                return f"**Command Center Error**\n\n{exc}", "Minimum Range Ring", "Failed"

        st.session_state["command_processing"] = False
        return (
            "**Selection Error**\n\nPlease reply with valid location numbers from the list.",
            "Minimum Range Ring",
            "Pending",
        )

    # =========================================================================
    # Handle Minimum Range Ring type selection (Step 1.5)
    # =========================================================================
    minimum_type_selection = _extract_minimum_location_type(query)
    if minimum_pending and minimum_type_selection and not minimum_pending.get("selection_labels"):
        location_type = minimum_type_selection
        data_service = get_data_service()
        if location_type == "countries":
            selection_labels = data_service.get_country_list()
        else:
            selection_labels = data_service.get_city_list()

        set_command_minimum_pending(
            {
                "location_type": location_type,
                "selection_labels": selection_labels,
            }
        )
        st.session_state["command_processing"] = False
        message = _build_minimum_location_selection_message(location_type, selection_labels)
        return message, "Minimum Range Ring", "Pending"

    # =========================================================================
    # Handle Single Range Ring weapon selection (Step 2)
    # =========================================================================
    single_pending = get_command_single_pending()
    single_selection = _extract_single_weapon_selection(query)
    if single_pending and single_selection:
        weapons = single_pending.get("weapons", [])
        selected_index = single_selection - 1
        if 0 <= selected_index < len(weapons):
            weapon = weapons[selected_index]
            weapon_name = weapon.get("name", "Unknown")
            weapon_range = weapon.get("range_km", 0)
            
            progress_bar = st.progress(0, text="0% - Initializing...")
            
            def update_progress(pct: float, status: str):
                progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")
            
            try:
                output = _generate_single_range_output_with_weapon(
                    single_pending["country_name"],
                    single_pending["country_code"],
                    weapon,
                    progress_callback=update_progress,
                )
                progress_bar.progress(1.0, text="100% - Complete!")
                
                _update_single_pending_history_entry(
                    single_pending["country_name"],
                    weapon_name,
                    weapon_range,
                    "Completed",
                    output=output,
                )
                
                set_command_single_pending(None)
                # Clear processing state
                st.session_state["command_processing"] = False
                return output, "Single Range Ring", "Completed (Updated)"
            except CommandParsingError as exc:
                progress_bar.progress(1.0, text="Error!")
                # Clear processing state on error
                st.session_state["command_processing"] = False
                return f"**Command Center Error**\n\n{exc}", "Single Range Ring", "Failed"
        # Clear processing state on invalid selection
        st.session_state["command_processing"] = False
        return (
            "**Selection Error**\n\nPlease reply with a valid weapon number from the list.",
            "Single Range Ring",
            "Pending",
        )
    
    # =========================================================================
    # Handle Single Range Ring initial request (Step 1)
    # =========================================================================
    single_request = _extract_single_range_request(query)
    if single_request:
        country = single_request
        try:
            data_service = get_data_service()
            matched_country = _fuzzy_match(country, data_service.get_country_list(), cutoff=0.6)
            if not matched_country:
                raise CommandParsingError(f"Could not match country '{country}' in request.")

            country_code = data_service.get_country_code(matched_country)
            if not country_code:
                raise CommandParsingError(f"Could not resolve ISO code for '{matched_country}'.")

            weapons = data_service.get_weapon_systems(country_code)
            if not weapons:
                raise CommandParsingError(f"No weapon systems found for {matched_country}.")

            set_command_single_pending(
                {
                    "country_name": matched_country,
                    "country_code": country_code,
                    "weapons": weapons,
                }
            )

            message = _build_single_weapon_selection_message(matched_country, weapons)
            return message, "Single Range Ring", "Pending"
        except CommandParsingError as exc:
            return f"**Command Center Error**\n\n{exc}", "Single Range Ring", "Failed"
    
    # =========================================================================
    # Handle Minimum Range Ring initial request (Step 1)
    # =========================================================================
    minimum_request = _extract_minimum_range_request(query)
    if minimum_request:
        location_a, location_b = minimum_request
        try:
            data_service = get_data_service()
            country_match_a = _fuzzy_match(location_a, data_service.get_country_list(), cutoff=0.6)
            country_match_b = _fuzzy_match(location_b, data_service.get_country_list(), cutoff=0.6)
            city_match_a = _fuzzy_match(location_a, data_service.get_city_list(), cutoff=0.6)
            city_match_b = _fuzzy_match(location_b, data_service.get_city_list(), cutoff=0.6)

            if (country_match_a and country_match_b) and not (city_match_a and city_match_b):
                location_type = "countries"
            elif (city_match_a and city_match_b) and not (country_match_a and country_match_b):
                location_type = "cities"
            else:
                location_type = "unknown"

            if location_type == "unknown":
                set_command_minimum_pending({"location_type": location_type})
                message = _build_minimum_location_type_message()
                return message, "Minimum Range Ring", "Pending"

            selection_labels = (
                data_service.get_country_list()
                if location_type == "countries"
                else data_service.get_city_list()
            )
            set_command_minimum_pending(
                {
                    "location_type": location_type,
                    "selection_labels": selection_labels,
                }
            )
            st.session_state["command_processing"] = False
            message = _build_minimum_location_selection_message(location_type, selection_labels)
            return message, "Minimum Range Ring", "Pending"
        except CommandParsingError as exc:
            return f"**Command Center Error**\n\n{exc}", "Minimum Range Ring", "Failed"

    # =========================================================================
    # Handle Reverse Range Ring weapon selection (Step 2)
    # =========================================================================
    pending = get_command_reverse_pending()
    selection = _extract_reverse_weapon_selection(query)
    if pending and selection:
        weapons = pending.get("weapons", [])
        selected_index = selection - 1
        if 0 <= selected_index < len(weapons):
            weapon = weapons[selected_index]
            weapon_name = weapon.get("name", "Unknown")
            weapon_range = weapon.get("range_km", 0)
            
            # Create progress bar - same as analytical tool
            progress_bar = st.progress(0, text="0% - Initializing...")
            
            def update_progress(pct: float, status: str):
                """Callback to update progress bar from generate_reverse_range_ring."""
                progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")
            
            try:
                output = _generate_reverse_range_output_with_weapon(
                    pending["country_name"],
                    pending["city_name"],
                    pending["country_code"],
                    pending["target_coords"],
                    weapon,
                    progress_callback=update_progress,
                )
                progress_bar.progress(1.0, text="100% - Complete!")
                
                # Update the pending history entry with completion details and output
                _update_pending_history_entry(
                    pending["country_name"],
                    pending["city_name"],
                    weapon_name,
                    weapon_range,
                    "Completed",
                    output=output,
                )
                
                set_command_reverse_pending(None)
                # Clear processing state
                st.session_state["command_processing"] = False
                return output, "Reverse Range Ring", "Completed (Updated)"
            except CommandParsingError as exc:
                progress_bar.progress(1.0, text="Error!")
                # Clear processing state on error
                st.session_state["command_processing"] = False
                return f"**Command Center Error**\n\n{exc}", "Reverse Range Ring", "Failed"
        # Clear processing state on invalid selection
        st.session_state["command_processing"] = False
        return (
            "**Selection Error**\n\nPlease reply with a valid weapon number from the list.",
            "Reverse Range Ring",
            "Pending",
        )

    reverse_request = _extract_reverse_range_request(query)
    if reverse_request:
        country, city = reverse_request
        try:
            data_service = get_data_service()
            matched_country = _fuzzy_match(country, data_service.get_country_list(), cutoff=0.6)
            matched_city = _fuzzy_match(city, data_service.get_city_list(), cutoff=0.6)
            if not matched_country or not matched_city:
                raise CommandParsingError("Could not match country or city in request.")

            country_code = data_service.get_country_code(matched_country)
            target_coords = data_service.get_city_coordinates(matched_city)
            weapons = data_service.get_weapon_systems(country_code) if country_code else []
            if not country_code or not target_coords or not weapons:
                raise CommandParsingError("Missing country, target, or weapon data for selection step.")

            country_geometry = data_service.get_country_geometry(country_code)
            if country_geometry is None:
                raise CommandParsingError("Could not load shooter country geometry.")

            # Estimate minimum distance from shooter country to target city
            min_distance_km = None
            try:
                from app.geometry.utils import _extract_all_coordinates
                coords_list = _extract_all_coordinates(country_geometry)
                min_distance_km = min(
                    geodesic_distance(lat, lon, target_coords[0], target_coords[1])
                    for lon, lat in coords_list[:500]
                )
            except Exception:
                min_distance_km = None

            if min_distance_km is not None:
                weapons = [w for w in weapons if w.get("range_km", 0) >= min_distance_km]

            if not weapons:
                return (
                    "**No viable weapon systems found**\n\n"
                    f"None of the listed systems for {matched_country} can reach {matched_city}. "
                    "This task cannot proceed.",
                    "Reverse Range Ring",
                    "Failed",
                )

            set_command_reverse_pending(
                {
                    "country_name": matched_country,
                    "city_name": matched_city,
                    "country_code": country_code,
                    "target_coords": target_coords,
                    "weapons": weapons,
                }
            )

            message = _build_weapon_selection_message(matched_country, weapons)
            return message, "Reverse Range Ring", "Pending"
        except CommandParsingError as exc:
            return f"**Command Center Error**\n\n{exc}", "Reverse Range Ring", "Failed"

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

    was_processing = st.session_state.get("command_processing", False)
    query = _render_input_panel()
    if query:
        output, resolution, status = _mock_intent_response(query)

        # Only update command output for completed or failed tasks, not pending
        if status != "Pending":
            set_command_output(output)

        # Only add a new history entry if we're not updating an existing one
        # "Completed (Updated)" means we already updated the pending entry
        if status != "Completed (Updated)":
            is_task = resolution in ("Reverse Range Ring", "Single Range Ring", "Minimum Range Ring")
            add_command_history_entry(
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "Task" if is_task else "Query",
                    "text": query,
                    "resolution": resolution,
                    "status": status,
                }
            )

        # If a pending state was just set, rerun to show Step 2 UI immediately
        if status == "Pending" and (
            get_command_reverse_pending() is not None
            or get_command_single_pending() is not None
            or get_command_minimum_pending() is not None
        ):
            st.rerun()

    if not was_processing and not st.session_state.get("command_processing", False):
        _render_help_section()
    _render_product_output_viewer()
    _render_history()
