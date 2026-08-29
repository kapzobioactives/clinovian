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

ROOT = pathlib.Path(__file__).resolve().parent.parent
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
