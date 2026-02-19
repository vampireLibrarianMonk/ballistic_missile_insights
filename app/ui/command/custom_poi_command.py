"""Custom POI command flow with progressive validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union
import re

import streamlit as st

from app.models.inputs import DistanceUnit, PointOfInterest, CustomPOIRangeRingInput
from app.models.outputs import RangeRingOutput
from app.ui.layout.global_state import (
    get_command_custom_poi_pending,
    set_command_custom_poi_pending,
)
from app.ui.layout.global_state import update_command_history_entry
from app.ui.command.shared_command_utils import normalize_text
from app.geometry.services import generate_custom_poi_range_ring_multi


CommandOutput = Union[RangeRingOutput, str, None]


# -----------------------------
# Data structures
# -----------------------------


@dataclass
class POIEntry:
    name: str
    lat: float
    lon: float
    min_range: float
    max_range: float
    unit: str  # "km" | "mi"


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]
    cleaned: list[POIEntry]


# -----------------------------
# Parsing helpers
# -----------------------------


_UNIT_PATTERN = r"km|mi"


def _extract_pois(text: str) -> list[POIEntry]:
    """Lightweight regex-based extraction of POIs from free text.

    Heuristics:
    - Accepts groups like: "Name? lat lon min?-max? unit?" or "Name lat lon range unit".
    - Separators: semicolon, newline, or brackets to split multiple POIs.
    - Defaults: name -> "POI #n"; min_range -> 0 when only one value provided; unit -> km.
    """
    normalized = normalize_text(text)

    # Split potential groups by semicolons or bracketed blocks
    candidates = re.split(r";|\n|\]\s*\[|\[|\]", normalized)
    groups = [c.strip() for c in candidates if c.strip()]

    # Fallback: if no separators produced multiple, treat whole text as one group
    if not groups:
        groups = [normalized]

    pois: list[POIEntry] = []
    for idx, group in enumerate(groups, start=1):
        # Pattern to find: name? lat lon (min-max|max) unit?
        # Name can be words before the first number
        match = re.search(
            rf"(?P<name>[a-zA-Z\s']+)?\s*"
            rf"(?P<lat>-?\d+(?:\.\d+)?)\s+"
            rf"(?P<lon>-?\d+(?:\.\d+)?)\s+"
            rf"(?P<range>(?:\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?))\s*"
            rf"(?P<unit>{_UNIT_PATTERN})?",
            group,
        )
        if not match:
            # Try simpler "lat lon range unit" without name
            match = re.search(
                rf"(?P<lat>-?\d+(?:\.\d+)?)\s+"
                rf"(?P<lon>-?\d+(?:\.\d+)?)\s+"
                rf"(?P<range>(?:\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?))\s*"
                rf"(?P<unit>{_UNIT_PATTERN})?",
                group,
            )
            name = None
        else:
            name = match.group("name")

        if not match:
            continue

        lat = float(match.group("lat"))
        lon = float(match.group("lon"))
        range_raw = match.group("range")
        unit = match.group("unit") or "km"

        if "-" in range_raw:
            parts = re.split(r"-", range_raw)
            min_r = float(parts[0])
            max_r = float(parts[1])
        else:
            min_r = 0.0
            max_r = float(range_raw)

        poi_name = name.strip() if name else f"POI {idx}"

        pois.append(
            POIEntry(
                name=poi_name,
                lat=lat,
                lon=lon,
                min_range=min_r,
                max_range=max_r,
                unit=unit,
            )
        )

    return pois


def _validate_pois(pois: list[POIEntry]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    cleaned: list[POIEntry] = []

    for idx, p in enumerate(pois, start=1):
        errs = []
        warns = []

        if not (-90 <= p.lat <= 90):
            errs.append(f"POI {idx} ({p.name}): latitude must be between -90 and 90")
        if not (-180 <= p.lon <= 180):
            errs.append(f"POI {idx} ({p.name}): longitude must be between -180 and 180")

        if p.max_range <= 0:
            errs.append(f"POI {idx} ({p.name}): max range must be > 0")
        if p.min_range < 0:
            errs.append(f"POI {idx} ({p.name}): min range cannot be negative")
        if p.min_range > 0 and p.max_range <= p.min_range:
            errs.append(f"POI {idx} ({p.name}): max range must exceed min range when min > 0")

        if p.unit not in ("km", "mi"):
            errs.append(f"POI {idx} ({p.name}): unit must be km or mi")

        # Hard cap to flag suspicious values (allow override via warning only)
        if p.max_range > 20000:
            warns.append(f"POI {idx} ({p.name}): max range is very large ({p.max_range:,.0f}); ensure this is intentional")

        # Deduplicate names softly
        cleaned.append(p)
        errors.extend(errs)
        warnings.extend(warns)

    return ValidationResult(errors=errors, warnings=warnings, cleaned=cleaned)


# -----------------------------
# Pending UI helpers
# -----------------------------


def _render_poi_table(pois: list[POIEntry], validation: ValidationResult, is_processing: bool) -> None:
    if not pois:
        st.warning("No POIs detected. Provide at least one lat/lon and range.")
        return

    warn_block = validation.warnings
    error_block = validation.errors

    if warn_block:
        st.warning("\n".join(warn_block))
    if error_block:
        st.error("\n".join(error_block))

    st.markdown("**Detected POIs (edit inline):**")
    cols_header = st.columns([2, 1.2, 1.2, 1.2, 1.2, 0.8])
    headers = ["Name", "Lat", "Lon", "Min", "Max", "Unit"]
    for col, h in zip(cols_header, headers):
        col.markdown(f"**{h}**")

    for i, p in enumerate(pois):
        c_name, c_lat, c_lon, c_min, c_max, c_unit = st.columns([2, 1.2, 1.2, 1.2, 1.2, 0.8])
        p.name = c_name.text_input("", value=p.name, key=f"cpoi_name_{i}", disabled=is_processing)
        p.lat = c_lat.number_input(
            "",
            value=float(p.lat),
            key=f"cpoi_lat_{i}",
            disabled=is_processing,
            min_value=-90.0,
            max_value=90.0,
            step=0.0001,
            format="%.6f",
        )
        p.lon = c_lon.number_input(
            "",
            value=float(p.lon),
            key=f"cpoi_lon_{i}",
            disabled=is_processing,
            min_value=-180.0,
            max_value=180.0,
            step=0.0001,
            format="%.6f",
        )
        p.min_range = c_min.number_input("", value=float(p.min_range), key=f"cpoi_min_{i}", disabled=is_processing, min_value=0.0)
        p.max_range = c_max.number_input("", value=float(p.max_range), key=f"cpoi_max_{i}", disabled=is_processing, min_value=0.1)
        p.unit = c_unit.selectbox("", options=["km", "mi"], index=0 if p.unit == "km" else 1, key=f"cpoi_unit_{i}", disabled=is_processing)

    # Remove button set
    rm_cols = st.columns(len(pois))
    to_remove = []
    for i, col in enumerate(rm_cols):
        if col.button("🗑️ Remove", key=f"cpoi_rm_{i}", disabled=is_processing):
            to_remove.append(i)
    for idx in sorted(to_remove, reverse=True):
        pois.pop(idx)
        st.rerun()

    if st.button("➕ Add POI", key="cpoi_add", disabled=is_processing):
        pois.append(
            POIEntry(
                name=f"POI {len(pois)+1}",
                lat=0.0,
                lon=0.0,
                min_range=0.0,
                max_range=1000.0,
                unit="km",
            )
        )
        st.rerun()


# -----------------------------
# Pending panel rendering
# -----------------------------


def render_pending_panel() -> Optional[str]:
    pending = get_command_custom_poi_pending()
    if not pending:
        return None

    is_processing = st.session_state.get("command_processing", False)
    pois = pending.get("pois", [])

    st.markdown("### 📍 Step 2: Review Custom POIs")
    st.info("Custom POI range ring in progress. Review detected POIs, then confirm.")

    validation = _validate_pois(pois)
    _render_poi_table(pois, validation, is_processing)

    hard_errors = bool(validation.errors)

    confirm_btn = st.button(
        "✅ Confirm POIs",
        key="confirm_custom_poi",
        use_container_width=True,
        disabled=is_processing or hard_errors or not pois,
    )

    if confirm_btn and not is_processing and not hard_errors:
        # Re-run validation after any edits
        st.session_state["command_processing"] = True
        st.session_state["command_pending_query"] = "confirm custom poi"
        st.rerun()

    if st.session_state.get("command_output") is not None and not is_processing:
        st.divider()
        if st.button("🔄 Reset Execution Query", key="reset_execution_query_cpoi", use_container_width=True):
            from app.ui.command.shared_command_utils import clear_product_viewer

            clear_product_viewer()
            st.rerun()

    # Returning a falsy string prevents the main input form from rendering while the pending panel is shown.
    # (The command_center input loop checks for truthy return to proceed.)
    return ""


# -----------------------------
# Pending handler
# -----------------------------


def handle_pending(query: str):
    pending = get_command_custom_poi_pending()
    if not pending or query != "confirm custom poi":
        return None

    # Final validation before generation hand-off (generation not implemented here)
    pois = pending.get("pois", [])
    validation = _validate_pois(pois)
    if validation.errors:
        st.session_state["command_processing"] = False
        return (
            "**Validation Error**\n\n" + "\n".join(validation.errors),
            "Custom POI",
            "Pending",
        )
    try:
        # Build input list for generation
        poi_data_list = []
        for p in validation.cleaned:
            poi_data_list.append(
                {
                    "poi": PointOfInterest(name=p.name, latitude=p.lat, longitude=p.lon),
                    "min_range": p.min_range,
                    "max_range": p.max_range,
                    "unit": DistanceUnit(p.unit),
                }
            )

        output = generate_custom_poi_range_ring_multi(
            poi_data_list=poi_data_list,
            resolution=pending.get("resolution", "normal"),
        )

        original_query = pending.get("original_query", "")
        if original_query:
            output.description = f"User Query: {original_query}"

        # Update history entry
        update_command_history_entry(
            match_criteria={"resolution": "Custom POI", "status": "Pending"},
            updates={
                "status": "Completed",
                "poi_count": len(poi_data_list),
                "output": output,
                "text": f"Custom POI ({len(poi_data_list)} POIs)",
            },
        )

        set_command_custom_poi_pending(None)
        st.session_state["command_processing"] = False
        return output, "Custom POI", "Completed (Updated)"
    except Exception as exc:
        st.session_state["command_processing"] = False
        return f"**Command Center Error**\n\n{exc}", "Custom POI", "Failed"


# -----------------------------
# Initial parse
# -----------------------------


def parse_initial(query: str):
    normalized = normalize_text(query)
    # Quick intent cues
    if not any(k in normalized for k in ["custom poi", "poi", "point of interest", "lat", "lon", "range"]):
        return None

    extracted = _extract_pois(query)
    if not extracted:
        return None

    set_command_custom_poi_pending({
        "pois": extracted,
        "original_query": query,
    })

    mode = "Multiple" if len(extracted) > 1 else "Single"
    return (
        f"**{mode} Custom POI detected**\n\n"
        f"Parsed {len(extracted)} POI(s). Review in the input panel and confirm.",
        "Custom POI",
        "Pending",
    )


# -----------------------------
# Help tab
# -----------------------------


def help_tab(tab):
    with tab:
        st.markdown("**Custom POI Range Ring**")
        st.markdown(
            "Provide one or more POIs with lat/lon and range(s). Use semicolons or brackets to separate multiple POIs."
        )
        st.markdown("**Examples:**")
        st.code("Generate custom POI at 35.6762 51.4241 1200 km")
        st.code("Custom POIs: [Tehran 35.6762 51.4241 300-1200 km]; [Isfahan 32.6539 51.6660 0-800 mi]")

        # Embed dynamic validator (mirrors multiple-range format)
        from app.ui.command.shared_command_utils import render_html_template, get_shared_validation_js

        html = render_html_template(
            "cpoi_validator.html",
            replacements={"{{SHARED_JS}}": get_shared_validation_js()},
        )
        st.components.v1.html(html, height=360)
