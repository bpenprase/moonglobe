"""
prepare_mars_data.py
Builds the data files for the Mars Globe Explorer (mars/index.html).

Runs on GitHub (see .github/workflows/build-mars-data.yml), because it downloads from NASA and USGS:
  - NASA Mars Trek tile service: THEMIS daytime infrared mosaic (Mars Odyssey, ASU) and the
    Viking MDIM 2.1 colorized mosaic (USGS / NASA Ames), stitched into global maps
  - NASA PDS Geosciences Node: MOLA MEGDR topography, 16 pixels per degree (Mars Global Surveyor)
  - USGS Astrogeology: IAU Gazetteer of Planetary Nomenclature for Mars

Outputs (mars/data/):
  mars_ir_8k.jpg, mars_ir_4k.jpg          THEMIS day IR, greyscale
  mars_color_8k.jpg, mars_color_4k.jpg    Viking colorized mosaic
  mars_height.png                         MOLA elevation: meters = (red x 256 + green) x 8 - 10000
  features.json                           IAU names (with feature types) and landing sites
  layers.json                             which Mars Trek layers were found (used by the close-up script)
A report is written to mars/tools/mars_report.txt.
"""
import io, json, math, re, sys, time, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data"
REPORT = HERE / "mars_report.txt"
TREK = "https://trek.nasa.gov/tiles/Mars/EQ"
R_KM = 3389.5

LAYER_CANDIDATES = {
    "ir": ["Mars_MO_THEMIS-IR-Day_mosaic_global_100m_v12", "Mars_MO_THEMIS-IR-Day_mosaic_global_100m_v11",
           "THEMIS_DayIR_ControlledMosaics_100m_v2_oct2018", "Mars_MO_THEMIS-IR-Day_mosaic_global_100m"],
    "color": ["Mars_Viking_MDIM21_ClrMosaic_global_232m", "Viking_MDIM21_ClrMosaic_global_232m"],
}
MOLA_URLS = [
    "https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg016/megt90n000eb.img",
    "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg016/megt90n000eb.img",
    "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg016/MEGT90N000EB.IMG",
]
NAMES_URL = "https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MARS_nomenclature_center_pts.zip"

log_lines = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); log_lines.append(s)

