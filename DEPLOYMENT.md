# Clinovian deployment and release checklist

**Deployment platform:** GitHub Pages
**Public site:** `https://clinovian.com`
**PHI rule:** The public site, ordinary email, Formspree and Calendly are de-identified business-intake channels only.

## Platform constraints — read once

GitHub Pages serves static files from a published branch, verbatim. It supports
**no server-side redirects** and **no custom response headers**. Three things follow,
and all three were wrong in this repository until 2026.09.14-r8.

**1. Nothing is excluded by default.** Publishing the repository root would serve
`VALIDATION_REPORT.md`, `RELEASE_NOTES.md`, `CHANGELOG.md`, `DEPLOYMENT.md`,
`IDR_CLAIMS_REGISTER.md` and all of `scripts/` at public URLs — including this file
and the open-defects list. `.vercelignore` created a false sense of safety here: it
excluded those files from a *Vercel* deploy, and this site does not deploy to Vercel.
`scripts/build_publish.py` now assembles an allow-listed publish set instead, and CI
fails if an internal document reaches it.

**2. Redirects must be files.** The 66 routes in `data/routes.json` are materialised
as static stubs — meta refresh, canonical pointing at the destination, `noindex`, and
a visible link for anyone without JavaScript. Extensionless routes become directory
indexes (`/services/index.html`), which is how GitHub Pages serves `/services/`.

**3. Security headers cannot be sent, and most cannot be replaced.** Two of the policies
`vercel.json` declared survive as meta tags. The rest are genuinely absent.

`http-equiv` accepts a **closed list** of pragma directives — `content-type`,
`default-style`, `refresh`, `x-ua-compatible`, `content-security-policy`. Anything else in
an `http-equiv` is ignored by browsers. Releases r8 to r11 shipped
`<meta http-equiv="X-Content-Type-Options" content="nosniff">` on all 64 pages and the
release gate *required* it: a check that passed while protecting nothing. Removed in r12.

| Control | Status on GitHub Pages |
|---|---|
| `Content-Security-Policy` | **Works** via `<meta http-equiv>`, minus `frame-ancestors` |
| Referrer policy | **Works** via `<meta name="referrer">` |
| **`X-Content-Type-Options: nosniff`** | **Not available.** Header-only; no meta equivalent exists |
| **`frame-ancestors` / `X-Frame-Options`** | **Not available.** Clickjacking protection cannot be set |
| **`Strict-Transport-Security`** | **Not settable by this repository.** Enable "Enforce HTTPS" in repo settings, then verify with `curl -I` what GitHub actually sends. Do not assert HSTS until you have seen the header |
| **`Permissions-Policy`** | **Not available** |

Four of the six controls a security questionnaire asks about cannot be delivered here. That
is a property of the hosting choice, not an oversight. **Do not claim any of them on
`security.html` or in a questionnaire** — a buyer's reviewer runs `curl -I` and finds out.
If a client requires these headers contractually, the site has to move to a host that can
send them; that is a hosting decision, not a code change.

`vercel.json` and `.vercelignore` were deleted in 2026.09.14-r8. The gate fails if they,
or `netlify.toml`, `_headers` or `_redirects`, reappear: each configures a platform this
site does not run on, and their rules are silently inert.

## 0. Procedure verification record

Every command in this document was executed from a clean extraction of the
**2026.09.14-r12** archive on 14 September 2026 and completed as documented:

| Command | Result |
|---|---|
| `python3 scripts/generate_sitemap.py` | `sitemap.xml written with 61 URLs`, exit 0 |
| `python3 scripts/validate_site.py` | `0 errors, 0 warnings across 64 pages`, exit 0 |
| `node --check main.js` | exit 0 |
| `python3 scripts/build_shared.py --check` | `shared regions up to date across 64 pages`, exit 0 |
| `python3 scripts/check_preview.py <host>` | verified against a local server: passes on a matching build, fails with a named mismatch on a stale one |
| `npm ci && node scripts/acceptance/inquiry-flow.js` | **39 passed, 0 failed** against the r12 build |
| `python3 scripts/check_preview.py <host> --matrix` | loop detection and split-signal detection both verified against local servers; **not yet run against production, which is still the older build** |

