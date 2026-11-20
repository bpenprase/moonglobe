"""
fetch_detail_tiles.py
Downloads high-resolution close-up images of popular lunar regions for the Lunar Globe Explorer.

Source: NASA Moon Trek tile service, LRO Wide Angle Camera global mosaic at 303 pixels per degree
(about 100 m per pixel), NASA/GSFC/Arizona State University.

For each region in tools/detail_regions.json the script
  1. works out which Moon Trek tiles cover the region,
  2. downloads and stitches them into one image,
  3. gently matches its large-scale brightness to the globe's base map so the two blend without a seam,
  4. saves data/detail/<region>.jpg and lists everything in data/detail/regions.json.

It also checks that the tiles line up with the base map, and whether Moon Trek lets web pages on other
sites load its tiles directly (needed for live close-ups everywhere on the Moon).
A summary is written to tools/detail_report.txt.

This normally runs on GitHub (see .github/workflows/fetch-detail-tiles.yml) whenever this file or
the region list changes. To run it yourself:  pip install numpy pillow scipy  then
python3 tools/fetch_detail_tiles.py
The same script makes the Mars close-ups (THEMIS daytime infrared) when run with --body Mars and the
options listed in .github/workflows/build-mars-data.yml.
"""
import argparse, io, json, math, os, re, shutil, sys, time, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description="Download close-up images from NASA Trek tiles")
ap.add_argument("--body", default="Moon")
ap.add_argument("--layer", default="LRO_WAC_Mosaic_Global_303ppd_v02")
ap.add_argument("--layers-json", help="read --layer/--ext/--lon-shift from this file (key 'ir'), as written by prepare_mars_data.py")
ap.add_argument("--ext", default="jpg")
ap.add_argument("--radius", type=float, default=1737.4)
ap.add_argument("--native-ppd", type=float, default=303.0)
ap.add_argument("--max-level", type=int, default=8)
ap.add_argument("--lon-shift", type=float, default=0.0)
ap.add_argument("--regions", default=str(ROOT / "tools" / "detail_regions.json"))
ap.add_argument("--features", default=str(ROOT / "data" / "features.json"))
ap.add_argument("--base", default=str(ROOT / "data" / "moon_albedo_8k.jpg"))
ap.add_argument("--out", default=str(ROOT / "data" / "detail"))
ap.add_argument("--report", default=str(ROOT / "tools" / "detail_report.txt"))
ap.add_argument("--source", default="NASA Moon Trek, LRO WAC global mosaic 303 ppd (NASA/GSFC/ASU)")
ARGS = ap.parse_args()
if ARGS.layers_json:
    _L = json.load(open(ARGS.layers_json)).get("ir", {})
    ARGS.layer, ARGS.ext = _L.get("layer", ARGS.layer), _L.get("ext", ARGS.ext)
    ARGS.lon_shift, ARGS.max_level = _L.get("lon_shift_deg", 0.0), _L.get("max_level", ARGS.max_level)
OUT = Path(ARGS.out)
REPORT = Path(ARGS.report)
LAYER = ARGS.layer
TREK = os.environ.get("TREK_BASE", f"https://trek.nasa.gov/tiles/{ARGS.body}/EQ")
BASE_URL = f"{TREK}/{LAYER}/1.0.0"
KM_PER_DEG = 2 * math.pi * ARGS.radius / 360     # 30.32 km per degree on the Moon, 59.16 on Mars
MAX_SIDE = 4096                                  # largest image side we keep
NATIVE_PPD = ARGS.native_ppd
SITE_ORIGIN = "https://bpenprase.github.io"

log_lines = []
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    log_lines.append(s)

START = time.time()
TIME_LIMIT = 40 * 60          # seconds; stop starting new regions after this

def http_get(url, headers=None, tries=3):
    req = urllib.request.Request(url, headers={"User-Agent": "LunarGlobeExplorer/1.0 (education; Soka University of America)", **(headers or {})})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read(), dict(r.headers)
        except Exception as e:
            if getattr(e, "code", None) == 404:
                return None, {}
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))

# ---------------------------------------------------------------- 1. tile layout
def standard_layout():
    """The usual Moon Trek layout: level z has 2^(z+1) x 2^z tiles of 256 px covering the whole Moon."""
    template = BASE_URL + "/default/default028mm/{TileMatrix}/{TileRow}/{TileCol}." + ARGS.ext
    levels = [dict(id=str(z), lon0=-180.0 + ARGS.lon_shift, lat0=90.0, mw=2 ** (z + 1), mh=2 ** z, tw=256, th=256,
                   deg=180.0 / (256 * 2 ** z), deg_scale=None) for z in range(0, ARGS.max_level + 1)]
    return levels, template

