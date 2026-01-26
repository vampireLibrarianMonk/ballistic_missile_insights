#!/usr/bin/env python3
"""
ap_news_pull.py

Standalone Associated Press (AP) News RSS puller for missile-related events.
"""

from __future__ import annotations
import sys
import feedparser
from datetime import datetime, timezone

AP_RSS = "https://apnews.com/hub/world-news?rss"

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
    feed = feedparser.parse(AP_RSS)
    printed = 0

    for entry in feed.entries:
        text_blob = f"{entry.get('title','')} {entry.get('summary','')}"

        if not contains_keywords(text_blob):
            continue

        print("\n-----------------------------")
        print("Source:     AP")
        print(f"Published:  {parse_datetime(entry).isoformat()}")
        print(f"Title:      {entry.get('title')}")
        print(f"Summary:    {entry.get('summary','')[:300]}...")
        print(f"Source URL: {entry.get('link')}")
        print("Type:       Open-source missile-related news signal")

        printed += 1
        if printed >= MAX_EVENTS:
            break

    print(f"\n[*] Printed {printed} AP events")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