The regression suite was audited by injecting, one at a time, the specific defect each
check claims to catch and confirming the build fails: **29 of 29 caught.** Two checks
were found not to fire and were repaired before this record was written — `F03` passed
silently when `#intake-status` was deleted rather than merely moved, and `F11` accepted
fieldset-level disabling without control-level disabling.

Re-run this verification whenever a script changes. A check nobody has tried to defeat
is not evidence.

## 1. Pre-release repository checks

Run from the repository root:

```bash
python3 scripts/generate_sitemap.py
python3 scripts/build_shared.py --check
python3 scripts/validate_site.py
node --check main.js
python3 scripts/build_publish.py _site
```

`build_publish.py` is the step that makes the site safe to publish. Never publish the
repository root.

The validator must finish with zero warnings and zero errors. It checks the canonical
service catalog, metadata, schema, internal links and fragments, forms, accessibility
structure, specimens, routes, CSP, sitemaps, RSS, robots directives, prohibited legacy
claims and internal documentation. It then runs the regression suite — service CTA
routing, confirmation-region nesting and announcement, conditional-field disabling,
menu dismissal, AR inventory arithmetic, retired clinical assertions, specimen
document control, specimen self-consistency, PDF withdrawal, shared-region drift,
article citation apparatus and content dates.

Two cautions. First, `regression_checks()` was defined but never called from `main()`
until 2026.09.14-r4, so the entire suite was dead code while earlier release notes
claimed it was running — if you refactor `main()`, keep the call. Second, **the gate
does not validate clinical, coding or regulatory accuracy.** No script can. Material
clinical claims require a qualified reviewer, recorded in the clinical review log in
`VALIDATION_REPORT.md`.

## 1b. Inquiry-flow acceptance tests

The static gate cannot execute the form. `scripts/acceptance/inquiry-flow.js` loads the
real `contact.html` into a DOM, runs the real `main.js`, and drives the inquiry flow.
Only `fetch()` is mocked, so no request leaves the machine and no inbox is touched.

```bash
npm ci                      # jsdom is pinned in package.json
node scripts/acceptance/inquiry-flow.js
```

All 39 assertions must pass. It covers the success confirmation (visible, announced,
focused, fields hidden rather than the whole form), validation failure, server rejection,
network failure, retry, duplicate submission, service preselection for every CTA on the
site, menu open/Escape/ARIA agreement, conditional-field disabling and FormData
serialisation, and the no-JavaScript fallbacks.

This is what "browser acceptance" means for F03, F07, F08 and F11. Re-run it whenever
`main.js`, `contact.html` or `shared/nav.html` changes.

## 1c. Canonical host (F13)

Verified state of production on 14 September 2026:

| | Observed |
|---|---|
| `https://www.clinovian.com/` | serves an older build, HTTP 200 |
| Canonical tag on those pages | `https://clinovian.com/` — the apex |
| Internal links on those pages | absolute `https://www.clinovian.com/...` |
| This repository | apex everywhere: 63 canonicals, 62 `og:url`, 61 sitemap entries, feed, JSON-LD |

**Live split host signal.** Every production page is served on `www` while its own
canonical names the apex, and every link on it points back to `www`. The page tells a
search engine the apex is authoritative and then links exclusively to the host it just
disowned.

**On GitHub Pages the host is set by the `CNAME` file, not by a redirect rule.**
`scripts/build_publish.py` writes `CNAME` from `data/routes.json` → `clinovian.com`.
Once that is published and DNS is correct, GitHub redirects `www` → apex automatically.
There is no loop risk here, because there is no second redirect rule to conflict with —
that hazard existed only under the Vercel configuration that has now been removed.

### Steps

1. **DNS.** Apex `clinovian.com` → GitHub Pages A/AAAA records;
   `www.clinovian.com` → `CNAME` to `<user>.github.io`. Both must exist, or the
   `www` → apex redirect has nothing to resolve.
