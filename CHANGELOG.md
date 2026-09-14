# September 14, 2026 (r12) — Corrections from independent review

An independent review of r11 found six real defects. Five were documentation or tooling;
one was a security control I got wrong and then built enforcement around.

**`X-Content-Type-Options` does not work as a meta tag.** `http-equiv` accepts a closed
list of pragma directives — `content-type`, `default-style`, `refresh`, `x-ua-compatible`,
`content-security-policy` — and this is not among them, so browsers ignore it entirely.
r8 shipped `<meta http-equiv="X-Content-Type-Options" content="nosniff">` on all 64 pages,
`validate_site.py` **required** it, `check_preview.py` asserted it on the deployed page,
and `DEPLOYMENT.md` listed it as "Delivered". A check that passed while protecting nothing,
which is the exact failure this project has spent eleven releases correcting elsewhere.
The meta CSP and `<meta name="referrer">` are genuinely valid; I extended that to a third
tag without verifying it. Tag removed, enforcement inverted into a guard against
reintroduction, documentation corrected to state the control is **not available**.

Four of the six controls a security questionnaire asks about cannot be delivered on this
platform. `DEPLOYMENT.md` now says so in one table and adds that moving to a host which
can send headers is a hosting decision, not a code change.

**`DEPLOYMENT.md` contradicted itself on HSTS** — "Not settable" in the platform table,
"HSTS is configured without preload" in a leftover Vercel-era section. Stale section removed.

**Release documents had drifted for eight releases.** `VALIDATION_REPORT.md` was headed
r11 while its captured run said it came from r3; `DEPLOYMENT.md` claimed verification from
r4 and an acceptance figure from r6; `RELEASE_NOTES.md` listed **F17 in two rows at once**,
"Cleared in r10" and "Open", because a hand-maintained status table was edited in place
each release. Every one of those is a symptom of hand-editing.

`VALIDATION_REPORT.md` is now **generated** by `scripts/generate_validation_report.py`,
which runs the gate, the shared-region check, the acceptance suite and the publish build
and captures their real output. `RELEASE_NOTES.md` no longer carries a status table at all
— one source, generated. The gate fails if either names the wrong release, if the captured
run is attributed to another archive, if a status table reappears in the release notes, or
if `DEPLOYMENT.md` contradicts itself on HSTS.

**jsdom was unpinned.** CI ran `npm install --no-save jsdom`, so the 39-test acceptance
suite ran against whatever `latest` was that day. Pinned to exactly `30.0.1`.

The first attempt at this fix was itself incomplete, and running the pipeline from the
packaged archive caught it: `npm ci` requires a committed `package-lock.json`, and
`.gitignore` excluded it. CI would have failed `npm ci` and fallen back to `npm install`
without complaint. An exact version in `package.json` pins jsdom but not its 38
transitive dependencies; only a lockfile does that. The lockfile is now committed, the
silent fallback is removed so a stale lockfile stops the build, and the gate requires the
lockfile to exist. It stays out of the published site.

**The post-deploy check could not fail the run.** `continue-on-error: true` meant a stale
or misrouted production deploy turned the step red and the workflow green — defeating the
check entirely. It now retries for five minutes against DNS propagation and then fails.
The gate rejects `continue-on-error` anywhere in the workflow.

**Accessibility — 26 tables without captions, 8 with no header cells.** Captions are
written per table, describing what each is for rather than boilerplate. The eight
label-value snapshot tables in the specimens now use `<th scope="row">`, which is what
makes a label-value pairing navigable. 43 tables, 0 without captions, 0 without headers.

**"A rational first purchase…"** on `escalation-memo.html` was market-study voice that
survived the r9 sweep. Replaced.

**What I would not change.** "Procurement fit" stays on ten pages. "Choose it when… do not
choose it as a substitute for…" is buyer guidance, not market study, and removing it would
make the pages less useful to the person deciding.

Gate: **0 errors, 0 warnings across 64 pages.** Acceptance: **39/39**. Twelve new checks,
each adversarially tested, 12/12 caught.

**Not closed by this archive, and stated plainly in `VALIDATION_REPORT.md`:** clinical
re-approval of all nine specimens, F17's operational PHI evidence, F13's one publish, and
the accessibility work that needs a real device and a screen reader.

