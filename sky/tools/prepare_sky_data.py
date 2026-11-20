"""
prepare_sky_data.py
Builds the data for the Celestial Sphere Explorer (sky/index.html) from the open d3-celestial data set
by Olaf Frohn (https://github.com/ofrohn/d3-celestial, BSD license), which is drawn from the Hipparcos
catalog, the IAU constellation boundaries, and standard deep-sky catalogs.

Outputs (sky/data/):
  stars.json       every star to magnitude 7.5: [ra, dec, magnitude, B-V color, HIP number]
  sky.json         star names, constellations (names, figures, boundaries, areas), Messier objects,
                   bright galaxies and other bright deep-sky showpieces
  milkyway.jpg     the Milky Way, painted from its outline contours, for the background of the sphere
Run:  python3 sky/tools/prepare_sky_data.py   (downloads the source files from GitHub)
"""
import json, math, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data"
OUT.mkdir(exist_ok=True)
SRC = "https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/"
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)

def load(name):
    p = CACHE / name
    if not p.exists():
        p.write_bytes(urllib.request.urlopen(SRC + name, timeout=120).read())
    return json.loads(p.read_text(encoding="utf-8"))

ra360 = lambda lon: round(lon % 360, 4)
fnum = lambda v: float(v) if str(v).strip() not in ("", "None") else None

# ---------------------------------------------------------------- stars
stars = []
for f in load("stars.8.json")["features"]:
    p = f["properties"]
    if p["mag"] > 7.5:
        continue
    lon, lat = f["geometry"]["coordinates"]
    stars.append([ra360(lon), round(lat, 4), round(p["mag"], 2), round(fnum(p["bv"]) if fnum(p["bv"]) is not None else 0.6, 2), f["id"]])
stars.sort(key=lambda s: s[2])                # brightest first
json.dump(stars, open(OUT / "stars.json", "w"), separators=(",", ":"))
hips = {s[4] for s in stars}
print("stars:", len(stars))

# ---------------------------------------------------------------- star names
names = {}
for hip, n in load("starnames.json").items():
    hip = int(hip)
    if hip not in hips:
        continue
    proper, bayer, flam, con = n.get("name", ""), n.get("bayer", ""), n.get("flam", ""), n.get("c", "")
    if proper or bayer or flam:
        names[hip] = [proper, bayer, flam, con]
print("named stars:", len(names), "proper names:", sum(1 for v in names.values() if v[0]))

# ---------------------------------------------------------------- constellations
cons = {}
for f in load("constellations.json")["features"]:
    p = f["properties"]
    lon, lat = f["geometry"]["coordinates"]
    cons[f["id"]] = dict(id=f["id"], name=p["name"], gen=p["gen"], en=p["en"].replace(" ", " "), rank=int(p["rank"]),
                         lra=ra360(lon), ldec=round(lat, 3), lines=[], bounds=[])
for f in load("constellations.lines.json")["features"]:
    for line in f["geometry"]["coordinates"]:
        cons[f["id"]]["lines"].append([[ra360(a), round(b, 4)] for a, b in line])
