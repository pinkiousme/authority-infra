---
name: pipeline-builder
version: 8.2
description: "Robust mode-aware pipeline report builder. Runs fully autonomously with no web research in the default path. Reads a frozen context file (schema v3), fetches real ICP-matched leads with live signals from Vibe Prospecting using a deterministic buyer-profile signal matrix, produces ONLY a validated data.json, then runs build_report.py to inject the data into the approved placeholder template. Model never assembles HTML. DEMO or LIVE. Email-only enrichment (no phone). Two-step events fetch (businesses then prospects). Per-client in-memory dedup. No web search unless explicitly opted in per client. Credit-cap-safe by design."
---

# pipeline-builder v8.2
## Robust Pipeline Report Engine (autonomous, web-free default, data-first)

## AUTONOMY (read first, overrides any default instinct)
This is an automated deployment routine, not a code-review task. Run end to end without stopping.
- Do NOT ask whether to proceed. Do NOT ask any question. There is no human watching.
- Do NOT create or propose a branch. Do NOT open or propose a pull request. Do NOT run git.
- Writing directly to `main` via the GitHub Contents API is the intended, correct, and only action. Deploy is a single Contents API PUT to main.
- The only acceptable stop is a hard failure you cannot recover from. Report it and end. Never pause for permission.
- Follow the steps below exactly and in order. Do not add steps. Do not explore. Do not research.

## Architecture principle
The model produces only a small validated JSON object. build_report.py injects it into the approved template through explicit `__PL_*` placeholders, asserting every one is hit and failing loudly if any is missing. The model never writes HTML.

## Data principle
Every fact on a card comes from the Vibe fetch and enrichment you already ran. LinkedIn URLs, names, titles, signals, and contact come from Vibe. You do NOT browse the web to fill cards in the default path (see Step 3).

## VERIFIED-ONLY DATA POLICY (non-negotiable, overrides convenience)
Every signal claim on a card MUST carry a verifiable public source link. No link, no lead.
- After fetching the businesses, call `fetch-businesses-events` and read each event's `data.link`, `data.title`, `data.description`.
- Keep a company ONLY if its event record has a real public `data.link` (http...). News-backed events (merger_and_acquisitions, new_funding_round, new_partnership, new_product, lawsuits_and_legal_issues, cost_cutting when news-derived) carry links. Pure workforce signals (decrease_in_all_departments and similar) usually have NO link and are UNVERIFIABLE: drop them, never claim them.
- Each delivered lead carries `signal_description` (the event description as plain fact), `source` (the event link), and `source_title` (the publication). The card renders a "Verify this signal" link to `source`.
- If nothing is verifiable, deliver nothing and report it. Never deploy a claim a client cannot check. No fabrication, ever.

## Selection principle
Which signals and filters to use is frozen in the context file. The routine derives nothing. It reads the two flags and the frozen filter, applies the matrix as a guard, and fetches.

---

## INPUTS (from the routine)
MODE: DEMO or LIVE · SLUG: lowercase-hyphenated · DATE: today DDMMYYYY
GitHub auth: read the `GH_TOKEN` environment variable for the Contents API Authorization header. Never expect a token pasted in the prompt, never print it.

## SELECTION MODEL
- `BUYER_PROFILE`: `venture` or `operator`. Controls funding inclusion, revenue floor, category discipline.
- `ADVISOR_FUNCTION`: `finance` or `operations`. Controls which department's hiring signals are weighted.

## SIGNAL MATRIX (deterministic guard — only valid Vibe event names)
Vibe has NO `leadership_change` or `office_expansion` event. Use only the valid enum below.
- venture: include `new_funding_round`, `hiring_in_[finance|operations]_department`. No revenue floor. Tech categories fine.
- operator: include `merger_and_acquisitions`, `cost_cutting`, `decrease_in_all_departments`, `hiring_in_[finance|operations]_department`. For operations advisors also add `new_office`. EXCLUDE `new_funding_round` always (guard: drop it if present in context, note the correction). Enforce context `revenue_floor`. Apply context `exclude_company_keywords`.
- advisor_function overlay: finance reads finance hiring; operations reads operations hiring plus `new_office` weighted up.
- `cost_cutting` + `decrease_in_all_departments` together are the valid proxy for a restructure/turnaround trigger (there is no literal "restructuring" event).
Do not autocomplete events at run time if `autocomplete_resolved: true`.

## MODE CONFIG
| Setting | DEMO | LIVE |
|---|---|---|
| Leads | 5 | 10 |
| Enrichment | email only | email only (no phone, ever) |
| Email on cards | hidden | shown |
| Phone on cards | never | never |
| Unmask method | show-sample (flat 5 credits) | export-to-csv (sized to credit_cap) |
| CTAs | yes (MODE-driven in template) | no |
| Deploy path | demo/[DATE]/[firstname]/index.html | prod/[SLUG]/pipeline/index.html |
| Dedup | no | yes |

---

