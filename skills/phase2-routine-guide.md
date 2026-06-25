# Phase 2 - Pipeline Builder - Routine Instructions and Run Guide

The complete system runs from GitHub. One skill, two modes. Demo runs manually on demand. Live runs on a weekly schedule. Same engine.

---

## WHAT LIVES IN GITHUB (single source of truth)

```
authority-infra/
--- assets/
-   --- templates/pipeline-report/index.html   - approved template
-   --- pipelind-logo-dark.png                  - logo (used in reports)
--- skills/
-   --- pipeline-builder.md                     - the mode-aware skill
--- inputs/
-   --- demo/[firstname-lastname]/context.md    - prospect context (DEMO)
-   --- prod/[clientname]/context.md            - client context (LIVE)
--- demo/[DDMMYYYY]/[firstname]/index.html       - deployed demo reports
--- prod/[clientname]/pipeline/index.html        - deployed live reports
```

---

## THE DEMO WORKFLOW (manual, on prospect comment)

When a prospect comments LEAD:

### Step 1 - Build their context file (one quick step)
Open a normal Claude chat. Attach their LinkedIn profile PDF. Say:
"Build a context.md for this prospect using the pipeline-builder format. Extract name, title, firm, website, location, their ICP, buying signals, voice rules, and Vibe filter derivation."

Claude returns a context.md. (This replaces the unreliable PDF-in-routine approach. A text file is tiny, always readable, never breaks.)

### Step 2 - Push the context file to GitHub
Put it at: `inputs/demo/[firstname-lastname]/context.md`
(e.g. `inputs/demo/dave-cotter/context.md`)
Drag-drop into the GitHub web UI, or ask Claude in that same chat to push it via the API.

### Step 3 - Run the DEMO routine
Go to claude.ai/code/routines. Use the saved "Pipeline Builder DEMO" routine (set up once, see below). Update the SLUG and DATE values, then click Run now.

### Step 4 - Send the DM
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

REQUIRES: GH_TOKEN set in the environment's Environment Variables (a GitHub
token with write access to the repo). It is read from the environment only,
never hardcoded. The script reads inputs from the local clone and deploys by
pushing to github.com with GH_TOKEN (api.github.com is proxy-blocked in cloud
and the GitHub App is read-only, so a token git push is the only write path).
Run: python3 skills/routine.py DEMO [SLUG] [DATE]

Follow the script exactly:
1. The script reads the context file from inputs/demo/[SLUG]/context.md (local clone).
2. When it prints the VIBE block, do the Vibe Prospecting MCP calls it lists,
   write the results to vibe_results.json, then re-run the same command.
3. The script builds, validates, and DEPLOYS the report itself (git push to main
   using GH_TOKEN). No manual deploy step. It prints the live URL on success.
4. Output the live URL and a suggested DM script.

Before each run, update SLUG to the prospect's folder name and DATE to today in DDMMYYYY.
```

Settings: Frequency = Manual / Run on demand (not scheduled). Connectors = Vibe Prospecting. Environment: set GH_TOKEN (write-scoped GitHub token) in Environment Variables.

---

## LIVE ROUTINE PROMPT (paste into claude.ai/code/routines, once you have a client)

Routine name: Pipeline Builder LIVE - [Client]

```
Run the pipeline-builder skill in LIVE mode.

Read the skill from:
https://raw.githubusercontent.com/pinkiousme/authority-infra/main/skills/pipeline-builder.md

INPUTS:
MODE: LIVE
SLUG: [clientname]
DATE: [auto today DDMMYYYY]

REQUIRES: GH_TOKEN set in the environment's Environment Variables (write-scoped
GitHub token, read from the environment only - never hardcoded).
Run: python3 skills/routine.py LIVE [SLUG] [DATE]

Follow the script exactly:
1. The script reads inputs/prod/[SLUG]/context.md and dedup.json from the local clone.
2. When it prints the VIBE block, do the Vibe Prospecting MCP calls it lists
   (email-only enrichment, dedup against dedup.json), write the results to
   vibe_results.json, then re-run the same command.
3. The script builds, validates, and DEPLOYS both the report and the updated
   dedup.json to main itself (git push using GH_TOKEN). No manual deploy step.
4. Output the live URL.

Run every Monday at 8:00 AM client local time.
```

Settings: Frequency = Weekly, Monday. Connectors = Vibe Prospecting. Environment: set GH_TOKEN (write-scoped GitHub token) in Environment Variables.

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
