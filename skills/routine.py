#!/usr/bin/env python3
"""
routine.py · Pipelind Pipeline Report Runner
Version: 1.0 · June 2026

Encodes the complete 9-step pipeline report build as a deterministic Python
script. Claude Code's only job is: python3 routine.py MODE SLUG DATE

Usage:
  python3 routine.py DEMO diane-maistros 19062026
  python3 routine.py LIVE anthony-perez 20062026

Environment required:
  GH_TOKEN  GitHub personal access token with repo write scope

This script handles:
  1. Read client context from GitHub
  2. Read build_report.py and template from GitHub
  3. Call Vibe Prospecting (fetch + enrich) via MCP
  4. Filter, dedup (LIVE), select target leads
  5. Write data.json (the only file the model authors)
  6. Run build_report.py deterministically
  7. Validate output.html
  8. Deploy to GitHub via Contents API
  9. Update dedup.json (LIVE only)
  10. Print final one-line status

What this script NEVER does:
  - Use any GitHub MCP connector or tool
  - Search the web
  - Call Vibe more than once (one fetch, one enrich)
  - Edit template.html
  - Deploy a file under 50,000 bytes
  - Ask questions or pause for permission
  - Use git or create branches or PRs
  - Use any token except os.environ["GH_TOKEN"]

Claude Code reads this file at runtime and executes these steps.
The Vibe MCP calls are the only place Claude's tool use is needed.
Everything else is deterministic Python.
"""

import sys
import os
import json
import base64
import subprocess
import urllib.request
import urllib.error
import re
from datetime import datetime


# ── Constants ──────────────────────────────────────────────────────────────

REPO = "pinkiousme/authority-infra"
COMMITTER = {"name": "pinkiousme", "email": "pinkious.me@gmail.com"}
MIN_OUTPUT_BYTES = 50_000
CALENDLY = "https://calendly.com/saurabh_zentro/30-min"

THEME_CYCLE = ["violet", "amber", "teal", "blue", "pink"]

# ── GitHub API helpers ──────────────────────────────────────────────────────

def _gh_request(method, path, payload=None):
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError(
            "GH_TOKEN environment variable is not set. "
            "Add it to your Claude Code cloud environment under Environment Variables."
        )
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref=main"
    if method == "PUT":
        url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "pipelind-routine/1.0")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {"message": str(e)}


def gh_read(path):
    """Read a file from main. Returns (text, sha). Raises FileNotFoundError if missing."""
    status, body = _gh_request("GET", path)
    if status != 200:
        raise FileNotFoundError(
            f"GitHub read failed for {path}: HTTP {status} {body.get('message', '')}"
        )
    text = base64.b64decode(body["content"]).decode("utf-8")
    return text, body["sha"]


def gh_read_json(path, default=None):
    """Read a JSON file from main. Returns default if file does not exist."""
    try:
        text, _ = gh_read(path)
        return json.loads(text)
    except FileNotFoundError:
        return default if default is not None else []


def gh_write(path, content_str, commit_message):
    """Create or update a file on main. Raises on failure."""
    # Get current SHA if file exists (needed for update)
    status, existing = _gh_request("GET", path)
    sha = existing.get("sha") if status == 200 else None

    payload = {
        "message": commit_message,
        "content": base64.b64encode(content_str.encode("utf-8")).decode(),
        "branch": "main",
        "committer": COMMITTER,
        "author": COMMITTER,
    }
    if sha:
        payload["sha"] = sha

    status, body = _gh_request("PUT", path, payload)
    if status not in (200, 201):
        raise RuntimeError(
            f"GitHub write failed for {path}: HTTP {status} {body.get('message', '')}"
        )
    return status


# ── Context parser ──────────────────────────────────────────────────────────

def parse_context(text):
    """
    Parse a context.md file into a dict.
    Reads key: value pairs and named sections (## SECTION).
    Returns a flat dict with all key-value pairs plus raw section text.
    """
    ctx = {}
    current_section = None
    section_lines = {}

    for line in text.splitlines():
        # Section header
        if line.startswith("## "):
            current_section = line[3:].strip()
            section_lines[current_section] = []
            continue

        # Key: value pair (not inside a section, or inside one — capture both)
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key and value:
                ctx[key.upper().replace(" ", "_")] = value

        # Accumulate section content
        if current_section is not None:
            section_lines[current_section].append(line)

    # Store raw section text for sections we need
    for section, lines in section_lines.items():
        ctx[f"_SECTION_{section.upper().replace(' ', '_')}"] = "\n".join(lines)

    return ctx


