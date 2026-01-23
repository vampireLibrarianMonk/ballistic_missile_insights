"""
News filters component for ORRG.
Provides filter controls for the news feed.
"""

import streamlit as st

from app.data.loaders import get_data_service
from app.ui.layout.global_state import get_news_filters, set_news_filters
from app.ui.news.news_feed import EventType


def render_news_filters() -> None:
    """Render news filter controls in the sidebar."""
    st.sidebar.markdown("### 🔍 News Filters")
    
    data_service = get_data_service()
    current_filters = get_news_filters()
    
    # Country filter
    countries = data_service.get_country_list()
    selected_countries = st.sidebar.multiselect(
        "Countries",
        options=countries,
        default=current_filters.get("countries", []),
        key="news_filter_countries",
        help="Filter news events by country",
    )
    
    # Event type filter
    event_types = [e.value for e in EventType]
    event_type_labels = {
        "test": "🧪 Test",
        "launch": "🚀 Launch",
        "statement": "📢 Statement",
        "exercise": "🎯 Exercise",
        "development": "🔬 Development",
        "deployment": "📍 Deployment",
        "other": "📰 Other",
    }
    
    selected_event_types = st.sidebar.multiselect(
        "Event Types",
        options=event_types,
        format_func=lambda x: event_type_labels.get(x, x),
        default=current_filters.get("event_types", []),
        key="news_filter_event_types",
    )
    
    # Time window filter
    time_options = {
        None: "All Time",
        7: "Last 7 Days",
        30: "Last 30 Days",
        90: "Last 90 Days",
        365: "Last Year",
    }
    
    selected_time = st.sidebar.selectbox(
        "Time Window",
        options=list(time_options.keys()),
        format_func=lambda x: time_options[x],
        index=0,
        key="news_filter_time",
    )
    
    # Range classification filter
    range_options = ["CRBM", "SRBM", "MRBM", "IRBM", "ICBM"]
    selected_ranges = st.sidebar.multiselect(
        "Range Classification",
        options=range_options,
        default=current_filters.get("range_classifications", []),
        key="news_filter_ranges",
    )
    
    # Update filters
    new_filters = {
        "countries": selected_countries,
        "event_types": selected_event_types,
        "time_window": selected_time,
        "range_classifications": selected_ranges,
    }
    
    if new_filters != current_filters:
        set_news_filters(new_filters)
    
    # Reset button
    if st.sidebar.button("🔄 Reset Filters", key="news_reset_filters"):
        set_news_filters({
            "countries": [],
            "event_types": [],
            "time_window": None,
            "range_classifications": [],
        })
        st.rerun()
    
    st.sidebar.divider()
