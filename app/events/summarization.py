"""Summarization pipeline for ORRG World Events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
import re

from app.events.article_scraper import fetch_article_text
from app.llm.bedrock_client import invoke_bedrock, BedrockUsage
from app.ui.news.news_feed import NewsEvent


@dataclass(frozen=True)
class SummaryResult:
    report: str
    usage: BedrockUsage | None
    event_count: int


def summarize_events(
    events: list[NewsEvent],
    profile_id: str,
    max_events: int = 12,
    user_query: str | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> SummaryResult:
    """Generate the standardized report for today's events."""
    selected = _filter_events(
        events,
        max_events,
        user_query=user_query,
        chat_history=chat_history,
    )
    if not selected:
        return SummaryResult(
            report=_build_empty_message(user_query),
            usage=None,
            event_count=0,
        )

    prompt = _build_prompt(selected, user_query=user_query, chat_history=chat_history)
    response, usage = invoke_bedrock(prompt, profile_id=profile_id)
    return SummaryResult(report=response.strip(), usage=usage, event_count=len(selected))


def _filter_events(
    events: list[NewsEvent],
    max_events: int,
    user_query: str | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> list[NewsEvent]:
    year_filter = _extract_year(user_query) or _extract_year_from_history(chat_history)
    country_filter = _extract_country_filter(user_query) or _extract_country_from_history(chat_history)

    if year_filter or country_filter:
        filtered = events
        if year_filter:
            filtered = [
                event for event in filtered
                if event.event_date.replace(tzinfo=timezone.utc).year == year_filter
            ]
        if country_filter:
            filtered = [
                event for event in filtered
                if event.country_code == country_filter
            ]
        filtered.sort(key=lambda e: e.event_date, reverse=True)
        return filtered[:max_events]

    now = datetime.now(timezone.utc)
    today = now.date()
    today_events = [
        event
        for event in events
        if event.event_date.replace(tzinfo=timezone.utc).date() == today
    ]

    if not today_events:
        cutoff = now - timedelta(hours=24)
        today_events = [
            event
            for event in events
            if event.event_date.replace(tzinfo=timezone.utc) >= cutoff
        ]

    today_events.sort(key=lambda e: e.event_date, reverse=True)
    return today_events[:max_events]


def _extract_year(user_query: str | None) -> int | None:
    if not user_query:
        return None
    lowered = user_query.lower()
    if "this year" in lowered or "current year" in lowered:
        return datetime.now(timezone.utc).year
    match = re.search(r"\b(20\d{2})\b", user_query)
    if not match:
        return None
    year = int(match.group(1))
    if 2000 <= year <= 2100:
        return year
    return None


def _extract_country_filter(user_query: str | None) -> str | None:
    if not user_query:
        return None
    lowered = user_query.lower()
    country_map = {
        "north korea": "PRK",
        "dprk": "PRK",
        "south korea": "KOR",
        "korea": "KOR",
        "iran": "IRN",
        "russia": "RUS",
        "russian": "RUS",
        "china": "CHN",
        "chinese": "CHN",
        "united states": "USA",
        "us": "USA",
        "america": "USA",
        "israel": "ISR",
        "israeli": "ISR",
        "india": "IND",
        "pakistan": "PAK",
        "ukraine": "UKR",
        "japan": "JPN",
        "taiwan": "TWN",
    }
    for name, code in country_map.items():
        if name in lowered:
            return code
    return None


def _extract_year_from_history(chat_history: list[dict[str, str]] | None) -> int | None:
    if not chat_history:
        return None
    for entry in reversed(chat_history):
        year = _extract_year(entry.get("content", ""))
        if year:
            return year
    return None


def _extract_country_from_history(chat_history: list[dict[str, str]] | None) -> str | None:
    if not chat_history:
        return None
    for entry in reversed(chat_history):
        country = _extract_country_filter(entry.get("content", ""))
        if country:
            return country
    return None


def _build_empty_message(user_query: str | None) -> str:
    year_filter = _extract_year(user_query)
    country_filter = _extract_country_filter(user_query)
    if year_filter and country_filter:
        return f"No events found for {country_filter} in {year_filter}."
    if year_filter:
        return f"No events found for {year_filter}."
    if country_filter:
        return f"No recent events found for {country_filter}."
    return "No events found in the last 24 hours."


def _build_prompt(
    events: list[NewsEvent],
    user_query: str | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> str:
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "You are an intelligence analyst creating a standardized daily report.",
        "Answer the user's question using the provided event material.",
        "Summarize with concise, factual language.",
        "Use the exact format below for each item:",
        f"ORRG DAILY INTEL REPORT — {report_date}",
        "",
        "1. HEADLINE",
        "   Source:",
        "   Country/Region:",
        "   Event Type:",
        "   Summary (2–4 sentences):",
        "   Confidence:",
        "   Source Link:",
        "",
        "If details are missing, state 'Unknown'.",
        "",
    ]

    if user_query:
        lines.append(f"User Question: {user_query}")
        lines.append("")

    if chat_history:
        lines.append("Conversation Context:")
        for entry in chat_history[-6:]:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            lines.append(f"- {role}: {content}")
        lines.append("")

    for idx, event in enumerate(events, start=1):
        article_text = None
        if event.source_url:
            try:
                article_text = fetch_article_text(event.source_url)
            except Exception:
                article_text = None

        summary_source = article_text or event.summary or ""
        lines.append(f"Event {idx}:")
        lines.append(f"Title: {event.title}")
        lines.append(f"Source: {event.source}")
        lines.append(f"Country/Region: {event.country_code or 'Unknown'}")
        lines.append(f"Event Type: {event.event_type.value}")
        lines.append(f"Confidence: {event.confidence.value}")
        lines.append(f"Source Link: {event.source_url or 'Unknown'}")
        lines.append("Article Text:")
        lines.append(summary_source[:6000])
        lines.append("")

    return "\n".join(lines)