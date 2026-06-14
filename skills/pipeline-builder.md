---
name: pipeline-builder
version: 1.0
description: "Mode-aware pipeline report builder. Runs in DEMO or LIVE mode from a single GitHub-hosted context file. Fetches real ICP-matched leads with live signals from Vibe Prospecting, injects them into the approved HTML template, and deploys to the correct path. Designed to run inside a Claude Code Routine (scheduled or manual one-time). All inputs read from GitHub, never from Claude Project knowledge base or chat attachments."
---

# pipeline-builder · v1.0
## Mode-Aware Pipeline Report Engine

This skill builds the weekly pipeline report. It runs identically whether triggered manually (DEMO, on a prospect comment) or on a schedule (LIVE, weekly for a client). The only difference is the MODE keyword passed by the routine.

ALL inputs are read from GitHub. This skill never relies on Claude Project knowledge base files or chat attachments, because routines cannot access those.

---

## INPUTS (passed by the routine)

The routine provides four values:
- `MODE`: either `DEMO` or `LIVE`
- `SLUG`: the person's folder name, lowercase-hyphenated (e.g. `dave-cotter`)
- `DATE`: today's date in DDMMYYYY format (e.g. `14062026`)
- `TOKEN`: the GitHub token for read and deploy

---

## MODE CONFIGURATION

Read MODE first. It controls every branch below.

| Setting | DEMO | LIVE |
|---|---|---|
| Lead count | 5 | 10 |
| Vibe enrichment (contacts) | OFF | ON |
| Email + phone on cards | NO (LinkedIn + website only) | YES |
| Conversion CTA + Content tab | YES | NO |
| Deploy path | `demo/[DATE]/[firstname]/index.html` | `prod/[SLUG]/pipeline/index.html` |
| Dedup against sheet | NO | YES (if SHEET_ID in context) |
| Live URL | `pipelind.com/demo/[DATE]/[firstname]` | `pipelind.com/prod/[SLUG]/pipeline` |

`[firstname]` = the lowercase first name from the context file (e.g. `dave`).

---

## STEP 1 · READ THE CONTEXT FILE

Fetch from GitHub raw:
```
https://raw.githubusercontent.com/pinkiousme/authority-infra/main/inputs/[MODE_LOWER]/[SLUG]/context.md
```
where `MODE_LOWER` is `demo` or `prod`.

Use the TOKEN in the Authorization header if the raw URL requires it.

Parse from the context file:
- PROSPECT_FIRST_NAME, PROSPECT_FULL_NAME, TITLE, FIRM, WEBSITE, LOCATION, LINKEDIN
- The prospect's ICP (buyer titles, stage, size, industries, geography)
- The buying signals that indicate active need
- The voice rules for outreach copy
- The VIBE FILTER DERIVATION block (job_level, company_size, country, linkedin_category, events)
- SHEET_ID (LIVE mode only, if present, for dedup)

If WEBSITE is present, optionally web-fetch it to sharpen ICP understanding. Zero Vibe cost. Do not block the build if the site is unreachable.

If the context file cannot be read, STOP and report the error. Never fabricate context.

---

## STEP 2 · FETCH REAL LEADS (Vibe Prospecting only)

Use Vibe Prospecting MCP. Never Apollo.io.

**CRITICAL · exclude_key placement:** `exclude_key` is a TOP-LEVEL parameter of fetch-entities, never inside `filters`. Placing it inside filters causes error -32602.

### 2A · Autocomplete first
Run autocomplete on `linkedin_category` using the industry terms from the context file (e.g. "healthtech saas software b2b"). Use the standardized values returned.

### 2B · Fetch

**DEMO mode (credit-efficient, intentional):**
Fetch BUSINESSES with the events filter (events are business-level), then identify the founder/CEO of each via web research in Step 3. This is the intended DEMO path: it uses one business-level fetch and avoids prospect-level credit draw.
```
fetch-entities(
  entity_type: "businesses",
  number_of_results: 8,
  filters: {
    company_size: [from context],
    company_country_code: { values: [from context] },
    linkedin_category: [autocomplete results],
    events: { values: [from context], last_occurrence: 90 }
  }
)
```
Pick the 5 businesses with the strongest, most recent signals. The founder/CEO name comes from web research in Step 3. Do NOT call enrich-prospects in DEMO mode.

**LIVE mode (full prospect fetch + enrichment):**
```
fetch-entities(
  entity_type: "prospects",
  number_of_results: 15,
  filters: {
    job_level: [from context VIBE FILTER block],
    company_size: [from context],
    company_country_code: { values: [from context] },
    linkedin_category: [autocomplete results],
    events: { values: [from context], last_occurrence: 90 }
  }
)
```
For LIVE dedup: read the Google Sheet (SHEET_ID, tab from context), collect delivered LinkedIn URLs, discard any returned lead already in the sheet.

Keep exactly the target count (DEMO: 5 · LIVE: 10) of clean leads. A clean lead has a real name, real company, and at least one active signal in the last 90 days. Discard borderline or unnamed entries.

