# Release notes — 2026.09.14-r12

**Deployment platform:** GitHub Pages · **Canonical host:** `https://clinovian.com`

Generated status lives in `VALIDATION_REPORT.md`, which is produced by
`scripts/generate_validation_report.py` from the delivered archive. **This file describes
what changed and why. It does not carry its own status table** — r11 had one that listed
F17 as both "Cleared in r10" and "Open" at the same time, because the table was maintained
by hand across eight releases. One source, generated, is the fix.

## Read this before publishing

1. **The specimens need clinical re-approval.** They were materially revised in r4; the
   review log still reads 13 September 2026. Re-confirm and re-date all nine.
2. **Do not accept clinical records.** F17's operational evidence — BAA, secure transfer,
   access controls, retention, incident response, offshore approval, insurance — does not
   exist yet. No-PHI business inquiries only.
3. **Four security headers are unavailable on this platform.** See `DEPLOYMENT.md` before
   answering a security questionnaire.
4. **Production still serves an older build** until this release is published.

## r12 — corrections found by independent review

- **`X-Content-Type-Options` as a meta tag is a no-op.** `http-equiv` supports a closed
  list of pragma directives and this is not one of them, so browsers ignore it. r8 shipped
  it on all 64 pages, the gate *required* it, and `DEPLOYMENT.md` listed it as delivered:
  a check that passed while protecting nothing, which is the exact failure this project
  has been correcting elsewhere. Tag removed, enforcement replaced with a guard against
  reintroduction, documentation corrected to state it is unavailable.
- **`DEPLOYMENT.md` contradicted itself on HSTS** — "not settable" in the platform table,
  "configured without preload" in a leftover Vercel-era section. The stale section is gone.
- **Release documents drifted.** `VALIDATION_REPORT.md` was headed r11 while its captured
  run said r3; `DEPLOYMENT.md` claimed verification from r4. Both are now generated or
  regenerated against the delivered archive.
- **jsdom was unpinned.** CI ran `npm install --no-save jsdom`, taking whatever `latest`
  was that day. Pinned to 30.0.1 in `devDependencies`; CI uses `npm ci`.
- **The post-deploy check could not fail the run.** `continue-on-error: true` meant a
  stale or misrouted production deploy went red in the step and green in the workflow. It
  now retries for five minutes against DNS propagation, then fails.
- **26 tables had no caption and 8 had no header cells at all.** Captions written per
  table rather than boilerplate; the eight label-value snapshot tables now use row headers.
- **"A rational first purchase…"** — market-study voice on `escalation-memo.html`,
  replaced with a plain statement of what clients usually do.

## How this archive is built and verified

```bash
python3 scripts/generate_sitemap.py
python3 scripts/build_shared.py --check
python3 scripts/validate_site.py
node --check main.js
npm ci && node scripts/acceptance/inquiry-flow.js
python3 scripts/build_publish.py _site
python3 scripts/generate_validation_report.py
```

CI runs all of it on every push to `main` and **refuses to publish** if an internal
document reaches the output or `CNAME` disagrees with the route map. `build_publish.py`
allow-lists what ships: publishing the repository root would expose this file,
`VALIDATION_REPORT.md`, `DEPLOYMENT.md`, `ANALYTICS.md` and `scripts/` at public URLs.

## Earlier releases

`CHANGELOG.md` carries the full history: PDF withdrawal (r3), specimen corrections (r4),
gate adversarial testing (r5), browser acceptance (r6), canonical host (r7), the GitHub
Pages platform correction (r8), market copy and citations (r9), homepage and policies
(r10), drift checking and measurement (r11).
