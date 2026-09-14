# Measurement plan (F21)

**Release:** 2026.09.14-r11 · **Owner:** Arun Kasturi · **Review:** monthly

This file was referenced by `main.js` and by earlier release notes before it existed.
That is the whole shape of the F21 problem: the site claimed measurement it did not have.

## What is not installed, and why

**No analytics product, no tag manager, no session recording, no cookie.** Not an
oversight — a decision. Three reasons:

1. The conversions that matter here happen off the website. Inquiry → qualified
   conversation → paid pilot → repeat order → actual hours and revisions per case. No
   page-view tool can see any of that, and the decisions that depend on it (is the offer
   viable, is the pricing right, which buyer route to pursue) depend on nothing else.
2. At current volume the interesting numbers are countable by hand. A tool would produce
   dashboards over a sample too small to act on.
3. `privacy.html` states plainly that nothing is installed. If that changes, **the notice
   is updated and a consent mechanism is added before the tool is enabled**, not after.

`window.clinovianEvents` in `main.js` is **session-local diagnostics, not analytics**. It
writes to a bounded in-page array, transmits nothing, and dies with the tab. It exists for
console inspection and for the acceptance tests. Do not cite it as a measurement source.

## Where the numbers actually come from

| Stage | Definition | Source |
|---|---|---|
| Inquiries received | Form submissions and direct emails | Formspree dashboard + inbox |
| Route | Which service and which page the inquiry came from | `routed_service_id`, `entry_page`, `inquiry_source` on the submission |
| Qualified | Fit assessment sent and a real scope discussed | Inbox, recorded at the time |
| Declined by Clinovian | Case refused, with the reason | Decline log — count these, they are the discipline evidence |
| Paid engagement | Fee agreed in writing and work started | Invoices |
| Delivered | Deliverable sent | Delivery log |
| Revisions | Revisions per deliverable, and whether in-allowance | Delivery log |
| Actual hours | Screening, records, sourcing, drafting, QA, comms, revisions | Time record per case |
| Repeat | A second paid order from the same client | Invoices |

### Inquiry attribution without a tracker

Three hidden fields ride along with a submission the person has chosen to send:

- `routed_service_id` — the service their CTA was for
- `entry_page` — which of **our own** pages they came from
- `inquiry_source` — a campaign tag from `utm_campaign` / `utm_source`, else `site` or `direct`

No cookie is set, no third party is contacted, and **nothing is recorded for a visitor who
never submits**. A cross-site referrer is discarded entirely rather than reduced, so a
search query or a private URL on another site is never captured. Values are stripped to a
safe character set and length-capped. Verified against a DOM, including a Google referrer
carrying a search query, which produced an empty `entry_page`.

## What to record monthly

A single sheet, one row per month:

    inquiries · qualified · declined · paid · delivered
    median hours per case · median revisions · repeat orders
    top 3 entry pages · top 3 services requested

## What not to conclude

- **Do not report an overturn rate as a Clinovian outcome.** Outcomes depend on records and
  adjudicators outside our control. Report accepted, delivered, filed, decided, and
  unknown, and leave unknown visible — it will be the largest bucket for a while.
- **Do not read a funnel from a handful of cases.** Below roughly 30 paid engagements these
  are descriptive observations, not rates. Say "9 of 14", never "64%".
- **Do not let clinical text into any of it.** No case narrative, no payer name tied to a
  case, no identifiers in a spreadsheet, a tool, or this file.
- **Do not treat a declined case as a failure.** The decline rate is evidence that the
  suitability screen works. A rate near zero is the thing to worry about.

## The decision this exists to inform

The audit's commercial recommendation was to test appeals operations with an existing
filing workflow as the primary buyer route, with hospital overflow second and IDR as a
distinct workflow. That hypothesis is unvalidated. It is answered by paid pilots, repeat
orders, actual hours and revision burden — the rows above — and not by traffic.

Revisit this file when paid engagements pass roughly 30, or when an analytics tool is
genuinely needed. Until then, adding one would produce precision without information.
