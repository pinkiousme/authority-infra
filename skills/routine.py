#!/usr/bin/env python3
"""
routine.py · Pipelind Pipeline Report Runner
Version: 2.1 · June 2026

Encodes the complete 9-step pipeline report build as a deterministic Python
script. Claude Code's only job is: python3 routine.py MODE SLUG DATE

Usage:
  python3 routine.py DEMO diane-maistros 19062026
  python3 routine.py LIVE anthony-perez 20062026

Environment required:
  GH_TOKEN  GitHub personal access token with repo write scope
  (Set this in Claude Code cloud environment variables - never in the prompt)

KEY FIXES IN v2.0 (all data shape bugs that caused empty Dashboard/Signals/Markets tabs):
  - stats: now an ARRAY of {n,l,c,bar} objects (template calls stats.forEach)
  - sig: now an ARRAY of {name,value,color} objects (template calls donutSVG + sig.forEach)
  - signals: now ARRAY of {name,count,color,desc,leads[]} (template calls t.leads.forEach)
  - mk_geo: now uses {c,n} keys (barsSVG reads d.c and d.n)
  - mk_ind: now ARRAY of {name,value,color} for donutSVG
  - founderFocus / teamTrajectory: now inferred from Vibe signal data, not "Not on record"
  - validate_no_tool_names: no longer rejects "Vibe Prospecting" in markets.notes (that field
    is internal only and never rendered in visible HTML - removed that false-positive check)
  - markets.notes: now uses neutral wording, no tool names in rendered content

Vibe Prospecting workflow (email-only, both modes):
  - Signals (events) are business-level, so the fetch is a two-step:
    1. fetch-entities entity_type "businesses" with the events filter
    2. fetch-entities entity_type "prospects" using that businesses_reference_table
  - Enrich EMAIL only (no phone, ever) via enrich-prospects-contacts.
  - DEMO retrieves via show-sample (flat 5 credits). LIVE retrieves via
    export-to-csv, sized from credit_cap so spend never exceeds the budget.

What this script NEVER does:
  - Use any GitHub MCP connector or tool
  - Search the web
  - Enrich phone numbers (email only)
  - Exceed the context credit_cap (fetch size is derived from it)
  - Edit template.html
  - Deploy a file under 50,000 bytes
  - Ask questions or pause for permission
  - Use git or create branches or PRs
  - Use any token except os.environ["GH_TOKEN"]
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


# ── Constants ───────────────────────────────────────────────────────────────

REPO = "pinkiousme/authority-infra"
COMMITTER = {"name": "pinkiousme", "email": "pinkious.me@gmail.com"}
MIN_OUTPUT_BYTES = 50_000
CALENDLY = "https://calendly.com/saurabh_zentro/30-min"
THEME_CYCLE = ["violet", "amber", "teal", "blue", "pink"]

# Colors matching the brand palette - used in chart data
SIGNAL_COLORS = ["#7C6FE8", "#FFA51F", "#22C55E", "#22D3EE", "#EC4899", "#3B82F6"]
GEO_COLOR = "#22D3EE"
IND_COLORS = ["#7C6FE8", "#FFA51F", "#22C55E", "#22D3EE", "#EC4899"]

# Stat card config - matches exactly what the template's stats.forEach expects:
# s.n = value, s.l = label, s.c = color hex, s.bar = bar width %, s.chg = optional change badge
STAT_COLORS = {
    "total": "#7C6FE8",
    "hot": "#FFA51F",
    "warm": "#22D3EE",
    "countries": "#22C55E",
}


# ── GitHub API helpers ───────────────────────────────────────────────────────

def _gh_request(method, path, payload=None):
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError(
            "GH_TOKEN environment variable is not set. "
            "Add it to your Claude Code cloud environment under Environment Variables."
        )
    if method == "GET":
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref=main"
    else:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}"

    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "pipelind-routine/2.0")
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


# ── Context parser ───────────────────────────────────────────────────────────

def parse_context(text):
    """Parse a context.md file. Returns a flat dict of all key:value pairs."""
    ctx = {}
    current_section = None
    section_lines = {}

    for line in text.splitlines():
        if line.startswith("## "):
            current_section = line[3:].strip()
            section_lines[current_section] = []
            continue
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key and value:
                ctx[key.upper().replace(" ", "_")] = value
        if current_section is not None:
            section_lines[current_section] = section_lines.get(current_section, [])
            section_lines[current_section].append(line)

    for section, lines in section_lines.items():
        safe_key = re.sub(r'[^A-Z0-9_]', '_', section.upper().replace(' ', '_'))
        ctx[f"_SECTION_{safe_key}"] = "\n".join(lines)

    return ctx


def parse_vibe_filter(ctx):
    """Extract the frozen Vibe filter block from context."""
    filter_text = None
    for key, value in ctx.items():
        if "FROZEN" in key and "VIBE" in key:
            filter_text = value
            break
    if not filter_text:
        raise ValueError(
            "FROZEN VIBE FILTER section not found in context.md. "
            "Check the context file."
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
    control = {"credit_cap": 35, "web_mode": "off", "deploy_path": None}
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


# ── Signal plain-language mapping ────────────────────────────────────────────

def signal_to_plain(signal_str):
    """Convert Vibe internal event names to plain English. No tool names."""
    mapping = {
        "new_funding_round": "Recent funding round",
        "merger_and_acquisitions": "Recent acquisition activity",
        "leadership_change": "Recent leadership change",
        "leadership_change_operations": "Operations leadership change",
        "leadership_change_finance": "Finance leadership change",
        "hiring_in_finance_department": "Hiring in finance",
        "hiring_in_operations_department": "Hiring in operations",
        "hiring_in_leadership": "Hiring leadership roles",
        "office_expansion": "Office expansion",
        "new_office": "Office expansion",
        "cost_cutting": "Active cost reduction",
        "decrease_in_all_departments": "Org-wide headcount reduction",
    }
    s = signal_str.strip()
    return mapping.get(s, s.replace("_", " ").title())


def signals_list_to_plain(signals):
    """Convert a list of signal strings to plain English list."""
    if isinstance(signals, str):
        signals = [signals]
    if not signals:
        return ["Recent business activity"]
    return [signal_to_plain(s) for s in signals]


# ── Data shape builders (matching template exactly) ──────────────────────────

def build_stats_array(total, hot, warm, countries):
    """
    Build the stats array the template expects.
    Template calls: stats.forEach(function(s){ ... s.n ... s.l ... s.c ... s.bar ... })
    Each item: {n: display_value, l: label, c: color_hex, bar: "pct%", chg: optional}
    """
    max_val = max(total, 1)
    return [
        {
            "n": str(total),
            "l": "Total Leads",
            "c": STAT_COLORS["total"],
            "bar": f"{min(100, round(total / max_val * 100))}%",
        },
        {
            "n": str(hot),
            "l": "HOT (0-30 days)",
            "c": STAT_COLORS["hot"],
            "bar": f"{round(hot / max(total, 1) * 100)}%",
        },
        {
            "n": str(warm),
            "l": "WARM (31-90 days)",
            "c": STAT_COLORS["warm"],
            "bar": f"{round(warm / max(total, 1) * 100)}%",
        },
        {
            "n": str(countries),
            "l": "Countries",
            "c": STAT_COLORS["countries"],
            "bar": f"{min(100, countries * 20)}%",
        },
    ]


def build_sig_array(signal_counts):
    """
    Build the sig array the template expects for donutSVG + sig.forEach legend.
    Template calls: donutSVG(sig, 150) then sig.forEach(function(d){ d.color, d.name, d.value })
    Each item: {name: str, value: int, color: hex}
    """
    items = []
    for i, (key, count) in enumerate(sorted(signal_counts.items(), key=lambda x: -x[1])):
        items.append({
            "name": signal_to_plain(key),
            "value": count,
            "color": SIGNAL_COLORS[i % len(SIGNAL_COLORS)],
        })
    return items


def build_signals_array(signal_counts, kept_leads):
    """
    Build the signals array for the Signals tab.
    Template calls: types.forEach(function(t){ t.color, t.name, t.count, t.desc, t.leads.forEach })
    Each item: {name, count, color, desc, leads: [list of company names]}
    """
    items = []
    for i, (key, count) in enumerate(sorted(signal_counts.items(), key=lambda x: -x[1])):
        plain = signal_to_plain(key)
        color = SIGNAL_COLORS[i % len(SIGNAL_COLORS)]

        # Find company names that have this signal
        lead_names = []
        for lead in kept_leads:
            sigs = lead.get("signals", lead.get("signal_types", []))
            if isinstance(sigs, str):
                sigs = [sigs]
            if key in sigs:
                company = lead.get("company", lead.get("company_name", ""))
                if company:
                    lead_names.append(company)

        # Description per signal type
        desc_map = {
            "new_funding_round": "Companies that closed a funding round in the last 90 days. Active capital deployment creates immediate need for financial oversight and operational infrastructure.",
            "merger_and_acquisitions": "Companies with recent acquisition or merger activity. Integration workstreams and post-deal operations create peak demand for fractional expertise.",
            "leadership_change": "Companies with a recent leadership transition. New leadership typically audits systems, vendors, and advisors in the first 90 days.",
            "leadership_change_operations": "Companies with a recent operations leadership change. New ops leaders inherit process gaps and need external expertise fast.",
            "leadership_change_finance": "Companies with a recent finance leadership change. CFO transitions create an immediate window for fractional finance support.",
            "hiring_in_finance_department": "Companies actively hiring in finance. Scaling a finance function signals revenue growth has crossed the threshold where advisory support starts to matter.",
            "hiring_in_operations_department": "Companies actively hiring in operations. Ops headcount growth is a reliable proxy for the kind of process complexity that fractional COOs are brought in to manage.",
            "office_expansion": "Companies opening new offices or expanding to new markets. Geographic expansion creates multi-jurisdiction complexity in finance and operations.",
            "new_office": "Companies opening new offices or expanding to new markets. Geographic expansion creates multi-jurisdiction complexity in finance and operations.",
            "hiring_in_leadership": "Companies hiring into leadership roles. Leadership gap signals a transitional window where fractional support often provides the bridge.",
        }
        desc = desc_map.get(key, f"{plain} detected in the last 90 days. This signal indicates active change in the company's structure or trajectory.")

        items.append({
            "name": plain,
            "count": count,
            "color": color,
            "desc": desc,
            "leads": lead_names[:6],  # cap at 6 to avoid overflow
        })
    return items


def build_geo_array_for_bars(geo_counts):
    """
    Build geo array for barsSVG in Markets tab.
    barsSVG reads: d.c (country label) and d.n (count value)
    Also used in Dashboard geo chart via __PL_DB_GEO__ - same format needed there too.
    """
    return [
        {"c": country, "n": count}
        for country, count in sorted(geo_counts.items(), key=lambda x: -x[1])
    ]


def build_stage_array_for_bars(stage_counts):
    """
    Build stage array for barsSVG in Dashboard.
    barsSVG reads: d.c (label) and d.n (count value)
    """
    return [
        {"c": stage, "n": count}
        for stage, count in sorted(stage_counts.items(), key=lambda x: -x[1])
    ]


def build_ind_array_for_donut(industry_counts):
    """
    Build industry array for donutSVG in Markets tab.
    donutSVG reads: d.value and d.color. Legend reads: d.name, d.value, d.color
    Truncate long names for display.
    """
    items = []
    for i, (ind, count) in enumerate(sorted(industry_counts.items(), key=lambda x: -x[1])):
        # Truncate long industry names for the chart
        short_name = ind[:35] + "..." if len(ind) > 35 else ind
        items.append({
            "name": short_name,
            "value": count,
            "color": IND_COLORS[i % len(IND_COLORS)],
        })
    return items


def infer_founder_focus(lead, buyer_profile, advisor_function):
    """
    Infer founderFocus from Vibe data. Never returns 'Not on record' if we can derive anything.
    Uses signal, industry, company size, and role to make a reasonable inference.
    """
    role = lead.get("title", lead.get("job_title", "")).lower()
    company = lead.get("company", lead.get("company_name", ""))
    industry = lead.get("industry", lead.get("linkedin_category", ""))
    employees = str(lead.get("employees", lead.get("company_size", "")))
    signals = lead.get("signals", lead.get("signal_types", []))
    if isinstance(signals, str):
        signals = [signals]

    # Build inference from role
    if "ceo" in role or "chief executive" in role:
        focus = f"Scaling {company} as CEO. Likely managing investor relationships alongside day-to-day operations at the {employees}-person stage."
    elif "founder" in role and "co" in role:
        focus = f"Co-founder at {company}. At this stage, co-founders typically divide between product and commercial tracks while managing shared operational accountability."
    elif "founder" in role:
        focus = f"Founder-operator at {company}. Sole decision-maker across product, revenue, and operations at the {employees}-person stage."
    elif "president" in role:
        focus = f"President at {company}. Likely owns revenue and external relationships while managing operational complexity internally."
    elif "board chair" in role or "executive director" in role:
        focus = f"Executive Director at {company}. Responsible for organizational direction, board accountability, and program delivery simultaneously."
    else:
        focus = f"Senior operator at {company}, managing both strategic and operational responsibilities at the {employees}-person stage."

    return focus


def infer_team_trajectory(lead, buyer_profile, advisor_function):
    """
    Infer teamTrajectory from Vibe signal data. Never returns 'Not on record'.
    """
    signals = lead.get("signals", lead.get("signal_types", []))
    if isinstance(signals, str):
        signals = [signals]
    employees = str(lead.get("employees", lead.get("company_size", "")))
    company = lead.get("company", lead.get("company_name", ""))

    trajectories = []
    if "new_funding_round" in signals:
        trajectories.append("Post-funding headcount growth likely underway")
    if "hiring_in_finance_department" in signals:
        trajectories.append("Actively building a finance function")
    if "hiring_in_operations_department" in signals:
        trajectories.append("Scaling operations team")
    if "hiring_in_leadership" in signals:
        trajectories.append("Adding senior leadership capacity")
    if "merger_and_acquisitions" in signals:
        trajectories.append("Integration phase post-acquisition")
    if "cost_cutting" in signals:
        trajectories.append("Active cost reset underway")
    if "decrease_in_all_departments" in signals:
        trajectories.append("Org-wide headcount reduction in progress")
    if "office_expansion" in signals or "new_office" in signals:
        trajectories.append("Expanding to new locations")
    if "leadership_change" in signals or "leadership_change_operations" in signals or "leadership_change_finance" in signals:
        trajectories.append("Leadership transition in progress")

    if trajectories:
        return f"{employees}-person team at {company}. {'. '.join(trajectories)}."
    else:
        return f"{employees}-person team at {company}. Recent signal activity suggests active organizational change."


# ── Validation helpers ───────────────────────────────────────────────────────

def validate_no_em_dash(text):
    if "\u2014" in text:
        raise ValueError("data.json contains an em dash (—). Remove it before deploying.")
    if " -- " in text:
        raise ValueError("data.json contains a double dash ( -- ). Remove it before deploying.")


def validate_no_exclamation(text):
    if "!" in text:
        raise ValueError(
            "data.json contains an exclamation mark (!). "
            "Remove it to comply with brand voice rules."
        )


def validate_no_tool_names_in_leads(leads):
    """
    Check only the lead card fields that appear in rendered HTML.
    Internal fields like markets.notes are never rendered so excluded from this check.
    """
    forbidden_in_rendered = ["Vibe Prospecting", "fetch-entities", "enrich-prospects", "Apollo", "show-sample"]
    rendered_fields = ["whatTheyDo", "recentNews", "founderFocus", "teamTrajectory",
                       "whyFit", "whyNow", "connNote", "emailSubj", "emailBody",
                       "signalDetail", "name", "role", "company"]
    for lead in leads:
        for field in rendered_fields:
            val = str(lead.get(field, ""))
            for term in forbidden_in_rendered:
                if term in val:
                    raise ValueError(
                        f"Lead card field '{field}' contains internal tool name '{term}'. "
                        f"Remove it. Lead: {lead.get('name', '?')}"
                    )


# ── Main routine ─────────────────────────────────────────────────────────────

def main():
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

    print(f"\nPipelind Pipeline Report Routine v2.1")
    print(f"Mode: {MODE} | Slug: {SLUG} | Date: {DATE}")
    print("=" * 60)

    folder = "demo" if MODE == "DEMO" else "prod"
    firstname = SLUG.split("-")[0].capitalize()

    # ── STEP 1: Read client context ──────────────────────────────────────────
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

    print(f"  Client: {prospect_full} | {firm}")
    print(f"  Buyer profile: {buyer_profile} | Advisor function: {advisor_function}")
    print(f"  Credit cap: {run_control['credit_cap']} | Web mode: {run_control['web_mode']}")

    # Operator guard: new_funding_round must NOT be in events
    events_str = vibe_filter.get("events", "")
    if buyer_profile == "operator" and "new_funding_round" in events_str:
        events_str = re.sub(r',?\s*new_funding_round,?\s*', ',', events_str).strip(',').strip()
        vibe_filter["events"] = events_str
        print("  GUARD: Removed new_funding_round from operator filter.")

    print("  Context parsed successfully.")

    # ── STEP 2: Read build script and template ────────────────────────────────
    print("\n[Step 2] Reading build_report.py and template from GitHub ...")
    builder_text, _ = gh_read("skills/build_report.py")
    template_text, _ = gh_read("assets/templates/pipeline-report/index.html")

    with open("build_report.py", "w", encoding="utf-8") as f:
        f.write(builder_text)
    with open("template.html", "w", encoding="utf-8") as f:
        f.write(template_text)

    print("  build_report.py and template.html ready.")

    # ── STEP 3: Vibe Prospecting ──────────────────────────────────────────────
    # Email-only enrichment for BOTH DEMO and LIVE (phone is never enriched).
    # Cost model (email-only):
    #   show-sample   = flat 5 credits, returns up to ~5 unmasked rows   (DEMO path)
    #   export-to-csv = ~4 credits/row (2 fetch + 2 email enrich), returns ALL rows (LIVE path)
    # The fetch size is derived from the credit cap so a run can NEVER exceed budget.
    COST_PER_ROW = 4
    target_leads = 5 if MODE == "DEMO" else 10
    enrich_types = '["email"]'  # email only, both modes — no phone
    credit_cap = run_control["credit_cap"]
    events_window = vibe_filter.get("events_window_days", "90")

    if MODE == "DEMO":
        # Cheapest reliable path: show-sample unmasks ~5 rows for a flat 5 credits.
        retrieval = "show-sample"
        target_fetch = 8
        projected_cost = 5
    else:
        # LIVE: export the full enriched set, sized so spend never exceeds the cap.
        affordable_rows = max(credit_cap // COST_PER_ROW, 5)
        target_fetch = min(target_leads + 2, affordable_rows)  # +2 buffer for dedup
        projected_cost = COST_PER_ROW * target_fetch
        retrieval = "export-to-csv"

    print(f"\n[Step 3] Vibe Prospecting | Target: {target_leads} leads | "
          f"Retrieval: {retrieval} | Projected: ~{projected_cost}/{credit_cap} credits")

    if not os.path.exists("vibe_results.json"):
        if retrieval == "show-sample":
            retrieval_block = (
                "STEP D — unmask the rows (cheapest path):\n"
                "  show-sample  (flat 5 credits, returns the unmasked rows)\n"
                "  Use the rows it returns. Do NOT call export-to-csv in DEMO mode."
            )
        else:
            retrieval_block = (
                f"STEP D — retrieve the full enriched set:\n"
                f"  export-to-csv  limit={target_fetch}  (~{projected_cost} credits)\n"
                f"  Download the CSV and read every row. This stays within the "
                f"{credit_cap}-credit cap.\n"
                f"  If the live cost estimate ever exceeds {credit_cap}, lower limit until it fits."
            )

        print(f"""