# September 14, 2026 (r11) — F20, F21

**F20 — the drift check now opens a page.**

`check_services()` compared `data/site.json` against `service-catalog.json` and stopped
there, while its own docstring called it "the check that catches a price changed on one
page and not the others". It never opened a page. Two data files agreeing with each other
says nothing about what a buyer reads. It also never compared `turnaround` at all, despite
turnaround being one of the two figures most likely to drift.

It now reads each service's own page and its entry on `services.html` and requires the
canonical price and turnaround to appear there, after normalising dash and space variants
so an en dash typed as a hyphen reads as a typo rather than a pricing change. It separately
flags a page advertising a *different* starting price, which is drift even when the correct
figure also appears somewhere on the page. Verified by injecting five kinds of drift —
catalog/site.json turnaround mismatch, a wrong price on a service page, a missing
turnaround, a wrong price on `services.html`, and a wrong P2P price — 5/5 caught.

**F21 — measurement that exists, instead of instrumentation that does not.**

`window.clinovianEvents` wrote to a bounded in-page array that nothing read and that died
with the tab, under a comment calling it "privacy-conscious conversion instrumentation",
referencing an `ANALYTICS.md` that was not in the repository. Three problems: dead code,
an overclaiming label, and a dangling reference.

The buffer is kept — the acceptance tests assert on it and it is useful in a console — but
relabelled **"session-local diagnostics. NOT analytics"**, with the reason stated inline.

**Inquiry attribution without a tracker.** `routed_service_id` already rode along with
submissions. Two fields join it: `entry_page` (which of *our own* pages the person came
from) and `inquiry_source` (a campaign tag, else `site` or `direct`). No cookie, no third
party, and **nothing recorded for a visitor who never submits**. A cross-site referrer is
discarded entirely rather than reduced to a hostname, so a search query or a private URL on
another site is never captured. Verified in a DOM against a Google referrer carrying a
search query: `entry_page` came back empty. Injection and length cases also checked.

`privacy.html` was updated in the same change, because it states that no tracker is
installed and that claim has to stay true. The gate now fails if the form carries
attribution fields the notice does not disclose.

**`ANALYTICS.md`** now exists and says what is deliberately *not* installed and why: the
conversions that matter here — qualified conversation, paid pilot, repeat order, actual
hours, revision burden — happen off the website, and no page-view tool can see any of them.
It defines each funnel stage against a real source (Formspree, inbox, invoices, delivery
log, time record), and sets out what not to conclude: no Clinovian overturn rate, no
percentages below roughly 30 paid engagements, no clinical text anywhere, and a decline
rate near zero treated as a warning rather than a win.

**Gate.** Twelve checks added, each adversarially tested, 12/12 caught after two test-side
corrections — one mutation was case-sensitive and missed a capitalised instance, another
introduced a syntax error so the check fired for the wrong reason.

Gate: **0 errors, 0 warnings across 64 pages.** Acceptance: **39/39**.

**All 21 audit findings are now cleared or explicitly scoped.** What remains is the
accessibility work in section 9 of the audit — 29 tables without captions, 8 snapshot
tables without header cells, mobile hero sizing overridden by `!important`, and the
contrast, target-size, reduced-motion and screen-reader checks the audit did not measure.
F13's deployment half also remains: production still serves an older build until this
release is published.

# September 14, 2026 (r10) — F16, F17, F18

**F16 — homepage 1,916 → 1,308 words, navigation 35 → 22 links.**

The homepage carried the entire service catalogue: 15 service links across three audience
tracks, duplicating `services.html` in 668 words. It now shows the three services people
actually order first — escalation memo, P2P brief, AI appeal QA — each with its starting
price and turnaround, and one link to the full catalogue.

"Four routes in. Pick the one that describes you." presented hospitals, RCM firms, IDR
teams and AI vendors as four equally mature propositions. The audit's commercial
recommendation was to test appeals operations with an existing filing workflow as the
primary hypothesis. The section now leads with that route and groups the other three as
"also served", with their different onboarding paths stated rather than implied.

