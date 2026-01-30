"""
News feed component for ORRG.
Displays news events related to missile and weapon system activities.
Supports JSON file loading for event ingestion from multiple sources.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import json

import streamlit as st

from app.ui.layout.global_state import (
    get_news_filters,
    set_selected_news_event,
    is_analyst_mode,
)


class EventType(Enum):
    """Types of news events matching the ORRG design spec."""
    LAUNCH = "launch"           # ● Launch Event
    EXERCISE = "exercise"       # ▲ Missile Exercise / Test
    DEPLOYMENT = "deployment"   # ■ Deployment / Readiness Activity
    NUCLEAR = "nuclear"         # ◆ Nuclear Test
    TEST = "test"               # ◇ Other Significant Strategic Testing
    STATEMENT = "statement"     # Policy/Statement
    DEVELOPMENT = "development" # Development activity
    OTHER = "other"             # Other


class WeaponClass(Enum):
    """Weapon system classification by range."""
    CRBM = "CRBM"   # Close-Range Ballistic Missile (<300 km)
    SRBM = "SRBM"   # Short-Range Ballistic Missile (300-1000 km)
    MRBM = "MRBM"   # Medium-Range Ballistic Missile (1000-3000 km)
    IRBM = "IRBM"   # Intermediate-Range Ballistic Missile (3000-5500 km)
    ICBM = "ICBM"   # Intercontinental Ballistic Missile (>5500 km)
    UNKNOWN = "unknown"


class NewsSource(Enum):
    """News sources for event aggregation."""
    GDELT = "GDELT"
    BBC = "BBC"
    AP = "AP"
    REUTERS = "Reuters"
    OTHER = "Other"


class ConfidenceLevel(Enum):
    """Confidence levels for event attribution."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCONFIRMED = "unconfirmed"


