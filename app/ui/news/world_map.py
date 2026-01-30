"""
News world map component for ORRG.
Renders news events on the world map for situational awareness.
"""

import streamlit as st
import pydeck as pdk

from app.ui.layout.global_state import get_selected_news_event, get_map_style
from app.ui.news.news_feed import NewsEvent, EventType


def get_event_color(event_type: EventType) -> list[int]:
    """Get RGB color for event type matching the ORRG design spec."""
    colors = {
        EventType.LAUNCH: [255, 0, 0],        # Red - ● Launch Event
        EventType.EXERCISE: [255, 193, 7],    # Yellow - ▲ Missile Exercise / Test
        EventType.DEPLOYMENT: [76, 175, 80],  # Green - ■ Deployment / Readiness
        EventType.NUCLEAR: [255, 0, 255],     # Magenta - ◆ Nuclear Test
        EventType.TEST: [255, 87, 51],        # Orange-red - ◇ Other Strategic Testing
        EventType.STATEMENT: [66, 135, 245],  # Blue - Policy/Statement
        EventType.DEVELOPMENT: [156, 39, 176], # Purple - Development
        EventType.OTHER: [158, 158, 158],     # Gray - Other
    }
    return colors.get(event_type, [100, 100, 100])


def render_news_world_map(events: list[NewsEvent]) -> None:
    """
    Render news events on a world map.
    
    Args:
        events: List of NewsEvent objects to display
    """
    # Get map style
    map_style = get_map_style()
    if map_style == "dark":
        map_style_url = "mapbox://styles/mapbox/dark-v10"
    else:
        map_style_url = "mapbox://styles/mapbox/light-v10"
    
    # Get selected event for highlighting
    selected = get_selected_news_event()
    
    # Prepare event data for layers
    event_data = []
    for event in events:
        color = get_event_color(event.event_type)
        
        # Highlight selected event
        if selected and selected.get("id") == event.id:
            radius = 50000  # Larger radius for selected
            color = [255, 255, 0]  # Yellow highlight
        else:
            radius = 30000
        
        event_data.append({
            "id": event.id,
            "title": event.title,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "color": color,
            "radius": radius,
            "event_type": event.event_type.value,
            "source": event.source,
            "date": event.event_date.strftime("%Y-%m-%d"),
        })
    
    # Create scatter plot layer for events
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=event_data,
        get_position=["longitude", "latitude"],
        get_color="color",
        get_radius="radius",
        pickable=True,
        opacity=0.7,
        stroked=True,
        filled=True,
        line_width_min_pixels=2,
    )
    
    # Determine view state
    if selected:
        view_state = pdk.ViewState(
            latitude=selected["latitude"],
            longitude=selected["longitude"],
            zoom=5,
            pitch=0,
        )
    else:
        # Default global view
        view_state = pdk.ViewState(
            latitude=30,
            longitude=60,
            zoom=1.5,
            pitch=0,
        )
    
    # Create tooltip
    tooltip = {
        "html": """
        <b>{title}</b><br/>
        📅 {date}<br/>
        📰 {source}<br/>
        🎯 {event_type}
        """,
        "style": {
            "backgroundColor": "steelblue",
            "color": "white",
        },
    }
    
    # Create deck
    deck = pdk.Deck(
        layers=[scatter_layer],
        initial_view_state=view_state,
        map_style=map_style_url,
        tooltip=tooltip,
    )
    
    # Render
    st.pydeck_chart(deck, width="stretch")


def render_news_event_markers(events: list[NewsEvent]) -> list[dict]:
    """
    Convert news events to marker data for world map overlay.
    
    Args:
        events: List of NewsEvent objects
        
    Returns:
        List of marker dictionaries for pydeck layer
    """
    markers = []
    for event in events:
        markers.append({
            "latitude": event.latitude,
            "longitude": event.longitude,
            "title": event.title,
            "color": get_event_color(event.event_type),
            "event_type": event.event_type.value,
        })
    return markers
