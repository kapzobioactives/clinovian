# Clinovian static validation report

**Validation date:** 16 July 2026  
**Artifact:** Remediated production repository  
**Result:** Static release gate passed with zero warnings and zero errors before packaging.

## Validated inventory

- 50 root HTML pages, including the custom 404 page
- 8 insight articles
- 8 specimen HTML documents
- 8 downloadable specimen PDFs
- Global CSS and JavaScript
- Vercel routes, redirects, headers, CSP and cache controls
- Canonical service catalog, FAQ synchronization, sitemap, RSS and robots files
- Internal release, deployment, regulatory-claims and validation documentation

## Automated checks

The release gate checks:

- HTML5 structure, language, viewport, one H1, heading hierarchy and landmarks
- title/description length, canonical, Open Graph, Twitter metadata, icons and RSS link
- valid JSON-LD and Article/FAQ/service schema requirements
- duplicate IDs, empty controls, valid list/table structure, captions and header scopes
- local links, assets, fragments, downloads and PDF existence/page count/text extraction
- explicit button types, form labels, field-error wiring, status regions and no-PHI controls
- article authorship, dates, review dates, primary-source sections and correction-policy links
- specimen document controls, assumptions, sources, limitations, navigation and PDF pairing
- exact service names, prices and turnaround promises across catalog, pages, FAQ and form
- prohibited legacy names, unsupported claims, stale pricing and known audit regressions
- Vercel clean/legacy routes, CSP allowances, headers and cache policy
- sitemap/HTML sitemap/RSS/robots consistency
- CSS syntax, absence of inline styles and `!important`, and JavaScript syntax

## Passed commands

```text
python3 scripts/validate_site.py
node --check main.js
```

The packaged ZIP is separately extracted and revalidated before delivery. A local HTTP smoke test checks direct static assets and pages for successful responses and nonempty payloads.

## Deliberate limitations

This report does not claim:

- live Vercel route/header verification;
- successful live Formspree or Calendly transaction;
- penetration testing or HIPAA/SOC 2/HITRUST certification;
- full WCAG conformance or assistive-technology certification;
- independent verification of credentials, insurance, legal entity documents or client references;
- legal advice, a credentialed U.S. coding audit or a payer/coverage determination;
- that external source URLs or regulatory rules will remain unchanged after the review date.

Those items are listed as production/diligence checks in `DEPLOYMENT.md` and the external remediation report.
