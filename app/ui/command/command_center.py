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
    MultipleRangeRingInput,
    DistanceUnit,
    OriginType,
)
from app.geometry.services import (
    generate_reverse_range_ring,
    generate_single_range_ring,
    calculate_minimum_distance,
    generate_multiple_range_rings,
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
    get_command_multiple_pending,
    set_command_multiple_pending,
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


def _extract_multiple_range_request(text: str) -> Optional[dict]:
    """Extract country, distances, unit, and missile names from a multiple range ring command."""
    normalized = _normalize_text(text)
    if "multiple" not in normalized:
        return None

    synonyms = r"multiple range rings|multiple range ring|multiple rings"
    prepositions = r"from|for"
    pattern = (
        rf"(?:generate|create|build|show)?\s*(?:{synonyms})\s+"
        rf"(?:{prepositions})\s+(?P<country>.+?)\s+"
        rf"at\s+(?P<distances>.+?)\s+(?P<unit>km|mi|nm)\b"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None

    country_raw = match.group("country").strip().rstrip(".")
    distances_raw = match.group("distances").strip()
    unit_raw = match.group("unit").lower()
    distances = [float(val) for val in re.findall(r"[\d.]+", distances_raw)]
    if not distances or not country_raw:
        return None

    missile_names = []
    names_match = re.search(r"missile names are (.+)$", text, flags=re.IGNORECASE)
    if names_match:
        names_text = names_match.group(1).strip().rstrip(".")
        missile_names = [
            name.strip()
            for name in re.sub(r"\band\b", ",", names_text, flags=re.IGNORECASE)
            .split(",")
            if name.strip()
        ]

    return {
        "country": country_raw,
        "distances": distances,
        "unit": unit_raw,
        "missile_names": missile_names,
    }


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

    if "multiple" in normalized or "missile names" in normalized:
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


def _update_multiple_pending_history_entry(
    country_name: str,
    ring_count: int,
    final_status: str,
    output: Optional[RangeRingOutput] = None,
) -> None:
    """Update the pending multiple range ring history entry with completion details."""
    updates = {
        "status": final_status,
        "text": f"Multiple range rings: {country_name} ({ring_count} rings)",
        "origin_country": country_name,
        "ring_count": ring_count,
    }
    
    if output is not None:
        updates["output"] = output
    
    update_command_history_entry(
        match_criteria={
            "resolution": "Multiple Range Ring",
            "status": "Pending",
        },
        updates=updates
    )


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

        # Render SVG once and reuse for both PNG and PDF, ensuring weapon_source flows through metadata
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
    multiple_pending = get_command_multiple_pending()
    multiple_pending_query = st.session_state.pop("command_multiple_pending_query", None)
    
    # Check if we're currently processing a task (to disable confirm button)
    is_processing = st.session_state.get("command_processing", False)
    pending_query = st.session_state.pop("command_pending_query", None)
    if pending_query:
        return pending_query

    if multiple_pending_query:
        return multiple_pending_query

    st.caption("Ask a question • Issue a task • Generate analysis • Get answers")

    # If there's a pending multiple range ring selection, show Step 2 UI
    if multiple_pending:
        st.markdown("### 📊 Step 2: Confirm Multiple Range Rings")
        st.info(
            f"**Multiple Range Ring in progress**\n\n"
            f"Origin Country: **{multiple_pending.get('country_name')}**"
        )

        # Initialize ranges in session state if not already
        if "command_multi_ranges" not in st.session_state:
            # Prepopulate from parsed data
            parsed_ranges = multiple_pending.get("ranges", [])
            st.session_state.command_multi_ranges = [
                {
                    "value": r[0],
                    "unit": r[1].value if hasattr(r[1], 'value') else r[1],
                    "label": r[2] if len(r) > 2 and r[2] else "",
                }
                for r in parsed_ranges
            ]

        # Display editable ranges
        st.markdown("**Range Rings:**")
        ranges_to_remove = []
        for i, range_item in enumerate(st.session_state.command_multi_ranges):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

            with col1:
                range_item["label"] = st.text_input(
                    f"Missile Name {i+1}",
                    value=range_item.get("label", ""),
                    key=f"cmd_multi_label_{i}",
                    disabled=is_processing,
                )

            with col2:
                range_item["value"] = st.number_input(
                    f"Range {i+1}",
                    value=float(range_item.get("value", 1000)),
                    min_value=1.0,
                    step=100.0,
                    key=f"cmd_multi_range_{i}",
                    disabled=is_processing,
                )

            with col3:
                unit_options = ["km", "mi", "nm"]
                current_unit = range_item.get("unit", "km")
                unit_index = unit_options.index(current_unit) if current_unit in unit_options else 0
                range_item["unit"] = st.selectbox(
                    f"Unit {i+1}",
                    options=unit_options,
                    index=unit_index,
                    key=f"cmd_multi_unit_{i}",
                    disabled=is_processing,
                )

            with col4:
                st.write("")  # Spacing
                if not is_processing and st.button("❌", key=f"cmd_multi_remove_{i}"):
                    ranges_to_remove.append(i)

        # Remove ranges marked for deletion
        for i in sorted(ranges_to_remove, reverse=True):
            st.session_state.command_multi_ranges.pop(i)
            st.rerun()

        # Add range button
        if not is_processing:
            if st.button("➕ Add Range", key="cmd_multi_add_range"):
                st.session_state.command_multi_ranges.append(
                    {"value": 1000, "unit": "km", "label": ""}
                )
                st.rerun()

        # Confirm / Generate button with JavaScript-based disable protection
        confirm_btn = st.button(
            "🚀 Generate Multiple Rings",
            key="confirm_multiple_generate",
            use_container_width=True,
            disabled=is_processing,
        )

        # Inject JavaScript to prevent double-clicks on the generate button
        components.html("""
        <script>
        (function() {
            function disableButton() {
                const buttons = window.parent.document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText && btn.innerText.includes('Generate Multiple Rings')) {
                        if (!btn.dataset.clickHandlerAttached) {
                            btn.dataset.clickHandlerAttached = 'true';
                            btn.addEventListener('click', function(e) {
                                // Immediately disable after click
                                this.disabled = true;
                                this.style.opacity = '0.5';
                                this.style.pointerEvents = 'none';
                                this.innerText = '⏳ Processing...';
                            });
                        }
                        break;
                    }
                }
            }
            // Try to attach immediately and after a short delay
            disableButton();
            setTimeout(disableButton, 100);
            setTimeout(disableButton, 300);
        })();
        </script>
        """, height=0)

        # Reset Execution Query button
        if get_command_output() is not None and not is_processing:
            st.divider()
            if st.button(
                "🔄 Reset Execution Query",
                key="reset_execution_query_multiple",
                use_container_width=True,
            ):
                _clear_product_viewer()
                st.rerun()

        if confirm_btn and st.session_state.command_multi_ranges and not is_processing:
            st.session_state["command_processing"] = True
            st.session_state["command_pending_query"] = "confirm multiple generate"
            st.rerun()

        return None

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

        # Confirm button with JavaScript-based disable protection
        confirm_btn = st.button(
            "✅ Confirm Selection",
            key="confirm_weapon",
            use_container_width=True,
            disabled=is_processing,
        )

        # Inject JavaScript to prevent double-clicks on the confirm button
        components.html("""
        <script>
        (function() {
            function disableButton() {
                const buttons = window.parent.document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText && btn.innerText.includes('Confirm Selection')) {
                        if (!btn.dataset.reverseClickHandler) {
                            btn.dataset.reverseClickHandler = 'true';
                            btn.addEventListener('click', function(e) {
                                this.disabled = true;
                                this.style.opacity = '0.5';
                                this.style.pointerEvents = 'none';
                                this.innerText = '⏳ Processing...';
                            });
                        }
                        break;
                    }
                }
            }
            disableButton();
            setTimeout(disableButton, 100);
            setTimeout(disableButton, 300);
        })();
        </script>
        """, height=0)

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

        # Confirm button with JavaScript-based disable protection
        confirm_btn = st.button(
            "✅ Confirm Selection",
            key="confirm_single_weapon",
            use_container_width=True,
            disabled=is_processing,
        )

        # Inject JavaScript to prevent double-clicks on the confirm button
        components.html("""
        <script>
        (function() {
            function disableButton() {
                const buttons = window.parent.document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText && btn.innerText.includes('Confirm Selection') && btn.closest('[data-testid]')) {
                        if (!btn.dataset.singleClickHandler) {
                            btn.dataset.singleClickHandler = 'true';
                            btn.addEventListener('click', function(e) {
                                this.disabled = true;
                                this.style.opacity = '0.5';
                                this.style.pointerEvents = 'none';
                                this.innerText = '⏳ Processing...';
                            });
                        }
                        break;
                    }
                }
            }
            disableButton();
            setTimeout(disableButton, 100);
            setTimeout(disableButton, 300);
        })();
        </script>
        """, height=0)

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
        location_type = minimum_pending.get("location_type", "countries")
        location_a = minimum_pending.get("location_a")
        location_b = minimum_pending.get("location_b")

        st.markdown("### 📏 Step 2: Confirm Minimum Range Ring")
        st.info(
            f"**Minimum Range Ring in progress**\n\n"
            f"Location Type: **{location_type.title()}**\n\n"
            f"Location A: **{location_a}**\n\n"
            f"Location B: **{location_b}**"
        )

        # Confirm / Generate button with JavaScript-based disable protection
        confirm_btn = st.button(
            "🚀 Calculate Minimum Distance",
            key="confirm_minimum_generate",
            use_container_width=True,
            disabled=is_processing,
        )

        # Inject JavaScript to prevent double-clicks
        components.html("""
        <script>
        (function() {
            function disableButton() {
                const buttons = window.parent.document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText && btn.innerText.includes('Calculate Minimum Distance')) {
                        if (!btn.dataset.minClickHandler) {
                            btn.dataset.minClickHandler = 'true';
                            btn.addEventListener('click', function(e) {
                                this.disabled = true;
                                this.style.opacity = '0.5';
                                this.style.pointerEvents = 'none';
                                this.innerText = '⏳ Processing...';
                            });
                        }
                        break;
                    }
                }
            }
            disableButton();
            setTimeout(disableButton, 100);
            setTimeout(disableButton, 300);
        })();
        </script>
        """, height=0)

        if get_command_output() is not None and not is_processing:
            st.divider()
            if st.button(
                "🔄 Reset Execution Query",
                key="reset_execution_query_minimum",
                use_container_width=True,
            ):
                _clear_product_viewer()
                st.rerun()

        if confirm_btn and location_a and location_b and not is_processing:
            st.session_state["command_processing"] = True
            st.session_state["command_pending_query"] = "confirm minimum generate"
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


def _render_murr_validator() -> None:
    """Render the Multiple Range Ring real-time validator widget."""
    import json

    data_service = get_data_service()
    countries = data_service.get_country_list()

    html = _render_html_template(
        "murr_validator.html",
        replacements={
            "{{COUNTRIES_JSON}}": json.dumps([c.lower() for c in countries]),
            "{{COUNTRIES_DISPLAY_JSON}}": json.dumps(sorted(countries)),
        },
    )

    components.html(html, height=400)


def _render_reverse_range_ring_validator() -> None:
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

    components.html(html, height=430)


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
            st.markdown("**Multiple Range Ring Task**")
            st.markdown(
                "Use the format: `Generate {multiple range rings} from {Country} at {distance 1, distance 2...} "
                "{km|mi|nm}. The respective missile names are {name 1, name 2...}.`"
            )
            st.markdown("**Example:**")
            st.code(
                "Generate multiple range rings from Korea, North at 500, 1000, 1500 km. "
                "The respective missile names are Missile 1, Missile 2 and Missile 3."
            )
            _render_murr_validator()
        
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
    # Handle Multiple Range Ring confirmation (Step 2)
    # =========================================================================
    multiple_pending = get_command_multiple_pending()
    if multiple_pending and query == "confirm multiple generate":
        # Get ranges from session state (editable by user in Step 2 UI)
        ranges_data = st.session_state.get("command_multi_ranges", [])
        if not ranges_data:
            st.session_state["command_processing"] = False
            return (
                "**Configuration Error**\n\nNo range rings configured. Please add at least one range.",
                "Multiple Range Ring",
                "Pending",
            )

        country_name = multiple_pending.get("country_name")
        country_code = multiple_pending.get("country_code")

        # Build ranges tuples from session state
        ranges = []
        for r in ranges_data:
            unit_map = {
                "km": DistanceUnit.KILOMETERS,
                "mi": DistanceUnit.MILES,
                "nm": DistanceUnit.NAUTICAL_MILES,
            }
            unit = unit_map.get(r.get("unit", "km"), DistanceUnit.KILOMETERS)
            label = r.get("label") if r.get("label") else None
            ranges.append((r.get("value", 1000), unit, label))

        try:
            data_service = get_data_service()
            country_geometry = data_service.get_country_geometry(country_code)
            if country_geometry is None:
                raise CommandParsingError(f"Could not load geometry for {country_name}.")

            # Single source for this run: first weapon with a source in the country's inventory
            weapon_source = None
            try:
                weapons = data_service.get_weapon_systems(country_code)
                first_with_source = next((w for w in weapons if w.get("source")), None)
                if first_with_source:
                    weapon_source = first_with_source.get("source")
            except Exception:
                weapon_source = None

            input_data = MultipleRangeRingInput(
                origin_type=OriginType.COUNTRY,
                country_code=country_code,
                ranges=ranges,
                weapon_source=weapon_source,
                resolution="normal",
            )

            progress_bar = st.progress(0, text="0% - Initializing...")

            def update_progress(pct: float, status: str):
                progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")

            output = generate_multiple_range_rings(
                input_data,
                origin_geometry=country_geometry,
                origin_name=country_name,
                progress_callback=update_progress,
            )
            original_query = multiple_pending.get("original_query", "")
            output.description = f"User Query: {original_query}" if original_query else f"Multiple Range Ring: {country_name}"
            progress_bar.progress(1.0, text="100% - Complete!")

            # Update pending history entry
            _update_multiple_pending_history_entry(
                country_name,
                len(ranges),
                "Completed",
                output=output,
            )

            # Clear pending state and session state
            set_command_multiple_pending(None)
            if "command_multi_ranges" in st.session_state:
                del st.session_state["command_multi_ranges"]
            st.session_state["command_processing"] = False
            return output, "Multiple Range Ring", "Completed (Updated)"
        except CommandParsingError as exc:
            st.session_state["command_processing"] = False
            return f"**Command Center Error**\n\n{exc}", "Multiple Range Ring", "Failed"

    # =========================================================================
    # Handle Minimum Range Ring confirmation (Step 2)
    # =========================================================================
    minimum_pending = get_command_minimum_pending()
    if minimum_pending and query == "confirm minimum generate":
        location_type = minimum_pending.get("location_type")
        location_a = minimum_pending.get("location_a")
        location_b = minimum_pending.get("location_b")

        if not location_a or not location_b:
            st.session_state["command_processing"] = False
            return (
                "**Configuration Error**\n\nMissing location data. Please try again.",
                "Minimum Range Ring",
                "Failed",
            )

        progress_bar = st.progress(0, text="0% - Initializing...")

        def update_progress(pct: float, status: str):
            progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")

        try:
            output, distance_km = _generate_minimum_range_output(
                location_type,
                location_a,
                location_b,
                progress_callback=update_progress,
            )
            original_query = minimum_pending.get("original_query", "")
            output.description = f"User Query: {original_query}" if original_query else f"Minimum Range Ring: {location_a} ↔ {location_b}"
            progress_bar.progress(1.0, text="100% - Complete!")

            _update_minimum_pending_history_entry(
                location_type,
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

    # =========================================================================
    # Handle Minimum Range Ring location selection (legacy Step 2)
    # =========================================================================
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
                output.description = f"User Query: {query}"
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
                original_query = single_pending.get("original_query", "")
                output.description = f"User Query: {original_query}" if original_query else f"Single Range Ring: {single_pending['country_name']}"
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
                    "original_query": query,
                }
            )

            message = _build_single_weapon_selection_message(matched_country, weapons)
            return message, "Single Range Ring", "Pending"
        except CommandParsingError as exc:
            return f"**Command Center Error**\n\n{exc}", "Single Range Ring", "Failed"
    
    # =========================================================================
    # Handle Minimum Range Ring initial request (Step 1 - set pending state)
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

            # Determine location type from matches
            if (country_match_a and country_match_b) and not (city_match_a and city_match_b):
                location_type = "countries"
                matched_a = country_match_a
                matched_b = country_match_b
            elif (city_match_a and city_match_b) and not (country_match_a and country_match_b):
                location_type = "cities"
                matched_a = city_match_a
                matched_b = city_match_b
            else:
                # Ambiguous - default to countries if both match countries
                if country_match_a and country_match_b:
                    location_type = "countries"
                    matched_a = country_match_a
                    matched_b = country_match_b
                elif city_match_a and city_match_b:
                    location_type = "cities"
                    matched_a = city_match_a
                    matched_b = city_match_b
                else:
                    # Couldn't match both locations
                    return (
                        f"**Location Error**\n\nCould not match both '{location_a}' and '{location_b}' "
                        "as valid countries or cities.",
                        "Minimum Range Ring",
                        "Failed",
                    )

            # Set pending state with the matched locations for Step 2 confirmation
            set_command_minimum_pending(
                {
                    "location_type": location_type,
                    "location_a": matched_a,
                    "location_b": matched_b,
                    "original_query": query,
                }
            )

            return (
                f"**Minimum Range Ring Setup**\n\n"
                f"Location Type: **{location_type.title()}**\n\n"
                f"Location A: **{matched_a}**\n\n"
                f"Location B: **{matched_b}**\n\n"
                f"Review and confirm in the input panel.",
                "Minimum Range Ring",
                "Pending",
            )
        except CommandParsingError as exc:
            return f"**Command Center Error**\n\n{exc}", "Minimum Range Ring", "Failed"

    # =========================================================================
    # Handle Multiple Range Ring initial request (Step 1 - set pending state)
    # =========================================================================
    multiple_request = _extract_multiple_range_request(query)
    if multiple_request:
        country = multiple_request["country"]
        distances = multiple_request["distances"]
        unit_raw = multiple_request["unit"]
        missile_names = multiple_request["missile_names"]

        unit_map = {
            "km": DistanceUnit.KILOMETERS,
            "mi": DistanceUnit.MILES,
            "nm": DistanceUnit.NAUTICAL_MILES,
        }
        unit = unit_map.get(unit_raw, DistanceUnit.KILOMETERS)

        # Build ranges tuples for pending state
        ranges = []
        for idx, distance in enumerate(distances):
            label = missile_names[idx] if idx < len(missile_names) else None
            ranges.append((distance, unit, label))

        try:
            data_service = get_data_service()
            matched_country = _fuzzy_match(country, data_service.get_country_list(), cutoff=0.6)
            if not matched_country:
                raise CommandParsingError(f"Could not match country '{country}' in request.")

            country_code = data_service.get_country_code(matched_country)
            if not country_code:
                raise CommandParsingError(f"Could not resolve ISO code for '{matched_country}'.")

            # Set pending state for Step 2 UI
            set_command_multiple_pending(
                {
                    "country_name": matched_country,
                    "country_code": country_code,
                    "ranges": ranges,
                    "original_query": query,
                }
            )

            # Clear any existing command_multi_ranges to force re-initialization
            if "command_multi_ranges" in st.session_state:
                del st.session_state["command_multi_ranges"]

            return (
                f"**Multiple Range Ring Setup**\n\n"
                f"Country: **{matched_country}**\n\n"
                f"Parsed {len(ranges)} range ring(s). Review and confirm in the input panel.",
                "Multiple Range Ring",
                "Pending",
            )
        except CommandParsingError as exc:
            return f"**Command Center Error**\n\n{exc}", "Multiple Range Ring", "Failed"

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
                original_query = pending.get("original_query", "")
                output.description = f"User Query: {original_query}" if original_query else f"Reverse Range Ring: {pending['country_name']} → {pending['city_name']}"
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
                    "original_query": query,
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

    query = _render_input_panel()
    if query:
        output, resolution, status = _mock_intent_response(query)

        # Only update command output for completed or failed tasks, not pending
        if status != "Pending":
            set_command_output(output)

        # Only add a new history entry if we're not updating an existing one
        # "Completed (Updated)" means we already updated the pending entry
        if status != "Completed (Updated)":
            is_task = resolution in (
                "Reverse Range Ring",
                "Single Range Ring",
                "Minimum Range Ring",
                "Multiple Range Ring",
            )
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
            or get_command_multiple_pending() is not None
        ):
            st.rerun()

    _render_help_section()
    _render_product_output_viewer()
    _render_history()
