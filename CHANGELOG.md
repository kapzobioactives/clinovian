# August 29, 2026 (second pass) — Second-opinion audit reconciliation

An independent second audit reviewed the remediated build and the (not yet redeployed) live site. Its verified findings are implemented below; its www recommendation was checked and reversed on evidence. Live check: both `clinovian.com` and `www.clinovian.com` return 200, and the page served at www already carries the apex canonical — so the defect was a missing host redirect, not a canonical conflict. Rewriting ~60 files to www would have contradicted the site's own canonicals.

- **Two further internal drafting notes removed** (the class corrected on the specialty pages in the first pass, missed on these two):
  - `recurring-clinical-review-capacity.html` — "The name should be reviewed for procurement clarity… may be the safer label…" replaced with the buyer-facing MBBS credential and licensure-boundary line.
  - `drg-downgrade.html` — "The dollar-delta ranges currently printed for several DRG pairs **in the supplied site** are not sourced…" replaced with a buyer-facing exposure-varies note.
- **`ai-appeal-qa.html`** — "Clinovian's *proposed* independent review" → "Clinovian's independent clinical QA review" (the service is live, not proposed).
- **`faq.html` deadline language corrected** (visible text + FAQ JSON-LD): the "estimated appeal-deadline flag based on standard timelines" promise is replaced with a client-supplied deadline carried forward as a priority flag, with an explicit statement that Clinovian does not calculate or verify payer/jurisdictional deadlines. This aligns the FAQ with the deadline discipline already applied to `ar-audit.html` in July.
- **Specimen redaction bars are now readable by assistive technology.** The bars were `aria-hidden`, so a screen reader heard "ambulatory status of ; post-acute episode documents a skilled-nursing need of minutes/day." Each bar now carries visually-hidden "[redacted in specimen]" text; the bar itself stays decorative, preserving the PHI-discipline motif.
- **`vercel.json`** — added a host-level 301 from `www.clinovian.com` to `clinovian.com` as the first redirect rule, making the apex canonical in fact as well as in markup. No dashboard step required.
- **`service-catalog.json`** — retained as a published, machine-readable mirror of the service pages; `last_updated` bumped to 2026-08-29 and a self-describing `$comment` added. Prices and turnarounds were verified against all nine service pages (0 mismatches) and are now checked on every release.
- **Release gate hardened** so this class of defect cannot ship again: three new banned phrases, seven internal-voice regexes (advisory language addressed to the site owner rather than a buyer, with an allow-list for legitimate "verify with the payer / review by counsel" copy), catalog-versus-page price and turnaround consistency, and a check that a host-level redirect exists. Regression-tested: reintroducing the removed note fails the gate.

Re-verified after these changes: gate 0 errors / 0 warnings across 62 pages; axe-core clean on every changed page; all 62 pages free of horizontal overflow at 390 px; content still renders with JavaScript disabled; no broken internal references.

Not adopted from the second audit, with reasons: standardizing on the `www` host (contradicted by the live evidence above); deleting "turnarounds are commitments, not estimates" (a genuine differentiator already conditioned on complete agreed inputs — scope it rather than neuter it); stripping outbound links while keeping vendor names on comparison pages (worst of both — links now carry nofollow/new-tab, or the comparison moves wholesale to a dedicated page); and pruning to ~25 pages (no Search Console data exists yet to make that call, as that audit itself cautions).

# August 29, 2026 — Full remediation of the independent site audit (C1–C3, H1–H9, M1–M13, D-series)

Deployment restored to a single source of truth and the audit's findings implemented, except H5/R9 (founder photo/LinkedIn — owner materials required) and items assigned to counsel/owner (M14 CSS refactor scheduled, M15 legal expansion, M16 analytics provider choice).