**If Vibe credits are exhausted mid-run:** stop fetching, use whatever real businesses/prospects were already returned, and complete the build with those plus web research. Note the actual count in the output. Never fabricate leads to reach the target. A real partial build beats a padded full one.

**Under-count fallback:** if fewer than target return after filtering, widen one filter once (signal window to 120 days OR one adjacent industry) and re-fetch only if credits allow.

### 2C · Enrichment (LIVE mode only)
```
enrich-prospects-contacts on all leads
parameters: { contact_types: ["email", "phone"] }
```
DEMO mode: SKIP this entirely. Saves credits. Cards show LinkedIn + website only.

Contact display waterfall (LIVE):
1. Work email present → primary
2. No work email, personal present → personal
3. Neither → "Direct contact not on record"
4. Phone present → show alongside; absent → "Direct contact not on record"

---

## STEP 3 · WEB RESEARCH (Company Intelligence · zero Vibe cost)

For each lead, run ONE web search on the company name. Extract four fields:
- What They Do: one-sentence product/service description
- Recent News: most recent headline or event (funding, launch, hire, partnership)
- Founder Focus: what the founder/exec is publicly discussing (from a recent post, article, or interview)
- Team Trajectory: growth direction (growing, stable, restructuring)

If a search returns nothing usable for a field, write "Not on record" rather than guessing. NEVER fabricate.

---

## STEP 4 · DERIVE PER-LEAD FIELDS

For each lead, generate from real data only:

**Signal classification:** HOT (signal 0-30 days) or WARM (31-90 days).

**Priority ranking:** dual signals first (two active signals same window), then HOT by recency. Top 2 (DEMO) or top 3 (LIVE) get the Priority badge.

**Why this fits [FirstName]:** match the lead's real signal and stage against the prospect's real background from the context file. Derived from two real inputs, never invented. Reference the prospect's specific experience where it genuinely overlaps.

**Why Now:** one paragraph on the signal and timing, in the prospect's diagnostic voice.

**Connection note:** max 280 characters, references the specific signal, no pitch, prospect's voice.

**Email draft:** subject line + 2-3 short paragraphs. Acknowledge the signal, name the pattern the prospect sees at this stage, soft open. No Calendly link inside the email. High-converting: specific, observed, non-salesy (per the constraint-setting principle: avoid language that trips the "I want your money" filter).

**Market Intelligence Pulse:** 3 sentences, max 80 words, counted from the actual signal distribution in the fetched pool. Declarative. No em dashes, no exclamation marks. Third sentence ties to a content angle.

---

## STEP 5 · BUILD HTML BY MECHANICAL INJECTION (NOT GENERATION)

**ABSOLUTE RULE: You must NOT write HTML from scratch. You must NOT design, restructure, or simplify anything. The approved template is the ONLY allowed output structure. Your job is mechanical find-and-replace on the template string, nothing more. If you generate your own HTML, the build is WRONG and must be discarded.**

### 5.1 · Fetch the template verbatim
```
https://raw.githubusercontent.com/pinkiousme/authority-infra/main/assets/templates/pipeline-report/index.html
```
Hold this entire file as a string. It is ~58KB and contains a sidebar, six tabs (Pipeline, Dashboard, Signals, Markets, Content, Settings), glassmorphism cards, SVG charts (donutSVG, areaSVG, barsSVG), and expandable lead cards with a toggleLead function. ALL of this must survive into the output unchanged. If your output is smaller than ~50KB or is missing the sidebar, tabs, charts, or toggleLead function, you have made an error: start over from the fetched template.

### 5.2 · Replace ONLY these specific tokens in the template string

**a) The LEADS array.** Find the exact block that starts with `var LEADS = [` and ends with the matching `\n];`. Replace ONLY that block with a new `var LEADS = [...]` containing the real leads. Every lead object must keep all 27 fields: id, theme, name, initials, role, company, country, stage, industry, employees, revenue, signalDetail, days, priority, linkedin, website, email, phone, whatTheyDo, recentNews, founderFocus, teamTrajectory, whyFit, whyNow, connNote, emailSubj, emailBody.
- theme: cycle violet, amber, teal, blue, pink
- **NEWLINE ESCAPING (critical):** inside any string value, write newlines as the two literal characters backslash + n. NEVER put a real line break inside a double-quoted JS string. This is the single most common cause of a broken build. After replacement, mentally parse the array to confirm no real newline sits inside any quoted value.

**b) Dashboard data variables.** Inside viewDashboard, replace the `var stats=[...]`, `var sig=[...]`, `var geo=[...]`, `var stage=[...]` lines with values matching the real leads. Same for the Market Pulse text string and the viewSignals `var types=[...]` and viewMarkets `var geo`/`var ind`. Replace values only; keep the variable names and structure identical.

**c) Header text.** Replace the client name "Dave Cotter" and "Kelsor Ventures" placeholder strings with the real prospect name and firm. Replace the week date.

**d) Logo.** In the sidebar brand area, ensure the logo block is:
```html
<img src="https://raw.githubusercontent.com/pinkiousme/authority-infra/main/assets/pipelind-logo-dark.png" alt="Pipelind" style="height:20px;width:auto" onerror="this.style.display='none';this.nextElementSibling.style.display='inline'"><span class="sb-wordmark" style="display:none">Pipelind</span>
```

