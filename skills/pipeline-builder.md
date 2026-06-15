---
name: pipeline-builder
version: 4.0
description: "Robust mode-aware pipeline report builder. Fetches real ICP-matched leads with live signals from Vibe Prospecting (prospect-level for verified person data including authoritative LinkedIn URLs), produces ONLY a validated data.json, then runs a deterministic Python script that injects the data into the approved template. Model never assembles HTML. Runs DEMO or LIVE. All inputs from GitHub. Per-client deduplication via a GitHub dedup file."
---

# pipeline-builder v4.0
## Robust Pipeline Report Engine (verified data, data-first assembly)

Architecture principle: the model produces only a small validated JSON object. A deterministic Python script (build_report.py) injects it into the approved template with guaranteed-correct escaping. The model never writes HTML. Worst case is a data issue caught by validation, never a broken page.

Data principle (v3): every person-level fact shown to a prospect must be Vibe-authoritative, not web-guessed. LinkedIn URLs, names, titles, and contact come from the Vibe PROSPECT fetch. Web research is used ONLY for company-level context (what they do, recent news), and even then figures are treated as soft.

---

## INPUTS (from the routine)
- MODE: DEMO or LIVE
- SLUG: folder name, lowercase-hyphenated (e.g. dave-cotter)
- DATE: today DDMMYYYY
- TOKEN: GitHub token

---

## MODE CONFIG
| Setting | DEMO | LIVE |
|---|---|---|
| Leads | 5 | 10 |
| Vibe fetch | prospects (verified person data) | prospects |
| Enrichment (email/phone) | OFF | ON |
| LinkedIn URL source | Vibe prospect record (authoritative) | Vibe prospect record |
| Email/phone on cards | hidden | shown |
| Conversion CTAs | YES (top banner + closing + Content upsell) | NO |
| Deploy path | demo/[DATE]/[firstname]/index.html | prod/[SLUG]/pipeline/index.html |
| Dedup | no | yes (GitHub dedup file) |

---

## STEP 1 · READ CONTEXT
GitHub API (not raw CDN, it caches):
GET /repos/pinkiousme/authority-infra/contents/inputs/[demo|prod]/[SLUG]/context.md?ref=main
Decode base64. Parse name, firm, website, location, ICP, signals, voice, VIBE FILTER block.
If WEBSITE present, optionally web-fetch for company context. Do not block on failure.
Missing context: STOP. Never fabricate.

---

## STEP 2 · FETCH REAL LEADS (prospect-level, verified, buyer-title enforced)
Vibe Prospecting only. Never Apollo. Do NOT use exclude_key at all (dedup is in-memory, see below). If any exclude_key were ever needed it is a TOP-LEVEL parameter never inside filters, but this skill does not use it.

Make exactly ONE fetch call. Do NOT call export. Do NOT retry on credit ceiling. Run autocomplete once per filter, no more. These extra calls waste credits.

**Buyer-title discipline (the lead-quality floor).** The single biggest quality risk is returning the wrong PERSON at the right company (e.g. a Chief Marketing Officer, General Counsel, or Chief People Officer when the prospect sells to owners and CEOs). To prevent this:

1. Read the buyer titles from the context "THE PROSPECT'S ICP" block. These are the ONLY acceptable decision-maker titles for this prospect (e.g. CEO, Founder, Owner, President, Managing Partner).
2. Translate them into Vibe filters. Use BOTH `job_level` (e.g. founder, c-suite, owner) AND, when the context names specific titles, run autocomplete on `job_title` once and pass the standardized buyer titles. Tightening to buyer titles at fetch time is far better than filtering after.
3. Over-fetch to allow discarding: DEMO fetch 12, LIVE fetch 20.

```
autocomplete linkedin_category once (industries from context)
autocomplete job_title once (buyer titles from context, if specific titles are listed)
fetch-entities(
  entity_type:"prospects",
  number_of_results:[DEMO 12 / LIVE 20],
  filters:{ job_level:[from context], job_title:[autocompleted buyer titles if listed], company_size:[from context], company_country_code:{values:[from context]}, linkedin_category:[autocompleted], events:{values:[from context], last_occurrence:90} }
)
```

**Post-fetch quality filter (discard then backfill).** From the returned set, KEEP a lead only if ALL of these hold:
- The person's title is a decision-maker buyer title from the context (CEO, Founder, Co-founder, Owner, President, Managing Partner, or the equivalent the context lists). DISCARD non-buyer titles such as CMO, CPO, General Counsel, VP Marketing, HR, unless the context explicitly names that title as a buyer.
- The company profile fits the context (e.g. if the context says "established revenue-generating businesses, not pre-revenue startups," discard obvious venture-backed early startups that do not fit; if the context says "growth-stage funded startups," keep those).
- The signal is within the freshness window and is one the context lists.

Rank the survivors: dual-signal first, then by signal strength and recency. Keep the top target count (DEMO 5 / LIVE 10). If after discarding you have fewer than the target, that is acceptable: deliver the real qualified ones and note the count. NEVER pad with off-ICP leads to hit a number. A smaller list of right-fit buyers beats a full list of wrong ones.