- **C1/C2 — vercel.json rebuilt.** All 18 legacy SPA rewrites removed; every `_redirects` rule ported as proper 301s (clean URLs → .html, legacy paths, superseded files); CSP corrected to allow Formspree (`connect-src`/`form-action`) and Calendly frames, Google Docs/Calendar era directives removed, `script-src 'self'` (no unsafe-inline); cache rules for CSS/JS/OG/PDF added. `_headers` and `_redirects` deleted. **Post-deploy: submit a live test inquiry and spot-check clean URLs.**
- **H9 — internal docs excluded from deploy** via new `.vercelignore` (CHANGELOG, DEPLOYMENT, IDR_CLAIMS_REGISTER, RELEASE_NOTES, VALIDATION_REPORT, superseded QA reports, scripts/, package.json); robots.txt simplified; belt-and-braces redirects for the old .md URLs.
- **C3 — release integrity restored.** `scripts/validate_site.py` and `scripts/generate_sitemap.py` recreated (release gate passes); `editorial-policy.html` created; `trust-center.html` and `accessibility.html` rebuilt on the standard site shell (missing `/styles/inline-utilities.css` reference removed); all 8 specimen PDFs regenerated from final HTML and linked ("Download this specimen as a PDF") on each specimen page.
- **H1 — leaked audit notes removed** from oncology/cardiology/neurology/orthopedic pricing-context sections; internal-policy diction reframed.
- **H2 — flagship memo canonicalized.** One 12-section list everywhere (homepage hero card rebuilt; service-page section 3/9 labels aligned to the specimen; section 12 is "Prevention Note & Pattern Tags" and the specimen now carries a client-facing prevention note); appealability verdict scale standardized to strong/moderate/weak/not-recommended.
- **H3 — free step named once.** "Initial fit assessment" sitewide; hero badge no longer promises a "verdict"; undefined "Appealability screen" rows removed from both turnaround tables and the FAQ (visible + JSON-LD); homepage pill 01 retitled.
- **H4/M9/M10/M11 — structure.** Every table now sits in a focusable `table-wrap` scroll region (24 wrapped, 6 upgraded); specimen mobile horizontal overflow eliminated; `<main>` landmark added to all specimens; trust strip is an `aside` landmark; smooth-scroll disabled under reduced motion; decorative menu glyphs aria-hidden.
- **H6 — PHI filter precision.** Bare "email/phone/address" words no longer block submission; the filter now targets identifier patterns (dates, keyword+value, SSN/phone shapes, 9+ digit runs) and the error names the matched fragment. Unit-tested.
- **H7 — external links.** All non-Clinovian links open in a new tab with `noopener noreferrer` (plus `nofollow` on commercial/vendor links; CMS/OIG/Calendly stay followed) and an accessible "opens in a new tab" note.
- **H8 — content no longer JS-gated.** `no-js` class on every page; reveal animation applies only under `html.js`.
- **M1 — late-batch metadata.** Ten 190-char descriptions rewritten ≤155 with og:description synced; truncated hero paragraphs replaced with complete sentences.
- **M2/M6 — discovery.** sitemap.xml regenerated with real `lastmod` (59 URLs, now includes trust-center/accessibility/editorial-policy); sitemap.html expanded (post-acute settings, specialties, recurring capacity, trust pages); RSS alternate link on insights + all 8 articles; feed.xml rebuilt from page titles/dates; over-length insight-idr title shortened (78→54).
- **M3 — 404** now noindex, canonical removed, og:url aligned.
- **M4 — schema.** BreadcrumbList on 57+ pages; Service schema (with minPrice offers where published) on the nine catalog service pages.
- **M5 — internal links.** Homepage Concurrent Review row → its own page; four post-acute rows → SNF/IRF/LTACH/HH pages; insights listing aligned to article H1s; "find and recover" → "find and contest".
- **M7 — Federal IDR data refreshed** to CMS 2025 Q3–Q4 (1,145,039 determinations on 1,372,563 initiated disputes; ~85% initiating-party prevail; 62% ≤30 business days); claims register rows and review date updated.
- **M8/D3 — contrast.** New `--gold-text`/`--amber-text` tokens replace gold/amber for text (backgrounds/borders keep brand hues); footer tagline/legal-line/link opacities raised; low-opacity labels on dark panels bumped.
- **M12/M13 — brand assets.** One favicon (`/favicon.svg`) + apple-touch-icon linked on every page; SVG marks unified to `#183F2D`; single canonical Google Fonts URL sitewide; unused Outfit 300 dropped.
- **D1/D6/D8 — mobile & menus.** Compact single-row mobile header; footer links restored on mobile as a two-column grid; mega-menu/dropdown/drawer links in sentence case (uppercase reserved for eyebrows).
- **Copy nits** — AR-audit pricing wording aligned to the catalog ("Fixed fee after file scope"); empty trust-center/accessibility descriptions written; sample-ar-audit description trimmed to 147 chars.

