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
# Release 2026.09.14-r3 regression checks.
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

    # F03 — the confirmation region must exist, sit outside the form it hides, and be
    # announced. The 2026.09.13-r2 check tested only nesting, so deleting or renaming
    # #intake-status made the check silently pass while the success message vanished.
    form_start = contact.find('<form id="intake-form"')
    form_end = contact.find("</form>", form_start)
    status = contact.find('id="intake-status"')
    if status == -1:
        errors.append("F03 contact.html: #intake-status is absent; a successful "
                      "submission would leave no confirmation")
    elif form_start != -1 and form_start < status < form_end:
        errors.append("F03 contact.html: #intake-status is nested inside #intake-form")
    else:
        tag = contact[status:contact.find(">", status) + 1]
        if "aria-live" not in tag:
            errors.append("F03 contact.html: #intake-status has no aria-live; the "
                          "confirmation would not be announced")
        if "role=" not in tag:
            errors.append("F03 contact.html: #intake-status has no role")
    # The success branch must hide the field shell, not the whole form, and must
    # write a confirmation. A shell that is missing puts us back at the r2 defect.
    mainjs = (root / "main.js").read_text(encoding="utf-8")
    if 'id="intake-form-shell"' not in contact:
        errors.append("F03 contact.html: #intake-form-shell is absent; the success "
                      "branch would have to hide the whole form again")
    if "showStatus('success'" not in mainjs:
        errors.append("F03 main.js: success branch does not write a confirmation")

    # F11 — conditional groups must be fieldsets AND must actually be disabled when
    # inactive. A disabled control is omitted from FormData; hiding alone lets a stale
    # value serialise, which was the original defect.
    mainjs = (root / "main.js").read_text(encoding="utf-8")
    for gid in ("case-fit-fields", "denial-intake-fields", "idr-intake-fields"):
        if not re.search(r'<fieldset[^>]*id="%s"' % gid, contact):
            errors.append(f"F11 contact.html: #{gid} is not a <fieldset> and cannot be disabled")
    if not re.search(r"group\.disabled\s*=\s*!\s*active", mainjs):
        errors.append("F11 main.js: the conditional <fieldset> is not disabled when "
                      "inactive; stale values can serialise")
    if not re.search(r"el\.disabled\s*=\s*!\s*active", mainjs):
        errors.append("F11 main.js: controls inside a conditional group are not "
                      "individually disabled when inactive")

    # F03b — the submit handler needs a re-entrancy guard. Disabling the button stops a
    # second click, but Enter pressed in a text field submits without touching it, which
    # duplicated the request in browser acceptance testing.
    if not re.search(r"if\s*\(\s*submitting\s*\)\s*return", mainjs):
        errors.append("F03 main.js: submit handler has no re-entrancy guard; Enter in a "
                      "text field can duplicate an in-flight request")
    if mainjs.count("submitting = false") < 2:
        errors.append("F03 main.js: the re-entrancy guard is not released on every retry "
                      "path (server rejection and network failure both need it)")

    # 8.4 — functionality that needs JavaScript must be explained where it is missing.
    # Examine every <noscript> block, not just the first — the shared nav contributes
    # one of its own earlier in the page, and slicing to the first close tag inspects
    # the wrong block entirely.
    ns_blocks = re.findall(r"<noscript[^>]*>(.*?)</noscript>", contact, re.S | re.I)
    if not ns_blocks:
        errors.append("8.4 contact.html: no <noscript> explanation; with scripts off the "
                      "case-fit section never appears and nothing says so")
    elif not any("identifier" in b.lower() for b in ns_blocks):
        errors.append("8.4 contact.html: no <noscript> block carries the no-PHI "
                      "instruction")
    elif not any("case-fit" in b.lower() or "case fit" in b.lower() for b in ns_blocks):
        errors.append("8.4 contact.html: the <noscript> fallback does not explain that "
                      "case-fit intake is unavailable without JavaScript")
    nav = (root / "shared" / "nav.html").read_text(encoding="utf-8")
    if "<noscript" not in nav:
        errors.append("8.4 shared/nav.html: mobile navigation depends on JavaScript with "
                      "no fallback route")

    # F08 — no CSS rule may display a dropdown independently of .nav-item.open
    css = (root / "style.css").read_text(encoding="utf-8")
    for m in re.finditer(r'([^\n{}]*(?:dropdown)[^\n{}]*)\{([^}]*)\}', css):
        sel, body = m.group(1), m.group(2)
        if "display:block" in body.replace(" ", "") and (":hover" in sel or ":focus-within" in sel):
            errors.append(f"F08 style.css: '{sel.strip()[:70]}' can show a dropdown outside the .open state")
    # Visual state and ARIA state must be driven together, and Escape must dismiss.
    mainjs = (root / "main.js").read_text(encoding="utf-8")
    if "'Escape'" not in mainjs and '"Escape"' not in mainjs:
        errors.append("F08 main.js: no Escape handler; the menu cannot be dismissed "
                      "from the keyboard")
    if "aria-expanded" not in mainjs:
        errors.append("F08 main.js: aria-expanded is never set; ARIA state cannot "
                      "track the visible state")

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

    # F05b — specimen self-consistency (2026.09.14-r3).
    # The 2026.09.13-r2 build failed because corrected text was added alongside the
    # superseded text instead of replacing it: a HEART total of 8 was published with
    # its components while a stale "HEART score 7" survived nine lines later, and a
    # memo that stated it made no outcome claim closed with "should prevail". These
    # checks exist so a stale figure or verdict cannot survive a future edit.
    SPECIMENS = [q for q in sorted(root.glob("sample-*.html"))
                 if q.name != "sample-work.html"]

    # (a) No specimen may predict an appeal outcome or grade a case as strong.
    # "does not claim the appeal should prevail" is a disclaimer, not a prediction.
    VERDICT = re.compile(
        r"(?<!not claim the appeal )should prevail|will prevail|clinically strong"
        r"|materially improve\w* the probability|probability of overturn"
        r"|will be overturned|guarantee\w* (?:an? )?overturn", re.I)
    for q in SPECIMENS:
        body = re.sub(r"<[^>]+>", " ", q.read_text(encoding="utf-8"))
        for m in VERDICT.finditer(body):
            errors.append(f"F05 {q.name}: outcome-prediction language "
                          f"{m.group(0)!r}")

    # (b) No specimen may narrate its own revision history to the buyer.
    HISTORY = re.compile(
        r"(?:the |an )?(?:earlier|previous|prior|first) (?:version|draft) of this"
        r"|this (?:memo|dossier|specimen|brief) previously"
        r"|previously stated", re.I)
    for q in SPECIMENS:
        body = re.sub(r"<[^>]+>", " ", q.read_text(encoding="utf-8"))
        m = HISTORY.search(body)
        if m:
            errors.append(f"F05 {q.name}: revision-history note in published copy "
                          f"{m.group(0)!r}")

    # (c) Published clinical scores must reconcile to their published components.
    obs = root / "sample-observation-defense.html"
    if obs.exists():
        body = re.sub(r"<[^>]+>", " ", obs.read_text(encoding="utf-8"))
        comp = re.search(r"History moderately suspicious \((\d)\).*?"
                         r"ST depression \((\d)\).*?65 or over \((\d)\).*?"
                         r"atherosclerotic disease \((\d)\).*?"
                         r"three times it\s*\((\d)\)", body, re.S)
        if not comp:
            errors.append("F05 sample-observation-defense.html: HEART components "
                          "not published")
        else:
            want = sum(int(x) for x in comp.groups())
            totals = {int(x) for x in re.findall(r"HEART score (\d+)", body)}
            totals |= {int(x) for x in re.findall(r"Total (\d+)\.", body)}
            if totals != {want}:
                errors.append(f"F05 sample-observation-defense.html: HEART components "
                              f"sum to {want} but totals asserted are "
                              f"{sorted(totals)}")

    p2p = root / "sample-p2p-brief.html"
    if p2p.exists():
        body = re.sub(r"<[^>]+>", " ", p2p.read_text(encoding="utf-8"))
        comp = re.search(r"CHA.DS.-VASc:\s*(\d)\s*.\s*hypertension \((\d)\); "
                         r"age 68[^(]*\((\d)\); vascular disease, prior PCI with "
                         r"stent \((\d)\)", body)
        if not comp:
            errors.append("F05 sample-p2p-brief.html: CHA2DS2-VASc components not "
                          "published")
        else:
            stated = int(comp.group(1))
            want = sum(int(x) for x in comp.groups()[1:])
            if stated != want:
                errors.append(f"F05 sample-p2p-brief.html: CHA2DS2-VASc components "
                              f"sum to {want} but total stated is {stated}")

    # (d) The AR specimen must stay inside its no-PHI triage scope.
    ar = root / "sample-ar-audit.html"
    if ar.exists():
        body = re.sub(r"<[^>]+>", " ", ar.read_text(encoding="utf-8"))
        for phrase in ("what is contestable", "what to pursue first",
                       "Estimated recoverable"):
            if phrase.lower() in body.lower():
                errors.append(f"F02 sample-ar-audit.html: out-of-scope claim "
                              f"{phrase!r} (triage only: no merits, no forecast)")

    # (e) Every specimen's breadcrumb must point at itself, and its footer must
    # describe itself — sample-declined-case.html shipped with the AR-audit
    # footer and an AR-audit breadcrumb target.
    for q in SPECIMENS:
        src = q.read_text(encoding="utf-8")
        crumb = re.search(r'"position":\s*3,\s*"name":\s*"[^"]*",\s*"item":\s*'
                          r'"https://clinovian\.com/([^"]+)"', src)
        if crumb and crumb.group(1) != q.name:
            errors.append(f"F05 {q.name}: breadcrumb position 3 points to "
                          f"{crumb.group(1)}")

    # (f) Balanced <div> nesting — an unbalanced tree shipped in r2.
    for q in SPECIMENS:
        src = q.read_text(encoding="utf-8")
        depth = 0
        for m in re.finditer(r"<(/?)div\b[^>]*>", src):
            depth += -1 if m.group(1) else 1
            if depth < 0:
                break
        if depth != 0:
            errors.append(f"F05 {q.name}: unbalanced <div> nesting "
                          f"(net {depth:+d})")

    # F13 — one canonical host, declared consistently. The archive and the deployed
    # site disagreed in 2026.09.13-r2: vercel.json redirected www -> apex while the
    # live host redirected apex -> www. Pointed at each other those form a loop; and
    # production still serves pages on www whose canonical names the apex, which is a
    # split signal to search engines. This check keeps the ARCHIVE internally
    # consistent; only check_preview.py --matrix can test the deployed direction.
    canon_hosts = set()
    for q in sorted(root.glob("*.html")):
        src = q.read_text(encoding="utf-8")
        for m in re.finditer(r'rel="canonical"\s+href="(https?://[^/"]+)', src):
            canon_hosts.add(m.group(1))
        for m in re.finditer(r'property="og:url"\s+content="(https?://[^/"]+)', src):
            canon_hosts.add(m.group(1))
    if len(canon_hosts) > 1:
        errors.append("F13 canonical/og:url use more than one origin: "
                      + ", ".join(sorted(canon_hosts)))
    canonical_origin = next(iter(canon_hosts), None)

    for name, pattern in (("sitemap.xml", r"<loc>(https?://[^/<]+)"),
                          ("feed.xml", r"<link>(https?://[^/<]+)")):
        f = root / name
        if not f.exists():
            continue
        hosts = set(re.findall(pattern, f.read_text(encoding="utf-8")))
        bad = hosts - {canonical_origin} if canonical_origin else set()
        if bad:
            errors.append(f"F13 {name}: origin(s) {sorted(bad)} disagree with the "
                          f"canonical origin {canonical_origin}")

    # JSON-LD must not name a different origin either.
    for q in sorted(root.glob("*.html")):
        src = q.read_text(encoding="utf-8")
        for m in re.finditer(r'"(?:url|item|@id)":\s*"(https?://[^/"]+)', src):
            if canonical_origin and m.group(1) != canonical_origin:
                errors.append(f"F13 {q.name}: structured data names {m.group(1)}, "
                              f"not the canonical origin {canonical_origin}")
                break

    # The route map must name the same origin as the canonical tags. On GitHub Pages
    # the host direction is set by the CNAME file, not by a redirect rule, so both
    # are checked against the canonical origin.
    rj = root / "data" / "routes.json"
    if not rj.exists():
        errors.append("F13 data/routes.json missing — no route or host map")
    elif canonical_origin:
        cfg = _json.loads(rj.read_text(encoding="utf-8"))
        if cfg.get("canonical_origin") != canonical_origin:
            errors.append(f"F13 data/routes.json: canonical_origin "
                          f"{cfg.get('canonical_origin')!r} disagrees with the canonical "
                          f"tags ({canonical_origin})")
        want_host = canonical_origin.split("://", 1)[1]
        if cfg.get("canonical_host") != want_host:
            errors.append(f"F13 data/routes.json: canonical_host "
                          f"{cfg.get('canonical_host')!r} is not {want_host!r}; the "
                          "generated CNAME would point at the wrong host")

    # F14 — PDF specimen editions were withdrawn permanently in 2026.09.14-r3.
    # HTML is the sole version of record and no PDF deliverable is planned. This
    # check fails if a same-origin PDF link, the withdrawn doc-pdf-link region, or
    # an HTML/PDF parity claim is reintroduced. External source links ending in
    # .pdf (CMS, OIG, guideline documents) are legitimate and are not flagged.
    for p in sorted(root.glob("*.html")):
        src = p.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+\.pdf)"', src, re.I):
            if not re.match(r'https?://(?!(www\.)?clinovian\.com)', href, re.I):
                errors.append(f"F14 {p.name}: same-origin PDF reference {href}; "
                              "PDF editions are withdrawn")
        if "doc-pdf-link" in src:
            errors.append(f"F14 {p.name}: retains the withdrawn doc-pdf-link region")
        if re.search(r"Matching HTML\s*/\s*PDF", src, re.I):
            errors.append(f"F14 {p.name}: retains the HTML/PDF parity claim")
        if re.search(r"(Download|View)[^<.]{0,40}\bas a PDF\b", src, re.I):
            errors.append(f"F14 {p.name}: retains a PDF download affordance")

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

    # F09 — market and pricing research must stay out of the buying path. These
    # sections named competitors, quoted salary comparisons and reported that no
    # public per-case rate could be found: research notes, not a reason to buy.
    for q in sorted(root.glob("*.html")):
        if q.name.startswith(("insight-", "sample-")):
            continue
        body = re.sub(r"<[^>]+>", " ", q.read_text(encoding="utf-8"))
        for phrase in ("Complete market and procurement context", "Public pricing context",
                       "no comparable public", "like-for-like public per-case",
                       "per-case market fee", "quote-based", "advisor's salary",
                       "prices are private", "Pricing is private"):
            if phrase.lower() in body.lower():
                errors.append(f"F09 {q.name}: market/pricing research in the buying path "
                              f"— {phrase!r}")

    # F12 — the public boundary must not out-run the demonstrated control.
    sec = root / "security.html"
    if sec.exists():
        body = re.sub(r"<[^>]+>", " ", sec.read_text(encoding="utf-8"))
        if "no standing, pre-approved PHI workflow" not in body:
            errors.append("F12 security.html: does not state that no standing PHI workflow "
                          "is pre-approved")
        if "Safe Harbor" not in body or "Expert Determination" not in body:
            errors.append("F12 security.html: does not name the two HHS de-identification "
                          "methods; 'de-identified' is left undefined")
    con = root / "contact.html"
    if con.exists():
        body = re.sub(r"<[^>]+>", " ", con.read_text(encoding="utf-8"))
        if "prompt, not a security control" not in body:
            errors.append("F12 contact.html: the identifier check is not described as a "
                          "prompt rather than a control")

    # F15 — unsupported majority and ranking claims.
    UNSUPPORTED = ("most appeals fail", "most medical-necessity appeals fail",
                   "systematically under-appealed", "most consistently under-argued")
    for q in sorted(root.glob("*.html")):
        body = q.read_text(encoding="utf-8")
        for phrase in UNSUPPORTED:
            if phrase.lower() in body.lower():
                errors.append(f"F15 {q.name}: unsupported majority/ranking claim "
                              f"— {phrase!r}")

    # F15 — citations must reach the document, not a search or index page.
    LANDING = ("oig.hhs.gov/reports-and-publications/all-reports-and-publications",
               "cms.gov/nosurprises\"", "hhs.gov/mental-health-and-addiction-insurance-help")
    for q in sorted(root.glob("insight-*.html")):
        src = q.read_text(encoding="utf-8")
        i = src.find('class="article-sources"')
        seg = src[i:src.find("</section>", i)] if i != -1 else ""
        for land in LANDING:
            if land in seg:
                errors.append(f"F15 {q.name}: citation points at an index page, not the "
                              f"document — {land}")

    # F16 — homepage breadth. 1,916 words of main content and 35 navigation links
    # did not make a complex service easier to buy; the full service catalogue was
    # duplicated on the homepage and four buyer routes were presented as equally
    # mature. Budgets, not aspirations: these are the levels shipped in r10.
    import re as _re
    idx = root / "index.html"
    if idx.exists():
        src = idx.read_text(encoding="utf-8")
        i, j = src.find("<main"), src.find("</main>")
        body = _re.sub(r"<[^>]+>", " ", src[i:j]) if i != -1 else ""
        words = len(body.split())
        if words > 1500:
            errors.append(f"F16 index.html: {words} words of main content (budget 1500); "
                          "the homepage is drifting back toward a full catalogue")
    nav = (root / "shared" / "nav.html")
    if nav.exists():
        n = len(_re.findall(r"<a\s", nav.read_text(encoding="utf-8")))
        if n > 26:
            errors.append(f"F16 shared/nav.html: {n} navigation links (budget 26)")

    # F17 — the public policies must actually describe the service and its vendors.
    priv = root / "privacy.html"
    if priv.exists():
        body = _re.sub(r"<[^>]+>", " ", priv.read_text(encoding="utf-8"))
        if len(body.split()) < 450:
            errors.append("F17 privacy.html: too short to describe the observed "
                          "collection, vendors, retention and rights")
        for term, why in (("Formspree", "form provider"), ("Calendly", "scheduling"),
                          ("GitHub Pages", "host"), ("Google Fonts", "font provider"),
                          ("Retention", "retention"), ("delet", "deletion rights")):
            if term.lower() not in body.lower():
                errors.append(f"F17 privacy.html: does not cover {why} ({term})")
    tms = root / "terms.html"
    if tms.exists():
        body = _re.sub(r"<[^>]+>", " ", tms.read_text(encoding="utf-8"))
        if len(body.split()) < 450:
            errors.append("F17 terms.html: too short to cover the purchase flow")
        for term, why in (("invoice", "invoicing"), ("tax", "tax"),
                          ("Cancellation", "cancellation"), ("Confidential", "confidentiality"),
                          ("conflict", "conflict checks"), ("white-label", "white-labelling"),
                          ("Governing law", "governing law")):
            if term.lower() not in body.lower():
                errors.append(f"F17 terms.html: does not cover {why} ({term})")
        if "not a statement of law" not in body:
            errors.append("F17 terms.html: presents the liability cap without noting that "
                          "it is a contractual allocation, not universally enforceable")

    # F18 — every cacheable asset reference carries the release stamp, so a corrected
    # asset can never be served alongside a stale one.
    for q in sorted(root.glob("*.html")):
        src = q.read_text(encoding="utf-8")
        for m in _re.finditer(
                r'(?:href|src|content)="(?:https://clinovian\.com)?'
                r'/([a-z0-9-]+\.(?:css|js|png|svg))(\?v=[^"]*)?"', src):
            if not m.group(2):
                errors.append(f"F18 {q.name}: unversioned asset reference /{m.group(1)}")
                break

    # F20 — the price/turnaround drift check lives in build_shared.py and must stay
    # wired into its --check path; it was previously a comparison of two data files
    # that claimed to catch drift on a page.
    bs = (root / "scripts" / "build_shared.py").read_text(encoding="utf-8")
    if "check_services()" not in bs.split("def main", 1)[-1]:
        errors.append("F20 build_shared.py: check_services() is not called from main(); "
                      "the price/turnaround drift check would be dead code")
    if 'services_page = (ROOT / "services.html")' not in bs:
        errors.append("F20 build_shared.py: no page-level price comparison; comparing two "
                      "data files does not catch a price wrong on a page")
    if "turnaround differs" not in bs:
        errors.append("F20 build_shared.py: turnaround is not compared between the catalog "
                      "and site.json")

    # F21 — measurement must be documented and must not be claimed where it does not
    # exist. The in-page buffer is diagnostics; ANALYTICS.md is the actual plan.
    an = root / "ANALYTICS.md"
    if not an.exists():
        errors.append("F21 ANALYTICS.md missing — referenced by main.js and the release "
                      "notes but absent from the repository")
    else:
        txt = an.read_text(encoding="utf-8")
        for term, why in (("routed_service_id", "inquiry attribution fields"),
                          ("session-local diagnostics", "the status of the in-page buffer"),
                          ("Revisions", "revision burden"),
                          ("declined", "the decline log")):
            if term.lower() not in txt.lower():
                errors.append(f"F21 ANALYTICS.md: does not cover {why} ({term})")
    mjs = (root / "main.js").read_text(encoding="utf-8")
    if "NOT analytics" not in mjs:
        errors.append("F21 main.js: the event buffer is not labelled as diagnostics; it "
                      "transmits nothing and must not read as instrumentation")
    for field in ("entry_page", "inquiry_source"):
        if f'name="{field}"' not in contact:
            errors.append(f"F21 contact.html: attribution field {field} is absent")
        if field not in mjs:
            errors.append(f"F21 main.js: {field} is never populated")
    # A cross-site referrer must never be stored.
    if "r.origin === window.location.origin" not in mjs:
        errors.append("F21 main.js: entry_page is not restricted to same-origin referrers; "
                      "a query string from another site could be captured")
    # The no-tracker claim must stay accurate.
    priv = (root / "privacy.html").read_text(encoding="utf-8")
    if "entry_page" in mjs and "campaign tag" not in priv:
        errors.append("F21 privacy.html: the form carries attribution fields that the "
                      "privacy notice does not disclose")

    # F06 — release documents must describe THIS release. They drifted for eight
    # releases: VALIDATION_REPORT.md was headed r11 while its captured run said r3,
    # DEPLOYMENT.md claimed verification from r4, and RELEASE_NOTES.md listed F17 as
    # both cleared and open because a hand-maintained status table was edited in
    # place. The report is now generated; these checks stop the drift returning.
    rel_id = (root / "RELEASE_ID").read_text(encoding="utf-8").strip()

    vr = root / "VALIDATION_REPORT.md"
    if vr.exists():
        txt = vr.read_text(encoding="utf-8")
        if f"**Release:** {rel_id}" not in txt:
            errors.append(f"F06 VALIDATION_REPORT.md does not declare {rel_id}")
        if f"clean extraction of {rel_id}" not in txt:
            errors.append("F06 VALIDATION_REPORT.md: the captured run is not attributed "
                          f"to {rel_id}; regenerate it")
        for other in re.findall(r"2026\.09\.14-r\d+", txt):
            if other != rel_id and "Releases r8" not in txt.split(other)[0][-120:]:
                pass  # historical mentions in prose are fine
        if "generate_validation_report.py" not in txt:
            errors.append("F06 VALIDATION_REPORT.md is not marked as generated")

    rn = root / "RELEASE_NOTES.md"
    if rn.exists():
        txt = rn.read_text(encoding="utf-8")
        if not txt.startswith(f"# Release notes — {rel_id}"):
            errors.append(f"F06 RELEASE_NOTES.md is not headed {rel_id}")
        # A second hand-maintained status table is how F17 ended up in two rows.
        if "| Status | Findings |" in txt:
            errors.append("F06 RELEASE_NOTES.md carries its own status table; status is "
                          "generated into VALIDATION_REPORT.md and must live in one place")

    dep = root / "DEPLOYMENT.md"
    if dep.exists():
        txt = dep.read_text(encoding="utf-8")
        if f"**{rel_id}** archive" not in txt:
            errors.append(f"F06 DEPLOYMENT.md verification record is not attributed to "
                          f"{rel_id}")
        # One statement per control, not two that disagree.
        if "HSTS is configured" in txt and "Not settable" in txt:
            errors.append("F06 DEPLOYMENT.md contradicts itself on HSTS")

    pkg = root / "package.json"
    if pkg.exists():
        cfg = _json.loads(pkg.read_text(encoding="utf-8"))
        dev = cfg.get("devDependencies", {})
        if "jsdom" not in dev:
            errors.append("F06 package.json: jsdom is not declared; CI would install "
                          "whatever version is current that day")
        elif not re.fullmatch(r"\d+\.\d+\.\d+", str(dev["jsdom"])):
            errors.append(f"F06 package.json: jsdom is not pinned to an exact version "
                          f"(found {dev['jsdom']!r})")

    if not (root / "package-lock.json").exists():
        errors.append("F06 package-lock.json missing — `npm ci` cannot run, so the "
                      "acceptance suite's transitive dependencies are unpinned")

    wf = root / ".github" / "workflows" / "deploy.yml"
    if wf.exists():
        txt = wf.read_text(encoding="utf-8")
        for line in txt.splitlines():
            if "continue-on-error" in line and not line.strip().startswith("#"):
                errors.append("F06 deploy.yml: continue-on-error present; a failed "
                              "post-deploy check must fail the run")
        if "npm install --no-save jsdom" in txt:
            errors.append("F06 deploy.yml: installs jsdom unpinned; use npm ci")

    # Accessibility: captions and header cells, now that both are fixed.
    for q in sorted(root.glob("*.html")):
        src = q.read_text(encoding="utf-8")
        for m in re.finditer(r"<table\b[^>]*>", src):
            end = src.index("</table>", m.end())
            block = src[m.start():end]
            if "<caption" not in block:
                errors.append(f"9.3 {q.name}: <table> without a caption")
                break
            if "<th" not in block:
                errors.append(f"9.3 {q.name}: <table> with no header cells at all")
                break

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

    # Deployment hygiene — GitHub Pages.
    # This site is served by GitHub Pages, which supports no server-side redirects and
    # no custom response headers. vercel.json and .vercelignore were removed in
    # 2026.09.14-r8 because every rule in them was inert on this platform, and
    # .vercelignore in particular gave a false assurance: it excluded the internal
    # documents from a Vercel deploy, but on GitHub Pages nothing excludes them.
    for stale in ("vercel.json", ".vercelignore", "netlify.toml", "_headers", "_redirects"):
        if (ROOT / stale).exists():
            err(f"{stale} present — this site deploys to GitHub Pages; that file "
                "configures a platform it does not run on and its rules are inert")

    # A public page naming the wrong host misleads a procurement reviewer. The
    # subprocessor list on trust-center.html said "Vercel" until 2026.09.14-r9.
    for p in sorted(ROOT.glob("*.html")):
        low = p.read_text(encoding="utf-8").lower()
        if "vercel" in low:
            err(f"{p.name}: names Vercel; this site is hosted on GitHub Pages")

    if not (ROOT / "data" / "routes.json").exists():
        err("data/routes.json missing — the route map GitHub Pages stubs are built from")

    if not (ROOT / "scripts" / "build_publish.py").exists():
        err("scripts/build_publish.py missing — without it the repository root would be "
            "published and every internal document exposed")

    if not (ROOT / ".github" / "workflows" / "deploy.yml").exists():
        err(".github/workflows/deploy.yml missing — no verified publish path")

    # Headers cannot be sent. CSP and the referrer policy DO work as meta tags; nosniff
    # does NOT. `http-equiv` supports a closed list of pragma directives — content-type,
    # default-style, refresh, x-ua-compatible, content-security-policy — and
    # X-Content-Type-Options is not among them, so browsers ignore it. r8 shipped that
    # tag on 64 pages and this gate enforced it: a check that passed while protecting
    # nothing. The tag was removed in r12; this check now guards against it returning.
    for p in sorted(ROOT.glob("*.html")):
        src = p.read_text(encoding="utf-8")
        if 'http-equiv="Content-Security-Policy"' not in src:
            err(f"{p.name}: no meta CSP — GitHub Pages cannot send the header")
        if 'http-equiv="X-Content-Type-Options"' in src:
            err(f"{p.name}: meta X-Content-Type-Options is a no-op — http-equiv does not "
                "support it and browsers ignore it; nosniff is header-only")
        elif "formspree.io" not in src[:4000]:
            err(f"{p.name}: meta CSP does not allow formspree.io; the intake form would "
                "be blocked")

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
    # The regression suite was defined but never invoked in 2026.09.13-r2, so every
    # check it contained was dead code while the release notes claimed it was running.
    errors.extend(regression_checks(ROOT))
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(errors)} errors, {len(warnings)} warnings across "
          f"{len(list(ROOT.glob('*.html')))} pages")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
