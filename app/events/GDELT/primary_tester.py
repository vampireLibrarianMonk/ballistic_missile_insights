#!/usr/bin/env python3
"""
gdelt_test_pull.py

Standalone test script for pulling recent GDELT 2.1 Events
and printing inferred military / missile-related signals.

Correctly handles GDELT ZIP files.
"""

from __future__ import annotations

import io
import sys
import zipfile
import requests
import pandas as pd
from datetime import datetime, timezone

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

GDELT_EVENTS_INDEX = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

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

MILITARY_EVENT_CODES = {
    "190",  # Use conventional military force
    "195",  # Employ aerial weapons
    "202",  # Engage in mass killing
}
MISSILE_STATES = {"USA", "RUS", "CHN", "PRK", "IRN", "ISR", "IND", "PAK"}

MAX_EVENTS = 50

COL_EVENT_ID = 0
COL_DATE = 1
COL_EVENT_CODE = 26
COL_ACTOR1 = 7
COL_ACTOR2 = 17
COL_LAT = 39
COL_LON = 40
COL_LOC = 41
COL_SOURCE_URL = 60

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def get_latest_events_url() -> str:
    resp = requests.get(GDELT_EVENTS_INDEX, timeout=10)
    resp.raise_for_status()

    for line in resp.text.splitlines():
        if line.endswith(".export.CSV.zip"):
            return line.split()[-1]

    raise RuntimeError("No GDELT events file found")


def download_and_load_csv(url: str) -> pd.DataFrame:
    print(f"[GDELT] Downloading {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            return pd.read_csv(
                f,
                sep="\t",
                header=None,
                low_memory=False,
                encoding="latin-1",  # GDELT-safe
            )


def infer_confidence(row: pd.Series) -> float:
    score = 0.0

    text_blob = " ".join(str(row[i]) for i in [57, 58] if i in row.index).lower()

    # HARD GATE: if no missile keywords, this is NOT a missile signal
    if not any(k in text_blob for k in KEYWORDS):
        return 0.0

    if str(row[26]) in MILITARY_EVENT_CODES:
        score += 0.3

    # Keywords already confirmed to exist
    score += 0.3

    if row[7] in MISSILE_STATES or row[17] in MISSILE_STATES:
        score += 0.2

    try:
        tone = float(row[34])
        if tone < -5:
            score += 0.1
    except Exception:
        pass

    return min(score, 1.0)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    print("[*] Fetching latest GDELT events file...")
    url = get_latest_events_url()

    df = download_and_load_csv(url)
    print(f"[*] Loaded {len(df):,} events")

    printed = 0

    for _, row in df.iterrows():
        if printed >= MAX_EVENTS:
            break

        if pd.isna(row[COL_LAT]) or pd.isna(row[COL_LON]):
            continue

        confidence = infer_confidence(row)
        if confidence < 0.4:
            continue

        event_time = datetime.strptime(
            str(row[COL_DATE]), "%Y%m%d"
        ).replace(tzinfo=timezone.utc)

        print("\n-----------------------------")
        print(f"Event ID:   {row[COL_EVENT_ID]}")
        print(f"Date:       {event_time.isoformat()}")
        print(f"Location:   {row[COL_LOC]}")
        print(f"Lat / Lon:  {row[COL_LAT]}, {row[COL_LON]}")
        print(f"Actors:     {row[COL_ACTOR1]} → {row[COL_ACTOR2]}")
        print(f"Event Code: {row[COL_EVENT_CODE]}")
        print(f"Confidence: {confidence:.2f}")
        print("Type:       Open-source military/missile signal")

        source_url = row[COL_SOURCE_URL]
        print(f"Source URL: {source_url}")

        printed += 1

    print(f"\n[*] Printed {printed} candidate events")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
