# Clinovian deployment and release checklist

**Deployment platform:** Vercel only  
**Public site:** `https://clinovian.com`  
**PHI rule:** The public site, ordinary email, Formspree and Calendly are de-identified business-intake channels only.

`vercel.json` is the sole deployment source of truth. Do not add Netlify `_redirects` or `_headers` files; doing so recreates the configuration drift corrected in this release. Internal documents and `scripts/` are excluded from every deploy via `.vercelignore` — keep new internal files listed there.

## 1. Pre-release repository checks

Run from the repository root:

```bash
python3 scripts/generate_sitemap.py
python3 scripts/validate_site.py
node --check main.js
```

The validator must finish with zero warnings and zero errors. It checks the canonical service catalog, metadata, schema, internal links and fragments, forms, accessibility structure, specimens, PDFs, routes, CSP, sitemaps, RSS, robots directives, prohibited legacy claims and internal documentation.

## 2. Preview-deployment checks

Deploy an immutable Vercel preview before promoting to production. When network access is available, run:

```bash
python3 scripts/check_preview.py https://<preview-host>

The script is at `scripts/check_preview.py`. It is read-only (GET/HEAD only) and
exits non-zero on failure. Run it against the preview URL before promoting, and
again against production immediately after.
```

Confirm all of the following manually:

- `/`, every clean route, every `.html` route and every legacy redirect resolve to the intended page—not the homepage by mistake.
- The returned page title, H1, canonical URL and Open Graph URL match the requested page.
- `404.html` is returned for a nonexistent route and carries `noindex`.
- CSS, JavaScript, icons, RSS, sitemap and all eight specimen PDFs return successfully with the expected content type.
- Security headers in the preview match `vercel.json`; do not rely on local static-server behavior for header verification.

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
- Test representative screen-reader workflows for navigation, headings, tables, form errors and PDF/download links.
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
- Record the Git commit, Vercel deployment URL, release date and SHA-256 of the release ZIP.
- Re-run the preview checker against production.
- Submit one de-identified production inquiry and verify receipt.
- Keep the immediately preceding known-good Vercel deployment available for instant rollback.
- Roll back if routing, form submission, CSP, specimen downloads or material content is incorrect; do not patch production manually without reproducing the fix in the repository.

## 8. HSTS note

HSTS is configured without `preload`. Do not add the preload token or submit the domain to the preload list until every required subdomain is permanently HTTPS-capable and the owner accepts the difficult-to-reverse domain-wide consequence.

## Canonical host and redirect matrix

**Canonical host: `https://clinovian.com` (apex).** Every canonical tag, every
`sitemap.xml` URL and the `www` redirect in `vercel.json` point at the apex. A
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
