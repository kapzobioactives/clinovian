#!/usr/bin/env python3
"""Propagate shared page furniture from one source into every page.

Navigation, the mobile drawer, the footer and the trust strip were previously
hand-copied across 50+ pages. That produced real drift: 404.html carried an older
navigation and footer, and six pages carried divergent trust strips. This script
makes `shared/*.html` the single source and writes it into marked regions.

    python3 scripts/build_shared.py            # write shared regions into every page
    python3 scripts/build_shared.py --check     # exit 1 if any page is out of date
    python3 scripts/build_shared.py --init      # first run: wrap existing blocks in markers

Per-page navigation state (the `active` class) is DERIVED from each page's own
filename, so it is not duplicated data and does not need maintaining by hand.
Never hand-edit anything between the <!-- shared:x --> markers.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))

BLOCKS = [
    ("nav",    r'<nav id="nav".*?</nav>'),
    ("drawer", r'<div class="mobile-drawer" id="mobile-drawer">.*?(?=\n<main)'),
    ("trust",  r'<aside class="trust".*?</aside>'),
    ("footer", r'<footer.*?</footer>'),
]


def partial(name, page):
    """Return the shared partial for `name`, applying any per-page variant."""
    if name == "trust":
        variant = SITE.get("trust_variants", {}).get(page)
        if variant and variant != "default":
            p = ROOT / "shared" / f"trust-{variant}.html"
            if p.exists():
                return p.read_text(encoding="utf-8").rstrip("\n")
    return (ROOT / "shared" / f"{name}.html").read_text(encoding="utf-8").rstrip("\n")


def apply_active(nav_html, page):
    """Derive nav state from the page itself: mark the matching top-level link
    active, and mark a dropdown toggle active when the page sits inside it."""
    href = f'/{page}'

    def mark_link(m):
        if m.group(1) == href:
            return f'<li class="nav-item"><a href="{m.group(1)}" class="active">'
        return m.group(0)

    nav_html = re.sub(r'<li class="nav-item"><a href="([^"]+)">', mark_link, nav_html)

    # A dropdown toggle is active when the current page sits inside that dropdown:
    # either it is linked directly, or it matches one of the section's page prefixes.
    prefixes = SITE.get("nav_sections", {})
    out, pos = [], 0
    for m in re.finditer(r'<li class="nav-item[^"]*">(.*?)</li>', nav_html, re.S):
        chunk = m.group(0)
        if 'nav-dd-toggle' in chunk:
            label_m = re.search(r'nav-dd-toggle"[^>]*>([^<]+)', chunk)
            label = label_m.group(1).strip() if label_m else ""
            in_section = f'href="{href}"' in chunk
            for pref in prefixes.get(label, []):
                if page == pref or (pref.endswith("*") and page.startswith(pref[:-1])):
                    in_section = True
            if in_section:
                chunk = chunk.replace('class="nav-dd-toggle"', 'class="nav-dd-toggle active"', 1)
        out.append(nav_html[pos:m.start()]); out.append(chunk); pos = m.end()
    out.append(nav_html[pos:])
    return "".join(out)


def render(name, page):
    html = partial(name, page)
    if name == "nav":
        html = apply_active(html, page)
    return f'<!-- shared:{name} --><!-- generated from {SITE["partials"].get(name, "shared/" + name + ".html")} — do not edit by hand -->\n{html}\n<!-- /shared:{name} -->'


def init(paths):
    """Wrap the existing block in markers so later runs can find and replace it."""
    changed = 0
    for p in paths:
        src = p.read_text(encoding="utf-8")
        orig = src
        for name, pat in BLOCKS:
            if f'<!-- shared:{name} -->' in src:
                continue
            m = re.search(pat, src, re.S)
            if not m:
                continue
            src = src[:m.start()] + render(name, p.name) + src[m.end():].lstrip("\n") if False else \
                  src[:m.start()] + render(name, p.name) + src[m.end():]
        if src != orig:
            p.write_text(src, encoding="utf-8"); changed += 1
    return changed


def build(paths, check_only=False):
    stale = []
    for p in paths:
        src = p.read_text(encoding="utf-8")
        new = src
        for name, _ in BLOCKS:
            pat = re.compile(rf'<!-- shared:{name} -->.*?<!-- /shared:{name} -->', re.S)
            if not pat.search(new):
                continue
            new = pat.sub(lambda _m: render(name, p.name), new, count=1)
        if new != src:
            stale.append(p.name)
            if not check_only:
                p.write_text(new, encoding="utf-8")
    return stale


def check_services():
    """Service labels, prices and turnarounds are shared data too.

    Until 2026.09.14-r11 this compared data/site.json against service-catalog.json
    and stopped there, while claiming to be "the check that catches a price changed
    on one page and not the others". It never opened a page. Two files agreeing with
    each other says nothing about what a buyer reads.

    It now also reads each service's own page and its entry on services.html, and
    requires the price and turnaround shown there to match the canonical record."""
    errors = []
    cat_raw = json.loads((ROOT / "service-catalog.json").read_text(encoding="utf-8"))
    cat = {s["id"]: s for s in (cat_raw["services"] if isinstance(cat_raw, dict) else cat_raw)}
    contact = (ROOT / "contact.html").read_text(encoding="utf-8")
    intake_ids = set(re.findall(r'<option data-service-id="([^"]+)"', contact))

    for svc in SITE["services"]:
        sid = svc["id"]
        if sid not in intake_ids:
            errors.append(f"service '{sid}' has no matching intake option in contact.html")
        for key in ("page", "sample"):
            target = svc.get(key)
            if target and not (ROOT / target).exists():
                errors.append(f"service '{sid}' {key} points at missing file {target}")
        c = cat.get(sid)
        if c:
            if c["name"] != svc["name"]:
                errors.append(f"service '{sid}' name differs: catalog '{c['name']}' vs site.json '{svc['name']}'")
            if c["price"] != svc["price"]:
                errors.append(f"service '{sid}' price differs: catalog '{c['price']}' vs site.json '{svc['price']}'")
            if c.get("turnaround") != svc.get("turnaround"):
                errors.append(f"service '{sid}' turnaround differs: catalog "
                              f"'{c.get('turnaround')}' vs site.json '{svc.get('turnaround')}'")
        elif svc.get("in_catalog", True) and sid not in ("concurrent-review", "recurring-capacity"):
            errors.append(f"service '{sid}' is in site.json but not in service-catalog.json")

    for ev in SITE["evaluations"]:
        if ev["id"] not in intake_ids:
            errors.append(f"evaluation '{ev['id']}' has no matching intake option in contact.html")

    # The part that actually opens a page. A price or turnaround rendered on a
    # service page must match the canonical record, not merely match another
    # data file. Figures are compared after normalising dash and space variants,
    # because an en dash typed as a hyphen is a typo, not a pricing change.
    def norm(t):
        return (t.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
                 .replace("&#8211;", "-").replace("&#8212;", "-")
                 .replace("\u00a0", " ").lower())

    def money_and_clock(text):
        """Every dollar figure and every turnaround-shaped phrase in a page."""
        money = set(re.findall(r"\$[\d,]+", text))
        clock = set(m.group(0).strip().lower() for m in re.finditer(
            r"\d+\s*[-\u2013\u2014]\s*\d+\s*(?:hours?|business days?|days?)", text))
        return money, clock

    services_page = (ROOT / "services.html")
    services_text = norm(re.sub(r"<[^>]+>", " ", services_page.read_text(encoding="utf-8"))) \
        if services_page.exists() else ""

    for svc in SITE["services"]:
        page = ROOT / svc["page"] if svc.get("page") else None
        if not page or not page.exists():
            continue
        text = norm(re.sub(r"<[^>]+>", " ", page.read_text(encoding="utf-8")))
        want_money, want_clock = money_and_clock(norm(
            svc.get("price", "") + " " + svc.get("turnaround", "")))

        for amount in want_money:
            if amount not in text:
                errors.append(f"service '{svc['id']}': canonical price {amount} does not "
                              f"appear on {svc['page']}")
            if services_text and amount not in services_text:
                errors.append(f"service '{svc['id']}': canonical price {amount} does not "
                              "appear on services.html")
        for window in want_clock:
            if window not in text:
                errors.append(f"service '{svc['id']}': canonical turnaround "
                              f"'{window}' does not appear on {svc['page']}")

        # A different dollar figure presented as this service's own starting price
        # is drift, even when the canonical figure is also present somewhere.
        for m in re.finditer(r"(?:from|starts at|starting at)\s+(\$[\d,]+)", text):
            if want_money and m.group(1) not in want_money:
                errors.append(f"service '{svc['id']}': {svc['page']} advertises a starting "
                              f"price of {m.group(1)}; the canonical price is "
                              f"{sorted(want_money)[0]}")

    gov = SITE.get("governing_document")
    if gov and not (ROOT / gov).exists():
        errors.append(f"governing document {gov} is missing")
    return errors


def main(argv):
    paths = sorted(ROOT.glob("*.html"))
    if "--init" in argv:
        n = init(paths)
        print(f"markers inserted in {n} pages")
        return 0
    svc_errors = check_services()
    for e in svc_errors:
        print("ERROR: " + e, file=sys.stderr)
    stale = build(paths, check_only="--check" in argv)
    if "--check" in argv:
        if svc_errors:
            return 1
        if stale:
            print("ERROR: shared regions are out of date in:", ", ".join(stale), file=sys.stderr)
            print("Run: python3 scripts/build_shared.py", file=sys.stderr)
            return 1
        print(f"shared regions up to date across {len(paths)} pages")
        return 0
    print(f"shared regions rebuilt; {len(stale)} page(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