The mega menu held 21 service links plus four CTAs. Each column now leads with its
overview and carries the two services most often bought through it. Menu behaviour was
re-verified in a DOM after the restructure: open, Escape, ARIA state and focus all still
correct.

**F17 — privacy 146 → 855 words, terms 210 → 996 words.**

The privacy notice described a service that was not this one. It now covers what the form
actually collects field by field, the four third parties that see anything (GitHub Pages,
Formspree, Calendly, Google Fonts) in a table with what each one sees, a retention table
with actual periods, access/correction/deletion rights with a 30-day response commitment,
and two limits stated rather than glossed: we cannot guarantee removal from a provider's
backup cycle, and live-engagement records may be subject to retention obligations. It also
records that **no analytics, tracking or cookie is installed**, and that a consent
mechanism will be added before any such tool is enabled rather than after.

The terms covered nature of services, learning rights and a liability cap, and nothing
about buying. Added: invoicing in USD at 14 days, tax and withholding, when work starts,
the revision-versus-new-scope boundary (records arriving after delivery are a new scope,
quoted separately), a five-case cancellation and refund table including what happens when
Clinovian misses its own window, deliverable ownership and the condition that white-
labelling may not misrepresent who performed the review, confidentiality, conflict checks
with an explicit statement that Clinovian does not offer market exclusivity, and governing
law deliberately left to the signed engagement rather than imposed by a web page.

The liability cap is now framed as **a contractual allocation, not a statement of law**,
with liability that cannot lawfully be excluded carved out and the enforceability question
handed to the buyer's counsel. Operational detail is not duplicated — it points to the
Order Specification, which already covers units, pilots, revisions and the delivery clock.

**F18 — 134 unversioned asset references corrected.**

`og:image` carried the release stamp; the JSON-LD `image` and `logo`, `favicon.svg` and
`apple-touch-icon.png` did not. A corrected sharing image could therefore be served
alongside a stale structured-data image or a stale icon. Every cacheable asset reference
now carries one stamp, verified as still resolving when served statically. The sitemap
date-override mechanism the audit flagged as described-but-absent is present and in use:
`data/content-dates.json` is the source, and `generate_sitemap.py` fails if a page is
missing from it.

**Gate.** Thirteen checks added — homepage word and link budgets, required coverage in both
policies, the liability-cap framing, and unversioned assets — each adversarially tested,
13/13 caught. Two privacy tables needed focusable scroll wrappers; the existing
accessibility check caught that before packaging.

Gate: **0 errors, 0 warnings across 64 pages.** Acceptance: **39/39**.

Still open: F20 (shared-data generation), F21 (conversion measurement), and the
accessibility items in section 9 — table captions, snapshot-table headers, and mobile hero
sizing overridden by `!important`.

# September 14, 2026 (r9) — F09, F12, F15

**F09 — 28,236 characters of market research removed from the buying path.** Ten service
pages carried "Complete market and procurement context" and "Public pricing context"
sections; ten setting and specialty pages carried "Current alternatives" and a "Pricing
context" block. Between them they named competitors with outbound links, reported that no
comparable public per-case rate could be found, and discussed salary and overhead. That is
research, and it was sitting between a buyer and the purchase decision.

Removed: the two market blocks from all ten service pages, and "Current alternatives" from
all ten setting/specialty pages — "Why Clinovian is different" already sits immediately
after it and does that job. "Pricing context" was **split** rather than deleted: the
market-comparison sentence went, the Clinovian scope, fee and turnaround stayed, and the
heading is now "Scope, fee and turnaround". Kept throughout: "Minimum usable inputs",
"Service-specific failure modes" and "Procurement fit" — all three are buyer-facing.

`why-clinovian.html` claimed the $1,000 evaluation was "a smaller fraction still of one
month of a full-time advisor's salary". Replaced: the entry point is now explained without
asserting what a recovery is worth or what an alternative costs, since both depend on the
buyer's case mix and contracts.

**F12 — the public boundary now matches the demonstrated control.** `security.html` said
"Clinovian uses a BAA-governed secure transfer workflow with minimum-necessary access",
present tense, as though a standing approved workflow existed. It now states that **no
standing, pre-approved PHI workflow exists** and that the route, access controls and
retention are agreed with each client before any records move. "Secure transfer only"
became "Transfer route agreed before use", which is the commitment that can actually be
kept.