def parse_vibe_filter(ctx):
    """
    Extract the frozen Vibe filter from context into a dict.
    Reads from the FROZEN VIBE FILTER section.
    Returns a dict with all filter keys.
    """
    section_key = "_SECTION_FROZEN_VIBE_FILTER_(ROUTINE_USES_VERBATIM,_NO_DERIVATION)"
    # Try multiple possible section name variants
    filter_text = None
    for key, value in ctx.items():
        if "FROZEN" in key and "VIBE" in key:
            filter_text = value
            break

    if not filter_text:
        raise ValueError(
            "FROZEN VIBE FILTER section not found in context.md. "
            "Check the context file format."
        )

    vibe = {}
    for line in filter_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            vibe[key.strip()] = value.strip()

    return vibe


def parse_run_control(ctx):
    """Extract RUN CONTROL values from context."""
    control = {
        "credit_cap": 35,
        "web_mode": "off",
        "deploy_path": None,
    }
    for key, value in ctx.items():
        if key == "CREDIT_CAP":
            try:
                control["credit_cap"] = int(value)
            except ValueError:
                pass
        elif key == "WEB_MODE":
            control["web_mode"] = value.lower()
        elif key == "DEPLOY_PATH":
            control["deploy_path"] = value
    return control


# ── Validation helpers ──────────────────────────────────────────────────────

def validate_no_em_dash(text):
    if "\u2014" in text or " -- " in text:
        raise ValueError("data.json contains an em dash. Remove it before deploying.")


def validate_no_tool_names(text):
    forbidden = ["Vibe Prospecting", "fetch-entities", "enrich-prospects", "Apollo"]
    for term in forbidden:
        if term in text:
            raise ValueError(
                f"data.json contains a tool name or internal reference: '{term}'. "
                "Remove it before deploying."
            )


def validate_no_exclamation(text):
    if "!" in text:
        raise ValueError(
            "data.json contains an exclamation mark. "
            "Remove it to comply with brand voice rules."
        )


# ── Main routine ────────────────────────────────────────────────────────────

