#!/usr/bin/env python3
"""Merge downloaded DEM tiles into a single GeoTIFF.

This is a convenience wrapper around GDAL — the standard geospatial toolkit. GDAL is NOT
bundled with this project; install it once (see below), and this script will find its
command-line tools automatically:

    conda install -c conda-forge gdal      # cross-platform, easiest
    # or Windows: OSGeo4W (https://trac.osgeo.org/osgeo4w/)
    # or Debian/Ubuntu: sudo apt install gdal-bin
    # or macOS: brew install gdal

Usage:
    python scripts/merge_dem.py                       # srtm_data/*.tif -> srtm_merged.tif
    python scripts/merge_dem.py <input_dir> <output.tif>

It builds a virtual mosaic (gdalbuildvrt) then writes a compressed GeoTIFF
(gdal_translate). If those aren't present it falls back to gdal_merge.py.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

INSTALL_HINT = (
    "GDAL command-line tools not found on PATH.\n"
    "Install GDAL, then re-run:\n"
    "  conda install -c conda-forge gdal\n"
    "  (Windows) OSGeo4W: https://trac.osgeo.org/osgeo4w/\n"
    "  (Debian/Ubuntu) sudo apt install gdal-bin\n"
    "  (macOS) brew install gdal"
)


def main():
    in_dir = sys.argv[1] if len(sys.argv) > 1 else "srtm_data"
    out_tif = sys.argv[2] if len(sys.argv) > 2 else "srtm_merged.tif"

    tiles = sorted(glob.glob(os.path.join(in_dir, "*.tif")))
    if not tiles:
        sys.exit(f"No .tif tiles found in '{in_dir}'. "
                 f"Download some first, or pass the folder as the first argument.")
    print(f"Merging {len(tiles)} tiles from '{in_dir}' -> '{out_tif}'")

    have_vrt = shutil.which("gdalbuildvrt") and shutil.which("gdal_translate")
    have_merge = shutil.which("gdal_merge.py")

    try:
        if have_vrt:
            with tempfile.NamedTemporaryFile(suffix=".vrt", delete=False) as tmp:
                vrt = tmp.name
            try:
                subprocess.run(["gdalbuildvrt", vrt, *tiles], check=True)
                subprocess.run(["gdal_translate", "-co", "COMPRESS=DEFLATE",
                                "-co", "TILED=YES", vrt, out_tif], check=True)
            finally:
                if os.path.exists(vrt):
                    os.remove(vrt)
        elif have_merge:
            subprocess.run(["gdal_merge.py", "-co", "COMPRESS=DEFLATE",
                            "-o", out_tif, *tiles], check=True)
        else:
            sys.exit(INSTALL_HINT)
    except subprocess.CalledProcessError as e:
        sys.exit(f"GDAL failed (exit {e.returncode}). Check that the tiles are valid GeoTIFFs.")

    print(f"Done -> {out_tif}")


if __name__ == "__main__":
    main()