Added: a card defining what "de-identified" means here — HHS recognises Safe Harbor and
Expert Determination, deleting a name, DOB and record number is neither, a clinical
narrative can still identify through rare facts, and Clinovian does not certify that
material you send is de-identified. `contact.html` already said the identifier check is
"a prompt, not a security control"; the gate now requires that it keeps saying so.

**`trust-center.html` named Vercel as the hosting subprocessor.** Wrong since r8, and on a
procurement-facing page. Corrected to GitHub Pages; the gate now fails if any public page
names the wrong host.

**F15 — 20 unsupported claims replaced, 4 citations bound to documents.**

"Most medical-necessity appeals fail", "systematically under-appealed" and "one of the most
consistently under-argued" were majority and ranking assertions with no dataset behind them.
`insight-behavioral-health.html` contradicted itself outright: its sources block said no
comparative dataset had been identified and no ranking was asserted, while its body and its
meta description both asserted one. Each is now either attributed to the reviewer's
payer-side experience or stated without the quantifier, and the six-failure-modes article
now says in terms that no published dataset apportions appeal outcomes by cause.

Citations, previously pointing at index pages:

- OIG SNF report → **OEI-09-24-00331**, posted 11 June 2026, with the population stated
  (19 MAO parent companies, 29.3 million enrollees, ~86% of MA enrolment, June 2024 data).
- OIG LTCH/IRF companion → **OEI-09-24-00330**, same period and MAOs, noting that the 43%
  IRF figure conceals a 14%–86% range across plans.
- CMS No Surprises landing → the **Federal IDR Operations implementation timeline** and the
  final rule (**CMS-9897-F**, Federal Register 4 June 2026), with the staged dates kept
  separate and portal-dependent provisions explicitly marked as not yet fixed.
- HHS mental-health landing → the **CMS MHPAEA** page, including the applicability limit
  that MHPAEA does not apply directly to small group health plans.

The statistical framing around the 95%/18% figures was already correct — denominators,
selection limitation and an explicit warning that 95% describes roughly one denial in six,
self-selected. That was left alone.

**Gate.** Nine checks added across the three findings, each adversarially tested, 9/9
caught. Gate: **0 errors, 0 warnings across 64 pages.**

Still open: F16 (homepage breadth), F17 (privacy/terms), F18, F20, F21, accessibility.

# September 14, 2026 (r8) — The site runs on GitHub Pages, not Vercel

Every release up to r7 configured the wrong platform. `vercel.json` carried 74 redirects
and 8 header rules; on GitHub Pages **all of it was inert**. Three real consequences.

**1. Internal documents would have been public.** `.vercelignore` excluded
`VALIDATION_REPORT.md`, `RELEASE_NOTES.md`, `CHANGELOG.md`, `DEPLOYMENT.md`,
`IDR_CLAIMS_REGISTER.md` and `scripts/` from a *Vercel* deploy. This site does not deploy
to Vercel, so nothing excluded them. `https://clinovian.com/VALIDATION_REPORT.md` would
have served the open-defects list and the contested clinical review log to anyone who
guessed the filename — on a site selling clinical review credibility. `.vercelignore` was
worse than having no exclusion file, because it read like protection.

`scripts/build_publish.py` now assembles an **allow-listed** publish set: a file ships
because it was named, not because nobody excluded it. Verified by serving the built output
and confirming every internal path returns 404.

**2. Sixty-four routes would have 404'd.** GitHub Pages has no redirect support. Each
route in the new `data/routes.json` is materialised as a static stub — meta refresh,
canonical at the destination, `noindex`, and a visible link for anyone without JavaScript.
Extensionless routes become directory indexes (`/services/index.html`). All 64 verified
against a live server. The two legacy `.html` stubs already existed as real pages and were
correctly not overwritten.