Deliberately deferred: H5/R9 (owner materials), M14 inline-style/!important refactor (scheduled tech debt), M15 legal-page expansion (U.S. counsel), M16 analytics (owner to choose a cookieless provider; CSP will need its domain), D2 founder portrait, D4 per-page specialty exhibits, D5 CTA variation, D7 in-page mobile wayfinding beyond specimen fixes.

# July 17, 2026 — Cross-site consistency sweep (own-judgment pass)

Follow-up to the service-page build-out: reconciled every page that contradicted the rebuilt service pages or carried claims the portfolio report flagged, using judgment rather than treating the report as binding.

- `faq.html` — "AI Appeal Clinical QA: 24–48 hours per batch" changed to "24–48 hours per appeal, with batch scope and service levels confirmed at intake" in both visible text and JSON-LD (JSON-LD re-validated).
- `for-ai-vendors.html` — both batch promises disciplined, including the "10–50 appeals in 24–48 hours" claim the report specifically warned against (§28.9); batch scope now confirmed at intake.
- `insight-drg-downgrades.html` — unsourced per-pair dollar deltas ($4K–$40K overall; $4K–$8K through $15K–$30K+ per pair) removed; each pair now carries its clinical-validation focus instead; single exposure-varies qualifier added after the pair list. Article's conditional "recoverable revenue the provider is entitled to" retained (predicated on the downgrade being incorrect).
- `sample-ar-audit.html` — "Conservative estimate: $700K–$850K in contestable AR" reframed as client-supplied billed balances at issue ("not a recovery estimate"); "recoverable revenue" → "client-supplied balances"; deadline sentence now labeled client-supplied / to be verified with the payer; meta description "Recoverable AR" → "Category triage, client-supplied deadline flags."
- `for-hospitals.html` — unsourced "$250K–$400K+" physician-advisor cost replaced with the sourced posting range ($206,606–$413,212 before benefits and overhead); stale "Complex DRG and level-of-care cases may require 3–5 business days" corrected to the reconciled 5–7 bd (level-of-care) / 7–10 bd (DRG); impact-summary metric "estimated recoverable revenue at stake" → "client-supplied amounts at stake."
- `for-post-acute.html` — "Typical SNF denial at stake: $8,000–$25,000+" card replaced with per-diem × denied-days contract-arithmetic framing.
- `why-clinovian.html` — "$250K–$400K+" aligned to the sourced posting range; outcome one-liners "Recovers revenue your denial dashboard never shows you" → "Surfaces the paid-but-downgraded disputes…" and "Find the recoverable revenue…" → "Find the clinically contestable accounts…"; "the same review logic insurers apply under InterQual and MCG criteria" reframed as payer-side experience ("review discipline built applying InterQual and MCG criteria on the payer side") per §28.4.
- `insight-post-acute-denials.html` — "the federal data suggests you are likely sitting on recoverable revenue" softened to a non-extrapolating statement about uncontested appealable denials.
- `IDR_CLAIMS_REGISTER.md` — two new dated regulatory/statistical claims registered (H1-2025 determination volume; ~88% initiating-party prevail rate) with review triggers; last-reviewed date bumped to 2026-07-17.
- `drg-downgrade.html` — "the pairs the desk sees argued most" softened (implied internal volume data).
- `rcm-partners.html` — pre-existing stray `</div>` before `</main>` removed (page now passes tag-balance validation).

