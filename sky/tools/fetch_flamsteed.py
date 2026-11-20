"""
fetch_flamsteed.py
Downloads public-domain scans of John Flamsteed's Atlas Coelestis (London, 1729) onto the separate branch
'flamsteed-sources' (see .github/workflows/fetch-flamsteed.yml), so they do not weigh down the published site.

Sources
  1. Internet Archive item 'atlascoelestis00flam' (1729 first edition, Wellesley College Library, 400 ppi):
     a small preview of every page, then full-size images of the pages listed in PAGES below.
  2. Wikimedia Commons set "Atlas Coelestis by John Flamsteed (1729) NNN.jpg" (from RareMaps), fetched by
     building the file addresses directly (Commons limits search requests from shared servers).
"""
import hashlib, json, sys, time, urllib.request
from pathlib import Path

OUT = Path("sky_sources/flamsteed")
(OUT / "ia_preview").mkdir(parents=True, exist_ok=True)
(OUT / "ia").mkdir(parents=True, exist_ok=True)
(OUT / "commons").mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "CelestialSphereExplorer/1.0 (astronomy education, Soka University of America; https://github.com/bpenprase/moonglobe)"}
IA = "atlascoelestis00flam"
PAGES = []          # Internet Archive page numbers (n0, n1, ...) to download at full size; filled in once the previews are checked
log = []

def get(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except Exception as e:
            code = getattr(e, "code", None)
            if code == 404:
                return None
            wait = 20 * (i + 1)
            if code == 429:
                try: wait = max(wait, int(e.headers.get("Retry-After", wait)))
                except Exception: pass
            log.append(f"  retry in {wait}s after {code or e!r}: {url}")
            time.sleep(min(wait, 120))
    log.append(f"  gave up: {url}")
    return None

# ---------------------------------------------------------------- 1. Internet Archive
meta = json.loads(get(f"https://archive.org/metadata/{IA}") or b"{}")
n = int(meta.get("metadata", {}).get("imagecount", 0) or 0)
log.append(f"Internet Archive {IA}: {n} page images; title {meta.get('metadata', {}).get('title')!r}, date {meta.get('metadata', {}).get('date')!r}")
patterns = [f"https://archive.org/download/{IA}/page/n{{i}}_w{{w}}.jpg", f"https://archive.org/download/{IA}/page/n{{i}}.jpg"]
pattern = None
for p in patterns:
    data = get(p.format(i=10, w=800), tries=2)
    if data and data[:2] == b"\xff\xd8":
        pattern = p; break
log.append(f"  page image address: {pattern}")
if pattern:
    for i in range(n):
        d = get(pattern.format(i=i, w=700))
        if d: (OUT / "ia_preview" / f"n{i:03d}.jpg").write_bytes(d)
        time.sleep(0.3)
    for i in PAGES:
        d = get(pattern.format(i=i, w=5000))
        if d: (OUT / "ia" / f"n{i:03d}.jpg").write_bytes(d)
        time.sleep(1)

# ---------------------------------------------------------------- 2. Wikimedia Commons, by direct address
found = []
for k in range(1, 61):
    name = f"Atlas_Coelestis_by_John_Flamsteed_(1729)_{k:03d}.jpg"
    h = hashlib.md5(name.encode()).hexdigest()
    url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{name}/3840px-{name}"
    d = get(url, tries=4)
    if d and d[:2] == b"\xff\xd8":
        (OUT / "commons" / name).write_bytes(d); found.append(name)
    time.sleep(2)
log.append(f"Wikimedia Commons: {len(found)} plates downloaded: {found}")
(OUT / "log.txt").write_text("\n".join(log) + "\n")
print("\n".join(log))