**3. Security headers cannot be sent, and three cannot be replaced.** CSP,
`X-Content-Type-Options` and the referrer policy now ship as meta tags on all 64 pages.
**`frame-ancestors`/`X-Frame-Options`, `Strict-Transport-Security` and
`Permissions-Policy` are header-only and are therefore absent.** They are documented as
absent rather than quietly dropped: a buyer's security reviewer runs `curl -I` and finds
out either way. `check_preview.py` now reports headers as informational and fails only on
the meta policy, which is the part this platform can actually deliver.

**Removed:** `vercel.json`, `.vercelignore`. The gate fails if they, `netlify.toml`,
`_headers` or `_redirects` reappear.

**Added:** `data/routes.json` (route and host map), `scripts/build_publish.py`,
`.github/workflows/deploy.yml`, `.gitignore`, and generated `CNAME` + `.nojekyll`.

**F13 resolved.** The canonical host is now set by `CNAME`, generated from
`data/routes.json` and checked against the canonical tags. The redirect-loop hazard r7
warned about no longer exists — it was a property of the Vercel rule that has been deleted.
Production is still the older build; publishing this release replaces it.

CI runs the gate, the acceptance suite and the publish build on every push to `main`, and
**refuses to deploy** if an internal document reaches the output or `CNAME` disagrees with
the route map.

Gate: **0 errors, 0 warnings across 64 pages.** Eleven new platform checks, each
adversarially tested, 11/11 caught.

Still open: F09, F12, F15, F16, F17, F18, F20, F21 and the accessibility items.

# September 14, 2026 (r7) — Canonical host (F13): archive settled, one dashboard change left

Production was re-checked live on 14 September 2026 rather than relying on the audit's
12 September observation. It is still the older build, and there is a defect the audit
did not name.

**Live split host signal.** Every production page is served on `https://www.clinovian.com/`
while its own canonical tag names `https://clinovian.com/`, and every internal link on the
page is an absolute `https://www.clinovian.com/...` URL. The page tells a search engine the
apex is authoritative and then links exclusively to the host it just disowned. Confirmed on
both `/` and `/sitemap.html`. This is separate from the stale build and persists until the
host direction is settled.

**Redirect-loop hazard.** Production sends apex → `www`. This archive's `vercel.json` sends
`www` → apex. Applied together they bounce forever and every page becomes unreachable.
The Vercel domain setting must be changed **before** this archive is promoted, not after.
`DEPLOYMENT.md` section 1c gives the ordered procedure. Nothing in this repository can make
that change; it is a dashboard setting.

**Archive side — enforced, not merely correct.** The archive was already apex-consistent
(63 canonicals, 62 `og:url`, 61 sitemap entries, feed, JSON-LD, and a `www` → apex rule in
`vercel.json`). It is now *enforced*: `validate_site.py` fails if canonical and `og:url`
origins diverge, if `sitemap.xml` or `feed.xml` name a different origin, if structured data
names a different origin, if `vercel.json` redirects **away** from the canonical host — the
loop condition — or if its host rule points anywhere other than the canonical origin. Six
checks, each adversarially tested by injecting the defect, 6/6 caught. Switching to `www`
as the public host remains a legitimate choice; the gate will simply name everything else
that has to move with it.

**`check_preview.py` claimed a matrix test it did not have.** Its docstring advertised
"the canonical host/redirect matrix (apex vs www, http vs https)" while the code accepted a
single base URL and tested nothing of the sort — the same overclaiming pattern as the
regression suite that was never called and the `VALIDATION_REPORT` placeholder. It now
walks all four entry points one hop at a time under `--matrix`, requires each to settle on
`https://clinovian.com` with a 200, and reports a redirect loop explicitly instead of as an
opaque error. It also compares each served page's canonical tag against the host that
served it, which is exactly the defect production has today.

Both detectors were verified against live local servers: two mutually-redirecting servers
produce `outcome: loop` with the full hop trail, and a server whose canonical names a
different origin produces three named split-signal failures.

Gate: **0 errors, 0 warnings across 64 pages.**

Still open: F09, F12, F15, F16, F17, F18, F20, F21 and the accessibility items. F13's
archive half is done; its deployment half is one setting and one promote.

# September 14, 2026 (r6) — Inquiry flow, executed rather than inspected