2. **Repo → Settings → Pages.** Source: GitHub Actions (this repo publishes via
   `.github/workflows/deploy.yml`). Custom domain: `clinovian.com`. Enable
   **Enforce HTTPS**.
3. Push to `main`. CI runs the gate, the acceptance suite, builds the publish set,
   refuses to publish if an internal document is present, and deploys.
4. Verify:

   ```bash
   python3 scripts/check_preview.py https://clinovian.com --matrix
   ```

   This walks all four entry points — `http`/`https` × apex/`www` — one hop at a time,
   requires each to settle on `https://clinovian.com` with a 200, reports a redirect
   loop explicitly, compares the deployed `RELEASE_ID` against this working copy so a
   stale build is named rather than passing silently, and confirms the meta security
   policy survived to the served HTML.

If you would rather keep `www` as the public host, change `canonical_host` and
`canonical_origin` in `data/routes.json` — the gate will then name every canonical,
`og:url`, sitemap entry, feed link and JSON-LD URL that has to move with it.

## 2. Preview-deployment checks

GitHub Pages has no preview environment. Verify locally against the built publish set —
this is what CI will deploy, byte for byte:

```bash
python3 scripts/build_publish.py _site
cd _site && python3 -m http.server 8110
```

Then, in another shell:

```bash
python3 scripts/check_preview.py http://localhost:8110
```

`scripts/check_preview.py` is read-only (GET/HEAD only) and exits non-zero on failure.
Run it against the preview URL before promoting, and again against production
immediately afterwards.

It compares the **content** of the deployed `/RELEASE_ID` against the `RELEASE_ID` in
this working copy, not merely its status code. Until 2026.09.14-r4 it checked only for
a 200, so a host serving an older build passed — which is the condition F13 describes
in production today. A mismatch now fails the check and names both identifiers.

Confirm all of the following manually:

- `/`, every clean route, every `.html` route and every legacy redirect resolve to the intended page—not the homepage by mistake.
- The returned page title, H1, canonical URL and Open Graph URL match the requested page.
- `404.html` is returned for a nonexistent route and carries `noindex`.
- CSS, JavaScript, icons, RSS and sitemap return successfully with the expected content type.
- The meta security policy is present in the served HTML. Response **headers** cannot be
  set on this platform; `check_preview.py` reports them as informational, never as a pass.

## 3. Contact and scheduling tests

Use de-identified test data only.

- Submit the Formspree form through the normal JavaScript path and confirm the success message.
- Test required fields, invalid email, PHI-warning controls, server rejection, rate limit, network failure and resubmission.
- Disable JavaScript and confirm the native Formspree fallback is not blocked by the deployed Content Security Policy.
- Confirm the service query string preselects the correct service and reveals the correct denial or Federal IDR field set.
- Confirm the Calendly link opens in a new tab and includes the accessible “opens in a new tab” warning.
- Confirm no PHI is included in test messages, analytics or scheduling notes.

## 4. Responsive and accessibility checks

Test at minimum 320, 360, 390, 430, 768, 1024 and 1440 CSS pixels.

- Verify no horizontal page overflow; tables should scroll inside their labeled regions.
- Navigate every menu, dropdown, drawer, accordion and form control by keyboard.
- Verify visible focus, focus trapping, Escape behavior, return of focus and skip navigation.
- Test 200% and 400% zoom/reflow.
- Test reduced-motion preference.
- Test representative screen-reader workflows for navigation, headings, tables and form errors.
- Test on current Chrome, Edge, Firefox and Safari, plus representative Android and iOS devices.

The repository’s static checks reduce risk but do not certify WCAG conformance. Record any production issue in the correction log.

## 5. Content and diligence checks before launch

