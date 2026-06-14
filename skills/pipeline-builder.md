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

**CRITICAL — exclude_key placement:** `exclude_key` is a TOP-LEVEL parameter of fetch-entities, never inside `filters`. Placing it inside filters causes error -32602.

### 2A · Autocomplete first
Run autocomplete on `linkedin_category` using the industry terms from the context file (e.g. "healthtech saas software b2b"). Use the standardized values returned.

### 2B · Fetch
```
fetch-entities(
  entity_type: "prospects",
  number_of_results: [DEMO: 8 · LIVE: 15],   ← over-fetch to guarantee clean count after filtering
  filters: {
    job_level: [from context VIBE FILTER block],
    company_size: [from context],
    company_country_code: { values: [from context] },
    linkedin_category: [autocomplete results],
    events: {
      values: [from context, e.g. "new_funding_round", "hiring_in_finance_department", "hiring_in_operations_department"],
      last_occurrence: 90
    }
  }
)
```

For LIVE mode with dedup: read the Google Sheet (SHEET_ID, tab from context), collect delivered LinkedIn URLs, and discard any returned lead already in the sheet.

Keep exactly the target count (DEMO: 5 · LIVE: 10) of clean leads. A clean lead has: a real name, a real title, a real company, and at least one active signal in the last 90 days. Discard borderline or unnamed entries.

**Under-count fallback:** if fewer than the target return after filtering, widen one filter once (extend signal window to 120 days OR add one adjacent industry) and re-fetch. If still short, deliver what exists and note the count in the report header.

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

## STEP 5 · BUILD HTML FROM TEMPLATE

Fetch the approved template:
```
https://raw.githubusercontent.com/pinkiousme/authority-infra/main/assets/templates/pipeline-report/index.html
```

The template is plain HTML/CSS/SVG/vanilla-JS. Replace the data layer only. Do NOT regenerate the design.

### Data injection
Locate `var LEADS = [ ... ];` in the template script and replace with the real leads array. Each lead object needs every field: id, theme, name, initials, role, company, country, stage, industry, employees, revenue, signalDetail, days, priority, linkedin, website, email, phone, whatTheyDo, recentNews, founderFocus, teamTrajectory, whyFit, whyNow, connNote, emailSubj, emailBody.

**Theme assignment:** cycle violet, amber, teal, blue, pink across the leads for visual variety.

**CRITICAL — escape newlines:** inside the LEADS array, any real newline in a string value (especially emailBody) MUST be written as the two characters backslash-n, not an actual line break. An actual line break inside a JS double-quoted string breaks the entire script. Validate the script parses before deploying.

Also update: the signal summary stat numbers, the signal mix donut data, the geographic bar data, the funding stage bar data, the Signals view type counts and lead lists, the Markets view data, and the Market Intelligence Pulse text — all to reflect the real leads.

### Header personalization
- Topbar / sidebar: prospect full name + firm
- Sidebar logo: use the Pipelind logo image with text fallback (see LOGO block below)
- Page title and week label: current date

### MODE-specific HTML
- DEMO: keep the Content Engine tab and the conversion CTA. Show "Personalized For [FirstName] · Lead Demo" framing. Remove email/phone from cards and the contact strip (show only LinkedIn + website buttons). Card outreach still shows connection note + email draft (the email body is the value, even without the prospect's contact enriched).
- LIVE: remove the conversion CTA and the Content Engine upsell. Show email + phone on cards. Add the "Updated [date]" freshness framing.

### LOGO block (safe, with fallback)
In the sidebar brand area, use:
```html
<img src="https://raw.githubusercontent.com/pinkiousme/authority-infra/main/assets/pipelind-logo-dark.png"
     alt="Pipelind" style="height:22px;width:auto"
     onerror="this.style.display='none';this.nextElementSibling.style.display='inline'">
<span class="sb-wordmark" style="display:none">Pipelind</span>
```
This shows the logo image; if it ever fails to load, the text wordmark appears automatically. Cannot break the build.

### Remove test banner
The template carries a "Test run · Synthetic data" banner. REMOVE it for both DEMO and LIVE real builds. This is real data.

---

## STEP 6 · VALIDATE BEFORE DEPLOY

Before pushing, confirm:
- The script parses as valid JavaScript (no unescaped newlines or quotes in LEADS)
- Lead count matches target (5 DEMO / 10 LIVE)
- Zero em dashes anywhere
- Zero exclamation marks in visible copy
- No tool names (Vibe Prospecting, Explorium, Claude, GitHub) in visible HTML
- No pricing anywhere
- LinkedIn ACoA URLs rendered as-is with "may require login" title, never reconstructed
- Every lead has a real name, company, and at least one signal
- DEMO: no email/phone shown · LIVE: email shown, phone where available

If validation fails, fix and re-validate. Never deploy a broken file.

---

## STEP 7 · DEPLOY TO VERCEL VIA GITHUB

```
Repo: pinkiousme/authority-infra · Branch: main
DEMO path: demo/[DATE]/[firstname]/index.html
LIVE path: prod/[SLUG]/pipeline/index.html
Commit: "[MODE] pipeline report · [FirstName] · [DATE]"
```

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
