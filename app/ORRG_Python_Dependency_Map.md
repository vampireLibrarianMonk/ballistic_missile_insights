# Python Dependency Map to Application Capabilities

## Purpose

This document maps **Python dependencies** used by the Open Range Ring Generator (ORRG) to the **specific application capabilities** they enable.  
It serves as an architectural reference to justify dependency inclusion, support security reviews, and guide future maintenance or substitution.

Only open-source libraries are used. Each dependency has a clearly defined role and limited responsibility.

---

## Core Application Framework

### streamlit
**Capability**
- Web-based application framework
- UI layout, expanders, inputs, session state
- Application orchestration

**Used By**
- `app.py`
- All UI modules (`ui/`)

**Rationale**
Provides a lightweight, Python-native UI framework suitable for analyst workflows and rapid iteration.

---

## Geospatial Geometry & Mathematics

### shapely
**Capability**
- Polygon and MultiPolygon manipulation
- Geometry intersections, unions, differences
- Donut (ring-with-hole) construction

**Used By**
- Geometry service layer
- Reverse and minimum range calculations

**Rationale**
Provides robust geometry operations independent of any GIS platform.

---

### pyproj
**Capability**
- Geodesic calculations
- Great-circle distance computation
- Accurate buffering on an ellipsoid

**Used By**
- Geodesic buffer generation
- Distance and range calculations

**Rationale**
Ensures true geodesic accuracy and explicit CRS handling.

---

### geographiclib
**Capability**
- High-precision geodesic math
- Validation of long-distance calculations

**Used By**
- Long-range (IRBM / ICBM) calculations
- Analyst diagnostics and validation

**Rationale**
Provides mathematically rigorous geodesic computations for global-scale analysis.

---

## Data Handling & Formats

### geopandas
**Capability**
- GeoJSON and vector dataset handling
- Boundary loading and normalization
- Export-ready geometry containers

**Used By**
- Country boundary ingestion
- Geometry serialization

**Rationale**
Bridges geometry operations and file-based vector formats.

---

### fiona
**Capability**
- Vector file I/O
- GeoJSON and Shapefile read/write

**Used By**
- Export adapters
- Data ingestion pipelines

**Rationale**
Low-level, reliable vector format handling.

---

### pandas
**Capability**
- Tabular data manipulation
- Weapon system metadata
- News and event metadata tables

**Used By**
- Weapon databases
- News feed normalization

**Rationale**
Efficient handling of structured, non-spatial data.

---

## Visualization & Rendering

### pydeck
**Capability**
- Interactive map rendering
- Polygon, point, and line layers
- Tool-local analytical maps

**Used By**
- All range ring output maps
- World events map (news context)

**Rationale**
GPU-accelerated, web-native visualization suitable for complex geospatial overlays.

---

### matplotlib
**Capability**
- Static map rendering
- Deterministic image generation

**Used By**
- PNG export pipeline
- PDF export pipeline (map images)

**Rationale**
Provides server-side, reproducible image rendering independent of browser state.

---

## Export & Document Generation

### simplekml
**Capability**
- KML/KMZ file creation
- Placemark and polygon styling

**Used By**
- KMZ export adapter

**Rationale**
Lightweight and purpose-built for Google Earth-compatible outputs.

---

### reportlab
**Capability**
- PDF document creation
- Page layout and text rendering

**Used By**
- PDF export adapter

**Rationale**
Reliable, programmatic PDF generation without external dependencies.

---

## News Ingestion & NLP

### requests
**Capability**
- HTTP requests
- API and RSS ingestion

**Used By**
- News feed ingestion
- External data retrieval

**Rationale**
Simple, widely adopted HTTP client.

---

### feedparser
**Capability**
- RSS and Atom feed parsing

**Used By**
- News source ingestion

**Rationale**
Standard parser for syndicated news feeds.

---

### beautifulsoup4
**Capability**
- HTML parsing
- Article content extraction

**Used By**
- News article processing
- Metadata extraction pipelines

**Rationale**
Flexible parsing for semi-structured content.

---

## Language Model Integration (Optional / Pluggable)

### openai (or compatible LLM SDK)
**Capability**
- Article summarization
- Metadata extraction
- Confidence language detection

**Used By**
- News-to-analysis bridge
- Analyst metadata panels

**Rationale**
Provides structured summarization without automating analytical decisions.

---

## Utility & Infrastructure

### pydantic
**Capability**
- Input/output schema validation
- Strong typing for contracts

**Used By**
- Shared input objects
- Standard output objects

**Rationale**
Ensures contract consistency across tools and services.

---

### uuid
**Capability**
- Unique identifier generation

**Used By**
- Output object IDs
- Session tracking

**Rationale**
Stable object identification and stacking support.

---

### datetime
**Capability**
- Timestamp handling
- Event time normalization

**Used By**
- News events
- Export metadata

**Rationale**
Standard library support for temporal data.

---

## Explicit Non-Dependencies

The following classes of libraries are intentionally excluded:

- ArcGIS / ArcPy
- Proprietary GIS SDKs
- Planar-only geometry engines
- Browser-based screenshot tools
- Database servers (Phase 1)

---

## Dependency Philosophy

Each dependency in ORRG:
- Enables a clearly defined capability
- Has a narrow responsibility
- Can be replaced if necessary
- Introduces no hidden state or licensing risk

This mapping exists to support:
- Security review
- Dependency audits
- Long-term maintainability

---

## Status

This document represents the finalized **Python dependency-to-capability mapping** for the Open Range Ring Generator.
