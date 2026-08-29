#!/usr/bin/env python3
"""Regenerate sitemap.xml from the HTML pages in the repository root.

Rules:
- Excludes 404.html, redirect stubs, and any page whose robots meta contains noindex.
- lastmod comes from the page file's modification time (override via DATES below).
- Homepage is emitted as https://clinovian.com/ with priority 1.0.
Run from the repository root: python3 scripts/generate_sitemap.py
"""
import datetime
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


def main() -> int:
    pages = []
    for p in sorted(ROOT.glob("*.html")):
        if p.name in EXCLUDE:
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        robots = re.search(r'<meta name="robots" content="([^"]*)"', src)
        if robots and "noindex" in robots.group(1):
            continue
        lastmod = datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()
        loc = BASE if p.name == "index.html" else BASE + p.name
        changefreq, priority = PRIORITY.get(p.name, DEFAULT)
        pages.append((loc, lastmod, changefreq, priority))

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
