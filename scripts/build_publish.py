#!/usr/bin/env python3
"""Assemble the GitHub Pages publish directory.

    python3 scripts/build_publish.py [outdir]     # default: _site

GitHub Pages serves whatever is in the published branch or folder, verbatim. It
supports no server-side redirects and no custom response headers. Three
consequences drive this script:

1. Publishing the repository root would expose every internal document —
   VALIDATION_REPORT.md, RELEASE_NOTES.md, CHANGELOG.md, DEPLOYMENT.md and the
   scripts directory — at public URLs. This script copies an allow-listed set
   instead, so a file is published only because it was named.

2. The 66 redirects in data/routes.json cannot be server rules. Each is
   materialised as a static stub: meta refresh, a canonical pointing at the
   destination, noindex, and a visible link for anyone without JavaScript or
   with refresh disabled. Extensionless routes become directory indexes
   (/services/index.html), which is how GitHub Pages serves /services.

3. CNAME fixes the canonical host. Its content is the apex, matching every
   canonical tag in the site. .nojekyll disables Jekyll processing.

Run scripts/validate_site.py before this; the gate checks the source tree.
"""
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Everything published is named here. Nothing is published by default.
PUBLIC_SUFFIXES = {".html", ".css", ".js", ".xml", ".txt", ".png", ".svg", ".ico", ".webmanifest"}

# Files with a public suffix that must still never ship.
EXCLUDE_NAMES = {
    "structural_quality_report.json",
    "package.json",
    "package-lock.json",
}

# Directories never copied wholesale.
EXCLUDE_DIRS = {"scripts", "shared", "data", "node_modules", ".git", ".github", "_site"}

STUB = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Redirecting — Clinovian</title>
<meta name="robots" content="noindex,follow">
<meta http-equiv="refresh" content="0;url={to}">
<link rel="canonical" href="{origin}{to}">
</head>
<body style="font-family:Georgia,serif;padding:40px;max-width:40rem">
<p>This address has moved to <a href="{to}">{to}</a>.</p>
<p>If you are not redirected automatically, follow the link above.</p>
</body></html>
"""


def main(argv):
    out = pathlib.Path(argv[1]) if len(argv) > 1 else ROOT / "_site"
    routes_file = ROOT / "data" / "routes.json"
    routes = json.loads(routes_file.read_text(encoding="utf-8"))
    origin = routes["canonical_origin"]

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # 1. Copy the allow-listed public files from the repository root.
    copied = 0
    for src in sorted(ROOT.iterdir()):
        if src.is_dir():
            continue
        if src.name in EXCLUDE_NAMES:
            continue
        if src.suffix.lower() not in PUBLIC_SUFFIXES:
            continue
        shutil.copy2(src, out / src.name)
        copied += 1

    # 2. Materialise every redirect as a static stub.
    stubs = 0
    for r in routes["redirects"]:
        frm, to = r["from"].lstrip("/"), r["to"]
        target = out / frm / "index.html" if "." not in frm else out / frm
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            # A real page already occupies this path; never overwrite it.
            continue
        target.write_text(STUB.format(to=to, origin=origin), encoding="utf-8")
        stubs += 1

    # 3. Host and Jekyll control files.
    (out / "CNAME").write_text(routes["canonical_host"] + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    # 4. Refuse to ship an internal document, whatever the allow-list says.
    leaked = []
    for p in out.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".md":
            leaked.append(p.relative_to(out).as_posix())
    for name in ("scripts", "shared", "data", "node_modules"):
        if (out / name).exists():
            leaked.append(name + "/")
    if leaked:
        print("ERROR: internal files reached the publish set: " + ", ".join(leaked),
              file=sys.stderr)
        return 1

    print(f"  publish set: {out}")
    print(f"  {copied} public files copied")
    print(f"  {stubs} redirect stubs generated")
    print(f"  CNAME = {routes['canonical_host']}   .nojekyll written")
    print(f"  0 internal documents published")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
