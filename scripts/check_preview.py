#!/usr/bin/env python3
"""Post-deploy preview check for a Clinovian deployment.

Usage:  python3 scripts/check_preview.py https://<host> [--matrix]\n\n        --matrix additionally tests all four production entry points\n        (http/https x apex/www) and detects redirect loops. Use it\n        against production, not against a preview host.

Verifies, against a deployed host, the things the static gate cannot:
  - the canonical host/redirect matrix (apex vs www, http vs https)
  - a representative set of URLs return the expected status
  - a known legacy path redirects, and a nonexistent path returns a real 404
  - the meta-tag security policy survives to the deployed page
    (GitHub Pages cannot send security headers; see DEPLOYMENT.md)
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

# GitHub Pages does not let a site set response headers. The policy that used to
# live in vercel.json is now delivered as meta tags, which covers most of it — but
# not all. These are checked as informational only: their absence is a platform
# limit, not a regression, and failing the build on them would be dishonest.
#
# What a meta tag CANNOT replace:
#   frame-ancestors / X-Frame-Options  — header-only; clickjacking protection is
#                                        NOT available on this platform
#   Strict-Transport-Security          — header-only; GitHub's "Enforce HTTPS"
#                                        setting is the available substitute
#   Permissions-Policy                 — header-only
OPTIONAL_HEADERS = [
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "referrer-policy",
    "x-frame-options",
]


def fetch(url, method="GET", follow=False, want_body=False):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "clinovian-preview-check"})
    try:
        with opener.open(req, timeout=20) as r:
            body = ""
            if want_body:
                try:
                    body = r.read(4096).decode("utf-8", "replace")
                except Exception:  # noqa: BLE001
                    body = ""
            hdrs = dict((k.lower(), v) for k, v in r.headers.items())
            if want_body:
                return r.status, hdrs, r.headers.get("Location"), body
            return r.status, hdrs, r.headers.get("Location")
    except urllib.error.HTTPError as e:
        hdrs = dict((k.lower(), v) for k, v in e.headers.items())
        if want_body:
            return e.code, hdrs, e.headers.get("Location"), ""
        return e.code, hdrs, e.headers.get("Location")
    except Exception as e:  # noqa: BLE001
        if want_body:
            return None, {"error": str(e)}, None, ""
        return None, {"error": str(e)}, None


CANONICAL_ORIGIN = "https://clinovian.com"


def follow_chain(url, max_hops=6):
    """Follow redirects one hop at a time, returning the hop list.

    Returns (hops, outcome) where outcome is "ok", "loop", "too_many" or "error".
    Following manually — rather than letting urllib do it — is what makes a
    redirect loop visible instead of surfacing as an opaque error.
    """
    hops, seen = [], set()
    current = url
    for _ in range(max_hops):
        if current in seen:
            hops.append((current, None, None))
            return hops, "loop"
        seen.add(current)
        status, headers, location = fetch(current)
        hops.append((current, status, location))
        if status is None:
            return hops, "error"
        if status in (301, 302, 307, 308) and location:
            current = location if location.startswith("http") else (
                current.rsplit("/", 1)[0] + "/" + location.lstrip("/"))
            continue
        return hops, "ok"
    return hops, "too_many"


def check_host_matrix(failures):
    """Every entry point must terminate at one canonical origin.

    The audit's F13: production redirected apex -> www while vercel.json
    redirected www -> apex. Applied together those form a loop, and applied
    singly they disagree with the canonical tags. This tests all four entry
    points for real rather than asserting the matrix was checked.
    """
    print("\n  Canonical host / redirect matrix")
    entries = [
        "http://clinovian.com/",
        "https://clinovian.com/",
        "http://www.clinovian.com/",
        "https://www.clinovian.com/",
    ]
    for entry in entries:
        hops, outcome = follow_chain(entry)
        trail = " -> ".join(
            f"{u} [{s if s is not None else 'ERR'}]" for u, s, _ in hops)
        final_url, final_status, _ = hops[-1]

        if outcome == "loop":
            print(f"  [FAIL] {entry}\n         REDIRECT LOOP: {trail}")
            failures.append(f"redirect loop from {entry}")
            continue
        if outcome == "too_many":
            print(f"  [FAIL] {entry}\n         too many hops: {trail}")
            failures.append(f"too many redirects from {entry}")
            continue
        if outcome == "error":
            print(f"  [FAIL] {entry}\n         unreachable: {trail}")
            failures.append(f"{entry} unreachable")
            continue

        ok_origin = final_url.startswith(CANONICAL_ORIGIN + "/") or \
            final_url.rstrip("/") == CANONICAL_ORIGIN
        ok_status = final_status == 200
        if ok_origin and ok_status:
            print(f"  [ok  ] {entry}\n         {trail}")
        else:
            print(f"  [FAIL] {entry}\n         {trail}")
            if not ok_origin:
                failures.append(
                    f"{entry} settles on {final_url}, not {CANONICAL_ORIGIN} "
                    "— the deployed host direction disagrees with the canonical tags")
            if not ok_status:
                failures.append(f"{entry} ends with status {final_status}")


def check_meta_policy(base, failures):
    """The meta-tag policy must survive to the deployed page.

    GitHub Pages cannot send security headers, so these tags are the only policy
    the site actually delivers. If they are missing from the served HTML there is
    no policy at all.
    """
    print("\n  Meta-tag security policy (headers are not available on this platform)")
    status, _, _, body = fetch(base + "/", want_body=True)
    if status != 200:
        failures.append("cannot fetch / to check the meta policy")
        return
    for needle, label in (
        ('http-equiv="Content-Security-Policy"', "meta CSP"),
        ("formspree.io", "CSP allows formspree (intake form)"),
    ):
        if needle in body:
            print(f"  [ok  ] {label}")
        else:
            print(f"  [FAIL] {label} absent from the served page")
            failures.append(f"{label} absent from the deployed HTML")


def check_canonical_agreement(base, failures):
    """The canonical tag a page serves must name the host it was served from."""
    print("\n  Canonical tag agrees with the serving host")
    import re as _re
    for path in ("/", "/contact.html", "/sitemap.html"):
        status, _, _, body = fetch(base + path, want_body=True)
        if status != 200:
            continue
        m = _re.search(r'rel="canonical"[^>]*href="(https?://[^/"]+)', body)
        if not m:
            print(f"  [warn] {path}: no canonical tag in the first 4KB")
            continue
        canon_origin, served_origin = m.group(1), base
        if canon_origin.rstrip("/") == served_origin.rstrip("/"):
            print(f"  [ok  ] {path}: canonical {canon_origin}")
        else:
            print(f"  [FAIL] {path}: served from {served_origin} but canonical "
                  f"says {canon_origin}")
            failures.append(
                f"{path}: served on {served_origin} while its canonical names "
                f"{canon_origin} — split host signal")


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) != 1:
        print(__doc__)
        return 2
    base = args[0].rstrip("/")
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
    for h in OPTIONAL_HEADERS:
        present = h in headers
        print(f"  [{'ok  ' if present else 'none'}] {h}")

    # Release identity: the deployed build should expose the same release marker
    # that this working copy carries.
    marker = ROOT / "RELEASE_ID"
    if marker.exists():
        want = marker.read_text(encoding="utf-8").strip()
        status, _, _, body = fetch(base + "/RELEASE_ID", want_body=True)
        got = body.strip()
        print(f"\n  Local release id:    {want}")
        print(f"  Deployed release id: {got or '(none)'}  (status {status})")
        if status != 200:
            failures.append("deployed build does not expose /RELEASE_ID")
        elif got != want:
            failures.append(
                f"deployed build is not this release: /RELEASE_ID is {got!r}, "
                f"expected {want!r} — the host is serving a different build")
        else:
            print("  [ok ] deployed build matches this working copy")

    check_meta_policy(base, failures)
    check_canonical_agreement(base, failures)

    if "--matrix" in flags:
        check_host_matrix(failures)
    else:
        print("\n  (host matrix not tested — pass --matrix when checking production)")

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
