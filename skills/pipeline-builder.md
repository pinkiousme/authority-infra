---
name: pipeline-builder
version: 7.0
description: "Robust mode-aware pipeline report builder. Reads a frozen context file (schema v3), fetches real ICP-matched leads with live signals from Vibe Prospecting, applies a deterministic buyer-profile signal matrix so off-ICP companies are never fetched, produces ONLY a validated data.json, then runs build_report.py to inject the data into the approved placeholder template. Model never assembles HTML. DEMO or LIVE. Per-client in-memory dedup. Web is bounded. Credits are capped."
---

# pipeline-builder v7.0
## Robust Pipeline Report Engine (frozen filters, deterministic signals, data-first assembly)

**Integrity note (read once):** the routine that runs this skill must load it from the GitHub Contents API at a pinned commit SHA, never from the caching raw CDN on a moving branch. See the routine bootstrap block. This prevents stale or tampered instructions.

Architecture principle: the model produces only a small validated JSON object. build_report.py injects it into the approved template through explicit `__PL_*` placeholders, asserting every one is hit and failing loudly if any is missing. The model never writes HTML. Worst case is a data issue caught by validation, never a broken or wrong-data page.

Data principle: every person-level fact shown to a prospect must be Vibe-authoritative, not web-guessed. LinkedIn URLs, names, titles, and contact come from the Vibe PROSPECT fetch. Web is used only for company-level context and the market pulse, bounded, and figures are treated as soft.

Selection principle (new in v7): which signals and filters to use is decided at context-build time and frozen into the context file. The routine derives nothing. It reads the frozen filter and the two selection flags, applies the matrix below as a guard, and fetches.

---

## INPUTS (from the routine)
- MODE: DEMO or LIVE
- SLUG: folder name, lowercase-hyphenated (e.g. tamar-goltz)
- DATE: today DDMMYYYY
- TOKEN: GitHub token

---

## SELECTION MODEL (new in v7)
Every context file carries two flags. Neither is decided at run time.
- `BUYER_PROFILE`: `venture` or `operator`. Controls whether funding counts as a signal, the revenue floor, and category discipline.
- `ADVISOR_FUNCTION`: `finance` or `operations` (CFO maps to finance, COO maps to operations). Controls which department's hiring and leadership signals are read.

The context-builder has already written the final frozen `events` list into the context using the matrix below. The routine applies the matrix only as a guard (defense in depth), it does not re-derive the list.

## SIGNAL MATRIX (hard-coded, deterministic)

### buyer_profile = venture
Buyers are funded, scaling companies. Funding is a real buy signal.
- Events included: `new_funding_round` (primary), `leadership_change` in the advisor function, `hiring_in_[finance|operations]_department` per ADVISOR_FUNCTION.
- Revenue floor: none.
- Category discipline: tech categories are fine.

### buyer_profile = operator
Buyers are established, profitable, owner-run operating companies. Funding means a cash-burning startup, the wrong buyer.
- Events included: `merger_and_acquisitions` (primary), `leadership_change` in the advisor function, `hiring_in_[finance|operations]_department` per ADVISOR_FUNCTION, `office_expansion`.
- Events excluded, HARD RULE: `new_funding_round` is never in an operator events list. GUARD: if the context events list contains `new_funding_round` while BUYER_PROFILE is operator, drop it before fetching and note the correction.
- Revenue floor: required, from context `revenue_floor` (default $5M).
- Category discipline two layers: (1) prefer operator industry categories (and NAICS/SIC codes if available); (2) apply the context `exclude_company_keywords` discard list (default AI, robotics, SaaS, platform, marketplace, -tech) in the post-enrich filter.

### advisor_function overlay
- `finance`: hiring_in_finance_department, leadership_change finance.
- `operations`: hiring_in_operations_department, leadership_change operations, office_expansion weighted up.

Event identifiers are validated against Vibe's available events once at context-build time and frozen. Do not autocomplete events at run time if `autocomplete_resolved: true`.

---

