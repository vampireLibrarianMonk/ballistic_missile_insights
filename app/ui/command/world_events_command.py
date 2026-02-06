"""World Events command flow for the Command Center.

Goal
----
Expose World Events search + summary chat ONLY through the Step 1 user entry,
using the same two-step (parse → pending UI → confirm) pattern as the range ring
tasks.

There is intentionally **no always-visible World Events panel** rendered on the
Command Center page.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Optional, Union, Literal

import streamlit as st

from app.events.summarization import summarize_events
from app.llm.bedrock_client import get_profile_options
from app.data.loaders import get_data_service
from app.ui.layout.global_state import (
    get_command_world_events_pending,
    set_command_world_events_pending,
    update_command_history_entry,
)
from app.ui.news.news_feed import (
    NewsEvent,
    create_sample_events,
    get_loaded_events,
    init_news_events_state,
    set_loaded_events,
)


CommandOutput = Union[str, None]

TimeUnit = Literal["hours", "days", "week", "month", "year"]
Domain = Literal["missile", "nuclear"]
Activity = Literal["tests", "exercises", "combat activity", "deployment"]
DatasetHint = Literal["current", "sample", "live"]


@dataclass(frozen=True)
class WorldEventsSearchSpec:
    quantity: int
    unit: TimeUnit
    country: str  # ISO3 currently
    domain: Domain
    activity: Activity
    country_display: Optional[str] = None
    dataset_hint: Optional[DatasetHint] = None

    def to_display(self) -> str:
        country_disp = self.country_display or self.country
        ds = f" ({self.dataset_hint})" if self.dataset_hint else ""
        return (
            f"Show me events over the last {self.quantity} {self.unit} for {country_disp} "
            f"concerning {self.domain} {self.activity}."
        ) + ds


class CommandParsingError(Exception):
    """Raised when a world-events command cannot be parsed."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _levenshtein_distance(a: str, b: str) -> int:
    """Small, dependency-free Levenshtein distance for typo tolerance."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[m][n]


def _is_plausible_country_typo(user_value: str, options_lower: list[str]) -> bool:
    """Allow typos, but reject abbreviations/prefixes like 'Chin' for 'China'.

    Rules:
    - input length must be >= 5
    - best edit distance to a real country name must be <= 2
    """

    s = (user_value or "").strip().lower()
    if len(s) < 5:
        return False

    best = 999
    for opt in options_lower:
        if not opt:
            continue
        # cheap guard to reduce false positives
        if opt[0] != s[0]:
            continue
        d = _levenshtein_distance(s, opt)
        if d < best:
            best = d
            if best <= 1:
                break
    return best <= 2


def _extract_search_spec(text: str) -> Optional[WorldEventsSearchSpec]:
    """Parse:

    Show me events over the last # {hours|days|week|month|year} for {country}
    concerning {missile/nuclear} {tests/exercises/combat activity/deployment}.
    """

    normalized = _normalize(text)
    if "events" not in normalized or "over the last" not in normalized or "concerning" not in normalized:
        return None

    # Capture groups are intentionally strict to avoid hijacking other commands.
    # Quantity is optional; if omitted we assume qty=1.
    pattern = re.compile(
        r"show me events over the last\s+(?:(?P<qty>\d+)\s+)?(?P<unit>hour|hours|day|days|week|weeks|month|months|year|years)\s+"
        r"for\s+(?P<country>.+?)\s+concerning\s+(?P<domain>missile|nuclear)\s+"
        r"(?P<activity>tests|exercises|combat activity|deployment)\b"
        r"(?:\s+from\s+(?P<dataset>live|sample|current)\s+events?)?",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        # Try against normalized variant as well (handles casing/punctuation).
        match = pattern.search(normalized)
    if not match:
        return None

    qty_raw = match.group("qty")
    qty = int(qty_raw) if qty_raw else 1
    unit_raw = match.group("unit").lower()
    unit_map = {
        "hour": "hours",
        "hours": "hours",
        "day": "days",
        "days": "days",
        "week": "week",
        "weeks": "week",
        "month": "month",
        "months": "month",
        "year": "year",
        "years": "year",
    }
    unit = unit_map.get(unit_raw, unit_raw)
    country_raw = match.group("country").strip()
    country_display = country_raw
    # Accept ISO3 or country name. Normalize to ISO3 for internal filtering.
    if re.fullmatch(r"[A-Za-z]{3}", country_raw):
        code_candidate = country_raw.upper()
        data_service = get_data_service()
        if code_candidate not in set(data_service.get_country_codes()):
            return None
        country = code_candidate
        # If user used ISO3, prefer friendly display name.
        try:
            country_display = data_service.get_country_name(country)
        except Exception:
            country_display = country
    else:
        data_service = get_data_service()
        name_map = {c.lower(): c for c in data_service.get_country_list()}

        # Common alias handling (user-friendly names → canonical loader names)
        alias_map = {
            "north korea": "Korea, North",
            "south korea": "Korea, South",
            "united states": "United States of America",
            "usa": "United States of America",
            "uk": "United Kingdom",
            "russia": "Russian Federation",
        }

        normalized_country = (country_raw or "").strip().lower()
        normalized_country = alias_map.get(normalized_country, normalized_country)

        # 1) exact match
        matched_name = name_map.get(normalized_country)

        # 2) allow small typos (not abbreviations)
        if not matched_name and _is_plausible_country_typo(normalized_country, list(name_map.keys())):
            # Find the best match by edit distance.
            best_name = None
            best_d = 999
            for opt_lower, opt_canonical in name_map.items():
                if not opt_lower or opt_lower[0] != normalized_country[0]:
                    continue
                d = _levenshtein_distance(normalized_country, opt_lower)
                if d < best_d:
                    best_d = d
                    best_name = opt_canonical
            if best_name and best_d <= 2:
                matched_name = best_name

        if not matched_name:
            return None

        code = data_service.get_country_code(matched_name)
        if not code:
            return None
        country = code.upper()
        country_display = matched_name
    domain = match.group("domain").lower()
    activity = match.group("activity").lower()
    dataset_raw = match.group("dataset")
    dataset_hint: Optional[DatasetHint] = dataset_raw.lower() if dataset_raw else None  # type: ignore[assignment]

    if qty <= 0:
        return None

    return WorldEventsSearchSpec(
        quantity=qty,
        unit=unit,  # type: ignore[arg-type]
        country=country,
        country_display=country_display,
        domain=domain,  # type: ignore[arg-type]
        activity=activity,  # type: ignore[arg-type]
        dataset_hint=dataset_hint,
    )


def _is_daily_summary_request(text: str) -> bool:
    normalized = _normalize(text)
    # Keep this narrow so we don't steal unrelated queries.
    triggers = [
        "daily event summary",
        "daily intel report",
        "summarize today's events",
        "summarize todays events",
    ]
    if any(t in normalized for t in triggers):
        return True
    # Common phrasing.
    if "important events" in normalized and "today" in normalized:
        return True
    return False


def _compute_cutoff(spec: WorldEventsSearchSpec) -> datetime:
    now = datetime.now()
    if spec.unit == "hours":
        return now - timedelta(hours=spec.quantity)
    if spec.unit == "days":
        return now - timedelta(days=spec.quantity)
    if spec.unit == "week":
        return now - timedelta(days=7 * spec.quantity)
    if spec.unit == "month":
        return now - timedelta(days=30 * spec.quantity)
    return now - timedelta(days=365 * spec.quantity)


def _filter_events_for_spec(events: list[NewsEvent], spec: WorldEventsSearchSpec) -> list[NewsEvent]:
    cutoff = _compute_cutoff(spec)

    filtered = [e for e in events if e.event_date >= cutoff]
    filtered = [e for e in filtered if (e.country_code or "").upper() == spec.country.upper()]

    # If the user asks for a very short window (e.g. 24 hours) but the dataset is historical
    # (like our sample events), this can legitimately produce 0 matches. As a usability
    # fallback, widen to 30 days IF the filter would otherwise be empty.
    if not filtered and spec.unit == "hours" and spec.quantity <= 48:
        fallback_cutoff = datetime.now() - timedelta(days=30)
        filtered = [e for e in events if e.event_date >= fallback_cutoff]
        filtered = [e for e in filtered if (e.country_code or "").upper() == spec.country.upper()]

    # Keyword match on title/summary/tags
    # Domain terms: for "missile" we also treat common missile synonyms as domain hits.
    if spec.domain.lower() == "missile":
        terms = {"missile", "ballistic", "icbm", "irbm", "mrbm", "srbm", "crbm", "hypersonic"}
    else:
        terms = {"nuclear"}
    activity_terms = {
        "tests": {"test", "tested", "testing", "test fire"},
        "exercises": {"exercise", "drill", "maneuver"},
        "combat activity": {"combat", "strike", "attack", "fired", "launch"},
        "deployment": {"deploy", "deployed", "deployment", "stationed", "moved"},
    }.get(spec.activity, set())
    terms |= activity_terms

    def matches(e: NewsEvent) -> bool:
        blob = " ".join([
            e.title or "",
            e.summary or "",
            " ".join(e.tags or []),
        ]).lower()
        return any(t in blob for t in terms)

    filtered = [e for e in filtered if matches(e)]
    return sorted(filtered, key=lambda ev: ev.event_date, reverse=True)


def _update_pending_history_entry(final_status: str, updated_text: Optional[str] = None, output: Optional[str] = None) -> None:
    updates: dict = {"status": final_status}
    if updated_text:
        updates["text"] = updated_text
    if output is not None:
        updates["output"] = output

    update_command_history_entry(
        match_criteria={
            "resolution": "World Events",
            "status": "Pending",
        },
        updates=updates,
    )


def render_pending_panel() -> Optional[str]:
    """Step 2 UI. Returns empty string to hide Step 1 input when pending."""
    pending = get_command_world_events_pending()
    if not pending:
        return None

    init_news_events_state()
    is_processing = st.session_state.get("command_processing", False)

    st.markdown("### 🌍 Step 2: World Events")
    st.info("**World Events session in progress** — choose a dataset and run the query.")
    st.caption(f"Original user entry: {pending.get('original_query', '')}")

    # Dataset selection lives in session_state so it survives reruns.
    if "cmd_we_dataset" not in st.session_state:
        st.session_state.cmd_we_dataset = "Use currently loaded events"

    dataset_choice = st.radio(
        "Dataset",
        options=[
            "Use currently loaded events",
            "Load sample events",
            "Fetch live events now",
        ],
        index=[
            "Use currently loaded events",
            "Load sample events",
            "Fetch live events now",
        ].index(st.session_state.cmd_we_dataset),
        key="cmd_we_dataset_radio",
        disabled=is_processing,
    )
    st.session_state.cmd_we_dataset = dataset_choice

    spec_dict = pending.get("spec")
    mode = pending.get("mode")

    if mode == "search" and spec_dict:
        spec = WorldEventsSearchSpec(**spec_dict)
        st.markdown("#### 🧾 User entry")
        st.markdown(spec.to_display())
    elif mode == "chat":
        st.markdown("#### 🧾 User entry")
        st.markdown("Daily Event Summary / Chat")

    col_run, col_exit = st.columns([1, 1])
    with col_run:
        run = st.button(
            "✅ Run World Events",
            key="cmd_we_run",
            type="primary",
            use_container_width=True,
            disabled=is_processing,
        )
    with col_exit:
        exit_btn = st.button(
            "✖ Exit",
            key="cmd_we_exit",
            use_container_width=True,
            disabled=is_processing,
        )

    if exit_btn and not is_processing:
        set_command_world_events_pending(None)
        return ""

    if run and not is_processing:
        st.session_state["command_processing"] = True
        st.session_state["command_pending_query"] = "confirm world events"
        st.rerun()

    # Hide Step 1 input while pending.
    return ""


def handle_pending(query: str):
    pending = get_command_world_events_pending()
    if not pending:
        return None

    if query != "confirm world events":
        return None

    try:
        init_news_events_state()

        dataset_choice = st.session_state.get("cmd_we_dataset", "Use currently loaded events")
        if dataset_choice == "Load sample events":
            events = create_sample_events()
            set_loaded_events(events, "Sample Data")
        elif dataset_choice == "Fetch live events now":
            from app.events.adapter import fetch_live_events

            with st.spinner("Fetching live events..."):
                events, counts = fetch_live_events()
            if events:
                set_loaded_events(events, f"Live Feed ({sum(counts.values())} from {len(counts)} sources)")
        # Always read back from canonical store (ensures we display same objects as elsewhere)
        events = get_loaded_events()
        if not events:
            st.session_state["command_processing"] = False
            return (
                "**World Events Error**\n\nNo events are available. Choose sample events or fetch live events.",
                "World Events",
                "Pending",
            )

        mode = pending.get("mode")
        if mode == "search":
            spec_dict = pending.get("spec")
            if not spec_dict:
                raise CommandParsingError("Missing search spec.")
            spec = WorldEventsSearchSpec(**spec_dict)
            matched = _filter_events_for_spec(events, spec)

            lines = [
                "### 🌍 World Events Search",
                "",
                f"**Query:** {spec.to_display()}",
                f"**Dataset:** {st.session_state.get('news_events_source', 'Unknown')}",
                f"**Matches:** {len(matched)}",
                "",
                "**Top results:**",
            ]
            for e in matched[:10]:
                url = getattr(e, "source_url", None) or ""
                link = f" ([source]({url}))" if url else ""
                lines.append(
                    f"- **{e.event_date.strftime('%Y-%m-%d')}** · **{e.country_code}** · **{e.event_type.value}** · {e.title}{link}"
                )
            output = "\n".join(lines)

            _update_pending_history_entry(
                final_status="Completed",
                updated_text=f"World Events search ({len(matched)} matches)",
                output=output,
            )

            set_command_world_events_pending(None)
            st.session_state["command_processing"] = False
            return output, "World Events", "Completed (Updated)"

        # mode == chat
        profile_options = get_profile_options()
        if not profile_options:
            output = "Inference profiles not configured."
            _update_pending_history_entry(final_status="Failed", output=output)
            set_command_world_events_pending(None)
            st.session_state["command_processing"] = False
            return output, "World Events", "Failed"

        # Simple one-turn: use the user's entry as the query.
        user_query = pending.get("original_query") or "what important events happened so far today?"
        default_profile_id = st.session_state.get("news_inference_profile")
        if default_profile_id not in profile_options:
            default_profile_id = next(iter(profile_options.keys()))
            st.session_state.news_inference_profile = default_profile_id

        with st.spinner("Summarizing events..."):
            result = summarize_events(
                events,
                profile_id=default_profile_id,
                user_query=user_query,
                chat_history=None,
            )
        st.session_state.news_summary_usage = result.usage

        output = result.report
        _update_pending_history_entry(final_status="Completed", updated_text="World Events daily summary", output=output)
        set_command_world_events_pending(None)
        st.session_state["command_processing"] = False
        return output, "World Events", "Completed (Updated)"

    except Exception as exc:
        st.session_state["command_processing"] = False
        return f"**World Events Error**\n\n{exc}", "World Events", "Failed"


def parse_initial(query: str):
    """Parse the Step 1 user entry. If it's a world-events request, start a pending flow."""

    spec = _extract_search_spec(query)
    if spec:
        dataset_choice = None
        if spec.dataset_hint == "sample":
            dataset_choice = "Load sample events"
        elif spec.dataset_hint == "live":
            dataset_choice = "Fetch live events now"
        elif spec.dataset_hint == "current":
            dataset_choice = "Use currently loaded events"

        if dataset_choice:
            st.session_state["cmd_we_dataset"] = dataset_choice

        set_command_world_events_pending(
            {
                "mode": "search",
                "spec": {
                    "quantity": spec.quantity,
                    "unit": spec.unit,
                    "country": spec.country,
                    "domain": spec.domain,
                    "activity": spec.activity,
                    "country_display": spec.country_display,
                    "dataset_hint": spec.dataset_hint,
                },
                "original_query": query,
            }
        )
        return (
            "**World Events Search queued**\n\n"
            "Proceed to Step 2 to choose a dataset and run the query.",
            "World Events",
            "Pending",
        )

    if _is_daily_summary_request(query):
        set_command_world_events_pending(
            {
                "mode": "chat",
                "spec": None,
                "original_query": query,
            }
        )
        return (
            "**World Events Daily Summary queued**\n\n"
            "Proceed to Step 2 to choose a dataset and generate the summary.",
            "World Events",
            "Pending",
        )

    return None


