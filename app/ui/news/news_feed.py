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
                        # Handle various date formats
                        if "T" in date_str:
                            event_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
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


def create_sample_events() -> list[NewsEvent]:
    """Create sample news events for demonstration - realistic simulated events."""
    from uuid import uuid4
    
    return [
        # North Korea events
        NewsEvent(
            id=str(uuid4()),
            title="North Korea Launches MRBM into Sea of Japan",
            summary="DPRK conducted a test of what appears to be a medium-range ballistic missile from the Sunan area. The missile traveled approximately 800 km before landing in the Sea of Japan outside Japan's exclusive economic zone.",
            event_type=EventType.LAUNCH,
            country_code="PRK",
            latitude=39.0392,
            longitude=125.7625,
            event_date=datetime(2026, 1, 20, 10, 30),
            source="Reuters",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Hwasong-12",
            range_km=4500,
            tags=["MRBM", "launch", "Hwasong", "Sea of Japan"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="DPRK Tests New Solid-Fuel ICBM",
            summary="North Korea successfully tested a new solid-fuel intercontinental ballistic missile, marking a significant advancement in their nuclear delivery capabilities. State media claimed the test demonstrated 'rapid nuclear counterattack capability.'",
            event_type=EventType.TEST,
            country_code="PRK",
            latitude=40.0356,
            longitude=127.5101,
            event_date=datetime(2026, 1, 15, 6, 45),
            source="KCNA",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Hwasong-18",
            range_km=15000,
            tags=["ICBM", "solid-fuel", "test", "strategic"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="North Korea Fires Multiple Short-Range Missiles",
            summary="DPRK launched four short-range ballistic missiles from the Wonsan area toward the East Sea during military exercises. South Korean military is closely monitoring the situation.",
            event_type=EventType.LAUNCH,
            country_code="PRK",
            latitude=39.1500,
            longitude=127.4500,
            event_date=datetime(2026, 1, 8, 7, 15),
            source="AP",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="KN-23",
            range_km=600,
            tags=["SRBM", "multiple launch", "Wonsan"],
        ),
        
        # Iran events
        NewsEvent(
            id=str(uuid4()),
            title="Iranian Military Statement on Missile Readiness",
            summary="Iranian military officials announced enhanced missile readiness in response to regional tensions. The IRGC Aerospace Force commander stated that Iran's ballistic missile capabilities are at their 'highest level of preparedness.'",
            event_type=EventType.STATEMENT,
            country_code="IRN",
            latitude=35.6892,
            longitude=51.3890,
            event_date=datetime(2026, 1, 19, 14, 0),
            source="IRNA",
            confidence=ConfidenceLevel.MEDIUM,
            tags=["statement", "readiness", "IRGC"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="Iran Conducts Space Launch from Semnan",
            summary="Iran's Islamic Revolutionary Guard Corps launched a satellite carrier rocket from the Imam Khomeini Space Center. The launch is believed to be testing technologies applicable to long-range ballistic missiles.",
            event_type=EventType.LAUNCH,
            country_code="IRN",
            latitude=35.2347,
            longitude=53.9210,
            event_date=datetime(2026, 1, 12, 4, 30),
            source="BBC",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Qased SLV",
            range_km=1500,
            tags=["SLV", "space launch", "Semnan", "IRGC"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="Iran Tests Hypersonic Missile 'Fattah-2'",
            summary="Iran announced the successful test of its Fattah-2 hypersonic ballistic missile, claiming it can evade all existing missile defense systems. Western analysts are evaluating the claims.",
            event_type=EventType.TEST,
            country_code="IRN",
            latitude=32.4917,
            longitude=51.6694,
            event_date=datetime(2026, 1, 5, 9, 0),
            source="GDELT",
            confidence=ConfidenceLevel.MEDIUM,
            weapon_system="Fattah-2",
            range_km=1400,
            tags=["hypersonic", "MRBM", "test", "Fattah"],
        ),
        
        # Russia events
        NewsEvent(
            id=str(uuid4()),
            title="Russian Strategic Exercise Grom-2026",
            summary="Russia conducted scheduled strategic forces exercise 'Grom-2026' with multiple ICBM and SLBM test launches. The exercise involved all three legs of Russia's nuclear triad.",
            event_type=EventType.EXERCISE,
            country_code="RUS",
            latitude=55.7558,
            longitude=37.6173,
            event_date=datetime(2026, 1, 18, 8, 0),
            source="TASS",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Topol-M",
            range_km=11000,
            tags=["ICBM", "exercise", "strategic", "nuclear triad"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="Russia Deploys Iskander Missiles to Belarus",
            summary="Satellite imagery confirms additional Iskander-M tactical missile systems have been deployed to Belarus near the Polish border, raising concerns among NATO allies.",
            event_type=EventType.DEPLOYMENT,
            country_code="RUS",
            latitude=53.9006,
            longitude=27.5590,
            event_date=datetime(2026, 1, 10, 12, 0),
            source="Reuters",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Iskander-M",
            range_km=500,
            tags=["SRBM", "deployment", "Belarus", "tactical"],
        ),
        
        # China events
        NewsEvent(
            id=str(uuid4()),
            title="China Tests DF-27 Hypersonic Glide Vehicle",
            summary="China's People's Liberation Army Rocket Force conducted a test of the DF-27 hypersonic glide vehicle over the South China Sea. The test demonstrates advancing Chinese hypersonic capabilities.",
            event_type=EventType.TEST,
            country_code="CHN",
            latitude=19.9069,
            longitude=110.1690,
            event_date=datetime(2026, 1, 16, 3, 45),
            source="GDELT",
            confidence=ConfidenceLevel.MEDIUM,
            weapon_system="DF-27",
            range_km=8000,
            tags=["hypersonic", "HGV", "PLARF", "South China Sea"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="PLA Rocket Force Conducts Live-Fire Exercise",
            summary="China's PLA Rocket Force conducted large-scale live-fire exercises in western China, launching multiple DF-21D anti-ship ballistic missiles. The exercise comes amid heightened tensions in the Taiwan Strait.",
            event_type=EventType.EXERCISE,
            country_code="CHN",
            latitude=40.4167,
            longitude=93.5000,
            event_date=datetime(2026, 1, 3, 7, 30),
            source="BBC",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="DF-21D",
            range_km=1500,
            tags=["MRBM", "anti-ship", "exercise", "PLARF"],
        ),
        
        # India events
        NewsEvent(
            id=str(uuid4()),
            title="India Successfully Tests Agni-V ICBM",
            summary="India's Defence Research and Development Organisation (DRDO) successfully conducted a test of the Agni-V intercontinental ballistic missile from Abdul Kalam Island. The test validates India's nuclear deterrent capability.",
            event_type=EventType.TEST,
            country_code="IND",
            latitude=20.7500,
            longitude=87.1000,
            event_date=datetime(2026, 1, 14, 10, 15),
            source="AP",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Agni-V",
            range_km=5500,
            tags=["ICBM", "test", "DRDO", "nuclear deterrent"],
        ),
        
        # Pakistan events
        NewsEvent(
            id=str(uuid4()),
            title="Pakistan Tests Shaheen-III MRBM",
            summary="Pakistan's Strategic Plans Division conducted a successful test of the Shaheen-III medium-range ballistic missile. The test was part of a scheduled training exercise for the strategic forces.",
            event_type=EventType.TEST,
            country_code="PAK",
            latitude=28.3800,
            longitude=68.1100,
            event_date=datetime(2026, 1, 11, 5, 45),
            source="Reuters",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Shaheen-III",
            range_km=2750,
            tags=["MRBM", "test", "Shaheen", "SPD"],
        ),
        
        # Combat use events (simulated - Houthi/Yemen)
        NewsEvent(
            id=str(uuid4()),
            title="Houthi Forces Launch Missiles at Red Sea Shipping",
            summary="Yemen's Houthi forces claimed responsibility for launching anti-ship ballistic missiles at commercial vessels in the Red Sea. The attack disrupted international shipping routes and prompted military responses.",
            event_type=EventType.LAUNCH,
            country_code="YEM",
            latitude=15.3694,
            longitude=44.1910,
            event_date=datetime(2026, 1, 17, 16, 30),
            source="AP",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Anti-ship ballistic missile",
            range_km=300,
            tags=["combat", "anti-ship", "Houthi", "Red Sea"],
        ),
        NewsEvent(
            id=str(uuid4()),
            title="Houthi Statement Threatens Expanded Attacks",
            summary="Houthi military spokesperson announced plans to expand missile attacks against vessels bound for Israeli ports. The statement warned all shipping companies to avoid Israeli-linked vessels.",
            event_type=EventType.STATEMENT,
            country_code="YEM",
            latitude=15.3556,
            longitude=44.2067,
            event_date=datetime(2026, 1, 6, 11, 0),
            source="GDELT",
            confidence=ConfidenceLevel.MEDIUM,
            tags=["statement", "threat", "Houthi", "shipping"],
        ),
        
        # Israel event
        NewsEvent(
            id=str(uuid4()),
            title="Israel Conducts Arrow-3 Intercept Test",
            summary="Israel successfully tested its Arrow-3 exoatmospheric missile defense system, intercepting a target simulating a long-range ballistic missile threat. The test was conducted in cooperation with the United States.",
            event_type=EventType.TEST,
            country_code="ISR",
            latitude=31.8900,
            longitude=34.8100,
            event_date=datetime(2026, 1, 9, 14, 0),
            source="Reuters",
            confidence=ConfidenceLevel.HIGH,
            weapon_system="Arrow-3",
            range_km=2400,
            tags=["missile defense", "test", "Arrow", "intercept"],
        ),
    ]
