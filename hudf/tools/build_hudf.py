"""
build_hudf.py
Builds the data for the HUDF Explorer from the downloaded sources and the fitted coordinates (cache/wcs.json):

  ../data/hudf.dzi, ../data/hudf_files/   zoomable tiles of the 6200 x 6200 press image (Deep Zoom format)
  ../data/catalog.json                    every UVUDF object with its pixel position, shape, magnitudes and redshifts,
                                          joined with the MUSE DR2 spectroscopic redshifts, masses and star-formation rates
  ../data/wcs.json                        pixel <-> sky coordinate solution, for the page
  ../data/preview.jpg                     a small preview

Usage: python3 build_hudf.py SOURCES_DIR [--no-tiles]
"""
import json, math, sys, warnings
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
warnings.simplefilter("ignore")
from astropy.table import Table

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1])
OUT = HERE.parent / "data"; OUT.mkdir(exist_ok=True)
WCS = json.load(open(HERE / "cache" / "wcs.json"))
W, H = WCS["width"], WCS["height"]


def terms(u, v, order):
    t = [np.ones_like(u)]
    for k in range(1, order + 1):
        for j in range(k + 1): t.append(u ** (k - j) * v ** j)
    return np.stack(t, 1)


def tan(ra, dec):
    a, d, a0, d0 = np.radians(ra), np.radians(dec), math.radians(WCS["ra0"]), math.radians(WCS["dec0"])
    c = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(a - a0)
    return (np.degrees(np.cos(d) * np.sin(a - a0) / c) * 3600,
            np.degrees((np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(a - a0)) / c) * 3600)


def sky_to_px(ra, dec):
    xi, eta = tan(np.asarray(ra, float), np.asarray(dec, float))
    T = terms(xi / WCS["fwd_scale"], eta / WCS["fwd_scale"], WCS["fwd_order"])
    return T @ np.array(WCS["fx"]), T @ np.array(WCS["fy"])


# ------------------------------------------------------------------ the UVUDF catalog
cat = Table.read(SRC / "uvudf_cat.fits")
n = len(cat)
col = lambda c: np.array(cat[c], float)
RA, DEC = col("RA"), col("DEC")
PX, PY = sky_to_px(RA, DEC)

# the catalog's own pixel frame (X, Y) -> image pixels, to turn its position angles into image angles
A = np.stack([np.ones(n), col("X"), col("Y")], 1)
mx, *_ = np.linalg.lstsq(A, PX, rcond=None); my, *_ = np.linalg.lstsq(A, PY, rcond=None)
J = np.array([[mx[1], mx[2]], [my[1], my[2]]])
th = np.radians(col("THETA"))
dx = J[0, 0] * np.cos(th) + J[0, 1] * np.sin(th); dy = J[1, 0] * np.cos(th) + J[1, 1] * np.sin(th)
ANG = np.degrees(np.arctan2(dy, dx))                  # major axis in image pixels, degrees from +x toward +y (down)
ell = np.clip(col("ELLIPTICITY"), 0, 0.85)
area = np.maximum(col("AREAF"), 9)
A_AX = np.sqrt(area / math.pi / (1 - ell))             # isophotal semi-major axis, pixels
B_AX = A_AX * (1 - ell)

BANDS = ["F225W", "F275W", "F336W", "F435W", "F606W", "F775W", "F850LP", "F105W", "F125W", "F140W", "F160W"]
mags = np.stack([col("MAG_" + b) for b in BANDS], 1)
mags[(mags <= 0) | (mags > 40) | ~np.isfinite(mags)] = np.nan
REFS = {1: "Szokoly et al. 2004", 2: "Le Fèvre et al. 2004 (VVDS)", 3: "Mignoli et al. 2005 (K20)", 4: "Vanzella et al. 2008-2009 (GOODS/FORS2)",
        5: "Ravikumar et al. 2007", 6: "Popesso et al. 2009 (GOODS/VIMOS)", 7: "Balestra et al. 2010 (GOODS/VIMOS)", 8: "Kurk et al. 2013 (GMASS)",
        9: "Morris et al. 2015 (3D-HST grism)"}