Deliberately left unchanged: `sample-drg-downgrade.html` case-value estimate ($12,000–$18,000 "depending on facility-specific DRG rate differentials") — a case-specific, caveated figure inside a fictional specimen, which models the recommended practice; `contact.html` disputed-value placeholder ("e.g. $12,000–$18,000") — a form hint for the client's own actual amount.

# July 17, 2026 — Service-page content build-out (portfolio report implementation)

Source: Clinovian Comprehensive Service Portfolio Report (16 July 2026). All new copy is drawn from that report and existing site language; published prices and turnarounds match `engagements.html` exactly. No new pricing, outcome, or credential claims introduced.

**Twelve service pages expanded from thin single-panel layouts to full pages:**

- `escalation-memo.html` — 12-section memo anatomy grid, Premier 2025 survey context (qualified as survey findings), included/not-included scope band, fit criteria, integrity line (analysis-not-advocacy), engagement structure ($450 standard / complex quoted / $1,000 evaluation).
- `observation-defense.html` — prospective-standard thesis, hindsight-vs-record compare, rule-selection section (Medicare FFS Two-Midnight / MA 2024 final rule obligations / commercial contract control), deliverable components, fit criteria, quoted-after-scope + 5–7 bd.
- `drg-downgrade.html` — clinical-validation vs. coding-authority responsibility band (no code/DRG assignment), priority DRG pairs retained **with unsourced dollar deltas removed** and replaced by the report's exposure-varies language, queue/crossover analysis, 7–10 bd.
- `post-acute-denials.html` — OIG June 2026 stat band (12% SNF denial rate, 18% appealed, 95% overturned; 36%/43% LTACH/IRF overturn on appeal) with population-level disclaimer, four setting-specific frameworks (SNF/IRF/LTACH/HH), plan-rule discipline note, memo contents, fit criteria.
- `p2p-brief.html` — preparation-not-representation boundary, AMA survey context (56%/16%, marked as physician-reported perceptions), 8-part brief anatomy, strong/uncertain/missing evidence grading, one-call-one-issue scope rules, $300 / 24–48 h.
- `pre-denial-dossier.html` — **"so the first answer is yes" removed** (hero, meta, body) per report §28.6; replaced with clinical-completeness framing. CMS-0057-F decision-clock section (72 h / 7 days / 2026 specific-reason, impacted-payers + drug-exclusion caveat), exception-layer positioning, deadline-fit warning, scope boundaries.
- `concurrent-review.html` — record cut-off discipline (analysis states its cut-off; 24–48 h runs from complete agreed record), surge/exception positioning, delivered components, boundaries.
- `ai-appeal-qa.html` — NIST GenAI-profile context, QA deliverable contents (claim-by-claim verification, correction table not rewrite), three-verdict disposition, independence rationale, required inputs, engagement structure ($250 single; batches scoped at intake; recurring via capacity plans).
- `ar-audit.html` — inventory template/validation gating (72 h starts after clean inventory), "No PHI ≠ no sensitive data" caution, **deadline flags labeled client-supplied/client-to-verify** per report §28.7, triage-not-appealability boundary band (no recovery forecast, no deadline validation), transparent-rubric commitment.
- `nsa-idr.html` — added Federal IDR scale section (1,082,247 H1-2025 determinations, ~88% initiating-party prevail rate, explicitly disclaimed as non-attributable population figures) and client-inputs section; existing content unchanged.
- `rcm-partners.html` — added partner-arrangement inclusions (suitability rules, templates, unit fees, **white-label credential transparency**, revision controls/audit trail, partner-data-only pattern summaries, contact boundary) and partner-requirements + recurring-capacity section. Fixed a pre-existing stray `</div>` before `</main>`.
- `specialties.html` — rebuilt as full per-specialty evidence-framework sections (oncology, cardiology, orthopedics, neurology, behavioral health, post-acute link) with competence-boundary/decline rules; **unsourced claim-value ranges removed** per report §28.3 and replaced with exposure-varies language.