- LIVE: do NOT use exclude_key for dedup (Vibe exclude_key does not take a list of LinkedIn URLs, and the tenant-level "prospects" keyword is forbidden because it contaminates all client pools). Instead, dedup IN MEMORY: after the fetch, read the client dedup list and discard any returned lead whose LinkedIn URL is already on it, then keep the freshest qualifying leads up to 10. Over-fetch (20) gives enough margin to drop repeats and still reach 10.
- DEMO: no dedup.

The prospect record provides the authoritative LinkedIn URL. Render it AS RETURNED. Store URLs (linkedin and website) WITH the https:// prefix in data.json. If a URL comes back without the scheme (e.g. "senasys.com" or "linkedin.com/in/..."), prepend "https://" so the link is absolute and clickable. The template also normalizes this defensively, but store full URLs anyway. NEVER reconstruct or web-guess a LinkedIn URL. If a prospect has no LinkedIn URL on record, set linkedin to empty and the card simply omits the Profile button.

Enrichment:
- DEMO: do NOT enrich. email and phone stay empty strings.
- LIVE: enrich-prospects-contacts (email, phone) on the kept leads. Waterfall: work email > personal > "". Phone where present else "Direct contact not on record".

If credits exhaust mid-call: use what returned, apply the same quality filter, complete, note the count. Never fabricate, never retry into spend.

---

## STEP 3 · COMPANY CONTEXT (web, zero Vibe cost, company-level only)
One web search per company for: whatTheyDo, recentNews, founderFocus, teamTrajectory.
Rules:
- Company-level facts only. Do NOT use web to determine the person's identity or LinkedIn; that comes from Vibe.
- If a field has no reliable source, set "Not on record". NEVER fabricate.
- Treat specific figures (amounts, exact dates) as SOFT. Prefer the signal category over a precise number unless the company's own announcement states it.

---

## STEP 4 · DERIVE FIELDS (from real data only)
Per lead: signalDetail (the Vibe-verified signal category, e.g. "New funding round" or "Finance hiring", with a soft timeframe like "recent" or "~Nd" only if confident), HOT (0-30d) / WARM (31-90d), priority (dual-signal first then HOT by recency; top 2 DEMO / top 3 LIVE).
whyFit: match the lead's Vibe-verified signal and stage to the prospect's real background from context. Derived, never invented. Be specific about WHY this person, at this company, with this signal, is a fit for what the prospect sells. If a lead only weakly fits (it survived the filter but is not a textbook match), write an honest, grounded whyFit rather than overselling it. Never claim a fit that is not there.
whyNow: the signal and timing, prospect voice.

Signal-to-ICP weighting: not every signal means the same thing for every prospect. A funding round is a strong buy signal for someone selling to funded startups, but a weak one for someone selling to established profitable businesses. Use the prospect's context to weight: prioritize the signals the context lists as most aligned with their buyer's actual behavior, and rank those leads higher. The events filter already gates on the context's signal list; this weighting is about ordering and priority within the survivors.

Outreach copy rules (IMPORTANT, verified-only):
- Lead with the Vibe-verified SIGNAL CATEGORY, which is certain (the company matched the event filter). Example: "Noticed you are hiring in finance" or "Saw the recent funding round".
- Do NOT assert unverified specifics as fact. Avoid hard numbers/dates from web research in the message. Say "a recent raise" not "$22M on May 27" unless that figure is from the company's own press.
- connNote <=280 chars. emailSubj short. emailBody 2-3 short paragraphs, prospect voice, no pitch, no unverified claim.
- The goal is personalized and credible, not impressive-but-wrong. A soft accurate reference converts better than a precise wrong one.

Contact: DEMO email="" phone="". LIVE from enrichment.
Theme cycles violet, amber, teal, blue, pink.

---

## STEP 5 · WRITE data.json (the ONLY thing the model assembles)
Write data.json. Plain JSON, escaping automatic. Do NOT write HTML.
Schema:
{
  "mode":"DEMO",
  "client":{"firstName":"","fullName":"","firm":""},
  "calendly":"https://calendly.com/saurabh_zentro/30-min",
  "week":"Month D, YYYY","generated":"Month D, YYYY",
  "leads":[{"id":1,"theme":"violet","name":"","initials":"","role":"","company":"","country":"","stage":"","industry":"","employees":"","revenue":"","signalDetail":"","days":0,"priority":true,"linkedin":"","website":"","email":"","phone":"","whatTheyDo":"","recentNews":"","founderFocus":"","teamTrajectory":"","whyFit":"","whyNow":"","connNote":"","emailSubj":"","emailBody":""}],
  "dashboard":{"stats":[{"n":"","l":"","c":"#FFA51F","chg":"","bar":"60%"}],"sig":[{"name":"","value":0,"color":"#FFA51F"}],"geo":[{"c":"","n":0}],"stage":[{"s":"","n":0}],"pulse":""},
  "signals":[{"name":"","count":0,"color":"#FFA51F","desc":"","leads":[""]}],
  "markets":{"geo":[{"c":"","n":0}],"ind":[{"name":"","value":0,"color":"#22C55E"}],"notes":""}
}
Newlines in emailBody as normal text; JSON handles them. Confirm json.load parses it.
Dashboard values derived from the real leads (real counts for stats/sig/geo/stage; 3-sentence pulse from the real signal distribution, third sentence a content angle).