# ------------------------------------------------------------------ MUSE DR2 (Bacon et al. 2023)
def vizier_tables(path):
    L = open(path, encoding="utf-8", errors="replace").read().split("\n"); out = {}; i = 0
    while i < len(L):
        if L[i].startswith("#Table"):
            name = L[i].split()[1].rstrip(":"); j = i + 1
            while j < len(L) and (L[j].startswith("#") or not L[j].strip()): j += 1
            hdr = [h.strip() for h in L[j].split("|")]; k = j + 3; rows = []
            while k < len(L) and L[k].strip() and not L[k].startswith("#"):
                rows.append(dict(zip(hdr, [x.strip() for x in L[k].split("|")]))); k += 1
            out[name] = rows; i = k
        else: i += 1
    return out

def fnum(s):
    try: return float(s)
    except Exception: return float("nan")

muse = vizier_tables(SRC / "viz_J_ApA_670_A4.tsv")["J_A_A_670_A4_dr2-main"]
import re as _re
GREEK = {"LYALPHA": "Lyman-α", "HALPHA": "Hα (hydrogen)", "HBETA": "Hβ (hydrogen)", "HGAMMA": "Hγ (hydrogen)", "HDELTA": "Hδ (hydrogen)",
         "CaK": "Ca II K (calcium, absorption)", "CaH": "Ca II H (calcium, absorption)", "CaG": "G band (absorption)", "MgB": "Mg b (magnesium, absorption)",
         "NaD": "Na D (sodium, absorption)", "OII3727": "[O II] 3727 (oxygen)", "OII3727b": "[O II] 3727 (oxygen)"}
def line_name(code):
    if not code: return code
    if code.startswith("[") : return code + (" (oxygen)" if "O I" in code else "")
    base = code[:-1] if code.endswith("b") and code[:-1] in GREEK | {"LYALPHA": 1} else code
    if base in GREEK: return GREEK[base] + (" (emission)" if base.startswith("LYA") else "")
    m = _re.match(r"([A-Z][a-z]?)([IVX]+)(\d+)b?$", base if not base.endswith("b") else base[:-1])
    if m:
        el, ion, wl = m.groups()
        names = {"C": "carbon", "O": "oxygen", "Mg": "magnesium", "Fe": "iron", "Si": "silicon", "Al": "aluminium", "Ne": "neon", "N": "nitrogen", "He": "helium"}
        forb = {("O", "III", "5007"), ("O", "III", "4959"), ("O", "II", "3726"), ("O", "II", "3729"), ("Ne", "III", "3869"), ("Ne", "IV", "2424"), ("N", "II", "6584"), ("S", "II", "6717")}
        s_ = f"[{el} {ion}] {wl}" if (el, ion, wl) in forb else f"{el} {ion} {wl}"
        return f"{s_} ({names.get(el, el)})"
    m = _re.match(r"H(\d+)$", base)
    if m: return f"H{m.group(1)} (hydrogen)"
    return code
mra = np.array([fnum(r["RAJ2000"]) for r in muse]); mde = np.array([fnum(r["DEJ2000"]) for r in muse])
mmag = np.array([fnum(r["F775Wmag"]) for r in muse])
cosd = math.cos(math.radians(WCS["dec0"]))
tree = cKDTree(np.stack([RA * cosd, DEC], 1) * 3600)
MUSE = [None] * n
mused = 0
for k, r in enumerate(muse):
    p = np.array([mra[k] * cosd, mde[k]]) * 3600
    idx = tree.query_ball_point(p, 0.7)                 # VizieR gives these positions to 0.36"; allow for that
    best, bs = None, 9
    for i in idx:
        sep = math.hypot(*(tree.data[i] - p))
        dm = abs(mags[i, 5] - mmag[k]) if np.isfinite(mmag[k]) and np.isfinite(mags[i, 5]) else 0.6
        s = (sep / 0.3) ** 2 + (dm / 0.5) ** 2
        if s < bs: best, bs = i, s
    if best is None or bs > 6: continue
    if MUSE[best] is not None and MUSE[best][-1] <= bs: continue
    line = r.get("LineSNRMax", "")
    MUSE[best] = [int(r["ID"]), fnum(r["z"]), fnum(r["logMassP"]), fnum(r["logSFRP"]), line_name(line), bs]
mused = sum(m is not None for m in MUSE)
print(f"MUSE DR2: {len(muse)} sources, {mused} matched to UVUDF objects")

# ------------------------------------------------------------------ write the catalog
def r(x, nd):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)