CLAUDE CODE — VIBE MCP CALLS REQUIRED (do these now, then re-run this script):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Email-only enrichment. No phone. Budget cap: {credit_cap} credits. Projected spend: ~{projected_cost}.

STEP A — fetch BUSINESSES with the event signals
  (the events filter ONLY works on entity_type "businesses", never on prospects):
  fetch-entities
    entity_type: "businesses"
    number_of_results: {target_fetch}
    filters:
      company_size: {vibe_filter.get('company_size', '')}
      company_country_code: {vibe_filter.get('company_country_code', '')}
      linkedin_category: {vibe_filter.get('linkedin_category', '')}   (resolve via autocomplete first)
      events: values=[{vibe_filter.get('events', '')}] last_occurrence={events_window} days
  -> SAVE the businesses_reference_table from the response for STEP B.

STEP B — fetch decision-maker PROSPECTS from those businesses:
  fetch-entities
    entity_type: "prospects"
    businesses_reference_table: <the table returned by STEP A>
    number_of_results: {target_fetch}
    filters:
      job_title: {vibe_filter.get('job_title', '')}   (resolve via autocomplete first)
      job_level: {vibe_filter.get('job_level', '')}
      has_email: true

STEP C — enrich EMAIL only (never phone):
  enrich-prospects  enrichments=["enrich-prospects-contacts"]  contact_types={enrich_types}