Phase 3 is the part of the audit the static gate cannot reach. F03, F07, F08 and F11 were
all implemented in code and all "verified" by reading that code. r6 runs it instead:
`scripts/acceptance/inquiry-flow.js` loads the real `contact.html` into a DOM, executes
the real `main.js`, and drives the form. Only `fetch()` is mocked — no request leaves the
machine, no inbox is touched. **39 assertions, 0 failures.**

**Two real defects surfaced that code review had missed.**

- **Duplicate submission fired two requests.** The handler disables the submit button, so
  a second *click* is impossible — which is why reading the code looked fine. But Enter
  pressed in a text field submits the form without touching the button, and the test fired
  two `fetch` calls for one inquiry. A re-entrancy guard now sits in the handler itself and
  is released on both the server-rejection and network-failure paths so retry still works.
- **No `<noscript>` fallback existed anywhere.** With scripts disabled the case-fit section
  never appears and the mobile drawer cannot open, and nothing told the user either. The
  audit asked for "a useful fallback or an explicit, accessible explanation"; there was
  neither. `contact.html` now explains that the form sends a general business inquiry
  without JavaScript and gives the email route, **carrying the same no-PHI instruction as
  the network-failure fallback**. `shared/nav.html` offers a route to `/sitemap.html`.

**What the suite confirmed already worked:** the confirmation region is outside the form,
`aria-live`, `role=status`, becomes visible on a mocked 200, states the response window,
states nothing is committed, moves focus to a focusable heading, and hides `#intake-form-shell`
rather than the whole form. Validation failure marks `aria-invalid` and binds
`aria-describedby`, and the error clears when the field is corrected. Server rejection and
network failure both leave the fields editable and re-enable the button. All **14** service
CTAs across the site preselect their intended option, including all ten that the audit found
broken. Escape sets `aria-expanded=false`, removes `.open`, and leaves focus on the toggle.
The IDR fieldset is disabled when inactive and its stale value does not reach FormData.

**Gate.** Five checks added — re-entrancy guard, guard release on retry paths, and three
`<noscript>` checks — each adversarially tested, 5/5 caught. One of them was initially
wrong in the same way the old checks were: it sliced to the first `</noscript>` in the
page, which is the shared nav's, and inspected the wrong block. It now scans every block.

Gate: **0 errors, 0 warnings across 64 pages.** Acceptance: **39/39.**

Still open: F09, F12, F15, F16, F18, F20, F21, F17, F13 (production still serves an older
build) and the accessibility items in section 9.

# September 14, 2026 (r5) — The release gate, adversarially tested

r4 wired up a regression suite that had never been called. r5 asks the harder question:
do the checks actually fire? Each check was tested by injecting the specific defect it
claims to catch and confirming the build fails. **29 of 29 caught — after two repairs.**

**Two checks were silently dead.**

- **`F03` (confirmation region).** It tested only whether `#intake-status` sat inside
  `#intake-form`. Deleting or renaming the region entirely made the test pass, because a
  missing element is not "inside the form" — the success message would have vanished with
  the gate reporting clean. It now requires the region to exist, to sit outside the form,
  to carry `aria-live` and a `role`, and requires `#intake-form-shell` plus a success
  branch that writes a confirmation.
- **`F11` (stale field serialisation).** It matched `.disabled = !active` anywhere in
  `main.js`, so disabling the `<fieldset>` alone satisfied it. Either level alone still
  lets a value serialise. It now requires both `group.disabled` and `el.disabled`.
- **`F08`** additionally now requires an Escape handler and `aria-expanded` in `main.js`.
  Previously it checked only that no CSS hover rule could open a dropdown — a build with
  no keyboard dismissal at all would have passed.

**`scripts/check_preview.py` was comparing nothing.** It fetched `/RELEASE_ID`, discarded
the body, and tested only for a 200. Any host serving any build with any `RELEASE_ID` file
passed — which is precisely the F13 condition in production right now. `fetch()` gained an
optional body return, and the check now compares the deployed identifier against the
working copy and fails with both values named. Verified against a local HTTP server:
passes on a matching build, fails with a named mismatch on a stale one, exit 1.

**`DEPLOYMENT.md`.**