**e) Test banner.** Delete the line containing "Test run · Synthetic data". That is the only deletion.

**f) Mode-specific:**
- DEMO: keep the Content tab and conversion CTA exactly as in the template. In each lead card, the email and phone action buttons and contact strip should be hidden (DEMO has no enrichment), leaving LinkedIn + Website. The outreach arsenal (connection note + email draft) stays.
- LIVE: in viewContent, the CTA stays minimal or is removed; show email + phone on cards.

### 5.3 · Do not touch anything else
Every CSS rule, every SVG icon, every function (toggleLead, cp, render, donutSVG, areaSVG, barsSVG), the sidebar, the six-tab router, the responsive media queries: all unchanged. You are editing data, not design.

---

## STEP 6 · VALIDATE BEFORE DEPLOY

Confirm ALL of these. If any fail, fix and re-check. Never deploy a file that fails:
- Output size is ~55KB or larger (if much smaller, the template was not used, restart from 5.1)
- Contains `var LEADS`, `function toggleLead`, `function render`, `donutSVG`, the sidebar (`sb-item`), and all six tab names
- The script block parses as valid JavaScript (no unescaped newline or quote inside LEADS)
- Lead count matches target (5 DEMO / 10 LIVE)
- ZERO em dashes anywhere (search the whole file for the em-dash character and remove every one)
- Zero exclamation marks in visible copy
- No tool names (Vibe, Explorium, Claude, GitHub) in visible HTML
- No pricing anywhere
- Logo block present with fallback
- Test banner removed
- Every lead has a real name, company, and at least one signal

---

## STEP 7 · DEPLOY TO MAIN BRANCH (NEVER A FEATURE BRANCH)

**ABSOLUTE RULE: commit directly to the `main` branch. Do NOT create a new branch. Do NOT open a pull request. The report must land on main so Vercel deploys it to pipelind.com. If you push to any branch other than main, the deploy fails to reach the live domain.**

Use the GitHub Contents API (PUT to /contents/[path]) which commits directly to main:
```
Repo: pinkiousme/authority-infra
Branch: main   ← MANDATORY
DEMO path: demo/[DATE]/[firstname]/index.html
LIVE path: prod/[SLUG]/pipeline/index.html
Commit message: "[MODE] pipeline report · [FirstName] · [DATE]"
Committer name: pinkiousme
Committer email: pinkious.me@gmail.com   ← MANDATORY (wrong email causes silent Vercel deploy failure)
```
Method: GET the file at the path on main to retrieve its SHA if it exists, then PUT with `branch: "main"`, the base64 content, the SHA (if updating), and the committer block above. The Contents API commits straight to main with no branch and no PR.

Do NOT use `git push` (the proxy blocks it). Do NOT use a GitHub MCP tool that creates branches. Use the Contents API PUT only.

On deploy success, the live URL is:
- DEMO: https://pipelind.com/demo/[DATE]/[firstname]
- LIVE: https://pipelind.com/prod/[SLUG]/pipeline

On deploy failure: output the full HTML in chat. Never fail silently.

Use the GitHub Contents API. If the file exists at the path, GET its SHA first, then PUT with the SHA to update. Base64-encode the HTML. Set committer email pinkious.me@gmail.com.

Vercel auto-deploys on push. Live within 60-90 seconds.

On deploy failure: output the full HTML in chat as a downloadable artifact. Never fail silently.

---

## STEP 8 · OUTPUT SUMMARY

After deploy, output in chat:
```
PIPELINE REPORT COMPLETE
Mode: [DEMO / LIVE]
Person: [Full Name] · [Firm]
Leads: [N] · HOT: [N] · WARM: [N]
Enrichment: [OFF / ON]
Live URL: [full URL]
Deploy: [SUCCESS / FAILED]

[DEMO only] Suggested DM script:
Hey [FirstName], thanks for the LEAD comment. Built you a sample report based on your profile. [N] ICP-matched buyers, each with an active market signal from the last 90 days. Ready-to-send outreach on every card. Link: [URL]. This is what one week of the full system looks like.
```

---

## DATA INTEGRITY RULES (non-negotiable)

1. No fabricated data. Every point comes from the Vibe pull, web search, or the context file.
2. No fabricated contact details. Follow the waterfall. "Direct contact not on record" is the correct fallback.
3. No invented signal timing. "Approximately [N] days ago" when the exact date is not confirmed.
4. No invented company metrics. Omit a field rather than guess.
5. No fabricated LinkedIn URLs. ACoA URLs get the "may require login" title. Never construct a clean URL that does not resolve.
6. No tool names in visible HTML.
7. No pricing in any visible output.
8. Zero em dashes. Zero exclamation marks in visible copy.

---

## CREDIT REFERENCE

- DEMO: 1 fetch-entities call (~3 credits). No enrichment.
- LIVE: 1 fetch-entities call + 1 enrich-prospects-contacts (~8 credits total).
- Web search: 0 Vibe credits.
- Quality floor: every build uses real live-signal leads from one real Vibe fetch. Never compromised.
