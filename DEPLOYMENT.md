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
