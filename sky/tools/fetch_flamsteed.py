"""
fetch_flamsteed.py
Finds public-domain scans of John Flamsteed's Atlas Coelestis (1729, and the 1753 second edition) on
Wikimedia Commons, writes a list of what it found, and downloads them (at most 4000 pixels wide) into
sky_sources/flamsteed/. Runs on GitHub (.github/workflows/fetch-flamsteed.yml); the scans are kept on the
separate branch 'flamsteed-sources' so they do not weigh down the published site.
"""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

OUT = Path("sky_sources/flamsteed")
OUT.mkdir(parents=True, exist_ok=True)
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "CelestialSphereExplorer/1.0 (astronomy education, Soka University of America; github.com/bpenprase/moonglobe)"}

def api(**params):
    params.update(format="json", formatversion="2")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:
            time.sleep(3 * (i + 1)); err = e
    raise err

titles, log = {}, []
def add(t, why):
    if t.startswith("File:") and re.search(r"\.(jpe?g|png|tiff?)$", t, re.I):
        titles.setdefault(t, why)

# 1. categories (and one level of subcategories)
cats = ["Category:Atlas Coelestis", "Category:Atlas Coelestis (Flamsteed)", "Category:Atlas coelestis (1729)",
        "Category:Atlas Coelestis by John Flamsteed", "Category:John Flamsteed", "Category:Atlas Coelestis (1753)"]
seen = set()
while cats:
    c = cats.pop(0)
    if c in seen: continue
    seen.add(c)
    cont = {}
    while True:
        r = api(action="query", list="categorymembers", cmtitle=c, cmlimit="500", **cont)
        for m in r.get("query", {}).get("categorymembers", []):
            if m["ns"] == 14 and ("Flamsteed" in m["title"] or "Coelestis" in m["title"]):
                cats.append(m["title"])
            add(m["title"], c)
        if "continue" not in r: break
        cont = r["continue"]
    log.append(f"{c}: done")

# 2. full-text search
for q in ["Flamsteed Atlas Coelestis", "Atlas Coelestis 1729", "Flamsteed 1729", "Flamsteed 1753 Atlas", "Atlas coelestis Thornhill"]:
    r = api(action="query", list="search", srsearch=q, srnamespace="6", srlimit="100")
    for m in r.get("query", {}).get("search", []):
        add(m["title"], "search: " + q)

# 3. image info and download
items = []
names = list(titles)
for i in range(0, len(names), 40):
    r = api(action="query", titles="|".join(names[i:i + 40]), prop="imageinfo", iiprop="url|size|mime|extmetadata", iiurlwidth="4000")
    for p in r["query"]["pages"]:
        if "imageinfo" not in p: continue
        ii = p["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        items.append(dict(title=p["title"], found_by=titles[p["title"]], width=ii.get("width"), height=ii.get("height"),
                          url=ii.get("thumburl") or ii.get("url"), page=ii.get("descriptionurl"),
                          license=meta.get("LicenseShortName", {}).get("value", ""),
                          date=re.sub("<[^>]+>", "", meta.get("DateTimeOriginal", {}).get("value", ""))[:80],
                          description=re.sub("<[^>]+>", "", meta.get("ImageDescription", {}).get("value", ""))[:300]))
items.sort(key=lambda x: x["title"])
for it in items:
    if (it["width"] or 0) < 1200: continue
    fn = re.sub(r"[^A-Za-z0-9._-]+", "_", it["title"][5:])
    if re.search(r"\.tiff?$", fn, re.I): fn = re.sub(r"\.tiff?$", ".jpg", fn, flags=re.I)
    try:
        data = urllib.request.urlopen(urllib.request.Request(it["url"], headers=UA), timeout=120).read()
        (OUT / fn).write_bytes(data); it["file"] = fn
        time.sleep(0.5)
    except Exception as e:
        it["error"] = repr(e)
json.dump(items, open(OUT / "list.json", "w"), indent=1, ensure_ascii=False)
(OUT / "log.txt").write_text("\n".join(log) + f"\n{len(items)} files found, {sum(1 for i in items if 'file' in i)} downloaded\n")
print(len(items), "files found")