def get(url, tries=3, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "MarsGlobeExplorer/1.0 (education; Soka University of America)"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if getattr(e, "code", None) in (403, 404):
                return None
            if i == tries - 1:
                log("  failed:", url, repr(e)); return None
            time.sleep(2 * (i + 1))

# ---------------------------------------------------------------- Mars Trek layers
def tile_url(layer, ext, z, row, col):
    return f"{TREK}/{layer}/1.0.0/default/default028mm/{z}/{row}/{col}.{ext}"

def probe_layers():
    found = {}
    for key, names in LAYER_CANDIDATES.items():
        for name in names:
            for ext in ("jpg", "png"):
                data = get(tile_url(name, ext, 0, 0, 0), tries=2, timeout=30)
                if data:
                    try:
                        im = Image.open(io.BytesIO(data)); im.load()
                    except Exception:
                        continue
                    # deepest level available: test a tile near Gale crater (4.6 S, 137.4 E), well inside the mosaics
                    maxz = 0
                    for z in range(1, 12):
                        n = 256 * 2 ** z / 180.0
                        row, col = int((90 + 4.6) * n // 256), int((137.4 + 180) * n // 256)
                        if get(tile_url(name, ext, z, row, col), tries=2, timeout=30):
                            maxz = z
                        else:
                            break
                    found[key] = dict(layer=name, ext=ext, mode=im.mode, max_level=maxz,
                                      max_ppd=round(256 * 2 ** maxz / 180.0, 2))
                    log(f"Layer for {key}: {name} ({ext}, {im.mode}), deepest level {maxz} ({found[key]['max_ppd']} px/deg)")
                    break
            if key in found:
                break
        if key not in found:
            log(f"No Mars Trek layer found for {key}. Tried: {names}")
    return found

def stitch_global(layer, ext, z, mode):
    cols, rows = 2 ** (z + 1), 2 ** z
    canvas = Image.new(mode, (cols * 256, rows * 256))
    jobs = [(r, c) for r in range(rows) for c in range(cols)]
    missing = 0
    def one(rc):
        r, c = rc
        return rc, get(tile_url(layer, ext, z, r, c))
    with ThreadPoolExecutor(8) as ex:
        for (r, c), data in ex.map(one, jobs):
            if not data:
                missing += 1; continue
            canvas.paste(Image.open(io.BytesIO(data)).convert(mode), (c * 256, r * 256))
    log(f"  stitched {layer} level {z}: {cols * 256} x {rows * 256} px, {missing} of {len(jobs)} tiles missing")
    return canvas

# ---------------------------------------------------------------- MOLA
def load_mola():
    for url in MOLA_URLS:
        data = get(url, timeout=300)
        if data and len(data) == 5760 * 2880 * 2:
            a = np.frombuffer(data, dtype=">i2").reshape(2880, 5760).astype(np.float32)
            a = np.roll(a, 2880, axis=1)             # columns start at 0 E in the file; we want -180 at the left
            log(f"MOLA 16 px/deg loaded from {url}: {a.min() / 1000:.2f} to {a.max() / 1000:.2f} km")
            return a
        log("  MOLA not usable from", url, "bytes:", None if data is None else len(data))
    sys.exit("Could not download MOLA topography")

def hillshade(h, ppd):
    """Simple shaded relief (sun from the west, as in the THEMIS daytime images) used to check map alignment."""
    gy, gx = np.gradient(h)
    lat = np.radians(90 - (np.arange(h.shape[0]) + 0.5) / ppd)[:, None]
    m_per_px = 2 * math.pi * R_KM * 1000 / 360 / ppd
    sx = gx / (m_per_px * np.maximum(np.cos(lat), 0.05)); sy = -gy / m_per_px
    return (-sx * 0.7 + sy * 0.3) / np.sqrt(1 + sx * sx + sy * sy)

def best_shift(img, ref):
    """Longitude shift (in pixels) that best lines img up with ref, searched over the whole circle."""
    band = slice(int(img.shape[0] * 0.25), int(img.shape[0] * 0.75))
    a = img[band] - img[band].mean(); b = ref[band] - ref[band].mean()
    fa, fb = np.fft.rfft(a, axis=1), np.fft.rfft(b, axis=1)
    xc = np.fft.irfft((fb * np.conj(fa)).sum(axis=0), n=a.shape[1])
    k = int(np.argmax(np.abs(xc)))                     # thermal brightness can be anti-correlated with shading
    peak = float(abs(xc[k])); k = k - a.shape[1] if k > a.shape[1] // 2 else k
    norm = math.sqrt((a * a).sum() * (b * b).sum()) + 1e-9
    return k, peak / norm, abs(float((a * b).sum() / norm))

def finish_ir(img, h):
    """Fill the THEMIS gaps (poles above about 67 degrees, and small gores) with MOLA shaded relief matched to
    the infrared tones, then stretch the contrast so landforms show up at the scale of the whole planet."""
    from scipy.ndimage import binary_erosion, gaussian_filter
    a = np.asarray(img, dtype=np.float32)
    valid = binary_erosion(a > 3, iterations=3)
    hs = hillshade(h, 16.0)
    hs = np.asarray(Image.fromarray(hs.astype(np.float32), "F").resize(img.size, Image.BILINEAR), dtype=np.float32)
    sub = (slice(None, None, 4), slice(None, None, 4))
    va, vh = a[sub][valid[sub]], hs[sub][valid[sub]]
    c = np.corrcoef(va, vh)[0, 1]
    if c < 0:
        hs = -hs; vh = -vh
    hs = (hs - vh.mean()) / (vh.std() + 1e-6) * va.std() + va.mean()
    filled = np.where(valid, a, hs)
    w = gaussian_filter(valid.astype(np.float32), 6)
    out = filled * w + hs * (1 - w)
    # this THEMIS version is flattened at large scales, so add some MOLA relief everywhere:
    # it makes the volcanoes, basins and canyon walls readable when the whole planet is in view
    out = out + 0.7 * (hs - va.mean())
    lo, hi = np.percentile(out[sub], [0.5, 99.7])
    out = np.clip((out - lo) / (hi - lo), 0, 1) ** 0.95 * 255
    log(f"  infrared gaps filled from MOLA relief ({100 * (1 - valid.mean()):.1f}% of the map, relief correlation {c:+.2f}); contrast stretched")
    return Image.fromarray(out.astype(np.uint8), "L")

# ---------------------------------------------------------------- names
KIND_BY_TYPE = {
    "volcano": ["Mons", "Montes", "Tholus", "Tholi", "Patera", "Paterae"],
    "canyon": ["Vallis", "Valles", "Chasma", "Chasmata", "Fossa", "Fossae", "Labyrinthus", "Catena", "Catenae",
               "Sulci", "Sulcus", "Rima", "Rimae", "Cavus", "Cavi"],
    "region": ["Planitia", "Planum", "Plana", "Terra", "Terrae", "Vastitas", "Regio"],
    "crater": ["Crater", "Craters"],
    "albedo": ["Albedo Feature"],
}
TYPE_TO_KIND = {t.lower(): k for k, ts in KIND_BY_TYPE.items() for t in ts}

def load_names():
    import shapefile   # pyshp
    data = get(NAMES_URL, timeout=120)
    if not data:
        sys.exit("Could not download the Mars nomenclature")
    z = zipfile.ZipFile(io.BytesIO(data))
    dbf = [n for n in z.namelist() if n.lower().endswith(".dbf")][0]
    r = shapefile.Reader(dbf=io.BytesIO(z.read(dbf)))
    fields = [f[0] for f in r.fields[1:]]
    log("Nomenclature fields:", fields)
    recs = [dict(zip(fields, rec)) for rec in r.records()]
    log("  first record:", {k: str(v)[:60] for k, v in recs[0].items()})
    def f(rec, *names):
        low = {k.lower(): v for k, v in rec.items()}
        for n in names:
            if n in low and low[n] not in (None, ""):
                return low[n]
        return None
    out, kinds = [], {}
    for rec in recs:
        approval = str(f(rec, "approval", "approvalst") or "")
        if approval and "drop" in approval.lower():
            continue
        name = f(rec, "clean_name", "name")
        lat = f(rec, "center_lat", "centerlat", "lat")
        lon = f(rec, "center_lon", "centerlon", "lon")
        if name is None or lat is None or lon is None:
            continue
        lon = (float(lon) + 180) % 360 - 180
        diam = float(f(rec, "diameter", "diam") or 0)
        # the type field looks like "Crater, craters" or "Mons, montes": singular, then plural
        parts = [t.strip() for t in str(f(rec, "type", "feature_ty", "featuretyp") or "").split(",") if t.strip()]
        parts = [t[0].upper() + t[1:] for t in parts]
        last = str(name).split(" ")[-1]
        ftype = next((t for t in parts if t.lower() == last.lower()), parts[0] if parts else "")
        kind = TYPE_TO_KIND.get(parts[0].lower()) if parts else None
        kind = kind or TYPE_TO_KIND.get(last.lower(), "other")
        link = str(f(rec, "link") or "")
        m = re.search(r"Feature/(\d+)", link)
        fid = int(m.group(1)) if m else int(f(rec, "id", "feature_id") or 0)
        origin = re.sub(r"\s+", " ", str(f(rec, "origin") or "")).strip()[:220]
        out.append([str(name), round(float(lat), 3), round(lon, 3), round(diam, 2), kind, fid, ftype, origin])
        kinds[kind] = kinds.get(kind, 0) + 1
    log(f"Names: {len(out)} features by kind {kinds}")
    return out

LANDINGS = [
    ["Viking 1", 22.27, -47.95, "July 1976. First successful long-lived Mars lander (NASA), in Chryse Planitia."],
    ["Viking 2", 47.67, 134.28, "September 1976. Second Viking lander, in Utopia Planitia."],
    ["Mars Pathfinder / Sojourner", 19.13, -33.22, "July 1997. First Mars rover, Sojourner, at the mouth of Ares Vallis."],
    ["Spirit (MER-A)", -14.57, 175.47, "January 2004. Rover in Gusev crater; found evidence of ancient hot springs."],
    ["Opportunity (MER-B)", -1.95, -5.53, "January 2004. Rover at Meridiani Planum; drove more than 45 km in 14 years."],
    ["Phoenix", 68.22, -125.75, "May 2008. Arctic lander that dug up water ice just below the surface."],
    ["Curiosity (MSL)", -4.59, 137.44, "August 2012. Nuclear-powered rover in Gale crater, climbing Mount Sharp."],
    ["InSight", 4.50, 135.62, "November 2018. Geophysics lander that recorded more than 1,300 marsquakes."],
    ["Perseverance and Ingenuity", 18.44, 77.45, "February 2021. Rover collecting samples in Jezero crater's ancient river delta; Ingenuity made the first powered flight on another planet."],
    ["Zhurong (Tianwen-1)", 25.07, 109.93, "May 2021. China's first Mars rover, in southern Utopia Planitia."],
    ["Mars 3", -44.9, -160.1, "December 1971. Soviet lander, the first soft landing on Mars; it transmitted for about 20 seconds."],
    ["Beagle 2", 11.53, 90.43, "December 2003. British lander; found intact by orbiter images in 2015, but its solar panels never fully opened."],
    ["Schiaparelli", -2.05, -6.21, "October 2016. European test lander that crashed during descent."],
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    layers = probe_layers()
    json.dump(layers, open(OUT / "layers.json", "w"), indent=1)

    h = load_mola()                                         # meters, 2880 x 5760, -180..180
    small = np.array(Image.fromarray(h, "F").resize((2880, 1440), Image.BILINEAR))
    packed = np.clip(np.round((small + 10000.0) / 8.0), 0, 65535).astype(np.uint16)
    rgb = np.zeros(packed.shape + (3,), np.uint8); rgb[..., 0] = packed >> 8; rgb[..., 1] = packed & 255
    Image.fromarray(rgb, "RGB").save(OUT / "mars_height.png", optimize=True)
    log("Height map written: 2880 x 1440, 8 m steps")
    shade = hillshade(np.array(Image.fromarray(h, "F").resize((2048, 1024), Image.BILINEAR)), 2048 / 360)

    ref = {"ir": shade}
    for key in ("ir", "color"):
        if key not in layers:
            continue
        L = layers[key]
        mode = "L" if key == "ir" else "RGB"
        # alignment check at level 2 (2048 x 1024): infrared against MOLA relief, color against the infrared map
        g2 = np.asarray(stitch_global(L["layer"], L["ext"], 2, mode).convert("L"), dtype=np.float32)
        against = ref.get(key, ref.get("ir_img", shade))
        k, peak, as_is = best_shift(g2, against)
        log(f"Alignment of {key} with {'MOLA relief' if key == 'ir' or 'ir_img' not in ref else 'the infrared map'}: "
            f"correlation {as_is:.3f} as is, best {peak:.3f} at a shift of {k} px ({k * 360 / 2048:+.2f} deg)")
        if key == "ir":
            ref["ir_img"] = np.roll(g2, k if (abs(k) > 2 and peak > as_is + 0.05) else 0, axis=1)
        L["lon_shift_deg"] = k * 360 / 2048 if (abs(k) > 2 and peak > as_is + 0.05) else 0.0
        z = min(4, L["max_level"])
        g = stitch_global(L["layer"], L["ext"], z, mode)
        if L["lon_shift_deg"]:
            g = Image.fromarray(np.roll(np.asarray(g), round(L["lon_shift_deg"] / 360 * g.width), axis=1))
            log(f"  applied a {L['lon_shift_deg']:+.2f} deg longitude correction")
        g8 = g.resize((8192, 4096), Image.LANCZOS) if g.width != 8192 else g
        if key == "ir":
            g8 = finish_ir(g8, h)
        name = "mars_ir" if key == "ir" else "mars_color"
        g8.save(OUT / f"{name}_8k.jpg", quality=86, optimize=True, progressive=True)
        g8.resize((4096, 2048), Image.LANCZOS).save(OUT / f"{name}_4k.jpg", quality=88, optimize=True, progressive=True)
        a = np.asarray(g8.convert("L"))
        log(f"  {name}_8k.jpg written; {100 * (a < 3).mean():.1f}% of pixels are empty (black)")
    json.dump(layers, open(OUT / "layers.json", "w"), indent=1)

    feats = load_names()
    json.dump({"features": feats, "landings": LANDINGS}, open(OUT / "features.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    log("features.json written")

if __name__ == "__main__":
    try:
        main()
    finally:
        REPORT.write_text("Mars data report, " + time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()) + "\n\n" + "\n".join(log_lines) + "\n")
