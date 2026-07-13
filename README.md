# Global DEM Portal

A single-page web app for selecting elevation tiles on a map and downloading them,
across seven free global DEMs (six as GeoTIFF, one as raw gzip-compressed SRTM `.hgt`).
No build step, no backend, no API keys - `index.html` is the whole application.

By **Sharad Gupta** - [github.com/sharadgupta27](https://github.com/sharadgupta27) ·
[linkedin.com/in/sharadgupta27](https://www.linkedin.com/in/sharadgupta27/) ·
[sharadgupta27@gmail.com](mailto:sharadgupta27@gmail.com)

## Why this portal

Free global elevation data has always technically been "open," but getting a usable
GeoTIFF for a specific area is rarely simple in practice. NASA's official SRTM
distribution requires an Earthdata account and blocks direct browser access. Country-scale
downloads mean stitching together dozens of manually-named tiles. Different DEM products
(SRTM, NASADEM, ALOS, Copernicus) live on different portals with different tile-naming
conventions and coverage limits, so comparing them means learning each one from scratch.
And most GIS tools that *can* do all this assume you already have QGIS, GDAL, or a Python
environment installed - a real barrier for students, hobbyist mappers, or anyone who just
wants elevation data for one region without setting up a geospatial toolchain first.

This portal collapses that into: open a web page, click the area (or search a country, or
draw a shape, or upload a boundary), pick a resolution, download. No login, no installed
software, no per-dataset learning curve - and because it runs entirely client-side, it
costs nothing to host and adds no processing delay between the source data and your disk.

## Datasets

All tiles come from the [OpenTopography](https://opentopography.org) public S3 mirror,
which serves them anonymously and with CORS enabled, so the browser can download them
directly. Coverage differs by mission, and the map's red boundary lines follow the
selected product.

| Product | Resolution | Coverage | Mirror path |
| --- | --- | --- | --- |
| `SRTMGL1` | ~30 m | 56°S–60°N | `raster/SRTM_GL1/SRTM_GL1_srtm/{TILE}.tif` |
| `NASADEM` | ~30 m (void-filled SRTM) | 56°S–60°N | `raster/NASADEM/NASADEM_be/NASADEM_HGT_{tile}.tif` |
| `ALOS` AW3D30 | ~30 m (JAXA optical) | 82°S–82°N | `raster/AW3D30/AW3D30_global/ALPSMLC30_{TILE}_DSM.tif` |
| `COP30` Copernicus GLO-30 | ~30 m (TanDEM-X) | global | `raster/COP30/COP30_hh/Copernicus_DSM_10_{...}_DEM.tif` |
| `SRTMGL3` | ~90 m | 56°S–60°N | `raster/SRTM_GL3/SRTM_GL3_srtm/{North_0_29\|North_30_60\|South}/{TILE}.tif` |
| `COP90` Copernicus GLO-90 | ~90 m (TanDEM-X) | global | `raster/COP90/COP90_hh/Copernicus_DSM_30_{...}_DEM.tif` |
| `MAPZEN` Mapzen (Tilezen) | ~30 m | 56°S–60°N* | `skadi/{TILE[0:3]}/{TILE}.hgt.gz` (different mirror, see below) |

\* Capped to the SRTM band on purpose. Mapzen's underlying data is truly global -
it fills oceans and poles with ETOPO1/GMTED - but this portal only exposes it where
it overlaps the existing land-mask grid, so it doesn't need its own mask.

**Mapzen is different from the other six** in two ways: it comes from a separate,
unrelated mirror (the [AWS Open Data terrain-tiles bucket](https://registry.opendata.aws/terrain-tiles/),
not OpenTopography), and it's served as gzip-compressed raw SRTM `.hgt`
(the "[skadi](https://github.com/tilezen/joerd/blob/master/docs/formats.md)" format), not GeoTIFF - gunzip it to
get a `.hgt` raster that GDAL/QGIS read natively. It's also a frozen snapshot: Mapzen
the company shut down in 2018 and this bucket hasn't been updated since 2016, so treat
it as a historical/bathymetry-capable curiosity rather than the best-quality option -
Copernicus GLO-30 is the more current, more accurate choice for the same band.

The **Copernicus GLO-30/GLO-90** products are ESA's openly redistributable global DEM,
edited from Airbus **TanDEM-X** radar - they are the freely available "TanDEM-based" DEM.
(DLR's raw TanDEM-X 90 m product is also free but sits behind a registration wall with no
CORS, so it cannot be served to a browser; Copernicus is the open, browser-reachable form
of the same source data.)

NASA's own LP DAAC Cloud distribution hosts SRTM/NASADEM too, but every request needs an
Earthdata login and sends no CORS headers - those URLs cannot be fetched or clicked from a
web page, which is why this portal uses the OpenTopography mirror instead.

Tiles covering only ocean (or a latitude a given product does not reach) are absent from
the archive and return `404`. The downloader skips them and reports the count rather than
treating them as errors.

### Land mask

To keep users from selecting empty water, the map draws its grid only over 1°×1° cells
that actually have a tile, and clicks/box-selections over ocean are ignored. This is driven
by a compact bitmask (`LAND_MASK_B64` in `index.html`, ~8 KB) built from the union of the
SRTM GL1 and Copernicus GLO-90 tile listings on the mirror - 26,481 land cells worldwide.
It is a static snapshot; regenerate it if the mirror's coverage ever changes
(`scripts/build_land_mask.py`).

### India boundary

India's boundary is corrected in two independent places:

**1. On the basemap (what you see).** The CARTO/OSM raster basemaps draw India along the
de-facto line. The [india_boundary_corrector](https://github.com/ramSeraph/india_boundary_corrector)
library (loaded from jsDelivr, `L.tileLayer.indiaBoundaryCorrected`) rewrites those tiles
on the fly - masking the incorrect boundary and drawing India's official one from a bundled
PMTiles dataset. If that CDN script fails to load, the app falls back to plain tiles.

**2. In tile selection (what you download).** Searching **India** uses an embedded official
boundary (`INDIA_BOUNDARY` in `index.html`) rather than the Nominatim result, so the
selected DEM tiles cover all of Jammu & Kashmir, Pakistan-administered Kashmir (with
Gilgit-Baltistan), Aksai Chin, the Siachen region and Arunachal Pradesh. Selection samples
a 3×3 grid within each 1° cell, so border cells are captured even when their centre falls
just across a neighbouring country's line. Source: DataMeet Community Maps (Survey of India
composite), simplified; regenerate with `scripts/build_india_boundary.py`.

## Downloading

* **One tile selected** - saves a single `.tif` (or `.hgt.gz` for Mapzen).
* **Several tiles** - fetches them (4 at a time), bundles them into a ZIP with
  [JSZip](https://stuk.github.io/jszip/) (loaded on demand), and saves that.
* **Large selections** - the whole archive is assembled in browser memory, so above
  ~1 GB the app asks for confirmation and points you at the wget or Python script.
* **Merged GeoTIFF** - the *Merged GeoTIFF* tab generates an
  [OpenTopography API](https://portal.opentopography.org/apidocs/) call that returns one
  mosaicked raster for the whole bounding box instead of separate tiles. That endpoint
  needs a free API key, and isn't available for Mapzen (it isn't hosted on OpenTopography) -
  the tab is greyed out when Mapzen is selected.

To mosaic tiles yourself after downloading, use `scripts/merge_dem.py`. It's a thin
wrapper around [GDAL](https://gdal.org) - GDAL itself isn't bundled here (it's a large
C++ toolkit, not something to ship inside a static web page), so install it once:

```bash
conda install -c conda-forge gdal      # easiest, cross-platform
# or: sudo apt install gdal-bin (Debian/Ubuntu) · brew install gdal (macOS)
# or: OSGeo4W (https://trac.osgeo.org/osgeo4w/) on Windows

python scripts/merge_dem.py                       # srtm_data/*.tif(+*.hgt) -> srtm_merged.tif
python scripts/merge_dem.py <input_dir> <output.tif>
```

If you'd rather call GDAL directly: `gdal_merge.py -o srtm_merged.tif srtm_data/*.tif`
works the same way once GDAL is on your PATH. For Mapzen, `gunzip` the downloaded
`*.hgt.gz` files first - GDAL's HGT driver doesn't read the gzip wrapper transparently.

## Attribution

* **SRTM** - NASA JPL (2013), *SRTM Global 1 arc second*,
  [doi:10.5067/MEaSUREs/SRTM/SRTMGL1.003](https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL1.003)
* **NASADEM** - NASA JPL (2020), NASADEM_HGT v001
* **ALOS AW3D30** - © JAXA, ALOS World 3D-30m
* **Copernicus GLO-30 / GLO-90** - © ESA / Airbus, produced from TanDEM-X
* **Mapzen (Tilezen) terrain tiles** - © Mapzen, built from SRTM/GMTED/ETOPO1 and other
  sources; redistributed as a static snapshot via the
  [AWS Open Data Program](https://registry.opendata.aws/terrain-tiles/)

SRTM/NASADEM/ALOS/Copernicus redistributed by OpenTopography; Mapzen via AWS Open Data
(a separate mirror). Basemaps © OpenStreetMap contributors, © CARTO.
India boundary © [DataMeet Community Maps](https://github.com/datameet/maps); basemap
boundary correction via [india_boundary_corrector](https://github.com/ramSeraph/india_boundary_corrector)
(© ramSeraph, Unlicense; data OSM ODbL / Natural Earth).

---

© 2026 Sharad Gupta. Application code released under the MIT License; the elevation data
and map layers remain under the licenses of their respective providers listed above.