specz, specref = col("SPECZ"), np.array(cat["SPECZ_REF"])
rows, agree = [], []
for i in range(n):
    if not (-30 < PX[i] < W + 30 and -30 < PY[i] < H + 30): continue
    m = MUSE[i]
    zs, zsrc = None, None
    if m and np.isfinite(m[1]): zs, zsrc = m[1], "MUSE (Bacon et al. 2023)"
    if specz[i] > 0:
        if zs is not None: agree.append(abs(zs - specz[i]) / (1 + zs) < 0.02)
        else: zs, zsrc = specz[i], REFS.get(int(specref[i]), "literature")
    rows.append([int(cat["ID"][i]), r(PX[i], 1), r(PY[i], 1), r(RA[i], 6), r(DEC[i], 6),
                 r(A_AX[i], 1), r(B_AX[i], 1), r(ANG[i], 0),
                 r(col("Z_BPZ")[i], 3), r(col("ZMIN_BPZ")[i], 2), r(col("ZMAX_BPZ")[i], 2), r(col("ODDS_BPZ")[i], 2), r(col("Z_EAZY")[i], 3),
                 r(zs, 4), zsrc, r(col("GRISMZ")[i], 3) if col("GRISMZ")[i] > 0 else None,
                 int(cat["STAR"][i]), r(col("STELLARITY")[i], 2), int(cat["COE_ID"][i]) if cat["COE_ID"][i] > 0 else None,
                 [r(v, 2) for v in mags[i]],
                 m[0] if m else None, r(m[2], 2) if m else None, r(m[3], 2) if m else None, m[4] if m else None,
                 r(col("FWHM")[i], 1)])
print(f"catalog: {len(rows)} objects on the image; {sum(1 for x in rows if x[13] is not None)} with spectroscopic redshifts; "
      f"MUSE and older spectra agree for {sum(agree)}/{len(agree)}")
FIELDS = ["id", "x", "y", "ra", "dec", "a", "b", "pa", "zb", "zbmin", "zbmax", "odds", "ze", "zs", "zsrc", "zg", "star", "stellarity", "coe",
          "mags", "muse", "logm", "logsfr", "line", "fwhm"]
json.dump(dict(fields=FIELDS, bands=BANDS, wavelengths=[225, 275, 336, 435, 606, 775, 850, 1050, 1250, 1400, 1600], rows=rows,
               sources={"uvudf": "Rafelski et al. 2015, AJ 150, 31 (UVUDF): positions, photometry, BPZ and EAZY photometric redshifts",
                        "muse": "Bacon et al. 2023, A&A 670, A4 (MUSE Hubble Ultra Deep Field Surveys, DR2): spectroscopic redshifts, stellar masses, SFRs"}),
          open(OUT / "catalog.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump({k: WCS[k] for k in ["width", "height", "ra0", "dec0", "fwd_order", "fwd_scale", "fx", "fy", "inv_order", "inv_scale", "ix", "iy",
                               "pixscale", "north_deg", "parity", "matches", "rms_px"]}, open(OUT / "wcs.json", "w"), separators=(",", ":"))

# ------------------------------------------------------------------ tiles
img = Image.open(SRC / "heic0406a_large.jpg").convert("RGB")
img.resize((1200, 1200), Image.LANCZOS).save(OUT / "preview.jpg", quality=86)
if "--no-tiles" not in sys.argv:
    import shutil
    TS, OV = 254, 1
    base = OUT / "hudf_files"
    if base.exists(): shutil.rmtree(base)
    maxlev = math.ceil(math.log2(max(W, H)))
    cur = img
    for lev in range(maxlev, -1, -1):
        w, h = cur.size
        d = base / str(lev); d.mkdir(parents=True)
        for ty in range(math.ceil(h / TS)):
            for tx in range(math.ceil(w / TS)):
                x0, y0 = max(0, tx * TS - OV), max(0, ty * TS - OV)
                x1, y1 = min(w, (tx + 1) * TS + OV), min(h, (ty + 1) * TS + OV)
                cur.crop((x0, y0, x1, y1)).save(d / f"{tx}_{ty}.jpg", quality=84, optimize=True)
        if lev: cur = cur.resize((max(1, (w + 1) // 2), max(1, (h + 1) // 2)), Image.LANCZOS)
    (OUT / "hudf.dzi").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" '
                                  f'Format="jpg" Overlap="{OV}" TileSize="{TS}"><Size Width="{W}" Height="{H}"/></Image>\n')
    print("tiles written, levels 0 to", maxlev)