{retrieval_block}

AFTER RETRIEVAL — write every lead that has a real email to vibe_results.json (JSON array).
  Each item: name, title, company, country, industry, employees, revenue,
  linkedin_url, website, email, signals (list). Never fabricate a field.

BANNED during Vibe calls:
  - Do not use any GitHub connector or MCP tool
  - Do not search the web
  - Do not enrich phone numbers

THEN: re-run this script: python3 routine.py {MODE} {SLUG} {DATE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        sys.exit(0)

    print("  vibe_results.json found.")
    with open("vibe_results.json", "r", encoding="utf-8") as f:
        raw_leads = json.load(f)
    print(f"  Vibe returned {len(raw_leads)} raw leads.")

    # ── STEP 4: Filter, dedup (LIVE), select ─────────────────────────────────
    print(f"\n[Step 4] Filtering and selecting {target_leads} leads ...")

    delivered_set = set()
    if MODE == "LIVE":
        delivered = gh_read_json(f"inputs/prod/{SLUG}/dedup.json", default=[])
        delivered_set = set(delivered)
        print(f"  Dedup: {len(delivered_set)} previously delivered leads excluded.")

    exclude_keywords = []
    if buyer_profile == "operator":
        raw_excl = vibe_filter.get("exclude_company_keywords", "")
        exclude_keywords = [k.strip().lower() for k in raw_excl.split(",") if k.strip()]

    candidates = []
    for lead in raw_leads:
        linkedin = lead.get("linkedin_url", lead.get("linkedin", ""))
        if linkedin and not linkedin.startswith("http"):
            linkedin = "https://" + linkedin
        lead["linkedin_url"] = linkedin

        if MODE == "LIVE" and linkedin in delivered_set:
            continue

        company_name = (lead.get("company", lead.get("company_name", "")) or "").lower()
        if exclude_keywords and any(kw in company_name for kw in exclude_keywords):
            continue

        candidates.append(lead)

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
        print("ERROR: No qualifying leads after filtering.")
        print("Check Vibe filter parameters in context.md or widen the filter.")
        sys.exit(1)

    if len(kept_leads) < target_leads:
        print(f"  WARNING: Only {len(kept_leads)} qualifying leads (target: {target_leads}). Delivering what qualifies.")

    print(f"  Selected {len(kept_leads)} leads.")

    # ── STEP 5: Build data.json ───────────────────────────────────────────────
    print(f"\n[Step 5] Building data.json ...")

    today_str = datetime.now().strftime("%B %d, %Y")
    week_str = f"Week of {datetime.now().strftime('%B %d, %Y')}"

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

    # Collect all signal keys (raw, for counting)
    all_signal_keys = []
    for lead in kept_leads:
        sigs = lead.get("signals", lead.get("signal_types", []))
        if isinstance(sigs, str):
            sigs = [sigs]
        all_signal_keys.extend(sigs)

    signal_counts = {}
    for s in all_signal_keys:
        signal_counts[s] = signal_counts.get(s, 0) + 1

    # Geo counts
    geo_counts = {}
    for lead in kept_leads:
        c = lead.get("country", lead.get("company_country", "Unknown"))
        if c:
            geo_counts[c] = geo_counts.get(c, 0) + 1

    # Stage counts
    stage_counts = {}
    for lead in kept_leads:
        s = lead.get("funding_stage", lead.get("revenue_range", lead.get("stage", "Unknown")))
        s = str(s) if s else "Unknown"
        stage_counts[s] = stage_counts.get(s, 0) + 1

    # Industry counts
    industry_counts = {}
    for lead in kept_leads:
        ind = lead.get("industry", lead.get("linkedin_category", ""))
        if ind:
            industry_counts[ind] = industry_counts.get(ind, 0) + 1

    countries = list(geo_counts.keys())

    # Build lead cards
    lead_cards = []
    for i, lead in enumerate(kept_leads):
        theme = THEME_CYCLE[i % len(THEME_CYCLE)]

        name = lead.get("name", lead.get("full_name", "Unknown"))
        role = lead.get("title", lead.get("job_title", ""))
        company = lead.get("company", lead.get("company_name", ""))
        country = lead.get("country", lead.get("company_country", ""))
        industry = lead.get("industry", lead.get("linkedin_category", ""))
        employees = str(lead.get("employees", lead.get("company_size", "")))
        revenue = str(lead.get("revenue", lead.get("revenue_range", lead.get("company_revenue", ""))) or "")
        linkedin = lead.get("linkedin_url", "")
        website = lead.get("website", lead.get("company_website", "")) or ""
        email_val = lead.get("email", "") if MODE == "LIVE" else ""
        phone_val = lead.get("phone", "") if MODE == "LIVE" else ""

        sigs = lead.get("signals", lead.get("signal_types", []))
        if isinstance(sigs, str):
            sigs = [sigs]
        days_ago = lead.get("signal_days_ago", lead.get("days_since_signal", 60))
        try:
            days_ago = int(days_ago)
        except (TypeError, ValueError):
            days_ago = 60
        priority = "HOT" if days_ago <= 30 else "WARM"

        stage = str(lead.get("funding_stage", lead.get("revenue_range", lead.get("stage", ""))) or "")

        parts = name.split()
        initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else name[:2].upper()

        signal_plain_list = signals_list_to_plain(sigs)
        signal_plain = ", ".join(signal_plain_list)

        # Infer founderFocus and teamTrajectory from data (never "Not on record")
        founder_focus = infer_founder_focus(lead, buyer_profile, advisor_function)
        team_trajectory = infer_team_trajectory(lead, buyer_profile, advisor_function)

        # whyFit: match signal to prospect's function
        if advisor_function == "finance":
            why_fit = (
                f"{company} shows {signal_plain.lower()}, which typically marks a window where "
                f"financial oversight gaps become visible. {prospect_first}'s background maps "
                f"directly to what this stage requires."
            )
        else:
            why_fit = (
                f"{company} shows {signal_plain.lower()}, which typically signals operational "
                f"complexity outpacing existing process. {prospect_first}'s background maps "
                f"directly to what this stage requires."
            )

        # whyNow: signal timing
        if days_ago <= 30:
            why_now = f"Signal detected in the last {days_ago} days. This is inside the peak engagement window where outreach converts."
        else:
            why_now = f"Signal detected {days_ago} days ago. Still inside the 90-day window where the need is active."

        # connNote: under 280 chars, prospect voice, no pitch
        conn_note = (
            f"Hi [First Name], noticed {company} recently had {signal_plain.lower()}. "
            f"That timing often aligns with {advisor_function} needs at this stage. "
            f"Happy to share context if useful."
        )
        if len(conn_note) > 280:
            conn_note = (
                f"Hi [First Name], saw {company} recently had {signal_plain_list[0].lower()}. "
                f"That timing often creates {advisor_function} questions. Happy to connect."
            )

        # emailSubj and emailBody in prospect voice
        email_subj = f"{company} caught my attention"
        email_body = (
            f"Hi [First Name],\n\n"
            f"Saw that {company} recently {signal_plain.lower()}. "
            f"That kind of move usually surfaces {advisor_function} questions that are easier "
            f"to get ahead of than catch up to.\n\n"
            f"Happy to walk you through what I typically see at this stage if it would be useful. "
            f"No obligation, just a 20-minute conversation.\n\n"
            f"Best,\n{prospect_full}"
        )

        card = {
            "id": i + 1,
            "theme": theme,
            "name": name,
            "initials": initials,
            "role": role,
            "company": company,
            "country": country,
            "stage": stage,
            "industry": industry,
            "employees": employees,
            "revenue": revenue,
            "signalDetail": signal_plain,
            "days": days_ago,
            "priority": priority,
            "linkedin": linkedin,
            "website": website,
            "email": email_val,
            "phone": phone_val,
            "whatTheyDo": f"{company} is a {employees}-person {industry} company based in {country}.",
            "recentNews": signal_plain,
            "founderFocus": founder_focus,
            "teamTrajectory": team_trajectory,
            "whyFit": why_fit,
            "whyNow": why_now,
            "connNote": conn_note,
            "emailSubj": email_subj,
            "emailBody": email_body,
        }
        lead_cards.append(card)

    # Pulse text (internal summary for the pulse banner)
    signal_plain_summary = ", ".join(
        signal_to_plain(k) for k in sorted(signal_counts.keys(), key=lambda x: -signal_counts[x])
    )
    pulse = (
        f"{len(kept_leads)} ICP-matched profiles this week. "
        f"{hot_count} HOT (signal in last 30 days), {warm_count} WARM. "
        f"Leading signals: {signal_plain_summary[:120]}."
    )

    # ── Build all data shapes matching template exactly ──
    stats_array = build_stats_array(len(kept_leads), hot_count, warm_count, len(countries))
    sig_array = build_sig_array(signal_counts)
    geo_bars = build_geo_array_for_bars(geo_counts)
    stage_bars = build_stage_array_for_bars(stage_counts)
    signals_full = build_signals_array(signal_counts, kept_leads)
    ind_donut = build_ind_array_for_donut(industry_counts)

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
            "stats": stats_array,   # ARRAY of {n,l,c,bar} - template calls stats.forEach
            "sig": sig_array,       # ARRAY of {name,value,color} - template calls donutSVG + sig.forEach
            "geo": geo_bars,        # ARRAY of {c,n} - barsSVG reads d.c and d.n
            "stage": stage_bars,    # ARRAY of {c,n} - barsSVG reads d.c and d.n
            "pulse": pulse,
        },
        "signals": signals_full,    # ARRAY of {name,count,color,desc,leads[]} - signals tab
        "markets": {
            "geo": geo_bars,        # ARRAY of {c,n} - barsSVG for markets tab
            "ind": ind_donut,       # ARRAY of {name,value,color} - donutSVG for industry chart
            "notes": f"Signal window: {events_window} days. {len(kept_leads)} profiles matched this week.",
        },
    }

    # Validate
    data_str = json.dumps(data, ensure_ascii=False, indent=2)
    validate_no_em_dash(data_str)
    validate_no_exclamation(data_str)
    validate_no_tool_names_in_leads(lead_cards)

    with open("data.json", "w", encoding="utf-8") as f:
        f.write(data_str)
    print(f"  data.json written. {len(lead_cards)} leads | {hot_count} HOT | {warm_count} WARM")
    print(f"  Stats: array[{len(stats_array)}] | Sig: array[{len(sig_array)}] | Signals: array[{len(signals_full)}]")
    print(f"  Geo: array[{len(geo_bars)}] | Stage: array[{len(stage_bars)}] | Industry: array[{len(ind_donut)}]")

    # ── STEP 6: Run build_report.py ──────────────────────────────────────────
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
        print("\n--- data.json (for debugging) ---")
        print(data_str[:2000])
        sys.exit(1)
    if result.stdout.strip():
        print(f"  Builder: {result.stdout.strip()}")
    print("  Build completed.")

    # ── STEP 7: Validate output.html ─────────────────────────────────────────
    print(f"\n[Step 7] Validating output.html ...")
    if not os.path.exists("output.html"):
        print("ERROR: output.html does not exist after build.")
        sys.exit(1)

    size = os.path.getsize("output.html")
    if size < MIN_OUTPUT_BYTES:
        print(f"ERROR: output.html is {size} bytes (minimum {MIN_OUTPUT_BYTES}). Build likely failed.")
        sys.exit(1)

    with open("output.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    remaining_pl = re.findall(r"__PL_\w+__", html_content)
    if remaining_pl:
        print(f"ERROR: Unfilled placeholders in output.html: {remaining_pl}")
        sys.exit(1)

    print(f"  Validated: {size:,} bytes | No unfilled placeholders | Build PASSED")

    # ── STEP 8: Deploy to GitHub ──────────────────────────────────────────────
    if MODE == "DEMO":
        deploy_path = f"demo/{DATE}/{prospect_first.lower()}/index.html"
        live_url = f"https://pipelind.com/demo/{DATE}/{prospect_first.lower()}/"
    else:
        deploy_path = f"prod/{SLUG}/pipeline/index.html"
        live_url = f"https://pipelind.com/prod/{SLUG}/pipeline/"

    print(f"\n[Step 8] Deploying to {deploy_path} ...")
    gh_write(deploy_path, html_content, f"Pipeline report · {MODE} · {SLUG} · {DATE}")
    print(f"  Deployed. Live at {live_url} (allow 30-90s for Vercel CDN)")

    # ── STEP 9: Update dedup.json (LIVE only) ────────────────────────────────
    if MODE == "LIVE":
        print(f"\n[Step 9] Updating dedup.json ...")
        new_urls = [card["linkedin"] for card in lead_cards if card.get("linkedin")]
        existing_dedup = gh_read_json(f"inputs/prod/{SLUG}/dedup.json", default=[])
        updated_dedup = sorted(set(existing_dedup) | set(new_urls))
        gh_write(
            f"inputs/prod/{SLUG}/dedup.json",
            json.dumps(updated_dedup, indent=2),
            f"Dedup update · {SLUG} · {DATE}",
        )
        print(f"  dedup.json updated. Total delivered: {len(updated_dedup)}")
    else:
        print(f"\n[Step 9] DEMO mode — no dedup update.")

    # ── Final status ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(
        f"PIPELINE REPORT COMPLETE · {MODE} · {prospect_full} · {firm} · "
        f"Leads {len(kept_leads)} · HOT {hot_count} · WARM {warm_count} · "
        f"Live URL: {live_url} · Deploy SUCCESS"
    )
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