def main():
    # ── Parse arguments ──
    if len(sys.argv) < 4:
        print("Usage: python3 routine.py MODE SLUG DATE")
        print("  MODE: DEMO or LIVE")
        print("  SLUG: lowercase-hyphenated prospect/client folder name")
        print("  DATE: today in DDMMYYYY format")
        print("")
        print("Example: python3 routine.py DEMO diane-maistros 19062026")
        sys.exit(1)

    MODE = sys.argv[1].upper()
    SLUG = sys.argv[2].lower()
    DATE = sys.argv[3]

    if MODE not in ("DEMO", "LIVE"):
        print(f"ERROR: MODE must be DEMO or LIVE, got '{MODE}'")
        sys.exit(1)

    if not re.match(r"^\d{8}$", DATE):
        print(f"ERROR: DATE must be 8 digits in DDMMYYYY format, got '{DATE}'")
        sys.exit(1)

    print(f"\nPipelind Pipeline Report Routine v1.0")
    print(f"Mode: {MODE} | Slug: {SLUG} | Date: {DATE}")
    print("=" * 60)

    # ── Derive folder and firstname ──
    folder = "demo" if MODE == "DEMO" else "prod"
    firstname = SLUG.split("-")[0].capitalize()

    # ── STEP 1: Read client context ──
    print(f"\n[Step 1] Reading context from inputs/{folder}/{SLUG}/context.md ...")
    context_text, _ = gh_read(f"inputs/{folder}/{SLUG}/context.md")
    ctx = parse_context(context_text)

    prospect_first = ctx.get("PROSPECT_FIRST_NAME", firstname)
    prospect_full = ctx.get("PROSPECT_FULL_NAME", SLUG.replace("-", " ").title())
    firm = ctx.get("FIRM", "")
    buyer_profile = ctx.get("BUYER_PROFILE", "venture").lower()
    advisor_function = ctx.get("ADVISOR_FUNCTION", "finance").lower()

    vibe_filter = parse_vibe_filter(ctx)
    run_control = parse_run_control(ctx)

    print(f"  Client: {prospect_full} · {firm}")
    print(f"  Buyer profile: {buyer_profile} | Advisor function: {advisor_function}")
    print(f"  Credit cap: {run_control['credit_cap']}")
    print(f"  Web mode: {run_control['web_mode']}")

    # Operator guard: new_funding_round must NOT be in events
    events_str = vibe_filter.get("events", "")
    if buyer_profile == "operator" and "new_funding_round" in events_str:
        events_str = events_str.replace("new_funding_round,", "").replace("new_funding_round", "")
        vibe_filter["events"] = events_str.strip().strip(",")
        print("  GUARD: Removed new_funding_round from operator filter (not applicable).")

    print("  Context parsed successfully.")

    # ── STEP 2: Read build script and template from GitHub ──
    print("\n[Step 2] Reading build_report.py and template from GitHub ...")
    builder_text, _ = gh_read("skills/build_report.py")
    template_text, _ = gh_read("assets/templates/pipeline-report/index.html")

    with open("build_report.py", "w", encoding="utf-8") as f:
        f.write(builder_text)
    with open("template.html", "w", encoding="utf-8") as f:
        f.write(template_text)

    print("  build_report.py and template.html written to working directory.")

    # ── STEP 3: Vibe Prospecting ──
    # This step is performed by Claude Code using MCP tools.
    # The script prints the exact instruction Claude must follow.
    # Claude executes the Vibe calls, then writes the results to vibe_results.json.
    # The script then reads vibe_results.json and continues.

    target_fetch = 8 if MODE == "DEMO" else 12
    target_leads = 5 if MODE == "DEMO" else 10
    enrich_types = '["email"]' if MODE == "DEMO" else '["email", "phone"]'
    events_window = vibe_filter.get("events_window_days", "90")

    print(f"\n[Step 3] Vibe Prospecting · {target_leads} leads target")
    print(f"""
CLAUDE CODE INSTRUCTION — VIBE CALLS REQUIRED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Do these three things in order. Do nothing else until all three are complete.

3a. Call estimate-cost (0 credits) to confirm projected spend is under {run_control['credit_cap']} credits.
    If over cap: print "CREDIT CAP EXCEEDED" and stop.

3b. Call fetch-entities exactly ONCE with these exact parameters:
    entity_type: "prospects"
    number_of_results: {target_fetch}
    filters:
      job_title: {vibe_filter.get('job_title', '')}
      job_level: {vibe_filter.get('job_level', '')}
      company_size: {vibe_filter.get('company_size', '')}
      company_country_code: {vibe_filter.get('company_country_code', '')}
      linkedin_category: {vibe_filter.get('linkedin_category', '')}
      events: values=[{vibe_filter.get('events', '')}] last_occurrence={events_window} days

3c. Call enrich-prospects-contacts exactly ONCE on the fetch results.
    contact_types: {enrich_types}

After all three calls complete, write the enriched lead data to vibe_results.json.
Format: a JSON array of lead objects, each with all available fields from Vibe.

BANNED: Do not call any GitHub tool or connector. Do not search the web.
Do not call fetch-entities or enrich again. Do not export.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

    # Wait for vibe_results.json to exist (Claude Code writes it after MCP calls)
    if not os.path.exists("vibe_results.json"):
        print("WAITING: Claude Code must write vibe_results.json after Vibe calls.")
        print("Run this script again after vibe_results.json is present.")
        print("(Claude Code: after completing the Vibe calls above, write the results")
        print(" to vibe_results.json in the working directory, then re-run this script.)")
        sys.exit(0)

    print("  vibe_results.json found. Reading leads ...")
    with open("vibe_results.json", "r", encoding="utf-8") as f:
        raw_leads = json.load(f)

    print(f"  Vibe returned {len(raw_leads)} raw leads.")

    # ── STEP 4: Filter, dedup (LIVE), select ──
    print(f"\n[Step 4] Filtering and selecting {target_leads} leads ...")

    # Load dedup list for LIVE mode
    delivered_set = set()
    if MODE == "LIVE":
        delivered = gh_read_json(f"inputs/prod/{SLUG}/dedup.json", default=[])
        delivered_set = set(delivered)
        print(f"  Dedup: {len(delivered_set)} previously delivered leads excluded.")

    # Read exclusion keywords from context
    exclude_keywords = []
    if buyer_profile == "operator":
        raw_excl = vibe_filter.get("exclude_company_keywords", "")
        exclude_keywords = [k.strip().lower() for k in raw_excl.split(",") if k.strip()]

    # Filter leads
    # NOTE: Claude Code populates vibe_results.json with Vibe's enriched data.
    # Field names here match what Vibe Prospecting returns.
    # Common fields: linkedin_url, name, title, company, company_size,
    #                email, phone, signals (list), country, industry
    candidates = []
    for lead in raw_leads:
        linkedin = lead.get("linkedin_url", lead.get("linkedin", ""))
        # Ensure https:// prefix
        if linkedin and not linkedin.startswith("http"):
            linkedin = "https://" + linkedin
        lead["linkedin_url"] = linkedin

        # Skip deduped (LIVE only)
        if MODE == "LIVE" and linkedin in delivered_set:
            continue

        # Operator: check exclude keywords
        company_name = (lead.get("company", "") or "").lower()
        if exclude_keywords:
            if any(kw in company_name for kw in exclude_keywords):
                continue

        candidates.append(lead)

    # Sort: dual-signal first, then HOT (most recent signal first)
    def sort_key(lead):
        signals = lead.get("signals", lead.get("signal_types", []))
        if isinstance(signals, str):
            signals = [signals]
        dual = 1 if len(signals) >= 2 else 0
        days_ago = lead.get("signal_days_ago", lead.get("days_since_signal", 999))
        try:
            days_ago = int(days_ago)
        except (TypeError, ValueError):
            days_ago = 999
        return (-dual, days_ago)

    candidates.sort(key=sort_key)
    kept_leads = candidates[:target_leads]

    if len(kept_leads) == 0:
        print("ERROR: No qualifying leads after filtering. Cannot build report.")
        print("Check Vibe filter parameters in context.md.")
        sys.exit(1)

    if len(kept_leads) < target_leads:
        print(f"  WARNING: Only {len(kept_leads)} qualifying leads (target was {target_leads}).")
        print("  Delivering what qualifies. No padding with off-ICP leads.")

    print(f"  Selected {len(kept_leads)} leads.")

    # ── STEP 5: Write data.json ──
    # This is the only file this script authors.
    # Claude Code should fill in the card-level fields (whyFit, whyNow, connNote,
    # emailSubj, emailBody) based on the Vibe data and prospect context.
    # The script builds the full schema and delegates card authoring to Claude.

    print(f"\n[Step 5] Building data.json ...")

    today_str = datetime.now().strftime("%B %d, %Y")
    week_str = f"Week of {datetime.now().strftime('%B %d, %Y')}"

    # Count HOT vs WARM
    hot_count = 0
    warm_count = 0
    for lead in kept_leads:
        days_ago = lead.get("signal_days_ago", lead.get("days_since_signal", 60))
        try:
            days_ago = int(days_ago)
        except (TypeError, ValueError):
            days_ago = 60
        if days_ago <= 30:
            hot_count += 1
        else:
            warm_count += 1

    # Build lead cards
    # Claude Code fills in the authored fields below
    lead_cards = []
    for i, lead in enumerate(kept_leads):
        theme = THEME_CYCLE[i % len(THEME_CYCLE)]

        name = lead.get("name", lead.get("full_name", "Unknown"))
        role = lead.get("title", lead.get("job_title", ""))
        company = lead.get("company", lead.get("company_name", ""))
        country = lead.get("country", lead.get("company_country", ""))
        industry = lead.get("industry", lead.get("linkedin_category", ""))
        employees = str(lead.get("employees", lead.get("company_size", "")))
        revenue = lead.get("revenue", lead.get("company_revenue", ""))
        linkedin = lead.get("linkedin_url", "")
        website = lead.get("website", lead.get("company_website", ""))
        email_val = lead.get("email", "") if MODE == "LIVE" else ""
        phone_val = lead.get("phone", "") if MODE == "LIVE" else ""

        # Signal fields
        signals = lead.get("signals", lead.get("signal_types", []))
        if isinstance(signals, str):
            signals = [signals]
        days_ago = lead.get("signal_days_ago", lead.get("days_since_signal", 60))
        try:
            days_ago = int(days_ago)
        except (TypeError, ValueError):
            days_ago = 60
        priority = "HOT" if days_ago <= 30 else "WARM"

        # Stage: operator uses revenue bands, venture uses funding stage
        stage = lead.get("funding_stage", lead.get("revenue_range", lead.get("stage", "")))

        # Initials from name
        parts = name.split()
        initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else name[:2].upper()

        # Recent news = plain-language signal description (no tool names)
        signal_plain = ", ".join(signals) if signals else "Recent business activity"
        # Clean up any internal event names to plain English
        signal_plain = (signal_plain
            .replace("new_funding_round", "Recent funding round")
            .replace("merger_and_acquisitions", "Recent acquisition activity")
            .replace("leadership_change", "Recent leadership change")
            .replace("hiring_in_finance_department", "Hiring in finance")
            .replace("hiring_in_operations_department", "Hiring in operations")
            .replace("office_expansion", "Office expansion")
            .replace("hiring_in_leadership", "Hiring leadership roles")
            .replace("_", " ")
        )

        card = {
            "id": i + 1,
            "theme": theme,
            "name": name,
            "initials": initials,
            "role": role,
            "company": company,
            "country": country,
            "stage": str(stage),
            "industry": industry,
            "employees": employees,
            "revenue": str(revenue) if revenue else "",
            "signalDetail": signal_plain,
            "days": days_ago,
            "priority": priority,
            "linkedin": linkedin,
            "website": website,
            "email": email_val,
            "phone": phone_val,
            # Fields below: Claude Code authors these based on prospect context and Vibe data.
            # Do not leave placeholders. Fill every field before writing data.json.
            "whatTheyDo": lead.get("_whatTheyDo", f"{company} is a {employees}-person {industry} company."),
            "recentNews": signal_plain,
            "founderFocus": lead.get("_founderFocus", "Not on record"),
            "teamTrajectory": lead.get("_teamTrajectory", "Not on record"),
            "whyFit": lead.get("_whyFit", f"Signal match: {signal_plain} aligns with {prospect_full}'s target engagement window."),
            "whyNow": lead.get("_whyNow", f"Signal recorded in the last {days_ago} days."),
            "connNote": lead.get("_connNote", f"Hi [name], noticed {company} recently had {signal_plain.lower()}. That timing often aligns with [advisor_function] needs. Happy to share how I work if useful."),
            "emailSubj": lead.get("_emailSubj", f"{company} caught my attention"),
            "emailBody": lead.get("_emailBody", f"Hi [name],\n\nSaw that {company} recently {signal_plain.lower()}. That usually signals a window where [advisor function] infrastructure matters more than usual.\n\nHappy to walk you through what I typically see at this stage if it would be useful.\n\nBest,\n{prospect_full}"),
        }
        lead_cards.append(card)

    # Dashboard stats
    countries = list(set(l.get("country", "") for l in kept_leads if l.get("country")))
    industries = list(set(l.get("industry", lead.get("linkedin_category", "")) for l in kept_leads if l.get("industry")))

    # Signal breakdown for signals tab
    all_signals = []
    for lead in kept_leads:
        sigs = lead.get("signals", lead.get("signal_types", []))
        if isinstance(sigs, str):
            sigs = [sigs]
        all_signals.extend(sigs)
    signal_counts = {}
    for s in all_signals:
        signal_counts[s] = signal_counts.get(s, 0) + 1

    signals_arr = [{"type": k.replace("_", " ").title(), "count": v, "pct": round(v / len(kept_leads) * 100)}
                   for k, v in sorted(signal_counts.items(), key=lambda x: -x[1])]

    # Geo breakdown
    geo_counts = {}
    for lead in kept_leads:
        c = lead.get("country", lead.get("company_country", "Unknown"))
        geo_counts[c] = geo_counts.get(c, 0) + 1
    geo_arr = [{"country": k, "count": v} for k, v in sorted(geo_counts.items(), key=lambda x: -x[1])]

    # Stage breakdown
    stage_counts = {}
    for lead in kept_leads:
        s = lead.get("funding_stage", lead.get("revenue_range", lead.get("stage", "Unknown")))
        stage_counts[str(s)] = stage_counts.get(str(s), 0) + 1
    stage_arr = [{"stage": k, "count": v} for k, v in sorted(stage_counts.items(), key=lambda x: -x[1])]

    pulse = (
        f"{len(kept_leads)} ICP-matched profiles this week. "
        f"{hot_count} HOT (signal in last 30 days), {warm_count} WARM. "
        f"Signals: {', '.join(set(all_signals))[:120]}."
    )

    data = {
        "mode": MODE,
        "client": {
            "firstName": prospect_first,
            "fullName": prospect_full,
            "firm": firm,
        },
        "calendly": CALENDLY,
        "week": week_str,
        "generated": today_str,
        "leads": lead_cards,
        "dashboard": {
            "stats": {
                "total": len(kept_leads),
                "hot": hot_count,
                "warm": warm_count,
                "countries": len(countries),
            },
            "sig": signal_counts,
            "geo": geo_arr,
            "stage": stage_arr,
            "pulse": pulse,
        },
        "signals": signals_arr,
        "markets": {
            "geo": geo_arr,
            "ind": [{"industry": k, "count": 1} for k in industries],
            "notes": f"Data from Vibe Prospecting. {len(kept_leads)} profiles matched. Signal window: {events_window} days.",
        },
    }

    # Validate data before writing
    data_str = json.dumps(data, ensure_ascii=False, indent=2)
    validate_no_em_dash(data_str)
    validate_no_tool_names(data_str)
    validate_no_exclamation(data_str)

    with open("data.json", "w", encoding="utf-8") as f:
        f.write(data_str)
    print(f"  data.json written. {len(lead_cards)} leads. {hot_count} HOT, {warm_count} WARM.")

    # ── STEP 6: Run build_report.py ──
    print(f"\n[Step 6] Running build_report.py ...")
    result = subprocess.run(
        ["python3", "build_report.py", "data.json", "template.html", "output.html"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("BUILD FAILED:")
        print(result.stdout)
        print(result.stderr)
        print("\ndata.json contents:")
        print(data_str)
        sys.exit(1)
    if result.stdout:
        print(f"  Builder output: {result.stdout.strip()}")
    print("  Build completed.")

    # ── STEP 7: Validate output.html ──
    print(f"\n[Step 7] Validating output.html ...")
    if not os.path.exists("output.html"):
        print("ERROR: output.html does not exist after build. Check build errors above.")
        sys.exit(1)

    size = os.path.getsize("output.html")
    if size < MIN_OUTPUT_BYTES:
        print(f"ERROR: output.html is only {size} bytes (minimum {MIN_OUTPUT_BYTES}). Build likely failed.")
        sys.exit(1)

    with open("output.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    if "__PL_" in html_content:
        remaining = re.findall(r"__PL_\w+__", html_content)
        print(f"ERROR: Unfilled placeholders remain in output.html: {remaining}")
        sys.exit(1)

    print(f"  output.html validated. Size: {size:,} bytes. No unfilled placeholders.")

    # ── STEP 8: Deploy to GitHub ──
    if MODE == "DEMO":
        deploy_path = f"demo/{DATE}/{prospect_first.lower()}/index.html"
        live_url = f"https://pipelind.com/demo/{DATE}/{prospect_first.lower()}/"
    else:
        deploy_path = f"prod/{SLUG}/pipeline/index.html"
        live_url = f"https://pipelind.com/prod/{SLUG}/pipeline/"

    print(f"\n[Step 8] Deploying to {deploy_path} ...")
    commit_msg = f"Pipeline report · {MODE} · {SLUG} · {DATE}"
    gh_write(deploy_path, html_content, commit_msg)
    print(f"  Deployed successfully. Live at {live_url} (allow 30-90s for Vercel).")

    # ── STEP 9: Update dedup.json (LIVE only) ──
    if MODE == "LIVE":
        print(f"\n[Step 9] Updating dedup.json ...")
        new_urls = [l["linkedin"] for l in lead_cards if l.get("linkedin")]
        existing_dedup = gh_read_json(f"inputs/prod/{SLUG}/dedup.json", default=[])
        updated_dedup = sorted(set(existing_dedup) | set(new_urls))
        gh_write(
            f"inputs/prod/{SLUG}/dedup.json",
            json.dumps(updated_dedup, indent=2),
            f"Dedup update · {SLUG} · {DATE}",
        )
        print(f"  dedup.json updated. Total delivered: {len(updated_dedup)} leads.")
    else:
        print(f"\n[Step 9] DEMO mode — no dedup update.")

    # ── Final status line ──
    print(f"\n{'=' * 60}")
    print(
        f"PIPELINE REPORT COMPLETE · {MODE} · {prospect_full} · {firm} · "
        f"Leads {len(kept_leads)} · HOT {hot_count} · WARM {warm_count} · "
        f"Live URL: {live_url} · Deploy SUCCESS"
    )
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
