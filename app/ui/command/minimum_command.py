"""Minimum Range Ring command flow extracted from command_center."""

from __future__ import annotations

from typing import Optional, Union
import re

import streamlit as st
from shapely.geometry import Point

from app.models.inputs import MinimumRangeRingInput
from app.models.outputs import RangeRingOutput
from app.data.loaders import get_data_service
from app.geometry.services import calculate_minimum_distance
from app.ui.layout.global_state import (
    get_command_minimum_pending,
    set_command_minimum_pending,
    update_command_history_entry,
)
from app.ui.command.shared_command_utils import normalize_text, fuzzy_match


CommandOutput = Union[RangeRingOutput, str, None]


class CommandParsingError(Exception):
    """Raised when command parsing fails."""


def extract_minimum_range_request(text: str) -> Optional[tuple[str, str]]:
    normalized = normalize_text(text)
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


def extract_minimum_location_type(text: str) -> Optional[str]:
    normalized = normalize_text(text)
    match = re.search(r"select minimum type\s*(countries|cities)", normalized)
    if match:
        return match.group(1).lower()
    return None


def extract_minimum_location_selection(text: str) -> Optional[tuple[int, int]]:
    normalized = normalize_text(text)
    match = re.search(
        r"select minimum locations\s*(?P<first>\d+)\s*(?:and|,)\s*(?P<second>\d+)",
        normalized,
    )
    if match:
        return int(match.group("first")), int(match.group("second"))
    return None


def build_minimum_location_type_message() -> str:
    return "\n".join(
        [
            "**Minimum Range Ring setup**",
            "Select the location type to analyze by replying with:",
            "- `Select minimum type countries`",
            "- `Select minimum type cities`",
        ]
    )


def build_minimum_location_selection_message(location_type: str, locations: list[str]) -> str:
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


def generate_minimum_range_output(
    location_type: str,
    location_a: str,
    location_b: str,
    progress_callback: Optional[callable] = None,
) -> tuple[RangeRingOutput, float]:
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


def render_pending_panel() -> Optional[str]:
    minimum_pending = get_command_minimum_pending()
    if not minimum_pending:
        return None

    location_type = minimum_pending.get("location_type", "countries")
    location_a = minimum_pending.get("location_a")
    location_b = minimum_pending.get("location_b")
    is_processing = st.session_state.get("command_processing", False)

    st.markdown("### 📏 Step 2: Confirm Minimum Range Ring")
    st.info(
        f"**Minimum Range Ring in progress**\n\n"
        f"Location Type: **{location_type.title()}**\n\n"
        f"Location A: **{location_a}**\n\n"
        f"Location B: **{location_b}**"
    )

    confirm_btn = st.button(
        "🚀 Calculate Minimum Distance",
        key="confirm_minimum_generate",
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
        """,
        height=0,
    )

    if st.session_state.get("command_output") is not None and not is_processing:
        st.divider()
        if st.button(
            "🔄 Reset Execution Query",
            key="reset_execution_query_minimum",
            use_container_width=True,
        ):
            from app.ui.command.shared_command_utils import clear_product_viewer

            clear_product_viewer()
            st.rerun()

    if confirm_btn and location_a and location_b and not is_processing:
        st.session_state["command_processing"] = True
        st.session_state["command_pending_query"] = "confirm minimum generate"
        st.rerun()

    return None


def handle_pending(query: str):
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
            output, distance_km = generate_minimum_range_output(
                location_type,
                location_a,
                location_b,
                progress_callback=update_progress,
            )
            original_query = minimum_pending.get("original_query", "")
            output.description = (
                f"User Query: {original_query}"
                if original_query
                else f"Minimum Range Ring: {location_a} ↔ {location_b}"
            )
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

    # Legacy location selection path
    minimum_selection = extract_minimum_location_selection(query)
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
                output, distance_km = generate_minimum_range_output(
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

    minimum_type_selection = extract_minimum_location_type(query)
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
        message = build_minimum_location_selection_message(location_type, selection_labels)
        return message, "Minimum Range Ring", "Pending"

    return None


def parse_initial(query: str):
    minimum_request = extract_minimum_range_request(query)
    if not minimum_request:
        return None

    location_a, location_b = minimum_request
    try:
        data_service = get_data_service()
        country_match_a = fuzzy_match(location_a, data_service.get_country_list(), cutoff=0.6)
        country_match_b = fuzzy_match(location_b, data_service.get_country_list(), cutoff=0.6)
        city_match_a = fuzzy_match(location_a, data_service.get_city_list(), cutoff=0.6)
        city_match_b = fuzzy_match(location_b, data_service.get_city_list(), cutoff=0.6)

        if (country_match_a and country_match_b) and not (city_match_a and city_match_b):
            location_type = "countries"
            matched_a = country_match_a
            matched_b = country_match_b
        elif (city_match_a and city_match_b) and not (country_match_a and country_match_b):
            location_type = "cities"
            matched_a = city_match_a
            matched_b = city_match_b
        else:
            if country_match_a and country_match_b:
                location_type = "countries"
                matched_a = country_match_a
                matched_b = country_match_b
            elif city_match_a and city_match_b:
                location_type = "cities"
                matched_a = city_match_a
                matched_b = city_match_b
            else:
                return (
                    f"**Location Error**\n\nCould not match both '{location_a}' and '{location_b}' "
                    "as valid countries or cities.",
                    "Minimum Range Ring",
                    "Failed",
                )

        set_command_minimum_pending(
            {
                "location_type": location_type,
                "location_a": matched_a,
                "location_b": matched_b,
                "original_query": query,
            }
        )

        # Auto-proceed without a manual confirmation step. Enqueue the synthetic
        # "confirm" query so the pending handler runs on the next rerun.
        st.session_state["command_pending_query"] = "confirm minimum generate"

        return (
            f"**Minimum Range Ring Setup**\n\n"
            f"Location Type: **{location_type.title()}**\n\n"
            f"Location A: **{matched_a}**\n\n"
            f"Location B: **{matched_b}**\n\n"
            f"Calculating automatically...",
            "Minimum Range Ring",
            "Pending",
        )
    except CommandParsingError as exc:
        return f"**Command Center Error**\n\n{exc}", "Minimum Range Ring", "Failed"


def help_tab(tab):
    with tab:
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
        _render_minimum_range_ring_validator()


def _render_minimum_range_ring_validator() -> None:
    import json
    from app.ui.command.shared_command_utils import render_html_template

    data_service = get_data_service()
    countries = data_service.get_country_list()
    cities = data_service.get_city_list()

    html = render_html_template(
        "mrr_validator.html",
        replacements={
            "{{COUNTRIES_JSON}}": json.dumps([c.lower() for c in countries]),
            "{{CITIES_JSON}}": json.dumps([c.lower() for c in cities]),
            "{{COUNTRIES_DISPLAY_JSON}}": json.dumps(sorted(countries)),
            "{{CITIES_DISPLAY_JSON}}": json.dumps(sorted(cities)),
        },
    )

    st.components.v1.html(html, height=420)
