"""Build blackhole/index.html from tools/page_template.html and tools/stars.json.

Run from the blackhole/ folder:
    python tools/build_page.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
page = (HERE / "page_template.html").read_text(encoding="utf-8")
stars = (HERE / "stars.json").read_text(encoding="utf-8")
(HERE.parent / "index.html").write_text(page.replace("__STARS__", stars), encoding="utf-8")
print("Wrote", HERE.parent / "index.html")