## MODE CONFIG
| Setting | DEMO | LIVE |
|---|---|---|
| Leads | 5 | 10 |
| Vibe fetch | prospects (tight buyer-title filter) | prospects |
| Enrichment | YES, email only (to UNMASK identity + LinkedIn URL) | YES, email + phone |
| Email/phone on cards | hidden (fetched, not displayed) | shown |
| Conversion CTAs | YES (MODE-driven in template) | NO |
| Deploy path | demo/[DATE]/[firstname]/index.html | prod/[SLUG]/pipeline/index.html |
| Dedup | no | yes (GitHub dedup file) |

---

## STEP 1 · READ CONTEXT (frozen, no derivation)
GitHub API (not raw CDN, it caches):
GET /repos/pinkiousme/authority-infra/contents/inputs/[demo|prod]/[SLUG]/context.md?ref=main
Decode base64. Parse, in addition to name/firm/website/location/ICP/voice:
- `BUYER_PROFILE`, `ADVISOR_FUNCTION`
- the FROZEN VIBE FILTER block: job_title, job_level, company_size, company_country_code, linkedin_category, revenue_floor, events, events_window_days, exclude_company_keywords, autocomplete_resolved
- the RUN CONTROL block: credit_cap, web_mode, deploy_path

If `autocomplete_resolved: true`, treat job_title, linkedin_category, and events as final. Do NOT autocomplete, do NOT re-derive. The only permitted widen is the single signal-window widen in Step 2.
Missing context: STOP. Never fabricate.

---

## STEP 2 · FETCH REAL LEADS (frozen filter, buyer-title enforced)
Vibe Prospecting only. Never Apollo. Never use exclude_key (dedup is in-memory).

**Masking reality (read first, prevents the failure mode).** A fetch returns a small (~5 row) PREVIEW that is MASKED until you ENRICH. Therefore:
- Do NOT fetch a large loose set hoping to filter it down. The preview is masked and small.
- Do NOT call export to see more rows. Forbidden (costs credits, needs auth).
- Do NOT refetch on masked data. Masking is resolved by enrichment, not refetching. (This caused a 25-minute, 55-credit failed run.)
- Pattern: fetch a TIGHT well-filtered small set, then ENRICH to unmask.

**Credit gate (new in v7).** Before fetching, run `estimate-cost` (0 credits). If projected spend exceeds `credit_cap`, STOP and report. Do not fetch.

**Build the fetch from the frozen context filter.** Do not re-derive. Apply the matrix guard:
- If BUYER_PROFILE is operator, ensure `new_funding_round` is NOT in events. Drop it if present, note the correction.
- Buyer titles from context `job_title`. `job_level` only owner-level decision-makers (founder, owner, president); never bare c-suite unless the context says the prospect sells to that function.
- `company_size` only the context bands, never above the ceiling.
- `events` = frozen list, `last_occurrence`: events_window_days (default 90).

```
fetch-entities(
  entity_type:"prospects",
  number_of_results:[DEMO 8 / LIVE 12],
  filters:{ job_title:[context], job_level:[context], company_size:[context],
            company_country_code:{values:[context]}, linkedin_category:[context],
            events:{values:[context events], last_occurrence:[window]} }
)
```

**ENRICH to unmask (both modes).** enrich-prospects-contacts on the returned leads.
- DEMO: contact_types ["email"] (unmasks identity + LinkedIn URL; email retrieved, not displayed).
- LIVE: contact_types ["email","phone"]. Waterfall: work email > personal > "". Phone where present else "Direct contact not on record".

**Post-enrich quality filter (now data is visible). KEEP a lead only if ALL hold:**
- Title is a decision-maker buyer title from the context. DISCARD CFO, COO, CMO, CPO, General Counsel, VP-functional unless the context names them as buyers.
- Company profile fits: size within ceiling, right stage, right type.
- If BUYER_PROFILE is operator: revenue meets `revenue_floor`, and the company does NOT match any `exclude_company_keywords` (drop venture-tech that slipped through a keyword category).
- Signal is within the window and is one the context lists.
Rank survivors: dual-signal first, then signal strength and recency. Keep target count (DEMO 5 / LIVE 10).

**If fewer than target qualify:** widen ONE filter ONCE (signal window 90 to 120 days, OR one adjacent industry, OR the next size band still within the ICP ceiling) and refetch ONCE, then enrich. If still short, deliver what qualifies and note the count. NEVER pad with off-ICP leads. NEVER refetch more than once for count reasons.

