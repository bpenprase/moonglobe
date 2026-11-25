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

# 1. images: try the largest versions ESA/Hubble publishes (skipped when already downloaded)
IMAGES = {
    "heic0406a": "Hubble Ultra Deep Field (2004)",
    "heic1214a": "Hubble eXtreme Deep Field (2012)",
    "heic1406a": "Hubble Ultra Deep Field in ultraviolet light (2014)",
}
if "--catalogs-only" not in sys.argv:
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
# VizieR: the "asu-tsv" query returns every table of a catalog as tab-separated text. Try the mirrors in turn.
VIZ = ["https://vizier.cds.unistra.fr", "http://vizier.cfa.harvard.edu", "https://vizier.cfa.harvard.edu", "http://vizier.nao.ac.jp",
       "https://vizier.iucaa.in", "http://vizier.china-vo.org", "https://vizier.inasan.ru", "https://vizier.idia.ac.za"]
import re
def viz(cat):
    q = urllib.parse.urlencode({"-source": cat, "-out.all": "", "-out.max": "unlimited", "-out.form": "|"})
    for m in VIZ:
        url = f"{m}/viz-bin/asu-tsv?{q}"
        try:
            b = get(url, 300).decode("utf-8", "replace")
            nrows = sum(1 for L in b.splitlines() if L and not L.startswith("#") and not L.startswith("-"))
            log("  ", m, len(b), "bytes,", nrows, "lines")
            if nrows > 20:
                safe = cat.replace("/", "_").replace("+", "p")
                (OUT / f"viz_{safe}.tsv").write_text(b)
                return {"mirror": m, "file": f"viz_{safe}.tsv", "lines": nrows}
        except Exception as e:
            log("   fail", m, e)
    return None

# archives that keep catalog files as plain files: list one or two levels and take catalog-like files
CRAWL = ["https://archive.stsci.edu/hlsps/uvudf/", "https://archive.stsci.edu/pub/hlsp/udf/acs-wfc/", "https://archive.stsci.edu/hlsps/udf/",
         "https://archive.stsci.edu/hlsps/hudf12/", "https://archive.stsci.edu/hlsps/hudf09/", "https://amused.univ-lyon1.fr/data/UDF/HUDF/download/",
         "https://archive.stsci.edu/hlsps/hlf/", "https://archive.stsci.edu/missions/hlsp/uvudf/"]
WANT = re.compile(r"(cat|redshift|photz|zphot|specz|z_|bpz|eazy|main).*\.(fits|txt|cat|dat|csv|gz|tbl|ecsv)$", re.I)
def links(url):
    try:
        h = get(url, 60).decode("utf-8", "replace")
    except Exception as e:
        log("   list fail", url, e); return []
    out = []
    for href in re.findall(r'href="([^"?#]+)"', h):
        u = urllib.parse.urljoin(url, href)
        if u.startswith(url) and u != url: out.append(u)
    return sorted(set(out))
def size_of(u):
    try:
        req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r: return int(r.headers.get("Content-Length") or 0)
    except Exception: return -1
def crawl(root, depth=3):
    found = []
    todo = [(root, 0)]; seen = set()
    while todo:
        u, d = todo.pop(0)
        if u in seen: continue
        seen.add(u)
        for v in links(u):
            if v.endswith("/"):
                if d + 1 < depth: todo.append((v, d + 1))
            else:
                log("   seen", v)
                if WANT.search(v.rsplit("/", 1)[-1]): found.append(v)
        if len(seen) > 60: break
    got = []
    for v in found[:40]:
        n = size_of(v)
        if 0 < n < 95e6 or n == -1:
            try:
                b = get(v, 900); name = re.sub(r"[^A-Za-z0-9._-]", "_", v.split("//", 1)[1]); (OUT / name).write_bytes(b); got.append((name, len(b))); log("   got", v, len(b))
            except Exception as e:
                log("   get fail", v, e)
        else:
            log("   too big", v, n)
    return got

info = {}
for cat, desc in CATALOGS.items():
    log("catalog", cat, desc)
    r = viz(cat)
    if r: info[cat] = {"desc": desc, **r}
for root in CRAWL:
    log("crawl", root)
    info[root] = crawl(root)
json.dump(info, open(OUT / "catalogs.json", "w"), indent=1)
log("done")
