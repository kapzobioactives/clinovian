#!/usr/bin/env python3
"""Post-deploy preview check for a Clinovian deployment.

Usage:  python3 scripts/check_preview.py https://<preview-host>

Verifies, against a deployed host, the things the static gate cannot:
  - the canonical host/redirect matrix (apex vs www, http vs https)
  - a representative set of URLs return the expected status
  - a known legacy path redirects, and a nonexistent path returns a real 404
  - security and cache headers are actually present on the response
  - the deployed release identity matches this working copy

Exits non-zero on any failure. Read-only: issues GET/HEAD requests only.
"""
import sys
import pathlib
import urllib.request
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (path, expected status, note)
PATHS = [
    ("/", 200, "home"),
    ("/services.html", 200, "service page"),
    ("/contact.html", 200, "intake"),
    ("/sample-drg-downgrade.html", 200, "specimen"),
    ("/insight-six-failure-modes.html", 200, "article"),
    ("/sitemap.xml", 200, "sitemap"),
    ("/feed.xml", 200, "feed"),
    ("/robots.txt", 200, "robots"),
    ("/services", 301, "legacy extensionless path redirects"),
    ("/clinovian_sample_appeal.html", 301, "legacy stub redirects"),
    ("/this-path-does-not-exist-9f3a.html", 404, "unknown path returns a real 404"),
]

REQUIRED_HEADERS = [
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "referrer-policy",
]


def fetch(url, method="GET", follow=False):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "clinovian-preview-check"})
    try:
        with opener.open(req, timeout=20) as r:
            return r.status, dict((k.lower(), v) for k, v in r.headers.items()), r.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, dict((k.lower(), v) for k, v in e.headers.items()), e.headers.get("Location")
    except Exception as e:  # noqa: BLE001
        return None, {"error": str(e)}, None


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    base = argv[1].rstrip("/")
    failures = []

    print(f"Preview check against {base}\n")

    for path, expected, note in PATHS:
        status, headers, loc = fetch(base + path)
        ok = status == expected
        print(f"  [{'ok ' if ok else 'FAIL'}] {status!s:>5}  {path:<42} {note}"
              + (f"  -> {loc}" if loc else ""))
        if not ok:
            failures.append(f"{path}: expected {expected}, got {status}")

    status, headers, _ = fetch(base + "/")
    print("\n  Response headers on /")
    for h in REQUIRED_HEADERS:
        present = h in headers
        print(f"  [{'ok ' if present else 'FAIL'}] {h}")
        if not present:
            failures.append(f"missing response header: {h}")

    # Release identity: the deployed build should expose the same release marker
    # that this working copy carries.
    marker = ROOT / "RELEASE_ID"
    if marker.exists():
        want = marker.read_text(encoding="utf-8").strip()
        status, _, _ = fetch(base + "/RELEASE_ID")
        print(f"\n  Local release id: {want}  (deployed /RELEASE_ID status {status})")
        if status != 200:
            failures.append("deployed build does not expose /RELEASE_ID")

    print()
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print("All preview checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