for f in load("constellations.bounds.json")["features"]:
    g = f["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for poly in polys:
        cons[f["id"]]["bounds"].append([[ra360(a), round(b, 4)] for a, b in poly[0]])
borders = []
for f in load("constellations.borders.json")["features"]:
    for line in f["geometry"]["coordinates"]:
        borders.append([[ra360(a), round(b, 4)] for a, b in line])

# ---------------------------------------------------------------- deep sky
TYPE = {"gc": "Globular cluster", "oc": "Open cluster", "s": "Spiral galaxy", "e": "Elliptical galaxy", "i": "Irregular galaxy",
        "s0": "Lenticular galaxy", "g": "Galaxy", "sd": "Dwarf galaxy", "pn": "Planetary nebula", "snr": "Supernova remnant",
        "sfr": "Star-forming nebula", "en": "Emission nebula", "rn": "Reflection nebula", "bn": "Bright nebula", "pos": "Star cloud or asterism"}
messier = []
for f in load("messier.json")["features"]:
    p = f["properties"]; lon, lat = f["geometry"]["coordinates"]
    messier.append(dict(id=p["name"], name=p["alt"].replace("´", "'").replace("’", "'"), ngc=p["desig"], type=p["type"],
                        tname=TYPE.get(p["type"], p["type"]), mag=fnum(p["mag"]), dim=p["dim"], ra=ra360(lon), dec=round(lat, 4)))
# a few corrections and friendlier names
fix = {"M31": "Andromeda Galaxy", "M33": "Triangulum Galaxy", "M44": "Beehive Cluster (Praesepe)", "M45": "Pleiades (Seven Sisters)",
       "M51": "Whirlpool Galaxy", "M101": "Pinwheel Galaxy", "M104": "Sombrero Galaxy", "M77": "Cetus A", "M87": "Virgo A",
       "M24": "Sagittarius Star Cloud", "M73": "Four-star asterism", "M64": "Black Eye Galaxy", "M7": "Ptolemy's Cluster"}
for m in messier:
    if m["id"] in fix:
        m["name"] = fix[m["id"]]

GAL_NAMES = {"NGC 5128": "Centaurus A", "NGC 253": "Sculptor Galaxy", "NGC 55": "Sculptor dwarf neighbor NGC 55", "NGC 4565": "Needle Galaxy",
             "NGC 2403": "NGC 2403 (Camelopardalis)", "NGC 7331": "Deer Lick Galaxy", "NGC 4631": "Whale Galaxy", "NGC 3628": "Hamburger Galaxy",
             "NGC 6946": "Fireworks Galaxy", "NGC 300": "Sculptor Pinwheel", "NGC 1365": "Great Barred Spiral", "NGC 2903": "NGC 2903 (Leo)",
             "NGC 4038": "Antennae Galaxies", "NGC 6822": "Barnard's Galaxy", "IC 342": "Hidden Galaxy", "NGC 3115": "Spindle Galaxy",
             "NGC 2683": "UFO Galaxy", "NGC 4945": "NGC 4945 (Centaurus)", "NGC 147": "NGC 147 (Andromeda's companion)",
             "NGC 185": "NGC 185 (Andromeda's companion)", "NGC 891": "Silver Sliver Galaxy", "NGC 4449": "Box Galaxy", "NGC 7793": "NGC 7793 (Sculptor)",
             "NGC 1316": "Fornax A", "NGC 5907": "Splinter Galaxy", "NGC 4216": "NGC 4216 (Virgo)", "NGC 3521": "Bubble Galaxy",
             "NGC 1097": "NGC 1097 (Fornax)", "NGC 4725": "NGC 4725 (Coma)", "NGC 5195": "Whirlpool's companion"}
mpos = [(m["ra"], m["dec"]) for m in messier]
mngc = {m["ngc"].replace(" ", "") for m in messier}
galaxies = []
for f in load("dsos.14.json")["features"]:
    p = f["properties"]
    if p["type"] not in ("s", "e", "i", "s0", "g", "sd"):
        continue
    mag = fnum(p["mag"])
    if mag is None or mag > 11:
        continue
    lon, lat = f["geometry"]["coordinates"]; ra, dec = ra360(lon), round(lat, 4)
    desig = p["desig"]
    if desig.replace(" ", "") in mngc or any(abs(ra - a) * math.cos(math.radians(dec)) < 0.08 and abs(dec - b) < 0.08 for a, b in mpos):
        continue                       # already in the Messier list
    galaxies.append(dict(id=desig, name=GAL_NAMES.get(desig, ""), type=p["type"], tname=TYPE.get(p["type"], "Galaxy"),
                         mag=mag, dim=p["dim"], ra=ra, dec=dec))
galaxies += [dict(id="LMC", name="Large Magellanic Cloud", type="i", tname="Irregular galaxy", mag=0.9, dim="645x550", ra=80.894, dec=-69.756),
             dict(id="SMC", name="Small Magellanic Cloud", type="i", tname="Irregular galaxy", mag=2.7, dim="320x185", ra=13.187, dec=-72.829)]
galaxies.sort(key=lambda g: g["mag"])

SHOW_NAMES = {"Cr 140": "Collinder 140", "Cr 399": "Coathanger (Brocchi's Cluster)", "IC 2602": "Southern Pleiades", "NGC 6121": "M4 region",
              "NGC 2632": "Beehive", "Cr 39": "Alpha Persei Cluster", "C 41": "Hyades", "Cr 256": "Coma Star Cluster", "NGC 104": "47 Tucanae",
              "NGC 869": "Double Cluster (h Persei)", "NGC 884": "Double Cluster (chi Persei)", "NGC 2244": "Rosette Cluster",
              "NGC 2264": "Christmas Tree Cluster", "NGC 2362": "Tau Canis Majoris Cluster", "NGC 2451": "NGC 2451 (Puppis)", "NGC 2516": "Southern Beehive",
              "NGC 3372": "Carina Nebula", "NGC 3532": "Wishing Well Cluster", "NGC 5139": "Omega Centauri", "NGC 6231": "Northern Jewel Box",
              "IC 2391": "Omicron Velorum Cluster", "NGC 6405": "Butterfly Cluster", "NGC 6475": "Ptolemy's Cluster", "NGC 6611": "Eagle Nebula cluster",
              "GC": "Galactic Center (Sagittarius A*)"}
showpieces = []
for f in load("dsos.bright.json")["features"]:
    p = f["properties"]; lon, lat = f["geometry"]["coordinates"]; ra, dec = ra360(lon), round(lat, 4)
    if f["id"] in ("NGC 224", "NGC 598", "NGC 1976", "M 8", "M 45", "NGC 2632", "NGC 6405", "NGC 6475", "NGC 6611", "NGC 6121", "PGC 17223", "NGC 292"):
        continue                       # Messier objects or Magellanic Clouds, listed elsewhere
    showpieces.append(dict(id=f["id"], name=SHOW_NAMES.get(f["id"], ""), type=p["type"], tname=TYPE.get(p["type"], p["type"]),
                           mag=fnum(p["mag"]), dim=p["dim"], ra=ra, dec=dec))
showpieces.append(dict(id="Sgr A*", name="Galactic Center (Sagittarius A*)", type="pos", tname="Center of the Milky Way", mag=None, dim="",
                       ra=266.4168, dec=-29.0078))
showpieces = [s for s in showpieces if s["id"] != "GC"]

json.dump(dict(names=names, constellations=list(cons.values()), borders=borders, messier=messier, galaxies=galaxies,
               showpieces=showpieces), open(OUT / "sky.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("constellations:", len(cons), "border lines:", len(borders), "Messier:", len(messier), "galaxies:", len(galaxies),
      "showpieces:", len(showpieces))

# ---------------------------------------------------------------- Milky Way texture
# The Milky Way outlines are rings that circle the whole sky, so they are filled in galactic coordinates
# (where they run across the map) with an even-odd rule, then resampled to right ascension and declination.
W, H = 4096, 2048
G = np.array([[-0.0548755604, -0.8734370902, -0.4838350155],      # J2000 equatorial -> galactic rotation
              [+0.4941094279, -0.4448296300, +0.7469822445],
              [-0.8676661490, -0.1980763734, +0.4559837762]])
def eq2gal(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec)
    v = np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)])
    g = np.tensordot(G, v, axes=1)
    return np.degrees(np.arctan2(g[1], g[0])) % 360, np.degrees(np.arcsin(np.clip(g[2], -1, 1)))
