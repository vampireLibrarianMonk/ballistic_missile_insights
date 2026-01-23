# Open Range Ring Generator (ORRG)

**Slug / Repository Name:** `open-range-ring-generator`  
**Tagline:** *A fully open-source, web-based geodesic range ring analysis platform.*

---

## 1. Application Overview

The **Open Range Ring Generator (ORRG)** is a web-based geospatial analysis application designed to generate geodesic range ring products that were historically produced using proprietary ArcGIS/ArcPy tooling. This application fully replaces licensed software with open-source Python libraries while preserving analytical rigor and correctness.

ORRG provides an interactive **Streamlit-based interface** suitable for both general users and analysts. The application is divided into two functional domains:

1. **Situational Awareness** — a world map and filterable news feed focused on missile launches and strategic events.
2. **Analytical Tooling** — five modular range ring generators, each implemented as a self-contained UI section with independent outputs and export controls.

All analytical outputs are rendered locally within the tool that generated them and may be stacked and exported without impacting other tools or the global map.

---

## 2. User Roles and Interaction Model

The application supports two user modes:

- **General User**
- **Analyst**

Both modes have access to the same analytical capabilities, weapon systems, and datasets. The distinction between modes is strictly limited to **UI transparency and detail**, not functionality or access.

- General users see a streamlined interface focused on inputs and results.
- Analyst mode exposes additional diagnostic information such as geometry resolution, point density, processing metrics, and export metadata.

Mode selection is global, session-based, and affects only presentation and metadata visibility.

---

## 3. Global Layout and Functional Separation

The application layout intentionally separates **contextual awareness** from **analytical output**.

### World Map
- Displays missile launch and strategic event markers.
- Serves situational awareness only.
- **No range rings or analytical geometry are rendered here.**

### Analytical Outputs
- Rendered exclusively within the UI section of the tool that produced them.
- Each tool owns its own map, legend, and export controls.
- Outputs may be stacked and reviewed independently.

---

## 4. News Feed and Filtering Requirements

The news feed provides a scrollable list of missile-related and strategic events and is tightly coupled to the world map.

The news feed must support filtering by:
- Country
- Weapon system
- Range classification (CRBM, SRBM, MRBM, IRBM, ICBM)
- City or point location
- Optional time window

Selecting a news item highlights the corresponding marker on the world map but does **not** alter tool inputs or analytical outputs.

---

## 5. Analytical Tooling Requirements

The application contains five analytical tools, each implemented as a collapsible UI section:

1. **Single Range Ring Generator**  
   Generates a single geodesic range ring from a country boundary or point of origin.

2. **Multiple Range Ring Generator**  
   Generates multiple concentric range rings representing different weapon systems or ranges.

3. **Reverse Range Ring Generator**  
   Computes the geographic region from which a weapon system could reach a specified target point.

4. **Minimum Range Ring Generator**  
   Calculates and visualizes the minimum geodesic distance between two countries.

5. **Custom POI Range Ring Generator**  
   Generates minimum/maximum “donut” range rings from one or more user-defined points of interest.

Each tool:
- Is independent and stateless
- May produce multiple stacked outputs
- Renders its own map
- Provides export controls adjacent to each output

---

## 6. Export Requirements

Exports are **local to each tool output** and not global.

Each analytical output supports exporting to:
- **GeoJSON** (authoritative geometry)
- **KMZ**
- **PNG**
- **PDF**

PNG and PDF exports are generated using a deterministic **server-side analytical rendering pipeline** derived directly from geometry data (not browser screenshots).

In Analyst mode, exports may optionally include diagnostic metadata such as resolution, point count, CRS, and processing metrics.

---

## 7. Technical and Architectural Constraints

- Minimum Python version: **Python 3.12**
- All geometry calculations must be **true geodesic**
- No planar buffering
- No proprietary datasets, APIs, or libraries
- Stateless execution (no scratch directories or temporary workspaces)
- Explicit CRS handling (EPSG:4326)

---

## 8. Application File and Directory Structure

The application is structured to keep UI composition, news functionality, and analytical tooling cleanly separated.

```
open-range-ring-generator/
├── app.py
├── ui/
│   ├── layout/
│   ├── news/
│   └── tools/
├── geometry/
├── rendering/
├── exports/
├── data/
├── models/
└── README.md
```

---

## 9. app.py Responsibilities

The `app.py` file is intentionally minimal and orchestration-focused. Its responsibilities are limited to:

- Initializing Streamlit configuration
- Managing global session state
- Rendering the application header and mode toggle
- Rendering the world map and news feed
- Rendering the analytical tool stack

`app.py` contains **no geometry logic, rendering logic, or export logic**.

---

## 10. Status

This document represents the finalized requirements baseline for the Open Range Ring Generator.