- LIVE dedup: after enrich, read inputs/prod/[SLUG]/dedup.json (in memory), discard any lead whose LinkedIn URL is already listed, keep freshest up to 10. Never pass to exclude_key.
- DEMO: no dedup.

Store URLs (linkedin, website) WITH https://. If still masked or absent after enrichment, set linkedin to empty (card omits the Profile button). NEVER web-guess a LinkedIn URL.

If credits exhaust mid-run: use what enriched, apply the filter, complete, note the count. Never fabricate, never thrash, never retry on a ceiling or timeout.

---

## STEP 3 · COMPANY CONTEXT + PULSE (bounded web, new in v7)
Driven by context `web_mode`. Default `pulse_only`.
- `off`: no web calls. Company-context fields set "Not on record". Cards still render.
- `pulse_only` (DEFAULT): ONE batched web search per run for the market-pulse panel only. Hard timeout 20s. On timeout or failure, SKIP and compute the pulse from the fetched leads (e.g. "7 of 10 hiring in operations in the last 60 days"). Never blocks the report. No per-company search in this mode.
- `per_company`: opt-in, LIVE only, after the pipeline is proven stable. One search per company, hard per-call timeout, skip-on-fail, cached by company. Identity and LinkedIn still come from Vibe.

Rules for any web data: company-level only, never to determine identity or LinkedIn. No reliable source means "Not on record". Treat specific figures as SOFT.

---

## STEP 4 · DERIVE FIELDS (from real data only)
Per lead: signalDetail (Vibe-verified signal category, soft timeframe only if confident), HOT (0-30d) / WARM (31-90d), priority (dual-signal first then HOT by recency; top 2 DEMO / top 3 LIVE).
whyFit: match the lead's verified signal and stage to the prospect's real background. Derived, never invented. If a lead only weakly fits, write an honest grounded whyFit, never oversell.
whyNow: the signal and timing, prospect voice.
Signal-to-ICP weighting: rank the context's most-aligned signals higher among survivors.
Outreach copy: lead with the verified signal category. No unverified specifics (amounts, exact dates) as fact. connNote <=280 chars. emailSubj short. emailBody 2-3 short paragraphs, prospect voice, no pitch, no unverified claim. A soft accurate reference beats a precise wrong one.
Contact: DEMO email="" phone="". LIVE from enrichment.
Theme cycles violet, amber, teal, blue, pink.

---

## STEP 5 · WRITE data.json (the ONLY thing the model assembles)
Plain JSON, escaping automatic. No HTML. Schema (unchanged from v6):
```
{ "mode":"DEMO|LIVE",
  "client":{"firstName":"","fullName":"","firm":""},
  "calendly":"https://calendly.com/saurabh_zentro/30-min",
  "week":"Month D, YYYY","generated":"Month D, YYYY",
  "leads":[{"id":1,"theme":"violet","name":"","initials":"","role":"","company":"","country":"","stage":"","industry":"","employees":"","revenue":"","signalDetail":"","days":0,"priority":true,"linkedin":"","website":"","email":"","phone":"","whatTheyDo":"","recentNews":"","founderFocus":"","teamTrajectory":"","whyFit":"","whyNow":"","connNote":"","emailSubj":"","emailBody":""}],
  "dashboard":{"stats":[{"n":"","l":"","c":"#FFA51F","chg":"","bar":"60%"}],"sig":[{"name":"","value":0,"color":"#FFA51F"}],"geo":[{"c":"","n":0}],"stage":[{"s":"","n":0}],"pulse":""},
  "signals":[{"name":"","count":0,"color":"#FFA51F","desc":"","leads":[""]}],
  "markets":{"geo":[{"c":"","n":0}],"ind":[{"name":"","value":0,"color":"#22C55E"}],"notes":""}
}
```
Dashboard values derived from the real leads. `stage` may carry revenue or maturity bands for operator profiles (e.g. "$5-10M") instead of funding stages. Confirm json.load parses it.

---

