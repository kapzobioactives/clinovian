# Release notes — 2026.09.13-r2

Supersedes all previous release notes. Earlier notes claimed remediation that the
shipped files did not contain; nothing in this file should be read as carried forward.

## Scope of this release

Remediation of findings F01–F21 from the comprehensive audit dated 13 September 2026.

### Completed and verifiable in these files

| ID | Change |
|---|---|
| F01 | DRG specimen rebuilt: KDIGO staging corrected to a 3.09x rise reaching the Stage 3 creatinine threshold (stated conditionally); blanket AKI=MCC assertion removed; N17.0/N17.9 distinction named; discharge-summary basis for ATN added as Exhibit F; conditional conclusion; payment arithmetic shown from a fictional contract schedule |
| F02 | AR specimen rebuilt inside its stated scope: complete 47-row fictional inventory published and reconciling; mutually exclusive categories; deadline priority as an independent flag; top five corrected and sorted; all merits and recovery conclusions removed |
| F03 | `#intake-status` moved outside `#intake-form`; success hides the field shell only and moves focus to a confirmation heading |
| F04 | Medicare Advantage enrollee reconsideration window corrected to 65 calendar days, scoped to that process, sourced and dated. Other appeal windows deliberately left unchanged |
| F05 | **All eight specimens rebuilt** to one standard: document control (version, review date, reviewer with accurate credential limits, applicable framework, conditional-conclusion declaration), a published fictional source packet with exhibit references, evidence-to-criterion mapping, a conditional conclusion, numbered open questions, and a source list. A ninth specimen, `sample-declined-case.html`, publishes an appropriately declined case as required by audit §4.9 |
| F07 | All 30 service CTAs rewritten to stable service IDs; `setting` and `specialty` carried separately; resolver falls back to legacy labels so old links still work |
| F08 | Dropdown visibility driven solely by `.nav-item.open`; `:hover`/`:focus-within` display rules removed; Escape dismisses without requiring pointer or focus to move; drawer scroll-lock and background `inert` added; `aria-invalid`/`aria-describedby` error binding and an error summary added |
| F11 | Business inquiry separated from case-fit intake; conditional groups are fieldsets that are disabled, not merely hidden, so stale values cannot serialise |
| F12 | Inquiry framing states plainly that this is an ordinary business form and not an approved PHI workflow; identifier scan extended to all enabled text controls; network-error fallback retains the no-identifier instruction |
| F21 | Privacy-conscious event instrumentation with an allow-listed payload; no free text, field values, clinical narrative or identifiers |
| F06 | Release notes and validation report rewritten to state what the gate checks and, at length, what it does not. Nine regression checks added to `scripts/validate_site.py`, testing the actual defects. Clinical review log covering all nine specimens |
| F09 | Six source-confirmed internal-commentary leaks removed: the numbered "24. Engagement formats" heading, cost-based packaging commentary, the reference to an absent salary example, editing-history copy, the LTACH self-reference, and the psychiatry marketing instruction |
| F10 | New `order-specification.html` governs every price and turnaround representation: standard unit, per-service conversion, pilot eligibility, revisions, the five-stage clock, urgent restrictions, recurring terms, decline handling. Linked from 53 footers |
| F13 | Apex confirmed canonical; eight-row redirect matrix documented; `RELEASE_ID` marker added and verified by the preview script |
| F18 | Sitemap `lastmod` reads `data/content-dates.json`; filesystem mtime removed; a missing date is a hard error. Assets versioned across 60 pages; OG image no longer `immutable` without a versioned filename |
| F16 | Homepage restructured as a **router**, not a narrower pitch. The deliverable, the $450 starting price, the 48–72 hour turnaround and the primary CTA now appear within the first 600 characters of `<main>`, where previously the price was not on the page at all. Added a four-route self-selection section (denial/appeal operations, hospital teams, federal IDR, AI vendors), each with its own price and turnaround, plus links out to the post-acute and specialty hubs. Added an evidence strip showing evidence → criterion → reasoning → handoff from a corrected specimen, alongside the declined case. `services.html` now separates published-price services from quoted ones and leads with a "where to start" block. Nav and drawer primary CTA changed to the fit assessment. **No page was removed and no URL retired** — width was preserved deliberately as a commercial decision |
| F20 | Navigation, mobile drawer, footer and trust strip generated from `shared/*.html` via `scripts/build_shared.py`, replacing hand-copied duplicates across 53 pages. This fixed real drift: `404.html` carried an older navigation and footer, and six pages carried divergent trust strips. Per-page nav state is derived from the filename and prefix rules, not stored per page. `data/site.json` is the single source for service labels, prices, turnarounds and unit conversions, checked against `service-catalog.json` and the intake form. Two further defects surfaced and were fixed: `concurrent-review.html` had no intake option and its CTA routed to a different service |
| F19 | `scripts/check_preview.py` supplied — read-only checks of the redirect matrix, status codes, security headers and deployed release identity |
| F15 | All eight articles carry a named reviewer with accurate credential limits, publication and last-substantive-review dates, a next-review date with an event trigger, structured data naming a person, and a **Sources and limits** section with primary links. Statistics bounded to their populations and denominators (OIG 95% qualified against the 18% appeal rate and its self-selection; LTCH 36% and IRF 43% kept separate; CMS-0057-F scoped with the FFE exclusion and the 2026/2027 split). Behavioural-health ranking, the AI comparative-review claim, the IDR statistics and the "never appears in a denial dashboard" absolute all **withdrawn** for want of a source. The two observation articles given genuinely different purposes — one a Medicare applicability guide separating benchmark, exception and FFS presumption, the other a commercial-policy analysis that does not rely on CMS authority. A **claim register** (`data/claim-register.json`) records every checkable claim with its source, population, owner, interval and next review, including withdrawn claims so they are not reinstated by accident. `editorial-policy.html` now states what is actually in place and what is not |

### Decisions taken, not defects fixed

| ID | Decision |
|---|---|
| F14 | **PDF regeneration deferred.** The eight stale PDF exports have been removed from the repository and their download links replaced with a withdrawal note, because they still contained the clinical content that F01 and F02 corrected. The HTML pages are the version of record. Re-typesetting is outstanding |

### Outstanding — not addressed in this release

F17 (privacy, security and commercial-terms expansion) and the analysis layer for F21.

F16 was implemented as a routing restructure rather than the audience narrowing the
audit recommended. The audit advised leading with a single buyer hypothesis (RCM denial
and appeal firms). That recommendation is explicitly not evidence-based — the audit
states it follows from the site's capabilities and onboarding burden, not from
demonstrated demand. Narrowing before any conversion data exists would optimise for an
audience that has not been validated, so the client decided to preserve audience width
and fix the delay instead: the homepage now answers what/how much/how to start in the
first screenful and lets visitors self-select. Revisit once paid-pilot data exists.

F09 is substantially complete — all six source-confirmed internal-commentary leaks are
removed — but the broader market-study commentary across the ten core service pages
remains.

## Acceptance status

Unverified at the time of writing and **not claimed**: form delivery to the destination
inbox, mobile and cross-browser behaviour, screen-reader conformance, contrast and
target-size measurement, Core Web Vitals, production response headers, host and redirect
behaviour, and the clinical review of the six specimens not listed in the clinical review
log in `VALIDATION_REPORT.md`.