## STEP 1 · READ CONTEXT (frozen, no derivation)
GitHub API (not raw CDN): GET /repos/pinkiousme/authority-infra/contents/inputs/[demo|prod]/[SLUG]/context.md?ref=main · decode base64.
Read name/firm/website/location/ICP/voice, the two SELECTION FLAGS, the FROZEN VIBE FILTER block, and the RUN CONTROL block (credit_cap, web_mode, deploy_path).
If `autocomplete_resolved: true`, treat job_title, linkedin_category, events as final. Do NOT autocomplete. Missing context: STOP, never fabricate.

## STEP 2 · FETCH + ENRICH + UNMASK (email only, both modes)
Vibe Prospecting only. Never Apollo. Never exclude_key. EMAIL ONLY — never enrich phone in either mode.

Cost model (email-only): fetch is free exploration; `estimate-cost` and the enrich preview are free; `show-sample` is a flat 5 credits and returns up to ~5 unmasked rows; `export-to-csv` is ~4 credits per row and returns ALL rows. Pick the unmask method by mode (below). The enrich preview returns MASKED rows — unmask happens at show-sample or export, not at enrich.

OVERSAMPLE (critical): only ~3% of companies matching a news event also have a reachable owner-level email, so the BUSINESS fetch must be large (number_of_results 200-400 — it is free exploration). Verify events, drop AI/tech/venture and over-ceiling companies, then enrich + retrieve only the survivors up to the cap. A small business fetch yields almost no verified leads.
Sizing so spend never exceeds `credit_cap` (email-only export ≈ 4 credits/row):
- DEMO: oversample businesses, unmask the top survivors via show-sample (flat 5 credits, well under cap).
- LIVE: target 10. affordable_rows = credit_cap // 4. enrich/export = min(12, affordable_rows) survivors. Unmask via export-to-csv with limit = that count (≈ 4 credits each). At credit_cap 50 this is up to 12 rows / ~48 credits / up to 10 leads; at credit_cap 35 it auto-shrinks to 8 rows / ~32 credits. Never exceed the cap; if the live estimate is over, lower the limit until it fits. Never abort for budget.
- Reality: a narrow ICP may yield fewer than 10 verified leads in a week. Deliver what is genuinely verified and report the count. Never pad with unverified leads to hit a number.

Guard: if BUYER_PROFILE is operator, ensure `new_funding_round` is NOT in events. Buyer titles from context. job_level owner-level only. company_size context bands only. events = frozen list, window = events_window_days (default 90, valid range 30-90).

The events filter ONLY works on `entity_type:"businesses"`, so the fetch is TWO steps:
```
# STEP 2a — businesses carrying the signals
fetch-entities(entity_type:"businesses", number_of_results:[fetch],
  filters:{ company_size, company_country_code, linkedin_category,
            events:{values:[context], last_occurrence:[window]} })
# -> keep businesses_reference_table from the response

# STEP 2b — decision-makers at those businesses
fetch-entities(entity_type:"prospects", businesses_reference_table:[from 2a],
  number_of_results:[fetch],
  filters:{ job_title, job_level, has_email:true })
```
VERIFY (mandatory, before enrich): call `fetch-businesses-events` on the businesses_reference_table from 2a, event_types = your event list, timestamp_from = window days ago. Read each record's `data.link`, `data.title`, `data.description`. KEEP only companies whose event has a real public `data.link`. Drop unverifiable companies (e.g. headcount-only `decrease_in_all_departments` with no link) entirely. Then refine 2b to the surviving companies only.
ENRICH once: enrich-prospects-contacts, contact_types ["email"] (both modes). Then UNMASK by mode: DEMO show-sample, LIVE export-to-csv (limit = fetch). Use only rows that returned a real email AND a verified source link.
Post-enrich quality filter, keep a lead only if: decision-maker buyer title from context; company fits size/stage/type; if operator, company does NOT match `exclude_company_keywords`; signal is in-window and listed. Rank dual-signal first, then strength and recency. Keep target (DEMO 5 / LIVE 10).
If short: widen ONE filter ONCE (window 90 to 120 is NOT allowed — Vibe caps last_occurrence at 90; instead add one adjacent industry OR the next size band within ceiling), refetch ONCE, enrich. Still short: deliver what qualifies, note the count. NEVER pad off-ICP. NEVER refetch more than once.
LIVE dedup: read inputs/prod/[SLUG]/dedup.json in memory, drop already-delivered LinkedIn URLs. Never pass to exclude_key. DEMO: no dedup.
URLs stored WITH https://. Masked or absent after unmask: linkedin empty (card omits Profile button). Never web-guess a URL.
On ceiling or timeout: use what unmasked, filter, complete, note the count. Never retry, never thrash, never fabricate.

## STEP 3 · CARD CONTEXT + PULSE (NO WEB by default)
Default and `web_mode: off` and `web_mode: pulse_only`: do NOT call web_search at all. Do NOT research companies on the web. Derive every card field from the Vibe data you already have:
- `recentNews`: state the lead's Vibe signal in plain words (e.g. "Recent acquisition", "Hiring in operations", "New operations leader"). The signal IS the recent news.
- `whatTheyDo`: from the Vibe industry, size, and category.
- `founderFocus`, `teamTrajectory`: a short, soft inference from the signal and role, or "Not on record". Never asserted as a researched fact.
- `pulse`: compute from the fetched leads (e.g. "7 of 10 hiring in operations in the last 60 days, 2 with recent acquisitions").
Only `web_mode: per_company` (rare, explicit opt-in, LIVE only) permits web search: one bounded search per company, hard timeout, skip-on-fail, cached. Never the default. Web data is company-level only and never determines identity or LinkedIn.

