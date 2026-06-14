---
name: pipeline-builder
version: 2.0
description: "Robust mode-aware pipeline report builder. The routine fetches real ICP-matched leads with live signals, produces ONLY a validated data.json, then runs a deterministic Python script that injects the data into the approved template. Model reasoning never assembles HTML, so escaping bugs are structurally impossible. Runs in DEMO or LIVE mode. All inputs read from GitHub."
---

# pipeline-builder v2.0
## Robust Pipeline Report Engine (data-first architecture)

**The architecture principle:** the failure mode in v1 was the model hand-writing a 60KB HTML file and mis-escaping newlines, which broke the page. v2 removes that entirely. The model produces only a small, validated JSON data object. A deterministic Python script (build_report.py) does the template injection with guaranteed-correct escaping. The model never writes HTML.

Worst case: a data issue caught by validation, never a broken page.

---

## INPUTS (passed by the routine)
- MODE: DEMO or LIVE
- SLUG: folder name, lowercase-hyphenated (e.g. dave-cotter)
- DATE: today DDMMYYYY (e.g. 14062026)
- TOKEN: GitHub token for read and deploy

---

## MODE CONFIG
| Setting | DEMO | LIVE |
|---|---|---|
| Leads | 5 | 10 |
| Vibe fetch | businesses (cheap) | prospects |
| Enrichment | OFF | ON (email+phone) |
| Email/phone on cards | hidden (no data) | shown |
| Conversion CTA + Content tab | YES | NO |
| Deploy path | demo/[DATE]/[firstname]/index.html | prod/[SLUG]/pipeline/index.html |
| Footer label | "Personalized demo for [FirstName]" | "Live pipeline · [Firm]" |
| Dedup sheet | no | yes (if SHEET_ID present) |

---

## STEP 1 · READ CONTEXT
Fetch via GitHub API (not the raw CDN, which caches):
GET /repos/pinkiousme/authority-infra/contents/inputs/[demo|prod]/[SLUG]/context.md?ref=main
Decode base64. Parse: name, firm, website, location, ICP, signals, voice, the VIBE FILTER block, and SHEET_ID (LIVE only).
If WEBSITE present, optionally web-fetch it to sharpen ICP. Do not block on failure.
If context missing, STOP and report. Never fabricate.

---

## STEP 2 · FETCH REAL LEADS (one call, credit-optimized)
Vibe Prospecting only. Never Apollo. exclude_key is TOP-LEVEL, never inside filters (inside filters causes error -32602).

Make exactly ONE fetch call. Do NOT call export. Do NOT retry on credit ceiling. Do NOT call autocomplete more than once per filter. These extra calls wasted credits in v1.

DEMO (business-level, ~3 credits):
- autocomplete linkedin_category once (industries from context)
- fetch-entities(entity_type:"businesses", number_of_results:8, filters:{ company_size:[...], company_country_code:{values:[...]}, linkedin_category:[autocompleted], events:{values:[...], last_occurrence:90} })
- Pick the 5 strongest, most recent signals. Find each founder/CEO via web research in Step 3. No enrich-prospects in DEMO.

LIVE (prospect-level + enrichment, ~8 credits):
- fetch-entities(entity_type:"prospects", number_of_results:15, filters:{ job_level:[...], company_size:[...], company_country_code:{values:[...]}, linkedin_category:[autocompleted], events:{values:[...], last_occurrence:90} })
- dedup against the Google Sheet, keep 10
- enrich-prospects-contacts on the 10 (contact_types:["email","phone"])

If credits run out mid-call: use whatever real results returned, complete with those, note the count. Never fabricate, never retry into more spend.

---

## STEP 3 · WEB RESEARCH (zero Vibe cost)
One web search per company. Extract: whatTheyDo, recentNews, founderFocus, teamTrajectory. For DEMO, also confirm the founder/CEO name and LinkedIn URL.
If a field has no reliable source, set it to "Not on record". NEVER fabricate figures, dates, or names. Prefer the company's own announcement or a reputable outlet.

---

## STEP 4 · DERIVE FIELDS (from real data only)
Per lead: signal classification (HOT 0-30d / WARM 31-90d), priority (dual-signal first, then HOT by recency; top 2 DEMO / top 3 LIVE), whyFit (match lead's real signal+stage to the prospect's real background, never invented), whyNow, connNote (<=280 chars), emailSubj, emailBody (2-3 short paragraphs, prospect voice, no pitch). Theme cycles violet, amber, teal, blue, pink.
Contact fields: DEMO sets email and phone to empty string. LIVE fills from enrichment, using "Direct contact not on record" only when truly absent.

---

