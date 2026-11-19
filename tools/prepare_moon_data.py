"""
prepare_moon_data.py
Builds the data files used by the Lunar Globe Explorer web page.

Inputs (put them in tools/raw/):
  lroc_color_poles_8k.jpg   LROC WAC global mosaic, NASA SVS CGI Moon Kit (svs.gsfc.nasa.gov/4720)
  ldem_16_uint.png/.tif     LOLA elevation, 16 px/deg, in half-meters above a 1727.4 km sphere
  moon_iau_features.csv     IAU Gazetteer of Planetary Nomenclature (name, diameter, lat, lon)
  lunar100.csv             Charles Wood's Lunar 100 (name, description, x, y on a 5760 x 2880 grid)

Outputs (written to ../data/):
  moon_albedo_8k.jpg, moon_albedo_4k.jpg   greyscale base maps
  moon_height.png                         elevation packed into 16 bits (red = high byte, green = low byte), 8 m steps
  features.json                           all labels, landing sites and Lunar 100 entries

Run:  python3 prepare_moon_data.py
"""
import csv, json, re
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
RAW = Path(__file__).parent / "raw"
OUT = Path(__file__).parent.parent / "data"
OUT.mkdir(exist_ok=True)

# ---------- 1. Greyscale base maps ----------
color = Image.open(RAW / "lroc_color_poles_8k.jpg").convert("L")
color.save(OUT / "moon_albedo_8k.jpg", quality=86, optimize=True, progressive=True)
color.resize((4096, 2048), Image.LANCZOS).save(OUT / "moon_albedo_4k.jpg", quality=88, optimize=True, progressive=True)
print("albedo maps written")

# ---------- 2. Elevation ----------
src = next(p for p in RAW.iterdir() if p.name.startswith("ldem_16_uint"))
raw = np.array(Image.open(src)).astype(np.float64)        # half-meters above 1727.4 km
elev_m = raw * 0.5 - 10000.0                              # meters relative to the 1737.4 km reference sphere
print("elevation range (km):", elev_m.min() / 1000, elev_m.max() / 1000)
# resample to 2880 x 1440 (8 px/deg, about 3.8 km per pixel) with a float image, then quantize to 8 m steps
small = np.array(Image.fromarray(elev_m.astype(np.float32), mode="F").resize((2880, 1440), Image.BILINEAR))
packed = np.clip(np.round((small + 10000.0) / 8.0), 0, 65535).astype(np.uint16)  # elevation = value * 8 - 10000 m
rgb = np.zeros(packed.shape + (3,), np.uint8)
rgb[..., 0] = packed >> 8
rgb[..., 1] = packed & 255
Image.fromarray(rgb, "RGB").save(OUT / "moon_height.png", optimize=True)
print("height map written")

# ---------- 3. Feature names ----------
TYPES = {  # first word of an IAU name -> category used by the page
    "Mare": "mare", "Oceanus": "mare", "Lacus": "mare", "Sinus": "mare", "Palus": "mare",
    "Mons": "mount", "Montes": "mount", "Promontorium": "mount",
    "Vallis": "other", "Rima": "other", "Rimae": "other", "Rupes": "other", "Dorsum": "other",
    "Dorsa": "other", "Catena": "other", "Statio": "other", "Planitia": "other",
}
features = []
with open(RAW / "moon_iau_features.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        name = row["Feature_Name"].strip()
        diam = float(row["Diameter"] or 0)
        lat, lon = float(row["Center_Latitude"]), float(row["Center_Longitude"])
        lon = (lon + 180) % 360 - 180
        kind = TYPES.get(name.split(" ")[0], "crater")
        if kind == "crater" and re.search(r" [A-Z]{1,2}$", name):
            kind = "satellite"  # lettered satellite craters such as "Copernicus H"
        features.append([name, round(lat, 3), round(lon, 3), round(diam, 2), kind, int(row["Feature_ID"])])

lunar100 = []
with open(RAW / "lunar100.csv", newline="", encoding="utf-8") as f:
    for name, desc, x, y in csv.reader(f):
        if not x.strip().lstrip("-").isdigit():
            continue
        lon = (int(x) + 0.5) / 16 - 180
        lat = 90 - (int(y) + 0.5) / 16
        lunar100.append([name, round(lat, 3), round(lon, 3), desc])

# Landing sites (approximate published coordinates)
landings = [
    ["Apollo 11", 0.674, 23.473, "July 1969. Armstrong and Aldrin, first humans on the Moon (Mare Tranquillitatis)."],
    ["Apollo 12", -3.012, -23.422, "November 1969. Conrad and Bean landed beside the Surveyor 3 probe."],
    ["Apollo 14", -3.645, -17.471, "February 1971. Shepard and Mitchell explored the Fra Mauro highlands."],
    ["Apollo 15", 26.132, 3.634, "July 1971. Scott and Irwin, first Lunar Roving Vehicle, at Hadley Rille."],
    ["Apollo 16", -8.973, 15.500, "April 1972. Young and Duke explored the Descartes highlands."],
    ["Apollo 17", 20.191, 30.772, "December 1972. Cernan and Schmitt in the Taurus-Littrow valley; last crewed landing."],
    ["Luna 9", 7.08, -64.37, "February 1966. First soft landing and first photos from the lunar surface (USSR)."],
    ["Surveyor 1", -2.474, -43.339, "June 1966. First US soft landing."],
    ["Luna 16", -0.513, 56.364, "September 1970. First robotic sample return (USSR)."],
    ["Luna 17 / Lunokhod 1", 38.24, -35.00, "November 1970. First robotic rover on another world (USSR)."],
    ["Luna 21 / Lunokhod 2", 25.85, 30.45, "January 1973. Second Soviet rover, in Le Monnier crater."],
    ["Luna 24", 12.715, 62.213, "August 1976. Robotic sample return from Mare Crisium (USSR)."],
    ["Chang'e 3 / Yutu", 44.12, -19.51, "December 2013. Chinese lander and rover in Mare Imbrium."],
    ["Chang'e 4 / Yutu-2", -45.444, 177.588, "January 2019. First landing on the far side, in Von Karman crater."],
    ["Chang'e 5", 43.06, -51.92, "December 2020. Sample return of young basalts near Mons Rumker."],
    ["Chang'e 6", -41.64, -153.99, "June 2024. First sample return from the far side (Apollo basin)."],
    ["Chandrayaan-3", -69.37, 32.32, "August 2023. India's lander and rover near the south pole."],
    ["SLIM", -13.32, 25.25, "January 2024. Japan's precision lander near Shioli crater."],
    ["IM-1 Odysseus", -80.13, 1.44, "February 2024. First commercial lander, near Malapert A."],
    ["Blue Ghost 1", 18.56, 61.81, "March 2025. Commercial lander at Mons Latreille in Mare Crisium."],
]

json.dump({"features": features, "lunar100": lunar100, "landings": landings},
          open(OUT / "features.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
counts = {}
for f_ in features:
    counts[f_[4]] = counts.get(f_[4], 0) + 1
print("features:", counts, "lunar100:", len(lunar100), "landings:", len(landings))
