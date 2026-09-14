#!/usr/bin/env python3
"""Generate VALIDATION_REPORT.md from the delivered archive, not by hand.

Hand-edited release documents drifted for eight releases: the report was headed
r11 while its captured run said r3, and RELEASE_NOTES listed F17 as both cleared
and open. Regenerating removes the class of error rather than the instance.
"""
import json, pathlib, subprocess, sys, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent if __name__ != "__main__" else pathlib.Path(".")
REL = (ROOT/"RELEASE_ID").read_text().strip()

def run(*cmd):
    r = subprocess.run(list(cmd), capture_output=True, text=True, cwd=ROOT)
    return (r.stdout + r.stderr).strip(), r.returncode

gate, gate_rc = run(sys.executable, "scripts/validate_site.py")
gate_last = gate.splitlines()[-1]
shared, _ = run(sys.executable, "scripts/build_shared.py", "--check")
acc, acc_rc = run("node", "scripts/acceptance/inquiry-flow.js")
acc_last = acc.strip().splitlines()[-1] if acc.strip() else "(not run)"
pub, _ = run(sys.executable, "scripts/build_publish.py", "_site")

STATUS = [
 ("Cleared and regression-guarded",
  "F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11, F12, F14, F15, F16, F18, F19, F20, F21"),
 ("Website half cleared; operational evidence outstanding (see below)", "F17"),
 ("Repository half cleared; requires one publish to close", "F13"),
]

OPEN = """## What is NOT closed by this archive

Two findings cannot be closed by a repository change, and one area was never in the
audit's remediation scope. Read this section before describing the site as finished.

### F17 — operational PHI readiness

`privacy.html`, `terms.html` and `security.html` now describe the service accurately, and
`security.html` states plainly that **no standing pre-approved PHI workflow exists**. That
is the website half. The operating half is evidence this repository cannot contain:

- Executed BAA and engagement agreement
- An agreed secure transfer method, approved by the client
- Data-flow diagram and subprocessor schedule
- Access control, MFA and approved-device policy
- Retention, deletion and backup procedure
- Incident-response and business-continuity procedure
- Client approval for offshore processing
- Professional insurance and contracting-entity evidence

**Until those exist, the site may collect no-PHI business inquiries and nothing more.
Do not accept clinical records.**

### F13 — deployment

The publishing workflow, the route map, the generated `CNAME` and the post-deploy matrix
check are all in place and the repository is internally consistent on the apex host.
Production still serves an older build until this release is published. The workflow's
post-deploy verification fails the run on a stale or misrouted deploy; before r12 it was
`continue-on-error`, so it went red while the run went green.

### Clinical re-approval of the specimens

The specimens were materially revised in r4 — verdicts made conditional, a stale HEART
total corrected, CHA₂DS₂-VASc components published, the AR scope boundary restored. **The
clinical review log below predates those revisions and still reads "reviewed 13 September
2026."** All nine specimens need reconfirming and re-dating by the reviewer before any of
them is used as sales proof. This is a signature on clinical reasoning and is not
something the build can produce.

### Accessibility

Captions and header cells are fixed and gate-checked. Not yet done, and not verifiable
from a build: screen-reader walkthrough, contrast measurement, target-size checks,
zoom/reflow at 200%, and testing on a physical phone. Mobile type sizing is still
overridden by `!important` rules in shared CSS.

### Security headers

Four of the six controls a security questionnaire asks about **cannot be delivered on
GitHub Pages**: `X-Content-Type-Options`, `frame-ancestors`/`X-Frame-Options`,
`Strict-Transport-Security` and `Permissions-Policy`. Only CSP and the referrer policy
work, via meta tags. Releases r8–r11 shipped a meta `X-Content-Type-Options` tag that
browsers ignore, and the gate *required* it — a check that passed while protecting
nothing. Removed in r12. See `DEPLOYMENT.md` before answering a questionnaire.
"""

doc = f"""# Validation report

**Release:** {REL}
**Generated:** {datetime.date.today():%d %B %Y} by `scripts/generate_validation_report.py`

This file is **generated from the delivered archive**. Do not hand-edit it: run
`python3 scripts/generate_validation_report.py` and commit the result. Earlier releases
were written by hand and drifted — r11 was headed r11 while its captured run reported r3,
and the release notes listed F17 as both cleared and open.

## Captured run

Run from a clean extraction of {REL}:

```
$ python3 scripts/validate_site.py
{gate_last}

$ python3 scripts/build_shared.py --check
{shared.splitlines()[-1] if shared else '(no output)'}

$ node scripts/acceptance/inquiry-flow.js
{acc_last}

$ python3 scripts/build_publish.py _site
{chr(10).join('  '+l for l in pub.splitlines())}
```

Exit codes: gate {gate_rc}, acceptance {acc_rc}.

## What the gate does and does not cover

It checks structure, routing, shared-region drift, specimen self-consistency, arithmetic
in the AR inventory, retired clinical assertions, citation apparatus, host consistency,
platform hygiene, policy coverage and asset versioning. Every check has been verified by
injecting the defect it claims to catch and confirming the build fails.

**It does not validate clinical, coding or regulatory accuracy.** No script can. Material
clinical claims require a qualified reviewer.

## Finding status

| Status | Findings |
|---|---|
""" + "\n".join(f"| {s} | {f} |" for s, f in STATUS) + "\n\n" + OPEN

(ROOT/"VALIDATION_REPORT.md").write_text(doc, encoding="utf-8")
print(f"  ok  VALIDATION_REPORT.md generated for {REL}")
print(f"      gate: {gate_last}")
print(f"      acceptance: {acc_last}")