## STEP 5 · WRITE data.json (the ONLY thing the model assembles)
Write a file data.json. This is plain JSON, so escaping is automatic and safe. Do NOT write any HTML.
Schema:
{
  "mode": "DEMO",
  "client": {"firstName":"", "fullName":"", "firm":""},
  "week": "Month D, YYYY",
  "generated": "Month D, YYYY",
  "leads": [ {"id":1,"theme":"violet","name":"","initials":"","role":"","company":"","country":"","stage":"","industry":"","employees":"","revenue":"","signalDetail":"","days":0,"priority":true,"linkedin":"","website":"","email":"","phone":"","whatTheyDo":"","recentNews":"","founderFocus":"","teamTrajectory":"","whyFit":"","whyNow":"","connNote":"","emailSubj":"","emailBody":""} ],
  "dashboard": {
    "stats":[{"n":"","l":"","c":"#FFA51F","chg":"","bar":"60%"}],
    "sig":[{"name":"","value":0,"color":"#FFA51F"}],
    "geo":[{"c":"","n":0}],
    "stage":[{"s":"","n":0}],
    "pulse":""
  },
  "signals":[{"name":"","count":0,"color":"#FFA51F","desc":"","leads":[""]}],
  "markets":{"geo":[{"c":"","n":0}],"ind":[{"name":"","value":0,"color":"#22C55E"}],"notes":""}
}
Put newlines in emailBody as normal text; JSON encoding handles them. Confirm the JSON parses with json.load.

Guidance for dashboard values, derived from the real leads:
- stats: 4 cards. Use real counts (funding rounds, hiring signals, HOT signals, total leads). Colors amber/green/purple/cyan.
- sig: signal-type mix for the donut, real counts.
- geo: count leads per country.
- stage: count leads per funding stage.
- pulse: 3 sentences, max 80 words, from the real signal distribution. Declarative. Third sentence ties to a content angle.
- signals: one entry per signal type present, with the real leads under each.
- markets: geo by country, ind by industry, a 2-sentence coverage note.

---

## STEP 6 · ASSEMBLE HTML DETERMINISTICALLY (no model HTML writing)
Fetch via GitHub API:
- template: assets/templates/pipeline-report/index.html
- builder: skills/build_report.py
Run in the code sandbox:
python3 build_report.py data.json template.html output.html
The builder injects everything and handles all escaping via json.dumps. The model writes NO HTML.

---

## STEP 7 · VALIDATE output.html (must pass ALL before deploy)
In the sandbox:
- Extract the script block, run node --check on it. Must be valid JS.
- Size >= 55000 bytes.
- Contains: var LEADS, function toggleLead, function render, donutSVG, areaSVG, barsSVG, all six tab labels.
- Lead count == target (5 DEMO / 10 LIVE).
- Em dash count == 0.
- No "Vibe", "Explorium", "Claude" in visible HTML. No pricing.
- Footer shows the mode-correct label, not "Test data".
If any check fails, STOP, report which failed, output data.json and output.html. Never deploy a failing file.

---

## STEP 8 · DEPLOY TO MAIN (Contents API, never a branch)
Commit directly to main. Never create a branch. Never open a PR. A branch deploy never reaches pipelind.com.
GitHub Contents API PUT:
- path: DEMO -> demo/[DATE]/[firstname]/index.html · LIVE -> prod/[SLUG]/pipeline/index.html
- branch: "main"
- committer: { name:"pinkiousme", email:"pinkious.me@gmail.com" }   (wrong email = silent Vercel deploy fail)
GET the path first for its SHA if it exists, then PUT with the SHA. Do NOT use git push (proxy blocks it). Do NOT use a branch-creating MCP tool. Contents API PUT only.
LIVE only: append the 10 delivered LinkedIn URLs to the dedup sheet.
On failure: output the HTML in chat. Never fail silently.

---

## STEP 9 · OUTPUT SUMMARY
PIPELINE REPORT COMPLETE
Mode · Person · Firm
Leads: N · HOT: N · WARM: N
Enrichment: OFF/ON
Credits used (approx): N
Live URL: https://pipelind.com/...
Deploy: SUCCESS
Validation: ALL CHECKS PASSED
DEMO also outputs a suggested DM script.

---

## DATA INTEGRITY (non-negotiable)
1. No fabricated data anywhere. Real Vibe + real web research + context only.
2. No fabricated contacts. DEMO empty. LIVE waterfall, "Direct contact not on record" when absent.
3. No invented dates/figures/names. "Not on record" instead.
4. No tool names in visible HTML. No pricing.
5. Zero em dashes, zero exclamation marks in visible copy.
6. The model writes JSON, never HTML. The builder writes HTML, never invents data.

## CREDIT DISCIPLINE
- DEMO: 1 business fetch + 1 autocomplete. ~3 credits. No export, no enrich, no retry.
- LIVE: 1 prospect fetch + 1 enrich. ~8 credits.
- Never call export. Never retry on ceiling. These caused the 18-credit overspend in v1.