- Reconfirm every time-sensitive CMS, Federal Register, OIG, coding and policy source on the production date.
- Rebuild the sitemap/feed if any page date, title or URL changes.
- Verify the public service catalog against the signed quote/order-form templates.
- Confirm that the current identity, tax, qualification, insurance, security and subprocessor evidence supplied during diligence matches the public Trust Center. Do not publish an unverified credential, certificate, insurance claim, testimonial or client logo.
- Obtain appropriate U.S. counsel/coding/security review before relying on the public terms or content for a specific legal, coding or compliance conclusion.

## 6. PHI/security gate for client work

Do not accept PHI merely because a BAA is signed. Before any PHI transfer, document and approve:

- contracting parties and BAA chain;
- authorized users and least-privilege access;
- approved transfer/storage systems and regions;
- subprocessors and data flows;
- encryption, MFA, endpoint and incident controls;
- retention, deletion, backups and offboarding;
- minimum-necessary record scope;
- AI prohibition or specifically approved AI controls;
- incident contacts and client notification procedure.

## 7. Production promotion and rollback

- Promote the tested preview commit without rebuilding from a different working tree.
- Record the Git commit, the Actions run URL, release date and SHA-256 of the release ZIP.
- Re-run the preview checker against production.
- Submit one de-identified production inquiry and verify receipt.
- Rollback is `git revert` on `main`, which re-runs the workflow and republishes. There is
  no instant-promote equivalent on GitHub Pages, so a bad deploy is live until CI finishes.
- Roll back if routing, form submission, CSP, specimen rendering or material content is incorrect; do not patch production manually without reproducing the fix in the repository.

## Canonical host and redirect matrix

**Canonical host: `https://clinovian.com` (apex).** Every canonical tag, every
`sitemap.xml` URL and the generated `CNAME` point at the apex. A
redirect configured at the registrar or DNS provider that sends apex to `www` will
contradict the application-level rule and can produce conflicting redirects.

Before any release is promoted, verify all eight rows. Record the observed result —
not the intended one.

| Request | Expected final status | Expected final URL |
|---|---|---|
| `http://clinovian.com/` | 301 then 200 | `https://clinovian.com/` |
| `https://clinovian.com/` | 200 | `https://clinovian.com/` |
| `http://www.clinovian.com/` | 301 then 200 | `https://clinovian.com/` |
| `https://www.clinovian.com/` | 301 then 200 | `https://clinovian.com/` |
| `https://clinovian.com/services` | 301 | `https://clinovian.com/services.html` |
| `https://clinovian.com/clinovian_sample_appeal.html` | 301 | `https://clinovian.com/sample-work.html` |
| `https://clinovian.com/sitemap.xml` | 200 | served, parses |
| `https://clinovian.com/no-such-path.html` | 404 | custom 404 page, `noindex` |

Check the **final** status, the **final** destination, the `<link rel="canonical">`
on the landing page, and the response headers. A 200 on the apex is not sufficient
evidence on its own if a registrar-level rule is redirecting in the other direction.

## Release identity

Every deployment is tied to a release identifier held in the `RELEASE_ID` file at the
repository root, and to the source revision it was built from. Record both in the
deployment log. `scripts/check_preview.py` compares the local `RELEASE_ID` against the
deployed one, so a stale deployment is detected rather than assumed.

Current release: see `RELEASE_ID`. Do not promote a build whose `RELEASE_ID` differs
from the working copy that was reviewed.

## Shared page furniture

Navigation, the mobile drawer, the footer and the trust strip are generated, not
hand-copied. The source is `shared/*.html` plus `data/site.json`.

    python3 scripts/build_shared.py          # propagate into every page
    python3 scripts/build_shared.py --check  # exit 1 on drift (run in CI)

Never hand-edit anything between the `<!-- shared:x -->` markers — the next build
overwrites it. Edit the partial instead. Per-page navigation state is *derived* from
the page's own filename and the prefix rules in `data/site.json`, so a new article or
service page picks up the correct highlighting with no edit anywhere.

`data/site.json` is also the single source for service labels, prices, turnarounds and
unit conversions. `--check` fails if those diverge from `service-catalog.json` or if a
service has no matching option in the intake form. The release gate runs this check, so
a price changed on one page and not the others fails the build rather than shipping.
