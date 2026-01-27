#!/usr/bin/env python3
"""
bbc_news_pull.py

Standalone BBC News RSS puller for missile-related events.
"""

from __future__ import annotations
import sys
import feedparser
from datetime import datetime, timezone

from ..utilities import extract_country, extract_city

BBC_RSS = "https://feeds.bbci.co.uk/news/world/rss.xml"

KEYWORDS = [
    "missile",
    "ballistic",
    "rocket",
    "launch",
    "icbm",
    "irbm",
    "srbm",
    "crbm",
    "test fire",
]

MAX_EVENTS = 25


def contains_keywords(text: str) -> bool:
    text = text.lower()
    return any(k in text for k in KEYWORDS)


def parse_datetime(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc)


def main() -> None:
    feed = feedparser.parse(BBC_RSS)
    printed = 0
    found_keyword_events = False

    for entry in feed.entries:
        text_blob = f"{entry.get('title','')} {entry.get('summary','')}"

        if not contains_keywords(text_blob):
            continue

        found_keyword_events = True

        print("\n-----------------------------")
        print("Source:     BBC")
        print(f"Published:  {parse_datetime(entry).isoformat()}")
        print(f"Title:      {entry.get('title')}")
        print(f"Summary:    {entry.get('summary','')[:300]}...")
        print(f"Source URL: {entry.get('link')}")
        print("Type:       Open-source missile-related news signal")

        country = extract_country(entry.get('title'))
        print(f"Country:     {country}")
        city = extract_city(entry.get('title'))
        print(f"City:     {city}")

        printed += 1
        if printed >= MAX_EVENTS:
            break

    print(f"\n[*] Printed {printed} BBC events")

    # # Fallback: no keyword events found — print latest 5 as samples
    # if not found_keyword_events:
    #     print("\n[INFO] No keyword-matching events found. Printing latest 5 entries as samples.\n")
    #
    #     for entry in feed.entries[:5]:
    #         print("\n-----------------------------")
    #         print("Source:     BBC (SAMPLE)")
    #         print(f"Published:  {parse_datetime(entry).isoformat()}")
    #         print(f"Title:      {entry.get('title')}")
    #         print(f"Summary:    {entry.get('summary','')[:300]}...")
    #         print(f"Source URL: {entry.get('link')}")
    #         print("Type:       Sample news event (no keyword match)")
    #
    #         country = extract_country(entry.get('title'))
    #         print(f"Country:     {country}")
    #         city = extract_city(entry.get('title'))
    #         print(f"City:     {city}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
