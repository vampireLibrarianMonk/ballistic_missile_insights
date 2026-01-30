"""Multiple Range Rings command flow extracted from command_center."""

from __future__ import annotations

from typing import Optional, Union
import re

import streamlit as st

from app.models.inputs import MultipleRangeRingInput, DistanceUnit, OriginType
from app.models.outputs import RangeRingOutput
from app.data.loaders import get_data_service
from app.geometry.services import generate_multiple_range_rings
from app.ui.layout.global_state import (
    get_command_multiple_pending,
    set_command_multiple_pending,
    update_command_history_entry,
)
from app.ui.command.shared_command_utils import normalize_text, fuzzy_match, clear_product_viewer


CommandOutput = Union[RangeRingOutput, str, None]


class CommandParsingError(Exception):
    """Raised when command parsing fails."""


def extract_multiple_range_request(text: str) -> Optional[dict]:
    normalized = normalize_text(text)
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


def _update_multiple_pending_history_entry(
    country_name: str,
    ring_count: int,
    final_status: str,
    output: Optional[RangeRingOutput] = None,
) -> None:
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
        updates=updates,
    )


def render_pending_panel() -> Optional[str]:
    multiple_pending = get_command_multiple_pending()
    if not multiple_pending:
        return None

    is_processing = st.session_state.get("command_processing", False)
    multiple_pending_query = st.session_state.pop("command_multiple_pending_query", None)
    if multiple_pending_query:
        return multiple_pending_query

    st.markdown("### 📊 Step 2: Confirm Multiple Range Rings")
    st.info(
        f"**Multiple Range Ring in progress**\n\n"
        f"Origin Country: **{multiple_pending.get('country_name')}**"
    )

    if "command_multi_ranges" not in st.session_state:
        parsed_ranges = multiple_pending.get("ranges", [])
        st.session_state.command_multi_ranges = [
            {
                "value": r[0],
                "unit": r[1].value if hasattr(r[1], "value") else r[1],
                "label": r[2] if len(r) > 2 and r[2] else "",
            }
            for r in parsed_ranges
        ]

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
            st.write("")
            if not is_processing and st.button("❌", key=f"cmd_multi_remove_{i}"):
                ranges_to_remove.append(i)

    for i in sorted(ranges_to_remove, reverse=True):
        st.session_state.command_multi_ranges.pop(i)
        st.rerun()

    if not is_processing:
        if st.button("➕ Add Range", key="cmd_multi_add_range"):
            st.session_state.command_multi_ranges.append({"value": 1000, "unit": "km", "label": ""})
            st.rerun()

    confirm_btn = st.button(
        "🚀 Generate Multiple Rings",
        key="confirm_multiple_generate",
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
                    if (btn.innerText && btn.innerText.includes('Generate Multiple Rings')) {
                        if (!btn.dataset.clickHandlerAttached) {
                            btn.dataset.clickHandlerAttached = 'true';
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
        if st.button(
            "🔄 Reset Execution Query",
            key="reset_execution_query_multiple",
            use_container_width=True,
        ):
            clear_product_viewer()
            st.rerun()

    if confirm_btn and st.session_state.command_multi_ranges and not is_processing:
        st.session_state["command_processing"] = True
        st.session_state["command_pending_query"] = "confirm multiple generate"
        st.rerun()

    return None


def handle_pending(query: str):
    multiple_pending = get_command_multiple_pending()
    if multiple_pending and query == "confirm multiple generate":
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
            output.description = (
                f"User Query: {original_query}"
                if original_query
                else f"Multiple Range Ring: {country_name}"
            )
            progress_bar.progress(1.0, text="100% - Complete!")

            _update_multiple_pending_history_entry(
                country_name,
                len(ranges),
                "Completed",
                output=output,
            )

            set_command_multiple_pending(None)
            if "command_multi_ranges" in st.session_state:
                del st.session_state["command_multi_ranges"]
            st.session_state["command_processing"] = False
            return output, "Multiple Range Ring", "Completed (Updated)"
        except CommandParsingError as exc:
            st.session_state["command_processing"] = False
            return f"**Command Center Error**\n\n{exc}", "Multiple Range Ring", "Failed"

    return None


def parse_initial(query: str):
    multiple_request = extract_multiple_range_request(query)
    if not multiple_request:
        return None

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

    ranges = []
    for idx, distance in enumerate(distances):
        label = missile_names[idx] if idx < len(missile_names) else None
        ranges.append((distance, unit, label))

    try:
        data_service = get_data_service()
        matched_country = fuzzy_match(country, data_service.get_country_list(), cutoff=0.6)
        if not matched_country:
            raise CommandParsingError(f"Could not match country '{country}' in request.")

        country_code = data_service.get_country_code(matched_country)
        if not country_code:
            raise CommandParsingError(f"Could not resolve ISO code for '{matched_country}'.")

        set_command_multiple_pending(
            {
                "country_name": matched_country,
                "country_code": country_code,
                "ranges": ranges,
                "original_query": query,
            }
        )

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


def help_tab(tab):
    with tab:
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


def _render_murr_validator() -> None:
    import json
    from app.ui.command.shared_command_utils import render_html_template

    data_service = get_data_service()
    countries = data_service.get_country_list()

    html = render_html_template(
        "murr_validator.html",
        replacements={
            "{{COUNTRIES_JSON}}": json.dumps([c.lower() for c in countries]),
            "{{COUNTRIES_DISPLAY_JSON}}": json.dumps(sorted(countries)),
        },
    )

    st.components.v1.html(html, height=400)
