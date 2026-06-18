---
name: pipeline-builder
version: 8.0
description: "Robust mode-aware pipeline report builder. Runs fully autonomously with no web research in the default path. Reads a frozen context file (schema v3), fetches real ICP-matched leads with live signals from Vibe Prospecting using a deterministic buyer-profile signal matrix, produces ONLY a validated data.json, then runs build_report.py to inject the data into the approved placeholder template. Model never assembles HTML. DEMO or LIVE. Per-client in-memory dedup. No web search unless explicitly opted in per client. Single fetch, single enrich, single write."
---

# pipeline-builder v8.0
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

## Selection principle
Which signals and filters to use is frozen in the context file. The routine derives nothing. It reads the two flags and the frozen filter, applies the matrix as a guard, and fetches.

---

## INPUTS (from the routine)
MODE: DEMO or LIVE · SLUG: lowercase-hyphenated · DATE: today DDMMYYYY · TOKEN: GitHub token

## SELECTION MODEL
- `BUYER_PROFILE`: `venture` or `operator`. Controls funding inclusion, revenue floor, category discipline.
- `ADVISOR_FUNCTION`: `finance` or `operations`. Controls which department's hiring and leadership signals are read.

## SIGNAL MATRIX (deterministic guard)
- venture: include `new_funding_round`, `leadership_change` (function), `hiring_in_[finance|operations]_department`. No revenue floor. Tech categories fine.
- operator: include `merger_and_acquisitions`, `leadership_change` (function), `hiring_in_[finance|operations]_department`, `office_expansion`. EXCLUDE `new_funding_round` always (guard: drop it if present in context, note the correction). Enforce context `revenue_floor`. Apply context `exclude_company_keywords`.
- advisor_function overlay: finance to finance signals, operations to operations signals plus office_expansion weighted up.
Do not autocomplete events at run time if `autocomplete_resolved: true`.

## MODE CONFIG
| Setting | DEMO | LIVE |
|---|---|---|
| Leads | 5 | 10 |
| Enrichment | email only (to unmask identity + LinkedIn) | email + phone |
| Email/phone on cards | hidden | shown |
| CTAs | yes (MODE-driven in template) | no |
| Deploy path | demo/[DATE]/[firstname]/index.html | prod/[SLUG]/pipeline/index.html |
| Dedup | no | yes |

---

## STEP 1 · READ CONTEXT (frozen, no derivation)
GitHub API (not raw CDN): GET /repos/pinkiousme/authority-infra/contents/inputs/[demo|prod]/[SLUG]/context.md?ref=main · decode base64.
Read name/firm/website/location/ICP/voice, the two SELECTION FLAGS, the FROZEN VIBE FILTER block, and the RUN CONTROL block (credit_cap, web_mode, deploy_path).
If `autocomplete_resolved: true`, treat job_title, linkedin_category, events as final. Do NOT autocomplete. Missing context: STOP, never fabricate.

## STEP 2 · FETCH + ENRICH (one fetch, one enrich)
Vibe Prospecting only. Never Apollo. Never exclude_key.
Masking: the fetch preview is masked until enriched. Do NOT fetch large and filter down. Do NOT export. Do NOT refetch to unmask. Enrichment unmasks.
Credit gate: run `estimate-cost` (0 credits) first. If projected spend exceeds `credit_cap`, STOP and report. Do not fetch.
Build the fetch from the frozen context filter (no re-derivation). Guard: if BUYER_PROFILE is operator, ensure `new_funding_round` is NOT in events. Buyer titles from context. job_level owner-level only. company_size context bands only. events = frozen list, window = events_window_days (default 90).
```
fetch-entities(entity_type:"prospects", number_of_results:[DEMO 8 / LIVE 12],
  filters:{ job_title, job_level, company_size, company_country_code, linkedin_category,
            events:{values:[context], last_occurrence:[window]} })
```
ENRICH once: enrich-prospects-contacts. DEMO ["email"], LIVE ["email","phone"].
Post-enrich quality filter, keep a lead only if: decision-maker buyer title from context; company fits size/stage/type; if operator, revenue meets `revenue_floor` and company does NOT match `exclude_company_keywords`; signal is in-window and listed. Rank dual-signal first, then strength and recency. Keep target (DEMO 5 / LIVE 10).
If short: widen ONE filter ONCE (window 90 to 120, OR one adjacent industry, OR next size band within ceiling), refetch ONCE, enrich. Still short: deliver what qualifies, note the count. NEVER pad off-ICP. NEVER refetch more than once.
LIVE dedup: read inputs/prod/[SLUG]/dedup.json in memory, drop already-delivered LinkedIn URLs. Never pass to exclude_key. DEMO: no dedup.
URLs stored WITH https://. Masked or absent after enrich: linkedin empty (card omits Profile button). Never web-guess a URL.
On ceiling or timeout: use what enriched, filter, complete, note the count. Never retry, never thrash, never fabricate.

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
Outreach copy leads with the verified signal category. No unverified specifics as fact. connNote <=280 chars. emailSubj short. emailBody 2-3 short paragraphs, prospect voice, no pitch. Contact: DEMO empty, LIVE from enrichment. Theme cycles violet, amber, teal, blue, pink.

## STEP 5 · WRITE data.json (the only thing the model assembles)
Plain JSON, no HTML. Schema unchanged from v7 (mode, client, calendly, week, generated, leads[27 fields], dashboard{stats,sig,geo,stage,pulse}, signals[], markets{geo,ind,notes}). Operator `stage` may be revenue bands. Confirm it parses.

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
PIPELINE REPORT COMPLETE · Mode · Person · Firm · Leads N · HOT N · WARM N · Enrichment ON/OFF · web off · Credits approx N · Live URL · Deploy SUCCESS · Validation PASSED. DEMO also outputs a short DM script (no unverified specifics).

## SPEED + COST DISCIPLINE (low reasoning setting safe)
- NO web search in the default path. This is the single biggest speed and reliability lever.
- One fetch. One enrich. No autocomplete when resolved. No exploration. No template probing. One write.
- estimate-cost gate before fetch, capped by credit_cap. Enrich only survivors.
- At most one widen-and-refetch if under count. Never export. Never retry on ceiling or timeout.
- Target: 8 to 12 minutes. If you find yourself searching the web or asking a question, stop that, it is not part of this routine.

## DATA INTEGRITY (non-negotiable)
1. No fabricated data. Person and company facts from Vibe. Nothing invented. No web in the default path.
2. LinkedIn URLs Vibe-authoritative or empty. Buyer-title floor on every lead. Operator: funding excluded, revenue_floor enforced, exclude_company_keywords applied.
3. No unverified specifics as fact. No fabricated contacts (DEMO empty, LIVE waterfall).
4. No tool names or pricing in visible HTML. Zero em dashes, zero exclamation marks.
5. Model writes JSON, builder writes HTML and fails loud. One write to main (plus LIVE dedup.json). Never branch, PR, git, or archive. Never ask.