## STEP 6 · ASSEMBLE DETERMINISTICALLY (no model HTML)
Fetch via GitHub API: assets/templates/pipeline-report/index.html and skills/build_report.py.
Run: `python3 build_report.py data.json template.html output.html`
The builder injects all data through explicit `__PL_*` placeholders with correct escaping, strips the test banner, sets the footer per mode. The model writes NO HTML.
**The builder fails loud.** If a placeholder is missing, a placeholder survives, the lead count does not match, a seed identifier leaks, the script is invalid JS, an em dash or tool name appears, or the file is too small, it RAISES and writes nothing. If build_report.py errors: read the error, fix the named data.json field, re-run. Do NOT deploy.

---

## STEP 7 · VALIDATE (confirm, builder already self-checked)
- output.html exists and is >= 50000 bytes (if the builder raised, it will not exist: STOP).
- node --check the extracted script once more.
- Lead count == target (or the noted lower count).
- Spot-check: pulse renders, LinkedIn URLs present, no `__PL_` token remains.
If anything fails: STOP, report which, output data.json + the builder error. Never deploy a failing file.

---

## STEP 8 · DEPLOY (Contents API to main ONLY)
**ONE-WRITE rule.** Exactly ONE write: the report file, via Contents API, to main. Then STOP.
- No branch, no PR, no git push/commit/any git command (proxy blocks git, creates phantom branches).
- No archiving or backing up data.json, output.html, template, or builder anywhere in the repo. Working scratch only.
PUT (the only write):
- path: DEMO demo/[DATE]/[firstname]/index.html · LIVE prod/[SLUG]/pipeline/index.html
- branch:"main", committer AND author {name:"pinkiousme", email:"pinkious.me@gmail.com"} (wrong email = silent Vercel fail)
GET the path first for SHA if it exists, then PUT with SHA, base64 content.

LIVE dedup is the ONLY exception to one-write (after successful deploy):
- Read inputs/prod/[SLUG]/dedup.json (array of delivered LinkedIn URLs; missing = []).
- Append this week's delivered URLs, dedupe the array, PUT it back (committer email pinkious.me@gmail.com).
- NEVER pass this list to Vibe exclude_key.
DEMO: no dedup write, no other write at all.
On failure: output the HTML in chat. Never fail silently.

---

## STEP 9 · OUTPUT SUMMARY
PIPELINE REPORT COMPLETE · Mode · Person · Firm
Leads: N · HOT: N · WARM: N · Enrichment ON/OFF · web_mode · Credits used (approx): N
Live URL: https://pipelind.com/... · Deploy: SUCCESS · Validation: ALL CHECKS PASSED
DEMO also outputs a suggested DM script (no unverified specifics).

---

## SPEED + CREDIT DISCIPLINE
- One Vibe fetch. No autocomplete at run time when autocomplete_resolved. web_mode pulse_only by default (one bounded search, not per company).
- estimate-cost gate before fetch, capped by credit_cap. Enrich only quality-filter survivors, never rejects.
- DEMO: 1 tight fetch (8) + 1 enrichment (email). LIVE: 1 tight fetch (12) + 1 enrichment (email + phone).
- At most ONE widen-and-refetch if under count. NEVER call export. NEVER refetch to unmask. NEVER retry on ceiling or timeout.
- Do NOT probe the template (the builder handles injection). Fetch template, run builder, validate, deploy.
- Target: 10-15 minutes.

## DATA INTEGRITY (non-negotiable)
1. No fabricated data. Person data from Vibe, company context from web, nothing invented.
2. LinkedIn URLs: Vibe-authoritative or empty. Never web-guessed.
2a. Buyer-title floor: every delivered lead holds a decision-maker buyer title from the context.
2b. Operator profile: funding rounds excluded, revenue_floor enforced, exclude_company_keywords applied.
3. No unverified specifics asserted as fact in outreach copy. Soft references only.
4. No fabricated contacts. DEMO empty. LIVE waterfall.
5. No tool names in visible HTML. No pricing.
6. Zero em dashes, zero exclamation marks in visible copy.
7. Model writes JSON, never HTML. Builder writes HTML, never invents data, fails loud on any fault.
8. One write to GitHub: the report file (plus LIVE dedup.json). Never archive, never branch, never PR, never git.
