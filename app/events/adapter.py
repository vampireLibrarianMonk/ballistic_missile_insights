"""
Unified Event Adapter for ORRG News Feed.

Provides parallel fetching and normalization of events from multiple sources:
- GDELT 2.1 Events
- Reuters RSS
- BBC RSS
- AP News RSS

All events are normalized to the NewsEvent dataclass format.
"""

from __future__ import annotations

import io
import zipfile
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

import requests
import feedparser
import pandas as pd

# Import utilities for country/city extraction
try:
    from app.events.utilities import extract_country, extract_city
except ImportError:
    # Fallback if utilities not available
    def extract_country(text: str) -> str | None:
        return None
    def extract_city(text: str) -> str | None:
        return None


# =============================================================================
# Configuration
# =============================================================================

GDELT_EVENTS_INDEX = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
REUTERS_RSS = "https://feeds.reuters.com/reuters/worldNews"
BBC_RSS = "https://feeds.bbci.co.uk/news/world/rss.xml"
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
    "mrbm",
    "test fire",
    "nuclear",
    "warhead",
    "hypersonic",
]
MISSILE_KEYWORDS = {
    "missile",
    "ballistic",
    "rocket",
    "icbm",
    "irbm",
    "srbm",
    "crbm",
    "mrbm",
    "test fire",
    "nuclear",
    "warhead",
    "hypersonic",
}

MISSILE_STATES = {"USA", "RUS", "CHN", "PRK", "IRN", "ISR", "IND", "PAK"}

# Country code mapping from names
COUNTRY_CODE_MAP = {
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
    "yemen": "YEM",
    "houthi": "YEM",
    "syria": "SYR",
    "ukraine": "UKR",
    "taiwan": "TWN",
    "japan": "JPN",
}

# Capital city coordinates for fallback geolocation
CAPITAL_COORDS = {
    "PRK": (39.0392, 125.7625),  # Pyongyang
    "IRN": (35.6892, 51.3890),   # Tehran
    "RUS": (55.7558, 37.6173),   # Moscow
    "CHN": (39.9042, 116.4074),  # Beijing
    "USA": (38.9072, -77.0369),  # Washington DC
    "ISR": (31.7683, 35.2137),   # Jerusalem
    "IND": (28.6139, 77.2090),   # New Delhi
    "PAK": (33.6844, 73.0479),   # Islamabad
    "YEM": (15.3694, 44.1910),   # Sanaa
    "SYR": (33.5138, 36.2765),   # Damascus
    "UKR": (50.4501, 30.5234),   # Kyiv
    "KOR": (37.5665, 126.9780),  # Seoul
    "TWN": (25.0330, 121.5654),  # Taipei
    "JPN": (35.6762, 139.6503),  # Tokyo
}

MAX_EVENTS_PER_SOURCE = 25
REQUEST_TIMEOUT = 15


# =============================================================================
# Event Dataclass (matches NewsEvent structure)
# =============================================================================

