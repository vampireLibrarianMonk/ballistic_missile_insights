"""
News feed component for ORRG.
Displays news events related to missile and weapon system activities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

import streamlit as st

from app.ui.layout.global_state import (
    get_news_filters,
    set_selected_news_event,
    is_analyst_mode,
)


class EventType(Enum):
    """Types of news events."""
    TEST = "test"
    LAUNCH = "launch"
    STATEMENT = "statement"
    EXERCISE = "exercise"
    DEVELOPMENT = "development"
    DEPLOYMENT = "deployment"
    OTHER = "other"


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


def create_sample_events() -> list[NewsEvent]:
    """Create sample news events for demonstration."""
    from uuid import uuid4
    
    return [
        NewsEvent(
            id=str(uuid4()),
            title="North Korea Missile Test",
            summary="DPRK conducted a test of what appears to be a medium-range ballistic missile from the Sunan area.",
            event_type=EventType.TEST,
            country_code="PRK",
            latitude=39.0392,
            longitude=125.7625,
            event_date=datetime(2026, 1, 20, 10, 30),
            source="KCNA",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Hwasong-12",
            range_km=4500,
            tags=["MRBM", "test", "Hwasong"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="Iranian Military Statement",
            summary="Iranian military officials announced enhanced missile readiness in response to regional tensions.",
            event_type=EventType.STATEMENT,
            country_code="IRN",
            latitude=35.6892,
            longitude=51.3890,
            event_date=datetime(2026, 1, 19, 14, 0),
            source="IRNA",
            confidence=ConfidenceLevel.MEDIUM,
            tags=["statement", "readiness"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="Russian Strategic Exercise",
            summary="Russia conducted scheduled strategic forces exercise with multiple missile tests.",
            event_type=EventType.EXERCISE,
            country_code="RUS",
            latitude=55.7558,
            longitude=37.6173,
            event_date=datetime(2026, 1, 18, 8, 0),
            source="TASS",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Topol-M",
            range_km=11000,
            tags=["ICBM", "exercise", "strategic"],
        ),
    ]
