# GeoServer Setup for ORRG (AEQD & Eckert III Server-Side Reprojection)

This document provides **explicit, reproducible steps** to configure GeoServer so it can serve **server-side reprojected basemaps** for the ORRG PNG/SVG export pipeline, mirroring ArcGIS Server export behavior.

The end state is:
- GeoServer performs **all raster reprojection**
- ORRG requests basemaps via **WMS GetMap** using `SRS=EPSG:990001` (AEQD) or `SRS=EPSG:990002` (Eckert IV)
- Client-side Python code performs **no raster reprojection**

---

## 1. Prerequisites

- GeoServer **2.22+** (tested on 2.24.x)
- Java 11+
- GeoServer running locally at:
  ```
  http://localhost:8080/geoserver
  ```
- Access to GeoServer **data directory**

To confirm your data directory:
- GeoServer UI → **About & Status → System Status**
- Look for **Data directory** path (example: `/opt/geoserver/data_dir`)

If you are running GeoServer **in Docker**, you can usually locate the data directory by:
- Checking the `GEOSERVER_DATA_DIR` environment variable inside the container.
- Inspecting the container volume mapping (e.g., `-v /path/on/host:/opt/geoserver/data_dir`).

Example Docker checks:
```bash
docker exec -it <geoserver_container> printenv GEOSERVER_DATA_DIR
docker inspect <geoserver_container> --format='{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

---

## 2. Locate the `epsg.properties` File

GeoServer uses GeoTools CRS definitions from:

```text
<GEOSERVER_DATA_DIR>/user_projections/epsg.properties
```

If the directory does not exist, create it:

```bash
mkdir -p <GEOSERVER_DATA_DIR>/user_projections
```

If `epsg.properties` does not exist, create it:

```bash
touch <GEOSERVER_DATA_DIR>/user_projections/epsg.properties
```

---

## 3. Add ORRG CRS Definitions (REQUIRED)

Open `epsg.properties` and add **exactly** the following entries.
Save the file and ensure the **file permissions** allow GeoServer to read it.

### ORRG Azimuthal Equidistant (Dynamic Center via WMS bbox)

```properties
990001=PROJCS["ORRG Azimuthal Equidistant",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],PROJECTION["Azimuthal_Equidistant"],PARAMETER["latitude_of_center",0.0],PARAMETER["longitude_of_center",0.0],PARAMETER["false_easting",0.0],PARAMETER["false_northing",0.0],UNIT["metre",1.0],AUTHORITY["EPSG","990001"]]
```

> GeoServer will dynamically shift the effective center based on the WMS request BBOX.

---

### ORRG Eckert IV (Global Projection)

```properties
990002=PROJCS["ORRG Eckert IV",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],PROJECTION["Eckert_IV"],PARAMETER["Central_Meridian",0.0],UNIT["metre",1.0],AUTHORITY["EPSG","990002"]]
```

---

## 4. Restart GeoServer (MANDATORY)

GeoServer **only loads CRS definitions at startup**.

Restart GeoServer completely:

```bash
systemctl restart geoserver
# or
./bin/shutdown.sh && ./bin/startup.sh
```

If you are using Docker:
```bash
docker restart <geoserver_container>
```

---

## 5. Verify CRS Registration

### Test AEQD

```text
http://localhost:8080/geoserver/wms?
service=WMS&
version=1.1.1&
request=GetMap&
layers=ne:countries&
srs=EPSG:990001&
bbox=-5500000,-5500000,5500000,5500000&
width=1400&
height=900&
format=image/png
```

Expected result:
- PNG image returned
- Circular distortion centered on map extent

If you still see an XML error response (e.g., `InvalidSRS`), the CRS file was not loaded.

---

### Test Eckert IV

```text
http://localhost:8080/geoserver/wms?
service=WMS&
version=1.1.1&
request=GetMap&
layers=ne:countries&
srs=EPSG:990002&
bbox=-18000000,-9000000,18000000,9000000&
width=1400&
height=900&
format=image/png
```

Expected result:
- Global pseudo-cylindrical projection

---

## 6. Recommended Basemap Layers

For ORRG-style IC products, use **vector-rendered WMS layers**:

### Minimal Political Basemap
- `ne:countries`
- `ne:admin_0_boundary_lines_land`
- `ne:disputed_areas`

### Optional Context Layers
- `ne:populated_places`
- `ne:graticules_10`

> Avoid XYZ tiles (OSM, ESRI) — they cannot be reprojected server-side.

---

## 7. Python WMS Parameters (Final Reference)

```python
params = {
    "service": "WMS",
    "version": "1.1.1",
    "request": "GetMap",
    "layers": "ne:countries",
    "srs": "EPSG:990001",  # or EPSG:990002
    "bbox": f"{minx},{miny},{maxx},{maxy}",
    "width": width,
    "height": height,
    "format": "image/png",
}
```

---

## 8. Architectural Outcome

After this setup:

- GeoServer performs **all cartographic reprojection**
- ORRG client code only selects CRS + bbox
- PNG output matches **ArcGIS Server ExportMap** semantics
- SVG template, legend, and metadata remain unchanged

---

## 9. Common Failure Modes

| Error | Cause | Fix |
|------|------|-----|
| `No authority was defined for code EPSG:990001` | Missing epsg.properties or GeoServer did not reload | Add custom CRS + restart |
| `No transform for classification Eckert_III` | Eckert III unsupported by GeoTools | Use Eckert IV definition (EPSG:990002) |
| Blue background only | WMS error returned as XML | Check Content-Type |
| Axis swapped | Using WMS 1.3.0 | Use WMS 1.1.1 |
| Tile-like distortion | XYZ basemap | Use vector WMS layers |

## 10. Quick Health Check (Optional)

To confirm GeoServer is reachable and serving layers:

```text
http://localhost:8080/geoserver/wms?service=WMS&request=GetCapabilities
```

If you are inside a secure enclave, replace `localhost` with the host or container IP.

---

**This configuration is REQUIRED for true ArcGIS-like server-side reprojection.**

