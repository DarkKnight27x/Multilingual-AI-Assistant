"""
Run targeted scrapers and write reviewable markdown files.

Usage:
  python -m scrapers.run_scrape
"""

from __future__ import annotations

from pathlib import Path

from scrapers.normalize import to_markdown
from scrapers.portals.udyam import scrape_udyam
from scrapers.portals.gst import scrape_gst
from scrapers.portals.crs import scrape_crs
from scrapers.portals.myscheme import scrape_myscheme
from scrapers.portals.rti import scrape_rti

OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _write(name: str, data: dict) -> None:
    data_for_md = {k: v for k, v in data.items() if k != "raw_excerpt"}
    md = to_markdown(data_for_md)
    path = OUT_DIR / name
    path.write_text(md, encoding="utf-8")
    print(f"Wrote: {path}")


def main() -> None:
    print("Scraping Udyam...")
    _write("udyam_registration.md", scrape_udyam())

    print("Scraping GST...")
    _write("gst_registration.md", scrape_gst())

    print("Scraping CRS (Birth/Death)...")
    _write("birth_death_crs.md", scrape_crs())

    print("Scraping myScheme...")
    _write("myscheme.md", scrape_myscheme())

    print("Scraping RTI Online...")
    _write("rti_application.md", scrape_rti())

    print("\nNext:")
    print("1) Review files in scrapers/output/")
    print("2) Copy approved files into data/knowledge_base/<category>/")
    print("3) Run: python scripts/build_index.py")


if __name__ == "__main__":
    main()