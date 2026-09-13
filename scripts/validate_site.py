#!/usr/bin/env python3
"""Static release gate for the Clinovian site.

Run from the repository root: python3 scripts/validate_site.py
Exits non-zero on any error. Checks:
  - required head metadata (title/description lengths, canonical, og:url, viewport, icons, fonts)
  - exactly one H1; html lang + no-js class present
  - all JSON-LD blocks parse
  - internal links and local assets resolve to files in the repo
  - every <table> sits in a focusable scroll wrapper
  - external links carry target="_blank" and a rel with noopener
  - deployment hygiene: vercel.json parses; no _headers/_redirects; internal docs ignored
  - robots.txt, sitemap.xml (all URLs exist on disk; all indexable pages present), feed.xml well-formed
  - banned-phrase list (previously leaked/retired copy) never reappears
  - main.js parses (node --check) if node is available
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Release 2026.09.13-r2 regression checks.
# Each of these tests a defect that was actually found in a shipped build. They
# are deliberately narrow and mechanical. None of them validates clinical,
# coding or regulatory accuracy — that requires a qualified reviewer and is
# recorded in the clinical review log in VALIDATION_REPORT.md.
# ---------------------------------------------------------------------------

def regression_checks(root):
    import json as _json
    errors = []
    contact = (root / "contact.html").read_text(encoding="utf-8")

    # F07 — every service CTA resolves to an intake option (by stable ID or exact label)
    ids = set(re.findall(r'<option data-service-id="([^"]+)"', contact))
    labels = set(re.findall(r'<option[^>]*\svalue="([^"]*)"', contact))
    for p in sorted(root.glob("*.html")):
        src = p.read_text(encoding="utf-8")
        for raw in re.findall(r'contact\.html\?service=([^"\'>\s&#]+)', src):
            val = urllib.parse.unquote(raw)
            if val not in ids and val not in labels:
                errors.append(f"F07 {p.name}: service CTA '{val}' matches no intake option")

    # F03 — the confirmation region must not be inside the form it hides
    form_start = contact.find('<form id="intake-form"')
    form_end = contact.find("</form>", form_start)
    status = contact.find('id="intake-status"')
    if form_start != -1 and form_start < status < form_end:
        errors.append("F03 contact.html: #intake-status is nested inside #intake-form")

    # F11 — conditional groups must be fieldsets so they can be disabled, not just hidden
    for gid in ("case-fit-fields", "denial-intake-fields", "idr-intake-fields"):
        if not re.search(r'<fieldset[^>]*id="%s"' % gid, contact):
            errors.append(f"F11 contact.html: #{gid} is not a <fieldset> and cannot be disabled")

    # F08 — no CSS rule may display a dropdown independently of .nav-item.open
    css = (root / "style.css").read_text(encoding="utf-8")
    for m in re.finditer(r'([^\n{}]*(?:dropdown)[^\n{}]*)\{([^}]*)\}', css):
        sel, body = m.group(1), m.group(2)
        if "display:block" in body.replace(" ", "") and (":hover" in sel or ":focus-within" in sel):
            errors.append(f"F08 style.css: '{sel.strip()[:70]}' can show a dropdown outside the .open state")

    # F02 — the AR specimen's published arithmetic must reconcile
    ar_full = (root / "sample-ar-audit.html").read_text(encoding="utf-8")
    # scope strictly to the published inventory table, not the summary tables that
    # legitimately restate a subset of the same accounts
    _i = ar_full.find("<caption>Complete fictional inventory")
    ar = ar_full[_i:ar_full.find("</table>", _i)] if _i != -1 else ""
    rows = re.findall(r'<td>\$([\d,]+)</td><td>(Needs clinical record review|Missing information|'
                      r'Likely administrative routing|No clinical review indicated on the information supplied)</td>', ar)
    if len(rows) != 47:
        errors.append(f"F02 sample-ar-audit.html: inventory has {len(rows)} rows, expected 47")
    else:
        total = sum(int(v.replace(",", "")) for v, _ in rows)
        if total != 1274000:
            errors.append(f"F02 sample-ar-audit.html: inventory totals ${total:,}, expected $1,274,000")
        from collections import Counter
        counts = Counter(c for _, c in rows)
        expect = {"Needs clinical record review": 18, "Missing information": 12,
                  "Likely administrative routing": 10,
                  "No clinical review indicated on the information supplied": 7}
        for cat, n in expect.items():
            if counts.get(cat) != n:
                errors.append(f"F02 sample-ar-audit.html: '{cat}' has {counts.get(cat)} rows, expected {n}")
        review = sorted((int(v.replace(",", "")) for v, c in rows if c == "Needs clinical record review"), reverse=True)
        if review[:5] and min(review[:5]) < max(review[5:] or [0]):
            errors.append("F02 sample-ar-audit.html: the five listed top accounts are not the five largest")

    # F01 — the corrected clinical assertion must not come back
    banned_clinical = ["AKI is classified as an MCC", "AKI as an MCC",
                       "meets KDIGO Stage 2 AKI criteria", "Estimated recoverable"]
    for p in sorted(root.glob("*.html")):
        src = p.read_text(encoding="utf-8")
        for phrase in banned_clinical:
            if phrase in src:
                errors.append(f"F01/F02 {p.name}: retired assertion present — '{phrase}'")

    # F05 — every specimen carries a document-control block with a version and review date
    for p in sorted(root.glob("sample-*.html")):
        if p.name == "sample-work.html":
            continue
        src = p.read_text(encoding="utf-8")
        if 'class="doc-control"' not in src:
            errors.append(f"F05 {p.name}: no document-control block")
        if not re.search(r'SPEC-[A-Z0-9]+-\d{4}\.\d{2}-r\d', src):
            errors.append(f"F05 {p.name}: no specimen version identifier")

    # F14 — no page may link to a PDF that is not in the repository
    for p in sorted(root.glob("*.html")):
        src = p.read_text(encoding="utf-8")
        for href in re.findall(r'href="(/[^"]+\.pdf)"', src):
            if not (root / href.lstrip("/")).exists():
                errors.append(f"F14 {p.name}: links to missing PDF {href}")

    # F20 — shared page furniture and service data must come from one source.
    # Run the generator in check mode: if regenerating any shared region would change
    # a page, or if service names/prices have diverged between data/site.json, the
    # published catalog and the intake form, the release is stale.
    import subprocess
    r = subprocess.run([sys.executable, str(root / "scripts" / "build_shared.py"), "--check"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        for line in (r.stderr or "").strip().splitlines():
            errors.append("F20 " + line.replace("ERROR: ", ""))

    # F15 — every article carries a reviewer byline, a review date, and at least one
    # external source link inside the article body (not nav or footer)
    for p in sorted(root.glob("insight-*.html")):
        src = p.read_text(encoding="utf-8")
        i, j = src.find('<div class="article-body">'), src.find('<div class="article-cta">')
        body = src[i:j] if i != -1 and j > i else ""
        if 'class="article-byline"' not in src:
            errors.append(f"F15 {p.name}: no reviewer byline block")
        if "Last substantive review" not in src:
            errors.append(f"F15 {p.name}: no last-review date")
        if '"@type": "Person"' not in src:
            errors.append(f"F15 {p.name}: structured data does not name a person as author")
        if 'class="article-sources"' not in src:
            errors.append(f"F15 {p.name}: no Sources and limits section")
        if 'href="http' not in src[src.find('class="article-sources"'):] and 'href="http' not in body:
            errors.append(f"F15 {p.name}: no external primary source link in the article")

    # F15 — claims withdrawn for want of a source must not reappear
    withdrawn = ["highest denial-rate categories", "lowest appeal-filing rates",
                 "never appears in a denial dashboard", "95% of all denials"]
    for p in sorted(root.glob("*.html")):
        src = p.read_text(encoding="utf-8")
        for phrase in withdrawn:
            if phrase in src:
                errors.append(f"F15 {p.name}: withdrawn unsourced claim reappeared — '{phrase}'")

    # F18 — every indexable page has a recorded content date
    cd = root / "data" / "content-dates.json"
    if cd.exists():
        known = set(_json.loads(cd.read_text(encoding="utf-8"))["dates"])
        for p in sorted(root.glob("*.html")):
            if p.name not in known:
                errors.append(f"F18 {p.name}: no content date in data/content-dates.json")
    else:
        errors.append("F18 data/content-dates.json is missing")

    return errors

BASE = "https://clinovian.com/"

STUBS = {"clinovian_sample_appeal.html", "clinovian_sample_dossier.html"}
SELF_CONTAINED = {p.name for p in ROOT.glob("sample-*.html")} - {"sample-work.html"}

BANNED = [
    "should be removed or replaced",
    "should be removed or client-specific",
    "should not be used as a market fact",
    "so the first answer is yes",
    "verdict in 24",
    "Appealability screen",
    "1,082,247",
    "3-Case Denial Escalation Pilot",
    "3-Dispute IDR Clinical QA Pilot",
    "proposed independent review",
    "estimated appeal-deadline",
    "in the supplied site",
]

# Advisory language addressed to the site's owner rather than to a buyer. These
# regexes catch the class of leak found in the August 2026 audits (internal
# drafting notes shipped as published copy), not just the specific sentences.
INTERNAL_VOICE = [
    r"[Tt]he (?:name|page|site|website|section|copy|wording|label|heading|claim)s? "
    r"(?:should|must|needs? to|ought to|may need)",
    r"should be (?:reviewed|removed|replaced|renamed|reworded|dropped|deleted|shortened|expanded)"
    r"(?! by (?:the client|counsel|your))",
    r"(?:may|might) be the (?:safer|better|clearer|stronger)",
    r"consider (?:renaming|removing|replacing|rewording)",
    r"\b(?:TODO|TBD|FIXME|DRAFT NOTE|lorem ipsum)\b",
    r"is unsourced|citation needed|needs a source(?![\w-])",
    r"\[(?:insert|add|update|confirm)\b",
]

# Phrases that are legitimately client-facing despite matching the patterns above.
INTERNAL_VOICE_ALLOW = (
    "should be verified with the payer",
    "should be reviewed by the client",
    "reviewed by the client's counsel",
    "reviewed by the client\u2019s counsel",
)

CANONICAL_FONTS = ("family=Spectral:ital,wght@0,400;0,500;0,600;1,400&amp;"
                   "family=Outfit:wght@400;500;600;700&amp;"
                   "family=JetBrains+Mono:wght@400;500;600&amp;display=swap")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def check_page(p: pathlib.Path, files: set[str]) -> None:
    src = p.read_text(encoding="utf-8", errors="replace")
    name = p.name
    stub = name in STUBS

    if '<html lang="en"' not in src:
        err(f"{name}: missing <html lang=\"en\">")
    if 'class="no-js"' not in src.split(">", 2)[1] + ">" and 'class="no-js"' not in src[:250]:
        err(f"{name}: <html> missing no-js class")

    title = re.search(r"<title>(.*?)</title>", src, re.S)
    if not title:
        err(f"{name}: missing <title>")
    elif len(title.group(1).strip()) > 70:
        warn(f"{name}: title {len(title.group(1).strip())} chars (>70)")

    if not stub:
        desc = re.search(r'<meta name="description" content="([^"]*)"', src)
        if not desc:
            err(f"{name}: missing meta description")
        elif not (60 <= len(desc.group(1)) <= 165):
            warn(f"{name}: description {len(desc.group(1))} chars (target 60-160)")
        robots = re.search(r'<meta name="robots" content="([^"]*)"', src)
        noindex = bool(robots and "noindex" in robots.group(1))
        if not noindex and 'rel="canonical"' not in src:
            err(f"{name}: missing canonical")
        if not noindex and 'property="og:url"' not in src:
            err(f"{name}: missing og:url")
        if name not in STUBS and 'rel="icon"' not in src:
            err(f"{name}: missing favicon link")
        if name == "404.html" and not noindex:
            err("404.html: must carry noindex")
        if not SELF_CONTAINED.issuperset({name}) and "fonts.googleapis.com/css2" in src:
            if CANONICAL_FONTS not in src:
                err(f"{name}: non-canonical Google Fonts URL")

    h1s = re.findall(r"<h1[\s>]", src)
    if not stub and len(h1s) != 1:
        err(f"{name}: {len(h1s)} <h1> elements (need exactly 1)")

    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        try:
            json.loads(m.group(1))
        except Exception as e:  # noqa: BLE001
            err(f"{name}: invalid JSON-LD ({e})")

    for m in re.finditer(r'(?:href|src)="(/[^"#?]*)[#?]?[^"]*"', src):
        target = m.group(1).lstrip("/")
        if not target:
            continue
        if target not in files:
            err(f"{name}: broken local reference /{target}")

    for m in re.finditer(r"<table\b", src):
        before = src[max(0, m.start() - 220):m.start()]
        if 'tabindex="0"' not in before or "table-wrap" not in before and "table-scroll" not in before:
            err(f"{name}: <table> without focusable scroll wrapper near offset {m.start()}")

    for m in re.finditer(r'<a ([^>]*href="https?://[^"]+"[^>]*)>', src):
        attrs = m.group(1)
        if "clinovian.com" in attrs:
            continue
        if 'target="_blank"' not in attrs:
            err(f"{name}: external link missing target=_blank :: {attrs[:70]}")
        if "noopener" not in attrs:
            err(f"{name}: external link missing rel noopener :: {attrs[:70]}")

    low = src.lower()
    for phrase in BANNED:
        if phrase.lower() in low:
            err(f"{name}: banned phrase present: {phrase!r}")

    visible = re.sub(r"<script.*?</script>|<style.*?</style>", " ", src, flags=re.S)
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", visible))
    for pattern in INTERNAL_VOICE:
        for m in re.finditer(pattern, visible):
            snippet = visible[max(0, m.start() - 80):m.end() + 90]
            if any(a in snippet for a in INTERNAL_VOICE_ALLOW):
                continue
            err(f"{name}: internal/advisory language in published copy: "
                f"...{visible[max(0, m.start() - 40):m.end() + 50].strip()}...")


def check_repo() -> None:
    files = {p.name for p in ROOT.iterdir()}
    files |= {"scripts/" + p.name for p in (ROOT / "scripts").glob("*")} if (ROOT / "scripts").exists() else set()

    for legacy in ("_headers", "_redirects"):
        if (ROOT / legacy).exists():
            err(f"{legacy} present — Netlify files must not ship alongside vercel.json")

    try:
        vercel = json.loads((ROOT / "vercel.json").read_text())
        if "rewrites" in vercel:
            err("vercel.json: rewrites section present (legacy SPA config)")
        csp = ""
        for rule in vercel.get("headers", []):
            for h in rule.get("headers", []):
                if h["key"].lower() == "content-security-policy":
                    csp = h["value"]
        if "formspree.io" not in csp:
            err("vercel.json CSP does not allow formspree.io")
    except FileNotFoundError:
        err("vercel.json missing")
    except Exception as e:  # noqa: BLE001
        err(f"vercel.json invalid: {e}")

    ignore = (ROOT / ".vercelignore")
    if not ignore.exists():
        err(".vercelignore missing")
    else:
        body = ignore.read_text()
        for doc in ("CHANGELOG.md", "DEPLOYMENT.md", "IDR_CLAIMS_REGISTER.md",
                    "RELEASE_NOTES.md", "VALIDATION_REPORT.md"):
            if doc not in body:
                err(f".vercelignore missing {doc}")

    try:
        catalog = json.loads((ROOT / "service-catalog.json").read_text())
        for svc in catalog["services"]:
            page = ROOT / svc["url"].lstrip("/")
            if not page.exists():
                err(f"service-catalog.json: {svc['id']} points at missing page {svc['url']}")
                continue
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page.read_text(encoding="utf-8")))
            m = re.match(r"From \$([\d,]+)", svc["price"])
            if m and f"${m.group(1)}" not in text:
                err(f"service-catalog.json: price {svc['price']!r} not shown on {svc['url']}")
            turn = re.match(r"([\d\u2013\-]+ (?:hours|business days))", svc["turnaround"])
            if turn and turn.group(1) not in text:
                err(f"service-catalog.json: turnaround {turn.group(1)!r} not shown on {svc['url']}")
    except FileNotFoundError:
        warn("service-catalog.json absent (fine if intentionally not published)")
    except Exception as e:  # noqa: BLE001
        err(f"service-catalog.json invalid: {e}")

    try:
        vercel_txt = (ROOT / "vercel.json").read_text()
        if '"type": "host"' not in vercel_txt and '"type":"host"' not in vercel_txt:
            err("vercel.json: no host-level redirect — www and apex will both serve (duplicate content)")
    except FileNotFoundError:
        pass

    robots = (ROOT / "robots.txt").read_text()
    if "Sitemap: https://clinovian.com/sitemap.xml" not in robots:
        err("robots.txt missing sitemap line")

    try:
        tree = ET.parse(ROOT / "sitemap.xml")
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [u.text for u in tree.findall(".//s:loc", ns)]
        on_disk = set()
        for loc in locs:
            fname = loc.replace(BASE, "") or "index.html"
            on_disk.add(fname)
            if fname not in files:
                err(f"sitemap.xml lists missing file {fname}")
        for p in ROOT.glob("*.html"):
            if p.name in STUBS or p.name == "404.html":
                continue
            src = p.read_text(encoding="utf-8", errors="replace")
            robots_meta = re.search(r'<meta name="robots" content="([^"]*)"', src)
            if robots_meta and "noindex" in robots_meta.group(1):
                continue
            if p.name not in on_disk:
                err(f"sitemap.xml missing indexable page {p.name}")
        if not tree.findall(".//s:lastmod", ns):
            err("sitemap.xml has no lastmod values")
    except Exception as e:  # noqa: BLE001
        err(f"sitemap.xml invalid: {e}")

    try:
        ET.parse(ROOT / "feed.xml")
    except Exception as e:  # noqa: BLE001
        err(f"feed.xml invalid: {e}")

    if shutil.which("node"):
        r = subprocess.run(["node", "--check", str(ROOT / "main.js")],
                           capture_output=True, text=True)
        if r.returncode != 0:
            err(f"main.js syntax: {r.stderr.strip()[:200]}")
    else:
        warn("node not available — main.js not syntax-checked")

    for p in sorted(ROOT.glob("*.html")):
        check_page(p, files)


def main() -> int:
    check_repo()
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(errors)} errors, {len(warnings)} warnings across "
          f"{len(list(ROOT.glob('*.html')))} pages")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