**Sitewide corrections (report §28):**
- "so the first answer is yes" removed from `services.html`, `sample-work.html`, and `sample-pre-denial-dossier.html` (3 occurrences).
- DRG dollar-delta ranges removed from the `services.html` priority-pairs panel; exposure qualification added.
- Meta descriptions rewritten ≤160 chars where hero copy changed (`pre-denial-dossier`, `ar-audit`, `specialties`) and fixed the truncated `p2p-brief` description.

**Known residual items (not changed, flagged for owner decision):** dollar deltas remain in `insight-drg-downgrades.html` and `sample-drg-downgrade.html` (analysis/specimen context); FAQ still states "24–48 hours per batch" for AI QA (report §28.9 recommends scoping batch SLAs).

# July 16, 2026 — Comprehensive site audit and corrections

- **Pilot → Evaluation vocabulary migration completed.** All references to "pilot," "3-Case Denial Escalation Pilot," and "3-Dispute IDR Clinical QA Pilot" replaced sitewide with evaluation-era naming (3-Case Denial Evaluation, 3-Dossier Federal IDR Evaluation). Hero CTAs, nav, pricing cards, and contact form options all updated. The only surviving "pilot" reference was in `main.js` `isIdrService()`, which was fixed below.
- **Fixed `isIdrService()` in `main.js`** — the function still matched the retired "3-Dispute IDR Clinical QA Pilot" option, preventing IDR-specific intake fields from appearing for the current "3-Dossier Federal IDR Evaluation" product. Now correctly matches both IDR service options.
- **Corrected MS-DRG pairs** on `services.html`, `drg-downgrade.html`, and `insight-drg-downgrades.html`: replaced deleted FY2025 spinal-fusion DRGs 459/460 with current 447/448; corrected heart failure 291/293→291/292 and bowel 329/331→329/330 labels; added 871/872 (most common downgrade target) to the priority list; aligned sepsis delta figures to the insight article and specimen.
- **Deleted `vercel.json`** — legacy SPA configuration that contradicted `_headers`/`_redirects` and would break the contact form and clean URLs if deployed to Vercel.
- **Fixed duplicated clause** in `insight-two-midnight.html` (trailing repetition after inline link).
- **Fixed duplicated trust chip** on `404.html` (two "No PHI To Start" items) and regenerated 404 nav and footer to match current sitewide shell.
- **Reconciled turnaround claims** — replaced ambiguous "Complex DRG / level-of-care memo: 3–5 business days" with named-service turnarounds (Observation Defense 5–7 bd, DRG Challenge 7–10 bd, Post-Acute 5–7 bd) on `engagements.html`, `how-it-works.html`, `faq.html` (both visible text and JSON-LD).
- **Stubbed `clinovian_sample_appeal.html`** — replaced 45KB legacy document with noindex/canonical/meta-refresh redirect stub to `/sample-work.html`.
- **Corrected OIG report title** in `insight-post-acute-denials.html` to exact official title with report number (OEI-09-24-00331).
- **Fixed contact form:** aligned sidebar "NSA/IDR Dossier Request" label to "NSA/IDR Clinical Value Dossier"; added `aria-hidden="true"` to honeypot field.
- **Fixed British spellings** on live US-facing pages: "prioritises" → "prioritizes" (contact.html), "labelled" → "labeled" (sample-nsa-idr-dossier.html).
- **Reframed commercial-PPO/Two-Midnight authority** in `sample-observation-defense.html` — replaced direct CMS-authority claims with payer-invoked-standard framing; fixed "3-day hospitalization" → "42-hour hospitalization (one midnight)" to match the one-midnight scenario; added Medicare-vs-commercial scope notes to `insight-two-midnight.html` and `insight-observation-vs-inpatient.html`.
- **Superseded stale QA artifacts** — `structural_cleanup_quality_report.md` and `structural_quality_report.json` now marked as superseded (their assertions about zero inline styles, zero `!important`, and 8/8 shared footer no longer matched the shipped code).
- **Added missing `_redirects` entries** for nine newer pages.
- **Shortened 10 over-length meta descriptions** to ≤160 characters.
- **Added `og:url`** to the 9 late-batch pages that were missing it.
- **Unified Google Fonts payload** — all pages now load Spectral up to 600 and JetBrains Mono up to 600.
- **Added `datePublished`/`dateModified`** to Article JSON-LD on all 8 insight articles.
- **Added Privacy/Terms footer links** to all 8 specimen pages.
- **Added `prefers-reduced-motion` media query** to `style.css` for scroll-reveal and drawer transitions.
- **Defined `--forest-dark`** CSS variable in `:root`.
- **Fixed heading hierarchy** skip (h1→h3) in `engagements.html`.
- **Added `aria-hidden="true"`** to decorative redact bars on `index.html`.
- **Escaped `&` in Google Fonts URLs** sitewide (validator compliance).
- **Fleshed out** `concurrent-review.html` and `ar-audit.html` service-detail sections.
- **Aligned InterQual/MCG phrasing** on `why-clinovian.html` to the FAQ/about formulation.
- **Aligned pattern-report entitlement** language on `how-it-works.html` and `rcm-partners.html` to scope reporting to recurring-capacity clients.
- **DRG specimen precision:** changed "downgraded MCC to CC" to "MCC designation removed" in `sample-drg-downgrade.html`; updated FIM reference to Section GG in `sample-escalation-memo.html`.

