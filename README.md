# Global DEM Portal

A single-page web app for selecting elevation tiles on a map and downloading them as
GeoTIFF, across six free global DEMs. No build step, no backend, no API keys —
`index.html` is the whole application.

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

The **Copernicus GLO-30/GLO-90** products are ESA's openly redistributable global DEM,
edited from Airbus **TanDEM-X** radar — they are the freely available "TanDEM-based" DEM.
(DLR's raw TanDEM-X 90 m product is also free but sits behind a registration wall with no
CORS, so it cannot be served to a browser; Copernicus is the open, browser-reachable form
of the same source data.)

NASA's own LP DAAC Cloud distribution hosts SRTM/NASADEM too, but every request needs an
Earthdata login and sends no CORS headers — those URLs cannot be fetched or clicked from a
web page, which is why this portal uses the OpenTopography mirror instead.

Tiles covering only ocean (or a latitude a given product does not reach) are absent from
the archive and return `404`. The downloader skips them and reports the count rather than
treating them as errors.

### Land mask

To keep users from selecting empty water, the map draws its grid only over 1°×1° cells
that actually have a tile, and clicks/box-selections over ocean are ignored. This is driven
by a compact bitmask (`LAND_MASK_B64` in `index.html`, ~8 KB) built from the union of the
SRTM GL1 and Copernicus GLO-90 tile listings on the mirror — 26,481 land cells worldwide.
It is a static snapshot; regenerate it if the mirror's coverage ever changes.

## Downloading

* **One tile selected** — saves a single `.tif`.
* **Several tiles** — fetches them (4 at a time), bundles them into a ZIP with
  [JSZip](https://stuk.github.io/jszip/) (loaded on demand), and saves that.
* **Large selections** — the whole archive is assembled in browser memory, so above
  ~1 GB the app asks for confirmation and points you at the wget or Python script.
* **Merged GeoTIFF** — the *Merged GeoTIFF* tab generates an
  [OpenTopography API](https://portal.opentopography.org/apidocs/) call that returns one
  mosaicked raster for the whole bounding box instead of separate tiles. That endpoint
  needs a free API key.

To mosaic tiles yourself after downloading:

```bash
gdal_merge.py -o srtm_merged.tif srtm_data/*.tif
```

## Hosting on GitHub Pages

Yes — free, and this app is a perfect fit: it is fully static, and every service it calls
(the OpenTopography mirror, OpenStreetMap Nominatim, the basemap tiles) is reachable over
HTTPS with CORS from any origin.

```bash
git init
git add index.html README.md
git commit -m "SRTM DEM Portal"
git branch -M main
git remote add origin https://github.com/<you>/srtm-dem-portal.git
git push -u origin main
```

Then in the repository: **Settings → Pages → Source: Deploy from a branch**, pick
`main` and `/ (root)`, and save. The site appears at
`https://<you>.github.io/srtm-dem-portal/` within a minute or two.

Notes for a public deployment:

* The repository must be public for Pages on a free account. (Private repos can publish
  Pages only on a paid plan.)
* Pages is HTTPS-only, which the OpenTopography mirror requires — do not proxy it over
  plain HTTP.
* Nominatim's [usage policy](https://operations.osmfoundation.org/policies/nominatim/)
  caps geocoding at one request per second. The country search sends one request per
  lookup, which is fine for interactive use; do not add autocomplete-as-you-type.
* Bandwidth is not a concern: DEM tiles stream from OpenTopography straight to the
  visitor's browser and never touch GitHub's servers.

## Attribution

Cite whichever dataset you download:

* **SRTM** — NASA JPL (2013), *SRTM Global 1 arc second*,
  [doi:10.5067/MEaSUREs/SRTM/SRTMGL1.003](https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL1.003)
* **NASADEM** — NASA JPL (2020), NASADEM_HGT v001
* **ALOS AW3D30** — © JAXA, ALOS World 3D-30m
* **Copernicus GLO-30 / GLO-90** — © ESA / Airbus, produced from TanDEM-X

All redistributed by OpenTopography. Basemaps © OpenStreetMap contributors, © CARTO.
