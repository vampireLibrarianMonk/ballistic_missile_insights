"""Single Range Ring command flow extracted from command_center."""

from __future__ import annotations

from typing import Optional, Union
import re

import streamlit as st

from app.models.inputs import SingleRangeRingInput, DistanceUnit, OriginType
from app.models.outputs import RangeRingOutput
from app.data.loaders import get_data_service
from app.geometry.services import generate_single_range_ring
from app.ui.layout.global_state import (
    get_command_single_pending,
    set_command_single_pending,
    update_command_history_entry,
)
from app.ui.command.shared_command_utils import normalize_text, fuzzy_match


CommandOutput = Union[RangeRingOutput, str, None]


class CommandParsingError(Exception):
    """Raised when command parsing fails."""


def extract_single_range_request(text: str) -> Optional[str]:
    """Extract country from a single range ring command (non-reverse)."""
    normalized = normalize_text(text)

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


def build_single_weapon_selection_message(country_name: str, weapons: list[dict]) -> str:
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


def extract_single_weapon_selection(text: str) -> Optional[int]:
    normalized = normalize_text(text)
    match = re.search(r"select single weapon\s*(?P<index>\d+)", normalized)
    if match:
        return int(match.group("index"))
    return None


def generate_single_range_output_with_weapon(
    country_name: str,
    country_code: str,
    weapon: dict,
    progress_callback: Optional[callable] = None,
) -> RangeRingOutput:
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


def update_single_pending_history_entry(
    country_name: str,
    weapon_name: str,
    weapon_range: float,
    final_status: str,
    output: Optional[RangeRingOutput] = None,
) -> None:
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
        updates=updates,
    )


def render_pending_panel() -> Optional[str]:
    single_pending = get_command_single_pending()
    if not single_pending:
        return None

    # Flag that we have a pending state - return empty string at end to hide Step 1 input

    is_processing = st.session_state.get("command_processing", False)

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

    confirm_btn = st.button(
        "✅ Confirm Selection",
        key="confirm_single_weapon",
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
        """,
        height=0,
    )

    if st.session_state.get("command_output") is not None and not is_processing:
        st.divider()
        if st.button("🔄 Reset Execution Query", key="reset_execution_query_single", use_container_width=True):
            from app.ui.command.shared_command_utils import clear_product_viewer

            clear_product_viewer()
            st.rerun()

    if confirm_btn and selected_label and not is_processing:
        st.session_state["command_processing"] = True
        sel_idx = weapon_labels.index(selected_label) + 1
        st.session_state["command_pending_query"] = f"Select single weapon {sel_idx}"
        st.rerun()

    # Return empty string to signal that Step 1 input should be hidden
    return ""


def handle_pending(query: str):
    single_pending = get_command_single_pending()
    single_selection = extract_single_weapon_selection(query)
    if not (single_pending and single_selection):
        return None

    weapons = single_pending.get("weapons", [])
    selected_index = single_selection - 1
    if not (0 <= selected_index < len(weapons)):
        st.session_state["command_processing"] = False
        return (
            "**Selection Error**\n\nPlease reply with a valid weapon number from the list.",
            "Single Range Ring",
            "Pending",
        )

    weapon = weapons[selected_index]
    weapon_name = weapon.get("name", "Unknown")
    weapon_range = weapon.get("range_km", 0)

    progress_bar = st.progress(0, text="0% - Initializing...")

    def update_progress(pct: float, status: str):
        progress_bar.progress(min(pct, 1.0), text=f"{int(pct * 100)}% - {status}")

    try:
        output = generate_single_range_output_with_weapon(
            single_pending["country_name"],
            single_pending["country_code"],
            weapon,
            progress_callback=update_progress,
        )
        original_query = single_pending.get("original_query", "")
        output.description = (
            f"User Query: {original_query}"
            if original_query
            else f"Single Range Ring: {single_pending['country_name']}"
        )
        progress_bar.progress(1.0, text="100% - Complete!")

        update_single_pending_history_entry(
            single_pending["country_name"],
            weapon_name,
            weapon_range,
            "Completed",
            output=output,
        )

        set_command_single_pending(None)
        st.session_state["command_processing"] = False
        return output, "Single Range Ring", "Completed (Updated)"
    except CommandParsingError as exc:
        progress_bar.progress(1.0, text="Error!")
        st.session_state["command_processing"] = False
        return f"**Command Center Error**\n\n{exc}", "Single Range Ring", "Failed"


def parse_initial(query: str):
    single_request = extract_single_range_request(query)
    if not single_request:
        return None

    country = single_request
    try:
        data_service = get_data_service()
        matched_country = fuzzy_match(country, data_service.get_country_list(), cutoff=0.6)
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

        message = build_single_weapon_selection_message(matched_country, weapons)
        return message, "Single Range Ring", "Pending"
    except CommandParsingError as exc:
        return f"**Command Center Error**\n\n{exc}", "Single Range Ring", "Failed"


def help_tab(tab):
    with tab:
        st.markdown("**Single Range Ring Task**")
        st.markdown(
            "Use the format: `Generate a {single range ring|single ring|range ring} {from|for} {Country}.`"
        )
        st.markdown(
            "Then respond with `Select single weapon #` using the number from the returned list to generate "
            "the single range ring output and export options."
        )
        st.markdown("**Example:**")
        st.code("Generate a single range ring from Iran")
        _render_single_range_ring_validator()


def _render_single_range_ring_validator() -> None:
    import json
    from app.ui.command.shared_command_utils import render_html_template

    data_service = get_data_service()
    countries = data_service.get_country_list()

    html = render_html_template(
        "srr_validator.html",
        replacements={
            "{{COUNTRIES_JSON}}": json.dumps([c.lower() for c in countries]),
            "{{COUNTRIES_DISPLAY_JSON}}": json.dumps(sorted(countries)),
        },
    )

    st.components.v1.html(html, height=320)