# July 15, 2026 — IDR outreach alignment

- Standardized NSA/IDR dossier turnaround to 3–5 business days after receipt of the complete agreed record; expedited review by prior agreement.
- Added a separate 3-Dispute IDR Clinical QA Pilot without applying the hospital-denial pilot price.
- Renamed the hospital entry offer to 3-Case Denial Escalation Pilot.
- Updated navigation to “For RCM, IDR & AI Partners” and changed the universal menu CTA to “Discuss a Pilot.”
- Added IDR exception-review/overflow positioning and a selective-fit statement to the IDR landing page.
- Added conditional IDR intake fields and client-deadline responsibility language to the contact form.
- Replaced the unlimited free-screen promise sitewide with one complimentary initial fit assessment for prospective clients; ongoing triage is included in paid engagements.
- Tightened QPA and client-offer wording to preserve procedural and legal scope boundaries.

## 2026-07-15 — Federal IDR precision and commercial-boundary update

- Rebuilt the NSA/IDR service page around physician-authored clinical evidence, not filing administration.
- Corrected the framework to five enumerated additional circumstances.
- Removed market-rate benchmarking as a statutory factor and removed stale process-fee references from the specimen.
- Separated QPA, initial payment, and party offers in the specimen.
- Replaced the old batching example with a single-item fictional dispute and retired the legacy long-form dossier.
- Added explicit client/Clinovian responsibility boundaries, suitability filters, fixed dossier-scope pricing language, and an IDR Clinical QA Desk for RCM partners.
- Rewrote the IDR insight article for the 2026 final rule and added an internal regulatory claims register.

# Clinovian site patch — hero and CTA refinement

Implemented requested changes:

1. Changed hero title to: “When the denial is clinical, the appeal should be physician-authored.”
2. Removed duplicate hero CTA; retained a single common “View Sample Work” action.
3. Fixed CTA clickability by preventing the decorative CTA overlay from intercepting clicks.
4. Changed hero and bottom audit CTAs to route directly to the No-PHI AR Audit intake selection.
5. Reworked “Pricing anchors” into clearer “Engagement options” language.
6. Rewrote the No-PHI AR Audit pricing card from “fixed-fee or credited” to understandable buyer-facing language.
7. Replaced internal-sounding compliance heading with: “Security and PHI handling, laid out as a buyer-review checklist.”
8. Added an RCM Partnership Inquiry intake card and made “Discuss RCM Partnership” route directly to it.
9. Added mailto-based RCM partner inquiry flow with a no-PHI warning.
10. Fixed Vercel rewrites so clean URLs route to the bundled single-file `index.html` package.
11. Added Netlify `_redirects` and `robots.txt` back into the deploy package.
