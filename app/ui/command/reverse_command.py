"""Reverse Range Ring command flow extracted from command_center."""

from __future__ import annotations

from typing import Optional, Union
import re

import streamlit as st

from app.models.inputs import PointOfInterest, ReverseRangeRingInput, DistanceUnit
from app.models.outputs import RangeRingOutput
from app.data.loaders import get_data_service
from app.geometry.services import generate_reverse_range_ring
from app.geometry.utils import geodesic_distance
from app.ui.layout.global_state import (
    get_command_reverse_pending,
    set_command_reverse_pending,
    update_command_history_entry,
)
from app.ui.command.shared_command_utils import normalize_text, fuzzy_match


CommandOutput = Union[RangeRingOutput, str, None]


class CommandParsingError(Exception):
    """Raised when command parsing fails."""


def extract_reverse_range_request(text: str) -> Optional[tuple[str, str]]:
    """Extract shooter country and target city from a reverse range ring command."""
    normalized = normalize_text(text)
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


def extract_reverse_weapon_selection(text: str) -> Optional[int]:
    normalized = normalize_text(text)
    match = re.search(r"select reverse weapon\s*(?P<index>\d+)", normalized)
    if match:
        return int(match.group("index"))
    return None


def build_weapon_selection_message(country_name: str, weapons: list[dict]) -> str:
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


def generate_reverse_range_output_with_weapon(
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


def update_pending_history_entry(
    country_name: str,
    city_name: str,
    weapon_name: str,
    weapon_range: float,
    final_status: str,
    output: Optional[RangeRingOutput] = None,
) -> None:
    updates = {
        "status": final_status,
        "text": f"Reverse range ring: {country_name} → {city_name} using {weapon_name} ({weapon_range:,.0f} km)",
        "weapon_name": weapon_name,
        "weapon_range_km": weapon_range,
        "shooter_country": country_name,
        "target_city": city_name,
    }

    if output is not None:
        updates["output"] = output

    update_command_history_entry(
        match_criteria={
            "resolution": "Reverse Range Ring",
            "status": "Pending",
        },
        updates=updates,
    )


def render_pending_panel() -> Optional[str]:
    pending = get_command_reverse_pending()
    if not pending:
        return None

    is_processing = st.session_state.get("command_processing", False)

    st.markdown("### 🔄 Step 2: Select Weapon System")
    st.info(
        f"**Reverse Range Ring in progress**\n\n"
        f"Shooter: **{pending.get('country_name')}** → Target: **{pending.get('city_name')}**"
    )

    weapons = pending.get("weapons", [])
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

    confirm_btn = st.button(
        "✅ Confirm Selection",
        key="confirm_weapon",
        use_container_width=True,
        disabled=is_processing,
    )

    st.components.v1.html(
        """
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
        """,
        height=0,
    )

    if st.session_state.get("command_output") is not None and not is_processing:
        st.divider()
        if st.button("🔄 Reset Execution Query", key="reset_execution_query_step2", use_container_width=True):
            from app.ui.command.shared_command_utils import clear_product_viewer

            clear_product_viewer()
            st.rerun()

    if confirm_btn and selected_label and not is_processing:
        st.session_state["command_processing"] = True
        sel_idx = weapon_labels.index(selected_label) + 1
        st.session_state["command_pending_query"] = f"Select reverse weapon {sel_idx}"
        st.rerun()

    return None


def handle_pending(query: str):
    pending = get_command_reverse_pending()
    selection = extract_reverse_weapon_selection(query)
    if not (pending and selection):
        return None

    weapons = pending.get("weapons", [])
    selected_index = selection - 1
    if not (0 <= selected_index < len(weapons)):
        st.session_state["command_processing"] = False
        return (
            "**Selection Error**\n\nPlease reply with a valid weapon number from the list.",
            "Reverse Range Ring",
            "Pending",
        )

    weapon = weapons[selected_index]
    weapon_name = weapon.get("name", "Unknown")
    weapon_range = weapon.get("range_km", 0)

    progress_bar = st.progress(0, text="0% - Initializing...")

    def update_progress(pct: float, status: str):
        progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")

    try:
        output = generate_reverse_range_output_with_weapon(
            pending["country_name"],
            pending["city_name"],
            pending["country_code"],
            pending["target_coords"],
            weapon,
            progress_callback=update_progress,
        )
        original_query = pending.get("original_query", "")
        output.description = (
            f"User Query: {original_query}"
            if original_query
            else f"Reverse Range Ring: {pending['country_name']} → {pending['city_name']}"
        )
        progress_bar.progress(1.0, text="100% - Complete!")

        update_pending_history_entry(
            pending["country_name"],
            pending["city_name"],
            weapon_name,
            weapon_range,
            "Completed",
            output=output,
        )

        set_command_reverse_pending(None)
        st.session_state["command_processing"] = False
        return output, "Reverse Range Ring", "Completed (Updated)"
    except CommandParsingError as exc:
        progress_bar.progress(1.0, text="Error!")
        st.session_state["command_processing"] = False
        return f"**Command Center Error**\n\n{exc}", "Reverse Range Ring", "Failed"


def parse_initial(query: str):
    reverse_request = extract_reverse_range_request(query)
    if not reverse_request:
        return None

    country, city = reverse_request
    try:
        data_service = get_data_service()
        matched_country = fuzzy_match(country, data_service.get_country_list(), cutoff=0.6)
        matched_city = fuzzy_match(city, data_service.get_city_list(), cutoff=0.6)
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

        message = build_weapon_selection_message(matched_country, weapons)
        return message, "Reverse Range Ring", "Pending"
    except CommandParsingError as exc:
        return f"**Command Center Error**\n\n{exc}", "Reverse Range Ring", "Failed"


def help_tab(tab):
    with tab:
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
        _render_reverse_range_ring_validator()


def _render_reverse_range_ring_validator() -> None:
    import json
    from app.ui.command.shared_command_utils import render_html_template

    data_service = get_data_service()
    countries = data_service.get_country_list()
    cities = data_service.get_city_list()

    html = render_html_template(
        "rrr_validator.html",
        replacements={
            "{{COUNTRIES_JSON}}": json.dumps([c.lower() for c in countries]),
            "{{CITIES_JSON}}": json.dumps([c.lower() for c in cities]),
            "{{COUNTRIES_DISPLAY_JSON}}": json.dumps(sorted(countries)),
            "{{CITIES_DISPLAY_JSON}}": json.dumps(sorted(cities)),
        },
    )

    st.components.v1.html(html, height=430)
