"""
Open Range Ring Generator (ORRG)
A fully open-source, web-based geodesic range ring analysis platform.

This is the main Streamlit application entry point.
"""

import sys
from pathlib import Path

# Add the project root to the Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

# Page configuration must be first Streamlit command
st.set_page_config(
    page_title="Open Range Ring Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Now import app modules
from app.ui.layout.global_state import init_session_state, get_map_style, get_news_filters, set_news_filters
from app.ui.layout.header import render_header, render_sidebar_header
from app.ui.layout.mode_toggle import render_settings_panel
from app.ui.tools.tool_components import render_all_tools
from app.rendering.pydeck_adapter import render_world_map
from app.ui.news.news_feed import (
    NewsEvent, EventType, ConfidenceLevel, WeaponClass, NewsSource,
    get_event_type_icon, get_confidence_badge,
    load_events_from_json, init_news_events_state, get_loaded_events, set_loaded_events,
    create_sample_events, is_analyst_mode,
)
from app.ui.news.world_map import get_event_color


def render_news_filter_panel() -> dict:
    """
    Render the news filter panel in an expander.
    
    Returns:
        Dictionary of current filter settings
    """
    from datetime import datetime, timedelta
    
    filters = get_news_filters()
    
    with st.expander("🔍 Event Filters", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # Country filter (multi-select)
            country_options = ["PRK", "IRN", "RUS", "CHN", "USA", "PAK", "IND", "ISR"]
            selected_countries = st.multiselect(
                "Countries",
                options=country_options,
                default=filters.get("countries", []),
                key="news_filter_countries_main",
            )
            
            # Event type filter
            event_type_options = [e.value for e in EventType]
            event_type_labels = {
                "launch": "● Launch Event",
                "exercise": "▲ Exercise / Test",
                "deployment": "■ Deployment",
                "nuclear": "◆ Nuclear Test",
                "test": "◇ Strategic Test",
                "statement": "📢 Statement",
                "development": "🔬 Development",
                "other": "📰 Other",
            }
            selected_event_types = st.multiselect(
                "Event Types",
                options=event_type_options,
                format_func=lambda x: event_type_labels.get(x, x),
                default=filters.get("event_types", []),
                key="news_filter_event_types_main",
            )
        
        with col2:
            # Weapon class filter
            weapon_class_options = [w.value for w in WeaponClass if w != WeaponClass.UNKNOWN]
            selected_weapon_classes = st.multiselect(
                "Weapon Class",
                options=weapon_class_options,
                default=filters.get("weapon_classes", []),
                key="news_filter_weapon_classes_main",
            )
            
            # Source filter
            source_options = [s.value for s in NewsSource]
            selected_sources = st.multiselect(
                "Sources",
                options=source_options,
                default=filters.get("sources", []),
                key="news_filter_sources_main",
            )
        
        # Date range filter
        col3, col4 = st.columns(2)
        with col3:
            date_from = st.date_input(
                "From Date",
                value=filters.get("date_from", datetime.now() - timedelta(days=30)),
                key="news_filter_date_from",
            )
        with col4:
            date_to = st.date_input(
                "To Date",
                value=filters.get("date_to", datetime.now()),
                key="news_filter_date_to",
            )
        
        # Reset filters button
        if st.button("🔄 Reset Filters", key="news_reset_filters_main"):
            set_news_filters({})
            st.rerun()
    
    # Build and return filters
    new_filters = {
        "countries": selected_countries,
        "event_types": selected_event_types,
        "weapon_classes": selected_weapon_classes,
        "sources": selected_sources,
        "date_from": date_from,
        "date_to": date_to,
    }
    
    # Update global filters
    set_news_filters(new_filters)
    
    return new_filters


def apply_filters_to_events(events: list[NewsEvent], filters: dict) -> list[NewsEvent]:
    """Apply filters to event list."""
    from datetime import datetime
    
    filtered = events
    
    if filters.get("countries"):
        filtered = [e for e in filtered if e.country_code in filters["countries"]]
    
    if filters.get("event_types"):
        filtered = [e for e in filtered if e.event_type.value in filters["event_types"]]
    
    if filters.get("sources"):
        filtered = [e for e in filtered if e.source in filters["sources"]]
    
    if filters.get("date_from"):
        date_from = datetime.combine(filters["date_from"], datetime.min.time())
        filtered = [e for e in filtered if e.event_date >= date_from]
    
    if filters.get("date_to"):
        date_to = datetime.combine(filters["date_to"], datetime.max.time())
        filtered = [e for e in filtered if e.event_date <= date_to]
    
    # Sort by date (newest first)
    return sorted(filtered, key=lambda e: e.event_date, reverse=True)


def render_event_collection_feed(events: list[NewsEvent]) -> None:
    """Render the live event collection feed below the map."""
    st.markdown("### 📋 Live Event Collection Feed")
    
    if not events:
        st.info("No events match the current filters. Try adjusting filter settings or loading event data.")
        return
    
    st.caption(f"Showing {len(events)} event(s), sorted by date (newest first)")
    
    # Render events in expandable cards
    for event in events[:50]:  # Limit to 50 events
        icon = get_event_type_icon(event.event_type)
        
        with st.container():
            col1, col2, col3 = st.columns([0.05, 0.8, 0.15])
            
            with col1:
                st.markdown(f"**{icon}**")
            
            with col2:
                st.markdown(f"**{event.event_date.strftime('%Y-%m-%d')}** | **{event.event_type.value.title()}** | Country: **{event.country_code}** | Source: **{event.source}**")
                st.caption(event.summary[:250] + "..." if len(event.summary) > 250 else event.summary)
                
                # Tags
                if event.tags or event.weapon_system:
                    tags_str = ", ".join(event.tags) if event.tags else ""
                    if event.weapon_system:
                        tags_str = f"{event.weapon_system}, {tags_str}" if tags_str else event.weapon_system
                    st.caption(f"Tags: {tags_str}")
            
            with col3:
                if event.source_url:
                    st.link_button("🔗 Source", event.source_url, use_container_width=True)
            
            st.divider()


def render_world_map_with_events(events: list[NewsEvent]) -> None:
    """Render the world map with event markers."""
    import pydeck as pdk
    import streamlit.components.v1 as components
    from app.ui.layout.global_state import get_selected_news_event, set_selected_news_event
    
    # Get map style
    map_style = get_map_style()
    
    # Get selected event for highlighting
    selected = get_selected_news_event()
    
    # Build event data for scatter layer
    event_data = []
    for event in events:
        color = get_event_color(event.event_type)
        
        # Highlight selected event
        if selected and selected.get("id") == event.id:
            radius = 50000
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
            "summary": event.summary[:100] + "..." if len(event.summary) > 100 else event.summary,
        })
    
    # Create scatter layer for events
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
        radius_min_pixels=8,
        radius_max_pixels=30,
    )
    
    # Determine view state
    if selected:
        view_state = pdk.ViewState(
            latitude=selected["latitude"],
            longitude=selected["longitude"],
            zoom=5,
            pitch=0,
        )
    elif events:
        # Center on first event
        avg_lat = sum(e.latitude for e in events) / len(events)
        avg_lon = sum(e.longitude for e in events) / len(events)
        view_state = pdk.ViewState(
            latitude=avg_lat,
            longitude=avg_lon,
            zoom=2,
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
    
    # Create deck
    deck = pdk.Deck(
        layers=[scatter_layer],
        initial_view_state=view_state,
        map_style=map_style,
        tooltip={
            "html": """
            <b>{title}</b><br/>
            📅 {date}<br/>
            📰 {source}<br/>
            🎯 {event_type}<br/>
            <small>{summary}</small>
            """,
            "style": {
                "backgroundColor": "steelblue",
                "color": "white",
            },
        },
    )
    
    # Build legend HTML
    legend_html = """
    <div style="margin-top: 8px; font-size: 11px;">
        <div style="display: flex; align-items: center; margin: 2px 0;">
            <div style="width: 12px; height: 12px; background-color: rgb(255,0,0); border-radius: 50%; margin-right: 6px;"></div>
            <span>● Launch</span>
        </div>
        <div style="display: flex; align-items: center; margin: 2px 0;">
            <div style="width: 12px; height: 12px; background-color: rgb(255,193,7); border-radius: 50%; margin-right: 6px;"></div>
            <span>▲ Exercise</span>
        </div>
        <div style="display: flex; align-items: center; margin: 2px 0;">
            <div style="width: 12px; height: 12px; background-color: rgb(76,175,80); border-radius: 50%; margin-right: 6px;"></div>
            <span>■ Deployment</span>
        </div>
        <div style="display: flex; align-items: center; margin: 2px 0;">
            <div style="width: 12px; height: 12px; background-color: rgb(255,87,51); border-radius: 50%; margin-right: 6px;"></div>
            <span>◇ Test</span>
        </div>
        <div style="display: flex; align-items: center; margin: 2px 0;">
            <div style="width: 12px; height: 12px; background-color: rgb(66,135,245); border-radius: 50%; margin-right: 6px;"></div>
            <span>📢 Statement</span>
        </div>
    </div>
    """
    
    # Get deck HTML and inject legend
    deck_html = deck.to_html(as_string=True)
    
    legend_overlay = f'''
    <div id="legend-overlay" style="
        position: absolute;
        bottom: 20px;
        right: 20px;
        background-color: rgba(255, 255, 255, 0.92);
        border: 2px solid #333;
        border-radius: 6px;
        padding: 8px 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        max-width: 200px;
        z-index: 1000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    ">
        <div style="font-weight: bold; margin-bottom: 4px; font-size: 11px;">Event Types</div>
        {legend_html}
    </div>
    '''
    
    deck_html = deck_html.replace('</body>', f'{legend_overlay}</body>')
    
    # Render
    components.html(deck_html, height=500, scrolling=False)


def init_auto_refresh_state() -> None:
    """Initialize session state for auto-refresh timer."""
    if "news_last_fetch_time" not in st.session_state:
        st.session_state.news_last_fetch_time = None
    if "news_auto_refresh_enabled" not in st.session_state:
        st.session_state.news_auto_refresh_enabled = False


def get_refresh_status() -> tuple[str, int]:
    """
    Get the refresh status message and seconds until next refresh.
    
    Returns:
        Tuple of (status message, seconds remaining until next refresh)
    """
    from datetime import datetime, timedelta
    
    REFRESH_INTERVAL_MINUTES = 15
    
    last_fetch = st.session_state.get("news_last_fetch_time")
    
    if last_fetch is None:
        return "No events fetched yet", 0
    
    elapsed = datetime.now() - last_fetch
    next_refresh = last_fetch + timedelta(minutes=REFRESH_INTERVAL_MINUTES)
    remaining = next_refresh - datetime.now()
    
    if remaining.total_seconds() <= 0:
        return "Refresh due now", 0
    
    minutes = int(remaining.total_seconds() // 60)
    seconds = int(remaining.total_seconds() % 60)
    
    last_fetch_str = last_fetch.strftime("%H:%M:%S")
    next_refresh_str = next_refresh.strftime("%H:%M:%S")
    
    return f"Last: {last_fetch_str} | Next: {next_refresh_str} ({minutes}m {seconds}s)", int(remaining.total_seconds())


def render_refresh_timer_display() -> None:
    """Render the auto-refresh countdown timer display with live JavaScript countdown."""
    import streamlit.components.v1 as components
    from datetime import datetime
    
    last_fetch = st.session_state.get("news_last_fetch_time")
    
    # Always show the timer section after first fetch
    if last_fetch:
        status_msg, seconds_remaining = get_refresh_status()
        
        # Create a visible timer box
        st.markdown("---")
        
        # Auto-refresh checkbox (need this before the JS timer for state management)
        col_checkbox, col_spacer = st.columns([1, 4])
        with col_checkbox:
            auto_refresh = st.checkbox(
                "🔁 Enable Auto-Refresh",
                value=st.session_state.get("news_auto_refresh_enabled", False),
                key="auto_refresh_toggle",
                help="Automatically refresh events every 15 minutes"
            )
            st.session_state.news_auto_refresh_enabled = auto_refresh
        
        # Calculate values for JavaScript
        REFRESH_INTERVAL_SECONDS = 15 * 60  # 15 minutes
        last_fetch_str = last_fetch.strftime("%Y-%m-%d %H:%M:%S")
        auto_refresh_js = "true" if auto_refresh else "false"
        
        # JavaScript-based live countdown timer (light theme to match Streamlit)
        timer_html = f"""
        <div id="timer-container" style="
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            margin: 10px 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div style="flex: 1; min-width: 200px;">
                    <div style="color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Last Fetch</div>
                    <div style="color: #1e293b; font-size: 18px; font-weight: 600;">🕐 {last_fetch_str}</div>
                </div>
                <div style="flex: 1; min-width: 200px; text-align: center;">
                    <div style="color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Next Refresh In</div>
                    <div id="countdown" style="color: #0891b2; font-size: 28px; font-weight: bold; font-family: 'Courier New', monospace;">
                        --:--
                    </div>
                </div>
                <div style="flex: 1; min-width: 200px; text-align: right;">
                    <div style="color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Refresh Cycle</div>
                    <div style="background: #e2e8f0; border-radius: 8px; height: 24px; overflow: hidden; margin-top: 5px;">
                        <div id="progress-bar" style="
                            background: linear-gradient(90deg, #0891b2, #06b6d4);
                            height: 100%;
                            width: 0%;
                            transition: width 1s linear;
                            border-radius: 8px;
                        "></div>
                    </div>
                    <div id="progress-text" style="color: #334155; font-size: 14px; margin-top: 4px;">0%</div>
                </div>
            </div>
        </div>
        
        <script>
            (function() {{
                const REFRESH_INTERVAL = {REFRESH_INTERVAL_SECONDS};
                let secondsRemaining = {seconds_remaining};
                const autoRefresh = {auto_refresh_js};
                
                function updateTimer() {{
                    if (secondsRemaining <= 0) {{
                        document.getElementById('countdown').innerHTML = '🔄 REFRESH DUE';
                        document.getElementById('countdown').style.color = '#ea580c';
                        document.getElementById('progress-bar').style.width = '100%';
                        document.getElementById('progress-text').innerHTML = '100%';
                        
                        if (autoRefresh) {{
                            // Trigger Streamlit rerun by simulating user interaction
                            window.parent.postMessage({{type: 'streamlit:rerun'}}, '*');
                        }}
                        return;
                    }}
                    
                    const minutes = Math.floor(secondsRemaining / 60);
                    const seconds = secondsRemaining % 60;
                    const display = String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
                    
                    document.getElementById('countdown').innerHTML = '⏳ ' + display;
                    
                    // Update progress bar
                    const elapsed = REFRESH_INTERVAL - secondsRemaining;
                    const progressPercent = Math.min((elapsed / REFRESH_INTERVAL) * 100, 100);
                    document.getElementById('progress-bar').style.width = progressPercent + '%';
                    document.getElementById('progress-text').innerHTML = Math.round(progressPercent) + '%';
                    
                    // Color changes based on time remaining (darker shades for light background)
                    if (secondsRemaining < 60) {{
                        document.getElementById('countdown').style.color = '#ea580c';  // Dark orange when < 1 min
                    }} else if (secondsRemaining < 300) {{
                        document.getElementById('countdown').style.color = '#d97706';  // Dark amber when < 5 min
                    }} else {{
                        document.getElementById('countdown').style.color = '#0891b2';  // Dark cyan otherwise
                    }}
                    
                    secondsRemaining--;
                }}
                
                // Initial update
                updateTimer();
                
                // Update every second
                setInterval(updateTimer, 1000);
            }})();
        </script>
        """
        
        # Render the timer component
        components.html(timer_html, height=130, scrolling=False)
        
        # Trigger auto-refresh if enabled and timer expired (server-side backup)
        if auto_refresh and seconds_remaining <= 0:
            st.rerun()


def render_world_map_section() -> None:
    """Render the world map for situational awareness with news events."""
    from datetime import datetime
    
    st.header("🌍 ORRG – World Events")
    st.markdown("""
    *Situational awareness view - displays global context and live news events (Read-Only Context Layer).*  
    *Note: Analytical outputs are rendered within their respective tools below.*
    """)
    
    # Initialize states
    init_news_events_state()
    init_auto_refresh_state()
    
    # Check for auto-refresh trigger
    if st.session_state.get("news_auto_refresh_enabled", False):
        _, seconds_remaining = get_refresh_status()
        if seconds_remaining <= 0 and st.session_state.get("news_last_fetch_time"):
            # Trigger live fetch
            try:
                from app.events.adapter import fetch_live_events
                with st.spinner("🔄 Auto-refreshing events..."):
                    events, counts = fetch_live_events()
                    if events:
                        set_loaded_events(events, f"Live Feed ({sum(counts.values())} from {len(counts)} sources)")
                        st.session_state.news_last_fetch_time = datetime.now()
            except Exception as e:
                st.error(f"Auto-refresh failed: {e}")
    
    # Event source buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🌐 Fetch Live Events", key="fetch_live_events", type="primary"):
            import time
            
            # Create status placeholder for detailed updates
            status_container = st.empty()
            progress_bar = st.progress(0)
            
            try:
                from app.events.adapter import fetch_live_events, KEYWORDS
                
                # Step 1: Show initialization
                status_container.info("🔄 **Initializing news feed aggregator...**")
                progress_bar.progress(5)
                time.sleep(1)
                
                # Step 2: Show search criteria
                keywords_display = ", ".join(KEYWORDS[:8]) + "..."
                status_container.info(f"🔍 **Search Criteria:**\n\nKeywords: `{keywords_display}`")
                progress_bar.progress(10)
                time.sleep(1)
                
                # Step 3: Show sources being queried
                status_container.info("📡 **Connecting to news sources in parallel:**\n\n"
                                     "- 🌐 GDELT 2.1 Events Database\n"
                                     "- 📰 Reuters World News RSS\n"
                                     "- 📺 BBC World News RSS\n"
                                     "- 📋 Associated Press RSS")
                progress_bar.progress(20)
                time.sleep(1)
                
                # Step 4: Show filtering criteria
                status_container.info("🎯 **Filtering Criteria:**\n\n"
                                     "- Event types: Launch, Test, Exercise, Deployment, Nuclear, Statement\n"
                                     "- Countries: PRK, IRN, RUS, CHN, USA, ISR, IND, PAK, YEM\n"
                                     "- Confidence: High & Medium only\n"
                                     "- Geolocation: Must have valid coordinates")
                progress_bar.progress(30)
                time.sleep(1)
                
                # Step 5: Fetching
                status_container.info("⏳ **Fetching events from all sources...**\n\n"
                                     "This may take 5-15 seconds depending on network conditions.")
                progress_bar.progress(40)
                
                # Actual fetch
                events, counts = fetch_live_events()
                progress_bar.progress(80)
                
                # Always set the fetch timestamp regardless of whether events were found
                st.session_state.news_last_fetch_time = datetime.now()
                
                # Step 6: Processing results
                status_container.info(f"📊 **Processing results...**\n\n"
                                     f"Raw events found: {sum(counts.values())}\n"
                                     f"Deduplicating and normalizing...")
                time.sleep(1)
                progress_bar.progress(90)
                
                # Step 7: Final results
                if events:
                    set_loaded_events(events, f"Live Feed ({sum(counts.values())} from {len(counts)} sources)")
                    
                    # Show detailed source breakdown
                    source_info = "\n".join([f"- **{k}**: {v} events" for k, v in counts.items()])
                    status_container.success(f"✅ **Fetch Complete!**\n\n"
                                           f"**Total Events:** {len(events)}\n\n"
                                           f"**By Source:**\n{source_info}")
                    progress_bar.progress(100)
                    time.sleep(1.5)
                else:
                    # Still record that we fetched, but show warning
                    status_container.warning("⚠️ **No missile-related events found**\n\n"
                                           "The news sources did not return any events matching the search criteria.\n"
                                           "Try loading sample events to see the visualization.\n\n"
                                           "*Timer will still track refresh cycle.*")
                    progress_bar.progress(100)
                    
            except Exception as e:
                status_container.error(f"❌ **Error fetching live events:**\n\n{e}")
                progress_bar.progress(100)
            
            time.sleep(1)
            st.rerun()
    
    with col2:
        if st.button("📋 Load Sample Events", key="load_sample_events"):
            sample_events = create_sample_events()
            set_loaded_events(sample_events, "Sample Data")
            st.session_state.news_last_fetch_time = datetime.now()
            st.success(f"✅ Loaded {len(sample_events)} sample events")
            st.rerun()
    
    # Get current events
    all_events = get_loaded_events()
    
    with col3:
        if all_events:
            st.caption(f"📊 {len(all_events)} events loaded from: {st.session_state.get('news_events_source', 'Unknown')}")
    
    # Render refresh timer display
    render_refresh_timer_display()
    
    st.divider()
    
    # Render filter panel
    filters = render_news_filter_panel()
    
    # Apply filters to events
    filtered_events = apply_filters_to_events(all_events, filters) if all_events else []
    
    # Render the world map with event markers
    render_world_map_with_events(filtered_events)
    
    st.divider()
    
    # Render the live event collection feed
    render_event_collection_feed(filtered_events)




def main() -> None:
    """Main application entry point."""
    # Initialize session state
    init_session_state()
    
    # Render sidebar components
    render_sidebar_header()
    render_settings_panel()
    
    # Render main content
    render_header()
    
    # Create tabs for different sections
    tab1, tab2 = st.tabs(["🌍 Situational Awareness", "📊 Analytical Tools"])
    
    with tab1:
        render_world_map_section()
    
    with tab2:
        render_all_tools()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 12px;">
        Open Range Ring Generator (ORRG) | Open Source Geodesic Analysis Platform<br>
        All geometry calculations use true geodesic methods on WGS84 ellipsoid.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