def help_tab(tab):
    with tab:
        st.markdown("**World Events task**")
        st.markdown("This is a **two-step workflow**:")
        st.markdown(
            "1) **Step 1**: enter a World Events query (optionally include a dataset hint).  "
            "\n2) **Step 2**: confirm dataset + run the query."
        )

        st.markdown("#### Step 1 query format")
        st.code(
            "Show me events over the last 24 hours for PRK concerning missile tests."
        )

        st.markdown("#### Optional dataset hint")
        st.caption("Add one of the following to the end of the Step 1 query:")
        st.code(
            "from current events\nfrom sample events\nfrom live events"
        )

        st.markdown("#### Examples")
        st.code(
            "Show me events over the last 24 hours for PRK concerning missile tests from sample events.\n"
            "Show me events over the last 7 days for China concerning nuclear deployment from live events."
        )

        st.markdown("Or request a daily summary:")
        st.code("Daily event summary")

        _render_world_events_validator()


def _render_world_events_validator() -> None:
    """Help-tab validator widget (progressive checks while typing)."""
    from app.ui.command.shared_command_utils import render_html_template, get_shared_validation_js

    html = render_html_template(
        "we_validator.html",
        replacements={
            "{{SHARED_JS}}": get_shared_validation_js(),
        },
    )
    st.components.v1.html(html, height=360)
