#!/usr/bin/env python3
"""Rebuild the 1°x1° land/data mask embedded in index.html.

The mask marks every 1°x1° cell that actually has a DEM tile on the OpenTopography
mirror, so the portal can draw its grid over land only and refuse ocean selections.
It is the union of the SRTM GL1 (56S-60N) and Copernicus GLO-90 (global) tile listings.

Usage:
    python scripts/build_land_mask.py           # print base64 + stats
    python scripts/build_land_mask.py --write    # also splice it into ../index.html

No dependencies beyond the standard library.
"""
import argparse, base64, os, re, ssl, sys, urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import quote

HOST = "https://opentopography.s3.sdsc.edu/raster"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
HTML = os.path.join(os.path.dirname(__file__), "..", "index.html")

# The mirror's TLS chain trips Python's verifier on some platforms; the listing is
# public read-only data, so verification is not security-relevant here.
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def list_keys(prefix):
    keys, token = [], None
    while True:
        url = f"{HOST}?list-type=2&prefix={prefix}&max-keys=1000"
        if token:
            url += "&continuation-token=" + quote(token, safe="")
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60, context=_ctx) as r:
                    data = r.read()
                break
            except Exception:
                if attempt == 3:
                    raise
        root = ET.fromstring(data)
        keys += [c.find(f"{NS}Key").text for c in root.findall(f"{NS}Contents")]
        print(f"  {prefix}: {len(keys)} keys", end="\r", file=sys.stderr)
        if root.find(f"{NS}IsTruncated").text != "true":
            break
        token = root.findtext(f"{NS}NextContinuationToken")
    print(f"  {prefix}: {len(keys)} keys total   ", file=sys.stderr)
    return keys


def build_land():
    land = set()
    srtm_re = re.compile(r"/([NS])(\d{2})([EW])(\d{3})\.tif$")
    cop_re = re.compile(r"_([NS])(\d{2})_00_([EW])(\d{3})_00_DEM\.tif$")
    for prefix, rx in [("SRTM_GL1/SRTM_GL1_srtm/", srtm_re), ("COP90/COP90_hh/", cop_re)]:
        for k in list_keys(prefix):
            m = rx.search(k)
            if m:
                la = int(m[2]) * (1 if m[1] == "N" else -1)
                lo = int(m[4]) * (1 if m[3] == "E" else -1)
                land.add((la, lo))
    return land


def encode(land):
    bits = bytearray(360 * 180 // 8)  # idx = (lat+90)*360 + (lon+180)
    for la, lo in land:
        if -90 <= la < 90 and -180 <= lo < 180:
            idx = (la + 90) * 360 + (lo + 180)
            bits[idx >> 3] |= 1 << (idx & 7)
    return base64.b64encode(bytes(bits)).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="splice result into index.html")
    args = ap.parse_args()

    land = build_land()
    b64 = encode(land)
    print(f"land cells: {len(land)}   base64 chars: {len(b64)}", file=sys.stderr)

    if args.write:
        html = open(HTML, encoding="utf-8").read()
        new = re.sub(r'const LAND_MASK_B64 = "[^"]*";',
                     f'const LAND_MASK_B64 = "{b64}";', html, count=1)
        if new == html:
            sys.exit("ERROR: LAND_MASK_B64 line not found in index.html")
        open(HTML, "w", encoding="utf-8").write(new)
        print("index.html updated.", file=sys.stderr)
    else:
        print(b64)


if __name__ == "__main__":
    main()
