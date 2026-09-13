#!/usr/bin/env python3
"""Regenerate sitemap.xml from the HTML pages in the repository root.

Rules:
- Excludes 404.html, redirect stubs, and any page whose robots meta contains noindex.
- lastmod comes from data/content-dates.json, which records meaningful content
  changes. Filesystem modification times are deliberately NOT used: unpacking or
  rebuilding the archive rewrites them, which would publish false update dates.
  A page missing from that file is a hard error, so new pages cannot ship undated.
- Homepage is emitted as https://clinovian.com/ with priority 1.0.
Run from the repository root: python3 scripts/generate_sitemap.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://clinovian.com/"

EXCLUDE = {
    "404.html",
    "clinovian_sample_appeal.html",
    "clinovian_sample_dossier.html",
}

PRIORITY = {
    "index.html": ("weekly", "1.0"),
    "how-it-works.html": ("monthly", "0.9"),
    "services.html": ("monthly", "0.9"),
    "case-suitability.html": ("monthly", "0.9"),
    "engagements.html": ("monthly", "0.9"),
    "sample-escalation-memo.html": ("monthly", "0.9"),
    "insights.html": ("weekly", "0.7"),
    "privacy.html": ("yearly", "0.3"),
    "terms.html": ("yearly", "0.3"),
    "accessibility.html": ("yearly", "0.3"),
    "editorial-policy.html": ("yearly", "0.4"),
    "trust-center.html": ("monthly", "0.5"),
    "sitemap.html": ("monthly", "0.2"),
}
DEFAULT = ("monthly", "0.7")


CONTENT_DATES = json.loads((ROOT / "data" / "content-dates.json").read_text(encoding="utf-8"))["dates"]


def main() -> int:
    pages = []
    missing = []
    for p in sorted(ROOT.glob("*.html")):
        if p.name in EXCLUDE:
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        robots = re.search(r'<meta name="robots" content="([^"]*)"', src)
        if robots and "noindex" in robots.group(1):
            continue
        lastmod = CONTENT_DATES.get(p.name)
        if not lastmod:
            missing.append(p.name)
            continue
        loc = BASE if p.name == "index.html" else BASE + p.name
        changefreq, priority = PRIORITY.get(p.name, DEFAULT)
        pages.append((loc, lastmod, changefreq, priority))

    if missing:
        print("ERROR: no content date recorded for: " + ", ".join(missing), file=sys.stderr)
        print("Add them to data/content-dates.json in the same commit as the content change.", file=sys.stderr)
        return 1

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, changefreq, priority in pages:
        lines.append(
            f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod>"
            f"<changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>"
        )
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml written with {len(pages)} URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
