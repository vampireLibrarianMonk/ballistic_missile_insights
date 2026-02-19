"""Launch Trajectory command flow (progressive validation + redirect support).

Currently this module focuses on:
1) Enabling the Command Center status bar + validators to progressively validate
   "launch trajectory" style commands as the user types.
2) Providing a Help-tab validator widget consistent with the other range ring tools.

Trajectory generation/execution via Command Center is intentionally not
implemented yet (tool exists as an Analytical Tool, not a Command task).
"""

from __future__ import annotations

import re

import streamlit as st

from app.ui.command.shared_command_utils import render_html_template, get_shared_validation_js

from app.data.loaders import get_data_service
from app.ui.command.shared_command_utils import normalize_text, fuzzy_match
from app.models.outputs import LaunchTrajectoryOutput


def parse_initial(query: str):
    normalized = normalize_text(query)

    # Accept a few synonyms for progressive typing / user phrasing
    verbs = r"show|generate|create|build|visualize|display"
    type_syn = r"launch trajectory|trajectory|flight path|launch path"

    # Require from ... to ... to avoid misrouting
    pattern = rf"(?:{verbs})?\s*(?:a\s+)?(?:{type_syn})\s+from\s+(?P<origin>.+?)\s+to\s+(?P<dest>.+?)\.?$"
    m = re.search(pattern, normalized)
    if not m:
        return None

    origin_raw = (m.group("origin") or "").strip()
    dest_raw = (m.group("dest") or "").strip()
    if not origin_raw or not dest_raw:
        return None

    data_service = get_data_service()
    cities = data_service.get_city_list()
    countries = data_service.get_country_list()

    # Prefer exact canonical capitalization if possible; fuzzy-match otherwise
    origin_match = fuzzy_match(origin_raw, cities, cutoff=0.6) or fuzzy_match(origin_raw, countries, cutoff=0.6)
    dest_match = fuzzy_match(dest_raw, cities, cutoff=0.6) or fuzzy_match(dest_raw, countries, cutoff=0.6)

    if not origin_match or not dest_match:
        msg = (
            "**Launch Trajectory — Input Error**\n\n"
            "I couldn’t match one or both locations.\n\n"
            f"Origin provided: **{origin_raw}** → matched: **{origin_match or '—'}**\n"
            f"Destination provided: **{dest_raw}** → matched: **{dest_match or '—'}**\n\n"
            "Try using an exact city/country name from the lookup in the Help → Launch Trajectory tab."
        )
        return msg, "Launch Trajectory", "Failed"

    def resolve_coords(name: str) -> tuple[float, float] | None:
        # City coordinates
        coords = data_service.get_city_coordinates(name)
        if coords:
            return coords
        # Country centroid
        code = data_service.get_country_code(name)
        if code:
            centroid = data_service.get_country_centroid(code)
            if centroid:
                return centroid
        return None

    origin_coords = resolve_coords(origin_match)
    dest_coords = resolve_coords(dest_match)
    if not origin_coords or not dest_coords:
        msg = (
            "**Launch Trajectory — Resolution Error**\n\n"
            "Matched the names, but couldn’t resolve coordinates for one or both locations.\n\n"
            f"Origin: **{origin_match}**\n"
            f"Destination: **{dest_match}**\n"
        )
        return msg, "Launch Trajectory", "Failed"

    origin_lat, origin_lon = origin_coords
    dest_lat, dest_lon = dest_coords

    # Build a simple illustrative trajectory path (great-circle interpolation) with phases.
    # This is NOT a physics model; it matches the tool's disclaimer.
    from geographiclib.geodesic import Geodesic

    geod = Geodesic.WGS84
    inv = geod.Inverse(origin_lat, origin_lon, dest_lat, dest_lon)
    distance_km = inv["s12"] / 1000.0

    line = geod.Line(origin_lat, origin_lon, inv["azi1"])
    num_points = 60
    points = []
    for i in range(num_points + 1):
        f = i / num_points
        s = inv["s12"] * f
        pos = line.Position(s, Geodesic.STANDARD | Geodesic.LONG_UNROLL)

        if f < 0.2:
            phase = "boost"
            alt = 5000 + (f / 0.2) * 80000
        elif f < 0.8:
            phase = "midcourse"
            mid_f = (f - 0.2) / 0.6
            # Smooth arch peaking near midcourse center
            alt = 85000 + (1 - abs(mid_f - 0.5) * 2) * 220000
        else:
            phase = "terminal"
            term_f = (f - 0.8) / 0.2
            alt = 85000 * (1 - term_f)

        points.append(
            {
                "latitude": float(pos["lat2"]),
                "longitude": float(pos["lon2"]),
                "sequence_index": i,
                "altitude": float(max(0.0, alt)),
                "phase": phase,
                "sensor_id": "illustrative",
            }
        )

    sensors = [
        {
            "sensor_id": "illustrative",
            "name": "Illustrative Path",
            "sensor_class": "unknown",
            "detection_phase": None,
            "color": "#FF6B6B",
        }
    ]

    output = LaunchTrajectoryOutput(
        title="🚀 Launch Trajectory Visualization",
        description=f"User Query: {query}",
        origin_name=origin_match,
        destination_name=dest_match,
        origin_latitude=origin_lat,
        origin_longitude=origin_lon,
        destination_latitude=dest_lat,
        destination_longitude=dest_lon,
        distance_km=distance_km,
        points=points,
        sensors=sensors,
    )

    return output, "Launch Trajectory", "Completed"


def handle_pending(query: str):
    return None


def render_pending_panel():
    return None


def help_tab(tab):
    with tab:
        st.markdown("**Launch Trajectory**")
        st.markdown(
            "Visualize ballistic missile launch trajectories. This is an illustrative analytical visualization tool."
        )
        st.markdown("**Example:**")
        st.code("Show launch trajectory from Pyongyang to Tokyo")

        html = render_html_template(
            "traj_validator.html",
            replacements={"{{SHARED_JS}}": get_shared_validation_js()},
        )
        st.components.v1.html(html, height=420)