def read_layout():
    """Use the standard layout if its tiles load; otherwise read the WMTS capabilities file."""
    levels, template = standard_layout()
    try:
        top_level = levels[-1]; n = top_level["mh"]
        top, _ = http_get(tile_url(template, top_level, n // 2, n))
        if top and Image.open(io.BytesIO(top)).size == (256, 256):
            log(f"Using the standard {ARGS.body} Trek tile layout (test tile loaded).")
            for L in levels:
                log(f"  level {L['id']}: {L['mw']} x {L['mh']} tiles of 256 px, {1 / L['deg']:.2f} px/deg")
            return levels, template
    except Exception as e:
        log("Standard layout test failed:", repr(e))
    levels, template = [], None
    try:
        xml, _ = http_get(f"{BASE_URL}/WMTSCapabilities.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://www.opengis.net/wmts/1.0", "ows": "http://www.opengis.net/ows/1.1"}
        layer = root.find(".//w:Contents/w:Layer", ns)
        style = layer.find("w:Style/ows:Identifier", ns).text
        tms_id = layer.find("w:TileMatrixSetLink/w:TileMatrixSet", ns).text
        res = layer.find("w:ResourceURL", ns)
        template = res.get("template").replace("{Style}", style).replace("{TileMatrixSet}", tms_id)
        tms = [t for t in root.findall(".//w:Contents/w:TileMatrixSet", ns) if t.find("ows:Identifier", ns).text == tms_id][0]
        for tm in tms.findall("w:TileMatrix", ns):
            a, b = (float(v) for v in tm.find("w:TopLeftCorner", ns).text.split())
            lon0, lat0 = (b, a) if abs(a) <= 90 < abs(b) else (a, b)
            mw, mh = int(float(tm.find("w:MatrixWidth", ns).text)), int(float(tm.find("w:MatrixHeight", ns).text))
            tw, th = int(float(tm.find("w:TileWidth", ns).text)), int(float(tm.find("w:TileHeight", ns).text))
            scale = float(tm.find("w:ScaleDenominator", ns).text)
            deg_scale = scale * 0.00028 / (KM_PER_DEG * 1000)
            deg_width = 360.0 / (mw * tw)
            levels.append(dict(id=tm.find("ows:Identifier", ns).text, lon0=lon0, lat0=lat0, mw=mw, mh=mh, tw=tw, th=th,
                               deg=deg_width, deg_scale=deg_scale))
        log("Capabilities read OK. Style:", style, " TileMatrixSet:", tms_id)
    except Exception as e:
        log("Could not read capabilities either, trying the standard layout anyway. Reason:", repr(e))
        levels, template = standard_layout()
    log("Tile URL template:", template)
    for L in levels:
        from_scale = "n/a" if not L["deg_scale"] else "%.2f" % (1 / L["deg_scale"])
        log(f"  level {L['id']}: {L['mw']} x {L['mh']} tiles of {L['tw']} px, {1 / L['deg']:.2f} px/deg"
            f" (from scale: {from_scale}), top-left {L['lon0']}, {L['lat0']}")
    return levels, template

def tile_url(template, L, row, col):
    return template.replace("{TileMatrix}", L["id"]).replace("{TileRow}", str(row)).replace("{TileCol}", str(col))

def fetch_area(levels, template, L, west, north, wpx, hpx):
    """Stitch the area whose top-left corner is (west, north) degrees, wpx x hpx pixels at level L.
    Longitudes wrap around the Moon; rows outside the map stay black."""
    x0 = (west - L["lon0"]) / L["deg"]
    y0 = (L["lat0"] - north) / L["deg"]
    c0, r0 = math.floor(x0 / L["tw"]), math.floor(y0 / L["th"])
    c1, r1 = math.floor((x0 + wpx - 1) / L["tw"]), math.floor((y0 + hpx - 1) / L["th"])
    canvas = Image.new("L", ((c1 - c0 + 1) * L["tw"], (r1 - r0 + 1) * L["th"]))
    jobs = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if 0 <= r < L["mh"]]
    missing = []
    def get(rc):
        r, c = rc
        data, _ = http_get(tile_url(template, L, r, c % L["mw"]))
        return rc, data
    with ThreadPoolExecutor(8) as ex:
        for (r, c), data in ex.map(get, jobs):
            if not data:
                missing.append((r, c)); continue
            canvas.paste(Image.open(io.BytesIO(data)).convert("L"), ((c - c0) * L["tw"], (r - r0) * L["th"]))
    ox, oy = round(x0 - c0 * L["tw"]), round(y0 - r0 * L["th"])
    return canvas.crop((ox, oy, ox + wpx, oy + hpx)), len(jobs), missing

# ---------------------------------------------------------------- 2. base map helpers
BASE = np.asarray(Image.open(ARGS.base).convert("L"), dtype=np.float32)
BASE_PPD = BASE.shape[1] / 360.0

def base_crop(west, north, wdeg, hdeg, size):
    """The same area from the base map (with longitude wrap), resized to `size`."""
    x0 = (west + 180) * BASE_PPD
    y0 = (90 - north) * BASE_PPD
    nx, ny = max(2, math.ceil(wdeg * BASE_PPD) + 2), max(2, math.ceil(hdeg * BASE_PPD) + 2)
    xs = (np.floor(x0).astype(int) + np.arange(nx)) % BASE.shape[1]
    ys = np.clip(np.floor(y0).astype(int) + np.arange(ny), 0, BASE.shape[0] - 1)
    sub = BASE[np.ix_(ys, xs)]
    fx, fy = x0 - math.floor(x0), y0 - math.floor(y0)
    img = Image.fromarray(sub, "F").resize(size, Image.BICUBIC,
                                           box=(fx, fy, fx + wdeg * BASE_PPD, fy + hdeg * BASE_PPD))
    return np.asarray(img, dtype=np.float32)

# ---------------------------------------------------------------- 3. alignment check
def check_alignment(levels, template):
    """Stitch a whole-Moon image at a coarse level and find the longitude shift that best matches the base map."""
    L = min((l for l in levels if l["mw"] * l["tw"] >= 1024), key=lambda l: l["mw"] * l["tw"])
    w, h = round(360 / L["deg"]), round(180 / L["deg"])
    img, n, missing = fetch_area(levels, template, L, -180.0, 90.0, w, h)
    t = np.asarray(img, dtype=np.float32)
    b = np.asarray(Image.fromarray(BASE, "F").resize((w, h), Image.BILINEAR), dtype=np.float32)
    band = slice(int(h * 0.25), int(h * 0.75))            # compare the low-latitude band
    def corr(a, c):
        a, c = a[band] - a[band].mean(), c[band] - c[band].mean()
        return float((a * c).sum() / math.sqrt((a * a).sum() * (c * c).sum() + 1e-9))
    best = max(((corr(np.roll(t, k, axis=1), b), k) for k in range(-w // 2, w // 2, max(1, w // 720))), key=lambda x: x[0])
    shift_deg = best[1] * L["deg"]          # roll by +k lines the tiles up, so the true longitude is k pixels further east
    log(f"Alignment check at level {L['id']} ({w} x {h} px, {n} tiles, {len(missing)} missing): "
        f"correlation {corr(t, b):.3f} as is, best {best[0]:.3f} with a {shift_deg:+.2f} deg longitude correction")
    # fine search near zero in single pixels
    fine = max(((corr(np.roll(t, k, axis=1), b), k) for k in range(-6, 7)), key=lambda x: x[0])
    log(f"  fine check: best correlation {fine[0]:.3f} at {fine[1] * L['deg']:+.3f} deg")
    if abs(shift_deg) > 1 and best[0] > corr(t, b) + 0.1:
        log("  Applying the longitude correction to all levels.")
        for l in levels:
            l["lon0"] += shift_deg
        return shift_deg, best[0]
    return 0.0, corr(t, b)

# ---------------------------------------------------------------- 4. CORS check
def check_cors(levels, template):
    L = levels[0]
    try:
        _, hdrs = http_get(tile_url(template, L, 0, 0), headers={"Origin": SITE_ORIGIN})
        acao = {k.lower(): v for k, v in hdrs.items()}.get("access-control-allow-origin")
    except Exception as e:
        acao = None
        log("CORS check failed:", repr(e))
    ok = acao in ("*", SITE_ORIGIN)
    log(f"CORS: Access-Control-Allow-Origin = {acao!r} -> live tiles in the browser {'ALLOWED' if ok else 'NOT allowed'}")
    return ok

# ---------------------------------------------------------------- 5. regions
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def main():
    levels, template = read_layout()
    shift, align_corr = check_alignment(levels, template)
    cors = check_cors(levels, template)
    if align_corr < 0.5:
        log("STOPPED: the tiles do not line up with the globe's base map, so nothing was changed.")
        sys.exit(1)
    work = OUT.parent / "detail_new"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    feats = {f[0].lower(): f for f in json.load(open(ARGS.features))["features"]}
    spec = json.load(open(ARGS.regions))["regions"]
    out_regions = []
    for R in spec:
        if time.time() - START > TIME_LIMIT:
            log("Time limit reached; the remaining regions keep their previous images.")
            old = OUT / (slug(R["name"]) + ".jpg")
            prev = {r["file"]: r for r in json.load(open(OUT / "regions.json"))["regions"]} if (OUT / "regions.json").exists() else {}
            if old.exists() and old.name in prev:
                shutil.copy(old, work / old.name); out_regions.append(prev[old.name])
            continue
        if "feature" in R:
            f = feats.get(R["feature"].lower())
            if not f:
                log("Skipping (feature not found):", R["feature"]); continue
            lat, lon = f[1], f[2]
        else:
            lat, lon = R["lat"], R["lon"]
        hdeg = R["size_km"] / KM_PER_DEG
        wdeg = min(R["size_km"] / (KM_PER_DEG * max(math.cos(math.radians(lat)), 0.2)), 60.0)
        west, north = lon - wdeg / 2, min(89.9, lat + hdeg / 2)
        want_ppd = MAX_SIDE / max(wdeg, hdeg)
        usable = sorted(levels, key=lambda l: 1 / l["deg"])
        L = next((l for l in usable if 1 / l["deg"] >= min(want_ppd, NATIVE_PPD) * 0.98), usable[-1])
        wpx, hpx = round(wdeg / L["deg"]), round(hdeg / L["deg"])
        t0 = time.time()
        try:
            img, n, missing = fetch_area(levels, template, L, west, north, wpx, hpx)
        except Exception as e:
            log(f"FAILED {R['name']}: {e!r}"); continue
        scale = min(1.0, MAX_SIDE / max(wpx, hpx))
        if scale < 1:
            img = img.resize((round(wpx * scale), round(hpx * scale)), Image.LANCZOS)
        p = np.asarray(img, dtype=np.float32)
        ppd = p.shape[1] / wdeg
        # replace the largest-scale brightness with the base map's, keep all the fine detail
        b = base_crop(west, north, wdeg, hdeg, (p.shape[1], p.shape[0]))
        sigma = 1.5 * ppd / BASE_PPD
        valid = p > 2
        blended = p - gaussian_filter(p, sigma) + gaussian_filter(b, sigma)
        blended = np.where(valid, blended, b)
        name = slug(R["name"]) + ".jpg"
        Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8), "L").save(work / name, quality=86, optimize=True, progressive=True)
        out_regions.append(dict(name=R["name"], group=R.get("group", ""), file=name, lat=round(lat, 4), lon=round(lon, 4),
                                west=round(west, 5), north=round(north, 5), wdeg=round(wdeg, 5), hdeg=round(hdeg, 5),
                                w=p.shape[1], h=p.shape[0], m_per_px=round(KM_PER_DEG * 1000 / ppd), size_km=R["size_km"]))
        log(f"{R['name']}: level {L['id']}, {p.shape[1]} x {p.shape[0]} px, {KM_PER_DEG * 1000 / ppd:.0f} m/px, "
            f"{n} tiles, {len(missing)} missing, {time.time() - t0:.1f} s")

    info = dict(source=ARGS.source, layer=LAYER,
                updated=time.strftime("%Y-%m-%d"), alignment_correlation=round(align_corr, 3), lon_correction_deg=shift,
                live_tiles=cors, template=template,
                levels=[{k: L[k] for k in ("id", "lon0", "lat0", "mw", "mh", "tw", "th", "deg")} for L in levels],
                regions=out_regions)
    json.dump(info, open(work / "regions.json", "w"), indent=1)
    if not out_regions:
        log("STOPPED: no regions could be made, so nothing was changed."); shutil.rmtree(work); sys.exit(1)
    if OUT.exists():
        shutil.rmtree(OUT)
    work.rename(OUT)                       # swap in the new set (removed regions disappear)
    log(f"Done: {len(out_regions)} regions saved to data/detail/")

if __name__ == "__main__":
    try:
        main()
    finally:
        REPORT.write_text("Detail tile report, " + time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()) + "\n\n" + "\n".join(log_lines) + "\n")
