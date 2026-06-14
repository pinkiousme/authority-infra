# Phase 2 · Pipeline Builder · Routine Instructions and Run Guide

The complete system runs from GitHub. One skill, two modes. Demo runs manually on demand. Live runs on a weekly schedule. Same engine.

---

## WHAT LIVES IN GITHUB (single source of truth)

```
authority-infra/
├── assets/
│   ├── templates/pipeline-report/index.html   ← approved template
│   └── pipelind-logo-dark.png                  ← logo (used in reports)
├── skills/
│   └── pipeline-builder.md                     ← the mode-aware skill
├── inputs/
│   ├── demo/[firstname-lastname]/context.md    ← prospect context (DEMO)
│   └── prod/[clientname]/context.md            ← client context (LIVE)
├── demo/[DDMMYYYY]/[firstname]/index.html       ← deployed demo reports
└── prod/[clientname]/pipeline/index.html        ← deployed live reports
```

---

## THE DEMO WORKFLOW (manual, on prospect comment)

When a prospect comments LEAD:

### Step 1 · Build their context file (one quick step)
Open a normal Claude chat. Attach their LinkedIn profile PDF. Say:
"Build a context.md for this prospect using the pipeline-builder format. Extract name, title, firm, website, location, their ICP, buying signals, voice rules, and Vibe filter derivation."

Claude returns a context.md. (This replaces the unreliable PDF-in-routine approach. A text file is tiny, always readable, never breaks.)

### Step 2 · Push the context file to GitHub
Put it at: `inputs/demo/[firstname-lastname]/context.md`
(e.g. `inputs/demo/dave-cotter/context.md`)
Drag-drop into the GitHub web UI, or ask Claude in that same chat to push it via the API.

### Step 3 · Run the DEMO routine
Go to claude.ai/code/routines. Use the saved "Pipeline Builder DEMO" routine (set up once, see below). Update the SLUG and DATE values, then click Run now.

### Step 4 · Send the DM
The routine outputs the live URL and a suggested DM script. Report goes live at:
`pipelind.com/demo/[DDMMYYYY]/[firstname]`
Copy the URL into your DM. Done.

End-to-end: about 5 minutes of your time.

---

## DEMO ROUTINE PROMPT (paste into claude.ai/code/routines)

Routine name: Pipeline Builder DEMO

```
Run the pipeline-builder skill in DEMO mode.

Read the skill from:
https://raw.githubusercontent.com/pinkiousme/authority-infra/main/skills/pipeline-builder.md

INPUTS:
MODE: DEMO
SLUG: dave-cotter
DATE: 14062026
TOKEN: PASTE_GITHUB_TOKEN_HERE

Follow the skill exactly:
1. Read the context file from inputs/demo/[SLUG]/context.md
2. Fetch 5 real ICP-matched leads from Vibe Prospecting with live signals (last 90 days). No enrichment in DEMO mode.
3. Run one web search per lead for company intelligence.
4. Derive signal classification, priority ranking, why-fit, why-now, connection notes, email drafts, and the market pulse from real data only.
5. Fetch the approved template, inject the real leads, remove the test banner, keep the conversion CTA and Content tab (DEMO mode), show LinkedIn + website only (no email/phone in DEMO).
6. Validate the script parses and there are zero em dashes and zero exclamation marks.
7. Deploy to demo/[DATE]/[firstname]/index.html in pinkiousme/authority-infra via the GitHub Contents API.
8. Output the live URL and a suggested DM script.

Before each run, update SLUG to the prospect's folder name and DATE to today in DDMMYYYY.
```

Settings: Frequency = Manual / Run on demand (not scheduled). Connectors = Vibe Prospecting. Replace PASTE_GITHUB_TOKEN_HERE with your token.

---

## LIVE ROUTINE PROMPT (paste into claude.ai/code/routines, once you have a client)

Routine name: Pipeline Builder LIVE · [Client]

```
Run the pipeline-builder skill in LIVE mode.

Read the skill from:
https://raw.githubusercontent.com/pinkiousme/authority-infra/main/skills/pipeline-builder.md

INPUTS:
MODE: LIVE
SLUG: [clientname]
DATE: [auto today DDMMYYYY]
TOKEN: PASTE_GITHUB_TOKEN_HERE

Follow the skill exactly:
1. Read the context file from inputs/prod/[SLUG]/context.md
2. Fetch 15 leads from Vibe, dedup against the client Google Sheet, keep 10 clean leads with live signals.
3. Run enrich-prospects-contacts on the 10 leads (email + phone).
4. Run one web search per lead for company intelligence.
5. Derive all per-lead fields and the market pulse from real data only.
6. Fetch the approved template, inject the real leads, remove the test banner, remove the conversion CTA (LIVE mode), show email + phone on cards.
7. Validate, then deploy to prod/[SLUG]/pipeline/index.html.
8. Append the 10 delivered LinkedIn URLs to the client dedup sheet.
9. Output the live URL.

Run every Monday at 8:00 AM client local time.
```

Settings: Frequency = Weekly, Monday. Connectors = Vibe Prospecting, Google Drive (for dedup sheet).

---

## FIRST REAL TEST

To test the full DEMO pipeline on a real prospect right now:

1. Confirm `inputs/demo/dave-cotter/context.md` exists (already pushed).
2. Set up the DEMO routine above with SLUG: dave-cotter and DATE: today.
3. Run it. This WILL spend ~3 Vibe credits for the real lead fetch.
4. Check the live URL the routine outputs.

This proves the exact mechanism the LIVE weekly routine uses. If the demo build works end to end, the live build is guaranteed to work the same way.

---

## NOTES

- Demo and live use the identical skill and template. Only the mode differs.
- The context.md approach replaces PDF reading. LinkedIn PDFs are 4MB+ image files that exceed the GitHub API limit and contain no extractable text. The context.md is tiny, readable, and reliable.
- The logo loads from GitHub with a text fallback, so it cannot break a build.
- No Vibe credits are spent on enrichment in DEMO mode. Lead signal quality is never compromised: every build uses one real Vibe fetch with live 90-day signals.