def ring_mask(ring):
    l, b = eq2gal(np.array([a for a, _ in ring]) % 360, np.array([bb for _, bb in ring]))
    lu = np.degrees(np.unwrap(np.radians(l)))
    m = Image.new("1", (W, H), 0); d = ImageDraw.Draw(m)
    X = lambda ll: ll / 360 * W; Y = lambda bb: (90 - bb) / 180 * H
    if abs(lu[-1] - lu[0]) > 300 or (lu.max() - lu.min()) > 300:          # ring circles the whole sky: fill everything below it
        order = np.argsort(lu); lu, b = lu[order], b[order]
        for shift in (-360, 0, 360):
            pts = [(X(x + shift), Y(y)) for x, y in zip(lu, b)]
            pts += [(pts[-1][0], H + 2), (pts[0][0], H + 2)]
            d.polygon(pts, fill=1)
    else:
        for shift in (-360, 0, 360):
            d.polygon([(X(x + shift), Y(y)) for x, y in zip(lu, b)], fill=1)
    return np.asarray(m, bool)
acc_g = np.zeros((H, W), np.float32)
mw = load("mw.json")["features"]
for level, f in enumerate(mw):
    parity = np.zeros((H, W), bool)
    for poly in f["geometry"]["coordinates"]:
        for ring in poly:
            parity ^= ring_mask(ring)
    # make sure the galactic poles are outside (flip the parity if the convention came out reversed)
    if parity[0, 0] or parity[-1, 0]:
        parity = ~parity
    acc_g += parity.astype(np.float32)
    print(f"  Milky Way level {level + 1}: {100 * parity.mean():.1f}% of the sky")
acc_g /= max(1, len(mw))
# resample to right ascension (x, starting at RA 180 deg on the left edge, i.e. longitude -180) and declination (y)
ras = (np.arange(W) + 0.5) / W * 360 - 180
decs = 90 - (np.arange(H) + 0.5) / H * 180
RA, DEC = np.meshgrid(ras % 360, decs)
L, B = eq2gal(RA, DEC)
xi = np.clip((L / 360 * W).astype(int), 0, W - 1); yi = np.clip(((90 - B) / 180 * H).astype(int), 0, H - 1)
acc = acc_g[yi, xi]
img = Image.fromarray((np.clip(acc, 0, 1) ** 0.7 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
img.save(OUT / "milkyway.jpg", quality=88)
print("milkyway.jpg written")
