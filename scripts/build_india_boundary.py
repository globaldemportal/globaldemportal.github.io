#!/usr/bin/env python3
"""Rebuild the INDIA_BOUNDARY polygon embedded in index.html.

India's country search must use the boundary as claimed by the Government of India —
including Jammu & Kashmir, Pakistan-administered Kashmir (with Gilgit-Baltistan), Aksai
Chin, the Siachen region and Arunachal Pradesh. OpenStreetMap/Nominatim returns the
de-facto line and omits these, so we embed an official composite instead.

Source: DataMeet Community Maps (Survey of India composite), Douglas-Peucker simplified
to ~0.02 deg (plenty for 1 deg tile selection and a clean outline).

    python scripts/build_india_boundary.py            # print GeoJSON + stats
    python scripts/build_india_boundary.py --write     # splice into ../index.html

Standard library only.
"""
import argparse, json, math, os, re, ssl, sys, urllib.request

URL = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"
HTML = os.path.join(os.path.dirname(__file__), "..", "index.html")
TOL = 0.02          # simplification tolerance in degrees
MIN_AREA = 0.00008  # drop only degenerate specks; keep Lakshadweep/Andaman/Nicobar

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def dp(points, tol):
    if len(points) < 3:
        return points[:]
    x1, y1 = points[0]; x2, y2 = points[-1]
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy)
    dmax, idx = 0, 0
    for i in range(1, len(points) - 1):
        x0, y0 = points[i]
        d = abs(dx * (y1 - y0) - dy * (x1 - x0)) / L if L else math.hypot(x0 - x1, y0 - y1)
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return dp(points[:idx + 1], tol)[:-1] + dp(points[idx:], tol)
    return [points[0], points[-1]]


def ring_area(r):
    return abs(sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]
                   for i in range(len(r) - 1))) / 2


def simplify(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    out = []
    for poly in polys:
        rings = []
        for ri, ring in enumerate(poly):
            if ri == 0 and ring_area(ring) < MIN_AREA:
                rings = []; break
            s = dp(ring, TOL)
            if s[0] != s[-1]:
                s.append(s[0])
            if len(s) >= 4:
                rings.append([[round(p[0], 4), round(p[1], 4)] for p in s])
        if rings:
            out.append(rings)
    return {"type": "MultiPolygon", "coordinates": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    with urllib.request.urlopen(URL, timeout=90, context=_ctx) as r:
        obj = json.loads(r.read())
    geom = obj["features"][0]["geometry"] if obj.get("type") == "FeatureCollection" else obj
    simp = simplify(geom)
    out = json.dumps(simp, separators=(",", ":"))
    print(f"polys={len(simp['coordinates'])}  json={len(out)} bytes", file=sys.stderr)

    if args.write:
        html = open(HTML, encoding="utf-8").read()
        new = re.sub(r"const INDIA_BOUNDARY = \{.*?\};",
                     "const INDIA_BOUNDARY = " + out + ";", html, count=1, flags=re.S)
        if new == html:
            sys.exit("ERROR: INDIA_BOUNDARY line not found in index.html")
        open(HTML, "w", encoding="utf-8").write(new)
        print("index.html updated.", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