@dataclass
class NewsEvent:
    """Represents a news event for display."""
    id: str
    title: str
    summary: str
    event_type: EventType
    country_code: str
    latitude: float
    longitude: float
    event_date: datetime
    source: str
    source_url: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    weapon_system: Optional[str] = None
    range_km: Optional[float] = None
    tags: list[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


def get_event_type_icon(event_type: EventType) -> str:
    """Get emoji icon for event type."""
    icons = {
        EventType.TEST: "🧪",
        EventType.LAUNCH: "🚀",
        EventType.STATEMENT: "📢",
        EventType.EXERCISE: "🎯",
        EventType.DEVELOPMENT: "🔬",
        EventType.DEPLOYMENT: "📍",
        EventType.OTHER: "📰",
    }
    return icons.get(event_type, "📰")


def get_confidence_badge(confidence: ConfidenceLevel) -> str:
    """Get styled badge HTML for confidence level."""
    colors = {
        ConfidenceLevel.HIGH: "#28a745",
        ConfidenceLevel.MEDIUM: "#ffc107",
        ConfidenceLevel.LOW: "#fd7e14",
        ConfidenceLevel.UNCONFIRMED: "#dc3545",
    }
    color = colors.get(confidence, "#6c757d")
    return f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 10px;
        font-weight: bold;
    ">{confidence.value.upper()}</span>
    """


def render_news_event_card(event: NewsEvent) -> None:
    """Render a single news event card."""
    icon = get_event_type_icon(event.event_type)
    
    with st.container():
        # Header with icon and title
        col1, col2 = st.columns([0.9, 0.1])
        
        with col1:
            st.markdown(f"**{icon} {event.title}**")
        
        with col2:
            if st.button("📍", key=f"locate_{event.id}", help="Show on map"):
                set_selected_news_event({
                    "id": event.id,
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "title": event.title,
                })
                st.rerun()
        
        # Summary
        st.caption(event.summary[:200] + "..." if len(event.summary) > 200 else event.summary)
        
        # Metadata row
        meta_col1, meta_col2 = st.columns(2)
        
        with meta_col1:
            st.caption(f"📅 {event.event_date.strftime('%Y-%m-%d')}")
            st.caption(f"📰 {event.source}")
        
        with meta_col2:
            if event.weapon_system:
                st.caption(f"🎯 {event.weapon_system}")
            if event.range_km:
                st.caption(f"📏 {event.range_km:,.0f} km")
        
        # Analyst mode: show confidence and coordinates
        if is_analyst_mode():
            st.markdown(
                get_confidence_badge(event.confidence),
                unsafe_allow_html=True,
            )
            st.caption(f"📍 {event.latitude:.4f}, {event.longitude:.4f}")
        
        st.divider()


def render_news_feed(events: list[NewsEvent]) -> None:
    """
    Render the news feed panel.
    
    Args:
        events: List of NewsEvent objects to display
    """
    st.sidebar.markdown("### 📰 News Feed")
    
    if not events:
        st.sidebar.info("No news events to display.")
        return
    
    # Apply filters
    filters = get_news_filters()
    filtered_events = events
    
    if filters.get("countries"):
        filtered_events = [e for e in filtered_events if e.country_code in filters["countries"]]
    
    if filters.get("event_types"):
        filtered_events = [e for e in filtered_events if e.event_type.value in filters["event_types"]]
    
    if filters.get("time_window"):
        # Filter by time window (days)
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=filters["time_window"])
        filtered_events = [e for e in filtered_events if e.event_date >= cutoff]
    
    # Sort by date (newest first)
    filtered_events = sorted(filtered_events, key=lambda e: e.event_date, reverse=True)
    
    # Display count
    st.sidebar.caption(f"Showing {len(filtered_events)} of {len(events)} events")
    
    # Render events
    for event in filtered_events[:20]:  # Limit to 20 most recent
        with st.sidebar:
            render_news_event_card(event)


# =============================================================================
# JSON Event Loading Functions
# =============================================================================

def load_events_from_json(json_content: str) -> tuple[list[NewsEvent], list[str]]:
    """
    Load news events from JSON content.
    
    Expected JSON format:
    {
        "events": [
            {
                "id": "unique-id",
                "title": "Event Title",
                "summary": "Event summary...",
                "event_type": "launch|exercise|deployment|nuclear|test|statement|development|other",
                "country_code": "ISO 3-letter code",
                "latitude": 39.0,
                "longitude": 125.0,
                "event_date": "2026-01-20T10:30:00Z",
                "source": "GDELT|BBC|AP|Reuters|Other",
                "source_url": "https://...",
                "confidence": "high|medium|low|unconfirmed",
                "weapon_class": "CRBM|SRBM|MRBM|IRBM|ICBM|unknown",
                "weapon_system": "System Name",
                "range_km": 4500,
                "tags": ["tag1", "tag2"]
            }
        ]
    }
    
    Args:
        json_content: JSON string content
        
    Returns:
        Tuple of (list of NewsEvent objects, list of error messages)
    """
    from uuid import uuid4
    
    events = []
    errors = []
    
    try:
        data = json.loads(json_content)
        
        # Handle both array and object with "events" key
        if isinstance(data, list):
            event_list = data
        elif isinstance(data, dict):
            event_list = data.get("events", data.get("articles", []))
        else:
            errors.append("Invalid JSON structure: expected array or object with 'events' key")
            return [], errors
        
        for i, event_data in enumerate(event_list):
            try:
                # Parse event type
                event_type_str = event_data.get("event_type", "other").lower()
                try:
                    event_type = EventType(event_type_str)
                except ValueError:
                    event_type = EventType.OTHER
                
                # Parse confidence
                confidence_str = event_data.get("confidence", "medium").lower()
                try:
                    confidence = ConfidenceLevel(confidence_str)
                except ValueError:
                    confidence = ConfidenceLevel.MEDIUM
                
                # Parse event date
                date_str = event_data.get("event_date", event_data.get("date", ""))
                if date_str:
                    try:
                        # Handle various date formats - always create offset-naive datetime
                        if "T" in date_str:
                            # Remove timezone info to create offset-naive datetime
                            date_str_clean = date_str.replace("Z", "").replace("+00:00", "")
                            # Handle potential timezone offset like +05:00
                            if "+" in date_str_clean:
                                date_str_clean = date_str_clean.split("+")[0]
                            elif date_str_clean.count("-") > 2:
                                # Could be negative offset like -05:00
                                parts = date_str_clean.rsplit("-", 1)
                                if ":" in parts[-1]:
                                    date_str_clean = parts[0]
                            event_date = datetime.fromisoformat(date_str_clean)
                        else:
                            event_date = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        event_date = datetime.now()
                else:
                    event_date = datetime.now()
                
                # Ensure required fields exist
                if "latitude" not in event_data or "longitude" not in event_data:
                    errors.append(f"Event {i+1}: Missing latitude or longitude")
                    continue
                
                if "title" not in event_data:
                    errors.append(f"Event {i+1}: Missing title")
                    continue
                
                event = NewsEvent(
                    id=event_data.get("id", str(uuid4())),
                    title=event_data["title"],
                    summary=event_data.get("summary", event_data.get("description", "")),
                    event_type=event_type,
                    country_code=event_data.get("country_code", event_data.get("country", "UNK")),
                    latitude=float(event_data["latitude"]),
                    longitude=float(event_data["longitude"]),
                    event_date=event_date,
                    source=event_data.get("source", "Unknown"),
                    source_url=event_data.get("source_url", event_data.get("url")),
                    confidence=confidence,
                    weapon_system=event_data.get("weapon_system"),
                    range_km=event_data.get("range_km"),
                    tags=event_data.get("tags", []),
                )
                events.append(event)
                
            except Exception as e:
                errors.append(f"Event {i+1}: Parse error - {str(e)}")
        
    except json.JSONDecodeError as e:
        errors.append(f"JSON parse error: {str(e)}")
    
    return events, errors


def init_news_events_state() -> None:
    """Initialize session state for news events."""
    if "news_events" not in st.session_state:
        st.session_state.news_events = []
    if "news_events_loaded" not in st.session_state:
        st.session_state.news_events_loaded = False
    if "news_events_source" not in st.session_state:
        st.session_state.news_events_source = None


def get_loaded_events() -> list[NewsEvent]:
    """Get currently loaded news events from session state."""
    init_news_events_state()
    return st.session_state.news_events


def set_loaded_events(events: list[NewsEvent], source: str = None) -> None:
    """Set loaded events in session state."""
    init_news_events_state()
    st.session_state.news_events = events
    st.session_state.news_events_loaded = len(events) > 0
    st.session_state.news_events_source = source


def load_sample_events_from_file() -> tuple[list[NewsEvent], list[str]]:
    """
    Load sample news events from the JSON file in app/data/events/.
    
    Returns:
        Tuple of (list of NewsEvent objects, list of error messages)
    """
    from pathlib import Path
    
    # Path to the sample events JSON file
    sample_file = Path(__file__).parent.parent.parent / "data" / "events" / "sample_events.json"
    
    if not sample_file.exists():
        return [], [f"Sample events file not found: {sample_file}"]
    
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            json_content = f.read()
        return load_events_from_json(json_content)
    except Exception as e:
        return [], [f"Error reading sample events file: {str(e)}"]


def create_sample_events() -> list[NewsEvent]:
    """
    Create sample news events for demonstration.
    Loads events from the sample_events.json file in app/data/events/.
    Falls back to empty list if file cannot be loaded.
    """
    events, errors = load_sample_events_from_file()
    
    if errors:
        # Log errors but don't fail - return empty list as fallback
        import logging
        for error in errors:
            logging.warning(f"Sample events loading: {error}")
    
    return events