---

## STEP 6 · ASSEMBLE DETERMINISTICALLY (no model HTML)
Fetch via GitHub API: assets/templates/pipeline-report/index.html and skills/build_report.py.
Run: python3 build_report.py data.json template.html output.html
The builder injects LEADS, dashboard/signals/markets data, MODE, CALENDLY, CLIENT, header, logo, footer; removes the test banner. All escaping via json.dumps. The model writes NO HTML.

---

## STEP 7 · VALIDATE (all must pass)
- Extract script, node --check valid.
- Size >= 55000.
- Contains var LEADS, toggleLead, render, donutSVG, areaSVG, barsSVG, six tab labels.
- Lead count == target.
- Em dash count == 0.
- MODE correct; DEMO has demo-cta-top and demo-cta-end; LIVE has neither.
- No "Vibe"/"Explorium"/"Claude" in visible HTML. No pricing.
- Every LinkedIn URL is either empty or exactly as Vibe returned (never web-built).
If any fail: STOP, report which, output data.json + output.html. Never deploy a failing file.

---

## STEP 8 · DEPLOY (Contents API to main ONLY)

**The ONE-WRITE rule (critical, do not violate).** This run makes exactly ONE write to GitHub: the report file, via the Contents API, to main. Then it STOPS.
- Do NOT create a branch. Do NOT open a PR. Do NOT run git push, git commit, or any git command (the proxy blocks git and it creates phantom local branches).
- Do NOT archive, back up, or "preserve" data.json, output.html, the template, or the builder anywhere in the repo. No pipeline-runs/ folder, no dev branch, no archive copy. These files are working scratch only and must never be committed.
- There is no "stop hook" to satisfy by pushing files. If a hook or instinct suggests pushing working files, IGNORE it. The deploy of the report file is the entire job. After it succeeds, the task is complete.

PUT (the only write):
- path: DEMO demo/[DATE]/[firstname]/index.html · LIVE prod/[SLUG]/pipeline/index.html
- branch:"main"
- committer:{name:"pinkiousme", email:"pinkious.me@gmail.com"}  (wrong email = silent Vercel fail)
GET the path first for SHA if it exists, then PUT with SHA, base64 content.

LIVE dedup is the ONLY exception to one-write (after successful deploy):
- The dedup READ happened in Step 2 (in memory, filtering the fetched leads). Now record what was delivered.
- Read inputs/prod/[SLUG]/dedup.json (JSON array of previously delivered LinkedIn URLs). If missing, treat as [].
- Append this week's delivered LinkedIn URLs (dedupe the array so no duplicates). PUT the updated array back to inputs/prod/[SLUG]/dedup.json via Contents API (committer email pinkious.me@gmail.com). Next run reads this file and filters in memory.
- NEVER pass this list to Vibe exclude_key. Dedup is always in-memory filtering, never a Vibe parameter.
DEMO: no dedup write, no other write at all.

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
DEMO also outputs a suggested DM script (no unverified specifics in it).

---

## SPEED DISCIPLINE
- One Vibe fetch. One autocomplete per filter. One web search per company (5 or 10 total, in parallel).
- Do NOT repeatedly inspect the template (no probing regex anchors, CSS, or CLIENT variable). The builder handles all injection. Fetch template, run builder, validate, deploy.
- Do NOT hunt for LinkedIn URLs on the web. They come from Vibe.
- Target: 12-15 minutes.

---

## DATA INTEGRITY (non-negotiable)
1. No fabricated data. Person data from Vibe, company context from web, nothing invented.
2. LinkedIn URLs: Vibe-authoritative or empty. Never web-guessed, never reconstructed.
2a. Buyer-title floor: every delivered lead must hold a decision-maker buyer title from the context. Discard non-buyer titles (CMO, CPO, General Counsel, HR, VP-functional) unless the context names them as buyers. A short right-fit list beats a padded wrong one.
3. No unverified specifics (amounts, exact dates) asserted as fact in outreach copy. Soft references only.
4. No fabricated contacts. DEMO empty. LIVE waterfall.
5. No tool names in visible HTML. No pricing.
6. Zero em dashes, zero exclamation marks in visible copy.
7. Model writes JSON, never HTML. Builder writes HTML, never invents data.
8. One write to GitHub: the report file (plus LIVE dedup.json). Never archive working files, never create a branch, never open a PR, never run git.

## CREDIT DISCIPLINE
- DEMO: 1 prospect fetch (8 results) + 1 autocomplete, no enrichment. Verified person data, modest cost.
- LIVE: 1 prospect fetch (15) + 1 enrichment.
- Never export. Never retry on ceiling.