## STEP 4 · DERIVE FIELDS (from Vibe data only)
Per lead: signalDetail (Vibe signal category, soft timeframe only if confident), HOT (0-30d) / WARM (31-90d), priority (dual-signal first then HOT by recency; top 2 DEMO / top 3 LIVE).
whyFit: match the verified signal and stage to the prospect's real background. Derived, never invented. whyNow: the signal and timing, prospect voice.
Outreach copy leads with the verified signal category. No unverified specifics as fact. connNote <=280 chars. emailSubj short. emailBody 2-3 short paragraphs, prospect voice, no pitch. Contact: DEMO empty, LIVE email from enrichment (phone always empty). Theme cycles violet, amber, teal, blue, pink.

## STEP 5 · WRITE data.json (the only thing the model assembles)
Plain JSON, no HTML. Schema from v7 plus three verification fields per lead: `source` (the event's public URL, REQUIRED), `sourceTitle` (publication name), and `recentNews` set to the event's real `data.description` stated as plain fact. A lead with no `source` URL must NOT be written. Operator `stage` may be revenue bands. Confirm it parses.

## STEP 6 · ASSEMBLE (no model HTML)
GitHub API fetch assets/templates/pipeline-report/index.html and skills/build_report.py.
Run: `python3 build_report.py data.json template.html output.html`
The builder injects via `__PL_*` placeholders with correct escaping and FAILS LOUD on any fault (missing placeholder, leftover token, wrong lead count, seed leak, invalid JS, em dash, tool name, too small). If it errors: fix the named data.json field, re-run. Do NOT deploy a failing file. Do NOT probe or re-read the template.

## STEP 7 · VALIDATE (confirm)
output.html exists and >= 50000 bytes (if builder raised, it does not exist: STOP). node --check the script once. Lead count == target or noted lower. No `__PL_` token remains. Anything fails: STOP, report, output data.json and the error. Never deploy a failing file.

## STEP 8 · DEPLOY (one Contents API PUT to main, no questions)
ONE write: the report file, Contents API, to main, then STOP. No branch, no PR, no git, no archiving, no backups. Do not ask.
PUT path: DEMO demo/[DATE]/[firstname]/index.html · LIVE prod/[SLUG]/pipeline/index.html · branch main · committer AND author {name:pinkiousme, email:pinkious.me@gmail.com} (wrong email = silent fail). GET path first for SHA if it exists, then PUT.
LIVE dedup only (after deploy): read inputs/prod/[SLUG]/dedup.json, append delivered URLs, dedupe, PUT back. DEMO: no other write.
On failure: output the HTML in the run log. Never fail silently.

## STEP 9 · OUTPUT SUMMARY
PIPELINE REPORT COMPLETE · Mode · Person · Firm · Leads N · HOT N · WARM N · Enrichment ON/OFF · web off · Credits approx N · Live URL: https://pipelind.com/demo/[DATE]/[firstname]/ (DEMO) or https://pipelind.com/prod/[SLUG]/pipeline/ (LIVE) · Deploy SUCCESS · Validation PASSED. NEVER output a github.com URL as the live URL. The live URL is always the pipelind.com path. DEMO also outputs a short DM script (no unverified specifics).

## SPEED + COST DISCIPLINE (low reasoning setting safe)
- NO web search in the default path. This is the single biggest speed and reliability lever.
- One fetch. One enrich. No autocomplete when resolved. No exploration. No template probing. One write.
- estimate-cost gate before fetch, capped by credit_cap. Email-only enrichment. Size LIVE export to the cap so it can never overspend.
- Unmask cheaply: DEMO uses show-sample (flat 5 credits); LIVE uses export-to-csv sized to credit_cap. At most one widen-and-refetch if under count. Never retry on ceiling or timeout.
- Target: 8 to 12 minutes. If you find yourself searching the web or asking a question, stop that, it is not part of this routine.

## DATA INTEGRITY (non-negotiable)
1. No fabricated data. Person and company facts from Vibe. Nothing invented. No web in the default path. Every signal claim carries a verifiable public source link, or the lead is dropped (see VERIFIED-ONLY DATA POLICY).
2. LinkedIn URLs Vibe-authoritative or empty. Buyer-title floor on every lead. Operator: funding excluded, revenue_floor enforced, exclude_company_keywords applied.
3. No unverified specifics as fact. No fabricated contacts (DEMO empty, LIVE email-only from enrichment, phone never).
4. No tool names or pricing in visible HTML. Zero em dashes, zero exclamation marks.
5. Model writes JSON, builder writes HTML and fails loud. One write to main (plus LIVE dedup.json). Never branch, PR, git, or archive. Never ask.

