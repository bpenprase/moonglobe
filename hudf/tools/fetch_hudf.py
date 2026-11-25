"""
fetch_hudf.py
Downloads the Hubble Ultra Deep Field color images (ESA/Hubble, CC BY 4.0) and published galaxy catalogs
of the field from VizieR, into hudf_sources/. Run by the "Fetch HUDF sources" GitHub workflow.
"""
import csv, io, json, sys, time, urllib.parse, urllib.request
from pathlib import Path

OUT = Path("hudf_sources"); OUT.mkdir(exist_ok=True)
LOG = open(OUT / "log.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n"); LOG.flush()

def get(url, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (moonglobe HUDF app; education)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# 1. images: try the largest versions ESA/Hubble publishes
IMAGES = {
    "heic0406a": "Hubble Ultra Deep Field (2004)",
    "heic1214a": "Hubble eXtreme Deep Field (2012)",
    "heic1406a": "Hubble Ultra Deep Field in ultraviolet light (2014)",
}
for code, title in IMAGES.items():
    for kind, ext in [("publicationjpg", "jpg"), ("large", "jpg"), ("original", "tif"), ("screen", "jpg")]:
        url = f"https://esahubble.org/media/archives/images/{kind}/{code}.{ext}"
        try:
            b = get(url, 900)
            p = OUT / f"{code}_{kind}.{ext}"; p.write_bytes(b)
            log("image", code, kind, len(b), "bytes")
        except Exception as e:
            log("image fail", code, kind, e)

# 2. catalogs: every table of each VizieR catalog, as CSV, via TAP
CATALOGS = {
    "J/AJ/150/31": "Rafelski et al. 2015, UVUDF photometry and photometric redshifts",
    "J/A+A/670/A4": "Bacon et al. 2023, MUSE Hubble Ultra Deep Field survey DR2 (spectroscopic redshifts)",
    "J/A+A/608/A2": "Inami et al. 2017, MUSE HUDF redshifts DR1",
    "J/AJ/132/926": "Coe et al. 2006, HUDF photometric redshifts",
    "J/AJ/132/1729": "Beckwith et al. 2006, HUDF ACS catalog",
}
TAP = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"
def tap(q, fmt="csv"):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": fmt, "QUERY": q}).encode()
    req = urllib.request.Request(TAP, data=data, headers={"User-Agent": "Mozilla/5.0 (moonglobe HUDF app)"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read().decode("utf-8", "replace")

info = {}
for cat, desc in CATALOGS.items():
    try:
        t = tap(f"SELECT table_name, description FROM TAP_SCHEMA.tables WHERE table_name LIKE '{cat}/%'")
        rows = list(csv.DictReader(io.StringIO(t)))
        log("catalog", cat, [r["table_name"] for r in rows])
        info[cat] = {"desc": desc, "tables": {}}
        for r in rows:
            tn = r["table_name"]
            try:
                cols = tap(f"SELECT column_name, unit, ucd, description FROM TAP_SCHEMA.columns WHERE table_name = '{tn}'")
                body = tap(f'SELECT * FROM "{tn}"')
                safe = tn.replace("/", "_").replace("+", "p")
                (OUT / f"{safe}.csv").write_text(body)
                (OUT / f"{safe}.columns.csv").write_text(cols)
                n = body.count("\n") - 1
                info[cat]["tables"][tn] = {"file": f"{safe}.csv", "rows": n, "desc": r["description"]}
                log("  table", tn, n, "rows")
            except Exception as e:
                log("  table fail", tn, e)
            time.sleep(1)
    except Exception as e:
        log("catalog fail", cat, e)
json.dump(info, open(OUT / "catalogs.json", "w"), indent=1)
log("done")