- A malformed code fence had trapped three sentences of prose inside a `bash` block.
- The validator description claimed coverage it did not have. It now names the regression
  suite, warns that `regression_checks()` must stay wired into `main()`, and states
  plainly that **the gate does not validate clinical, coding or regulatory accuracy.**
- New section 0 records that every documented command was executed from a clean
  extraction and completed as written, with its actual output.

Gate: **0 errors, 0 warnings across 64 pages.**

Still open: F08 (browser acceptance), F09, F12, F15, F16, F18, F20, F21, F13 (production
still serves an older build — `check_preview.py` will now catch this), F17, and the
accessibility items. The clinical review log still predates the r4 specimen edits and
needs re-confirming by the reviewer.

# September 14, 2026 (r4) — Specimen corrections (F02/F05) and a dead regression suite

The contradictions an independent review found in 2026.09.13-r2 are corrected. The pattern
behind them is worth recording: corrected text had been **added alongside** the superseded
text rather than replacing it. `sample-observation-defense.html` published a correct HEART
component breakdown totalling 8, and a note explaining that the previous draft said 7 — then
nine lines later still read "HEART score 7 (high-risk)". The same file stated it made no
claim about prevailing, then closed with "Strong case... should prevail". Every defect below
is a sweep failure of that kind, not a reasoning failure.

- **`sample-observation-defense.html`** — stale "HEART score 7" in the Two-Midnight table
  corrected to 8 with a pointer to the component breakdown; closing verdict "Overall: Strong
  case... should prevail at Level 1 or Level 2" replaced with a conditional verdict that
  names what it rests on and defers to the open questions at Section 08.
- **`sample-escalation-memo.html`** — "clinically strong... materially improves the
  probability of overturn" replaced with a conditional statement that does not forecast.
- **`sample-p2p-brief.html`** — CHA₂DS₂-VASc published as components (hypertension 1, age
  68 i.e. 65–74 1, vascular disease/prior PCI 1; four components scoring zero named)
  reconciling to the stated 3, where it previously printed a bare "Score 3" despite Section
  01 promising components. The "most common reason P2P calls fail" majority claim became a
  described pattern with an explicit statement that no dataset ranks these causes.
- **`sample-ar-audit.html`** — footer and specimen description restored to the triage-only
  boundary; "showing what is contestable... and what to pursue first" replaced with what the
  service actually does, and an explicit statement that it does not assess merits, forecast
  recovery or decide what to abandon. **The 47-row inventory arithmetic was re-verified and
  is sound**: 18+12+10+7 = 47, $612,000+$318,000+$155,000+$189,000 = $1,274,000, top five
  = $203,600 sorted descending, containment holds ($39,700 ≥ $39,200), no duplicate IDs.
- **`sample-declined-case.html`** — carried the AR-audit footer verbatim, an AR-audit
  breadcrumb target, and a surplus `</div>` that closed `.doc-wrap` early (net −1). All
  three fixed; the footer now describes the declined-case specimen and its CTAs point at
  case suitability and fit assessment.