@dataclass
class FetchedEvent:
    """Raw fetched event before conversion to NewsEvent."""
    id: str
    title: str
    summary: str
    event_type: str
    country_code: str
    latitude: float
    longitude: float
    event_date: datetime
    source: str
    source_url: Optional[str] = None
    confidence: str = "medium"
    weapon_system: Optional[str] = None
    range_km: Optional[float] = None
    tags: list[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def contains_keywords(text: str) -> bool:
    """Check if text contains any missile-related keywords."""
    text = text.lower()
    if "launch" in text and not any(k in text for k in MISSILE_KEYWORDS):
        return False
    return any(k in text for k in KEYWORDS)


def infer_event_type(text: str) -> str:
    """Infer event type from text content."""
    text = text.lower()
    
    if any(w in text for w in ["launch", "fired", "fires", "attacked", "strike"]):
        return "launch"
    elif any(w in text for w in ["test", "tested", "testing"]):
        return "test"
    elif any(w in text for w in ["exercise", "drill", "maneuver"]):
        return "exercise"
    elif any(w in text for w in ["deploy", "stationed", "moved", "position"]):
        return "deployment"
    elif any(w in text for w in ["nuclear", "atomic", "warhead"]):
        return "nuclear"
    elif any(w in text for w in ["statement", "said", "announced", "warned", "threat"]):
        return "statement"
    else:
        return "other"


def infer_country_code(text: str) -> str:
    """Infer country code from text content."""
    text = text.lower()
    
    for name, code in COUNTRY_CODE_MAP.items():
        if name in text:
            return code
    
    # Try pycountry-based extraction
    extracted = extract_country(text)
    if extracted:
        extracted_lower = extracted.lower()
        for name, code in COUNTRY_CODE_MAP.items():
            if name in extracted_lower:
                return code
    
    return "UNK"


def get_coordinates(country_code: str, text: str) -> tuple[float, float]:
    """Get coordinates for an event, preferring capital cities."""
    # Try to find city coordinates first
    city = extract_city(text) if text else None
    # For now, use capital coordinates as fallback
    if country_code in CAPITAL_COORDS:
        return CAPITAL_COORDS[country_code]
    return (0.0, 0.0)


def generate_event_id(source: str, title: str, date: datetime) -> str:
    """Generate unique event ID from source, title and date."""
    content = f"{source}:{title}:{date.isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def parse_rss_datetime(entry) -> datetime:
    """Parse datetime from RSS entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc)


# =============================================================================
# Source Fetchers
# =============================================================================

def fetch_gdelt_events() -> list[FetchedEvent]:
    """Fetch and normalize events from GDELT 2.1."""
    events = []
    
    try:
        # Get latest events file URL
        resp = requests.get(GDELT_EVENTS_INDEX, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        
        events_url = None
        for line in resp.text.splitlines():
            if line.endswith(".export.CSV.zip"):
                events_url = line.split()[-1]
                break
        
        if not events_url:
            return events
        
        # Download and parse CSV
        resp = requests.get(events_url, timeout=30)
        resp.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            csv_name = z.namelist()[0]
            with z.open(csv_name) as f:
                df = pd.read_csv(f, sep="\t", header=None, low_memory=False, encoding="latin-1")
        
        # Process events
        count = 0
        seen_urls = set()
        for _, row in df.iterrows():
            if count >= MAX_EVENTS_PER_SOURCE:
                break
            # Check for keywords in source URL and other text fields
            text_blob = " ".join(str(row[i]) for i in [57, 58, 60] if i < len(row)).lower()

            if not contains_keywords(text_blob):
                continue

            # Deduplicate by source URL to avoid multiple rows from the same article
            source_url = str(row[60]) if not pd.isna(row[60]) else None
            if source_url and source_url in seen_urls:
                continue

            # Extract data
            try:
                event_date = datetime.strptime(str(int(row[1])), "%Y%m%d").replace(tzinfo=timezone.utc)
            except:
                event_date = datetime.now(tz=timezone.utc)

            source_host = None
            if source_url:
                try:
                    source_host = urlparse(source_url).netloc
                except Exception:
                    source_host = None

            title = (
                f"GDELT: {source_host}" if source_host else f"GDELT Event {row[0]}"
            )
            summary = (
                f"Source: {source_url}" if source_url else
                f"Location: {row[41]}. Actors: {row[7]} → {row[17]}"
            )

            country_code = infer_country_code(text_blob)
            if country_code == "UNK":
                # Try actor codes
                actor1 = str(row[7]) if not pd.isna(row[7]) else ""
                if actor1 in MISSILE_STATES:
                    country_code = actor1

            lat = None
            lon = None
            lat_lon_candidates = [(40, 41), (39, 40), (56, 57)]
            for lat_idx, lon_idx in lat_lon_candidates:
                try:
                    candidate_lat = float(row[lat_idx])
                    candidate_lon = float(row[lon_idx])
                except (TypeError, ValueError):
                    continue
                if -90 <= candidate_lat <= 90 and -180 <= candidate_lon <= 180:
                    lat, lon = candidate_lat, candidate_lon
                    break

            if lat is None or lon is None:
                row_debug = ", ".join(f"{idx}={row[idx]}" for idx in row.index)
                print(
                    f"[GDELT] Skipping event {row[0]}: invalid coordinates "
                    f"| row=[{row_debug}]"
                )
                continue

            if source_url:
                seen_urls.add(source_url)
            
            events.append(FetchedEvent(
                id=generate_event_id("GDELT", title, event_date),
                title=title,
                summary=summary,
                event_type=infer_event_type(text_blob),
                country_code=country_code,
                latitude=lat,
                longitude=lon,
                event_date=event_date,
                source="GDELT",
                source_url=source_url,
                confidence="medium",
                tags=["GDELT", "automated"],
            ))
            count += 1
    
    except Exception as e:
        print(f"[GDELT] Error fetching events: {e}")
    
    return events


def fetch_reuters_events() -> list[FetchedEvent]:
    """Fetch and normalize events from Reuters RSS."""
    events = []
    
    try:
        feed = feedparser.parse(REUTERS_RSS)
        count = 0
        
        for entry in feed.entries:
            if count >= MAX_EVENTS_PER_SOURCE:
                break
            
            text_blob = f"{entry.get('title', '')} {entry.get('summary', '')}"
            
            if not contains_keywords(text_blob):
                continue
            
            title = entry.get('title', 'Reuters Event')
            summary = entry.get('summary', '')[:500]
            event_date = parse_rss_datetime(entry)
            
            country_code = infer_country_code(text_blob)
            lat, lon = get_coordinates(country_code, text_blob)
            
            events.append(FetchedEvent(
                id=generate_event_id("Reuters", title, event_date),
                title=title,
                summary=summary,
                event_type=infer_event_type(text_blob),
                country_code=country_code,
                latitude=lat,
                longitude=lon,
                event_date=event_date,
                source="Reuters",
                source_url=entry.get('link'),
                confidence="high",
                tags=["Reuters", "news"],
            ))
            count += 1
    
    except Exception as e:
        print(f"[Reuters] Error fetching events: {e}")
    
    return events


def fetch_bbc_events() -> list[FetchedEvent]:
    """Fetch and normalize events from BBC RSS."""
    events = []
    
    try:
        feed = feedparser.parse(BBC_RSS)
        count = 0
        
        for entry in feed.entries:
            if count >= MAX_EVENTS_PER_SOURCE:
                break
            
            text_blob = f"{entry.get('title', '')} {entry.get('summary', '')}"
            
            if not contains_keywords(text_blob):
                continue
            
            title = entry.get('title', 'BBC Event')
            summary = entry.get('summary', '')[:500]
            event_date = parse_rss_datetime(entry)
            
            country_code = infer_country_code(text_blob)
            lat, lon = get_coordinates(country_code, text_blob)
            
            events.append(FetchedEvent(
                id=generate_event_id("BBC", title, event_date),
                title=title,
                summary=summary,
                event_type=infer_event_type(text_blob),
                country_code=country_code,
                latitude=lat,
                longitude=lon,
                event_date=event_date,
                source="BBC",
                source_url=entry.get('link'),
                confidence="high",
                tags=["BBC", "news"],
            ))
            count += 1
    
    except Exception as e:
        print(f"[BBC] Error fetching events: {e}")
    
    return events


def fetch_ap_events() -> list[FetchedEvent]:
    """Fetch and normalize events from AP News RSS."""
    events = []
    
    try:
        feed = feedparser.parse(AP_RSS)
        count = 0
        
        for entry in feed.entries:
            if count >= MAX_EVENTS_PER_SOURCE:
                break
            
            text_blob = f"{entry.get('title', '')} {entry.get('summary', '')}"
            
            if not contains_keywords(text_blob):
                continue
            
            title = entry.get('title', 'AP Event')
            summary = entry.get('summary', '')[:500]
            event_date = parse_rss_datetime(entry)
            
            country_code = infer_country_code(text_blob)
            lat, lon = get_coordinates(country_code, text_blob)
            
            events.append(FetchedEvent(
                id=generate_event_id("AP", title, event_date),
                title=title,
                summary=summary,
                event_type=infer_event_type(text_blob),
                country_code=country_code,
                latitude=lat,
                longitude=lon,
                event_date=event_date,
                source="AP",
                source_url=entry.get('link'),
                confidence="high",
                tags=["AP", "news"],
            ))
            count += 1
    
    except Exception as e:
        print(f"[AP] Error fetching events: {e}")
    
    return events


# =============================================================================
# Parallel Fetcher
# =============================================================================

def fetch_all_events_parallel(sources: list[str] = None) -> tuple[list[FetchedEvent], dict[str, int]]:
    """
    Fetch events from all sources in parallel.
    
    Args:
        sources: List of source names to fetch from. If None, fetches from all.
                 Valid values: "GDELT", "Reuters", "BBC", "AP"
    
    Returns:
        Tuple of (list of all fetched events, dict of counts per source)
    """
    if sources is None:
        sources = ["GDELT", "Reuters", "BBC", "AP"]
    
    fetcher_map = {
        "GDELT": fetch_gdelt_events,
        "Reuters": fetch_reuters_events,
        "BBC": fetch_bbc_events,
        "AP": fetch_ap_events,
    }
    
    all_events = []
    source_counts = {}
    
    # Use ThreadPoolExecutor for parallel fetching
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for source in sources:
            if source in fetcher_map:
                future = executor.submit(fetcher_map[source])
                futures[future] = source
        
        for future in as_completed(futures):
            source = futures[future]
            try:
                events = future.result()
                all_events.extend(events)
                source_counts[source] = len(events)
            except Exception as e:
                print(f"[{source}] Fetch failed: {e}")
                source_counts[source] = 0
    
    # Deduplicate by title similarity (simple hash-based)
    seen_titles = set()
    unique_events = []
    for event in all_events:
        title_hash = hashlib.md5(event.title.lower().encode()).hexdigest()[:8]
        if title_hash not in seen_titles:
            seen_titles.add(title_hash)
            unique_events.append(event)
    
    # Sort by date (newest first)
    unique_events.sort(key=lambda e: e.event_date, reverse=True)
    
    return unique_events, source_counts


def convert_to_news_events(fetched_events: list[FetchedEvent]) -> list:
    """
    Convert FetchedEvent objects to NewsEvent objects.
    
    Returns list of NewsEvent objects compatible with the news feed.
    """
    from app.ui.news.news_feed import NewsEvent, EventType, ConfidenceLevel
    
    news_events = []
    
    for fe in fetched_events:
        # Map event type
        try:
            event_type = EventType(fe.event_type)
        except ValueError:
            event_type = EventType.OTHER
        
        # Map confidence
        try:
            confidence = ConfidenceLevel(fe.confidence)
        except ValueError:
            confidence = ConfidenceLevel.MEDIUM
        
        # Skip events without valid coordinates
        if fe.latitude == 0.0 and fe.longitude == 0.0:
            continue
        
        news_events.append(NewsEvent(
            id=fe.id,
            title=fe.title,
            summary=fe.summary,
            event_type=event_type,
            country_code=fe.country_code,
            latitude=fe.latitude,
            longitude=fe.longitude,
            event_date=fe.event_date,
            source=fe.source,
            source_url=fe.source_url,
            confidence=confidence,
            weapon_system=fe.weapon_system,
            range_km=fe.range_km,
            tags=fe.tags or [],
        ))
    
    return news_events


# =============================================================================
# Main Entry Point
# =============================================================================

def fetch_live_events(sources: list[str] = None) -> tuple[list, dict[str, int]]:
    """
    Main entry point for fetching live events.
    
    Args:
        sources: Optional list of sources to fetch from
        
    Returns:
        Tuple of (list of NewsEvent objects, dict of counts per source)
    """
    fetched, counts = fetch_all_events_parallel(sources)
    news_events = convert_to_news_events(fetched)
    return news_events, counts


if __name__ == "__main__":
    # Test mode
    print("[*] Fetching live events from all sources...")
    events, counts = fetch_live_events()
    print(f"\n[*] Source counts: {counts}")
    print(f"[*] Total unique events: {len(events)}")
    
    for event in events[:5]:
        print(f"\n- {event.title}")
        print(f"  Source: {event.source}")
        print(f"  Date: {event.event_date}")
        print(f"  Location: {event.country_code} ({event.latitude}, {event.longitude})")