- **`sample-pre-denial-dossier.html`** — two revision-history notes ("The earlier version of
  this dossier...") rewritten as client-facing principles. The L4–L5 / L5-root anatomy
  analysis was already correct and conditional and is unchanged.

**Author-facing copy removed from published specimens.** Three specimens carried notes
addressed to whoever was editing them rather than to the buyer — an instruction to avoid the
word "unambiguous", and four separate explanations of what a previous draft got wrong. These
are the same class of leak as F09 and were sitting in the primary sales proof.

**`scripts/validate_site.py` — `regression_checks()` was never called.** It was defined in
r2 and `main()` ran only `check_repo()`, so the entire regression suite was dead code while
`RELEASE_NOTES.md` claimed "nine regression checks added... testing the actual defects". It
is now invoked from `main()` and passes. Six specimen checks were added: outcome-prediction
language, revision-history notes, HEART and CHA₂DS₂-VASc component reconciliation, AR scope
breach, breadcrumb self-reference, and balanced `<div>` nesting. **Each was verified by
reintroducing the original defect and confirming the build fails — 9/9 caught.**

Gate: **0 errors, 0 warnings across 64 pages**, with the regression suite actually running
for the first time.

Still open: F06 (release-doc accuracy, improved but ongoing), F08, F09, F12, F15, F16, F18,
F19, F20, F21, F13 (production still serves an older build), F17, and the accessibility
items. The clinical review log in `VALIDATION_REPORT.md` predates these edits and should be
re-confirmed and re-dated by the reviewer.

# September 14, 2026 — PDF specimen editions withdrawn permanently (2026.09.14-r3)

The downloadable PDF editions of the specimens are discontinued. The eight stale exports
were already removed in 2026.09.13-r2 and replaced with an interim "withdrawn pending
re-typesetting" notice; that notice implied the PDFs were returning. They are not. HTML is
now the sole published format for every specimen.

- **All nine specimen pages** — removed the dead `.doc-pdf-link` CSS rule, removed
  `.doc-pdf-link` from the `@media print` rule (the `.top-bar` suppression is preserved),
  and removed the interim withdrawal-notice paragraph.
- **Eight specimen pages** — the document-control row "Matching HTML / PDF", which claimed
  that the HTML page and "its PDF export" carry the same version, was factually false once
  the PDFs were deleted. Replaced with "Format of record — This HTML page is the sole
  version of record. No PDF edition of this specimen is published."
  (`sample-declined-case.html` never carried that row.)
- **`vercel.json`** — removed the `/(.*)\.pdf` cache-control and `Content-Disposition`
  header block; no PDF is served.
- **`DEPLOYMENT.md`** — removed "PDFs" from the validator coverage sentence, "all eight
  specimen PDFs" from the preview asset check, "PDF/download links" from the screen-reader
  workflow list, and "specimen downloads" from the rollback triggers.
- **`RELEASE_NOTES.md` / `VALIDATION_REPORT.md`** — F14 restated from "regeneration
  deferred" to "withdrawn permanently".
- **Release gate hardened against reintroduction.** `scripts/validate_site.py` F14 no
  longer checks for links to missing PDFs; it now fails the build if any page carries a
  same-origin `.pdf` link, the `doc-pdf-link` region, a "Matching HTML / PDF" parity claim,
  or a "download ... as a PDF" affordance. External `.pdf` source links to CMS, OIG and
  guideline documents remain permitted, since those are legitimate citations.
- **Release identity** bumped to `2026.09.14-r3` across `RELEASE_ID`, `data/site.json`,
  `data/content-dates.json`, both release documents and the asset `?v=` query strings.
  Specimen `lastmod` dates advanced to 2026-09-14.

Also fixed, because the release gate could not otherwise pass:

- **`/apple-touch-icon.png` added.** Every ordinary page referenced it; the file was absent
  from 2026.09.13-r2, producing **all 62 errors** the gate reported. It is rasterised from
  the existing `favicon.svg` mark at 180x180 — brand colours unchanged (`#183F2D` ground,
  `#f3efe4` glyph, `#b18a43` accent), opaque, square corners so iOS applies its own mask.
  A seven-day cache rule was added in `vercel.json`, matching the policy for the other icon
  assets. **Replace it if you have a designed icon; it is a faithful rasterisation of your
  own mark, not a new design.**
- **`VALIDATION_REPORT.md` result section.** It shipped with the placeholder "Run
  `python3 scripts/validate_site.py` and paste its summary block here" — meaning the gate
  had never been run against the delivered archive. It now carries captured output from a
  clean extraction: **0 errors, 0 warnings across 64 pages.** A "Known open defects"
  section was added listing what a passing gate does not cover.
- **`RELEASE_NOTES.md` completion claims.** The table headed "Completed and verifiable in
  these files" listed findings the independent review found partial or open. The heading is
  now "Changes attempted in this release", preceded by an independently verified status
  table. The clinical review log in `VALIDATION_REPORT.md` still records every specimen as
  "Rewritten"; that log carries the reviewer's name and date and has **not** been altered
  here, but the report now states plainly that the status is contested and must be
  re-confirmed before any specimen is used as sales proof.

Not addressed in this release: the specimen content corrections themselves (F02/F05), and
the open F09/F13/F15/F16/F17/F19/F20/F21 items. The gate passing does not mean the site is
ready for outreach.

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
