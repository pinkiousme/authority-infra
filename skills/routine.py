#!/usr/bin/env python3
"""
routine.py - Pipelind Pipeline Report Runner
Version: 2.2 - June 2026

Encodes the complete 9-step pipeline report build as a deterministic Python
script. Claude Code's only job is: python3 routine.py MODE SLUG DATE

Usage:
  python3 routine.py DEMO diane-maistros 19062026
  python3 routine.py LIVE anthony-perez 20062026

Environment required:
  GH_TOKEN  A GitHub token with write (contents) access to the repo, provided
            ONLY via the cloud environment's Environment Variables (never hard-
            coded in this file - the repo is public). Used solely to git-push the
            built report to `main`.

  Why a token + git push (and not the API or the GitHub App):
  - In cloud Routines, direct api.github.com is blocked by the network proxy
    ("GitHub access is not enabled for this session"), so the old API approach
    cannot work regardless of credentials.
  - The connected GitHub App is read-only, so MCP/App writes fail too.
  - git-over-HTTPS to github.com IS reachable, so pushing with GH_TOKEN is the
    one working write path. READS come from the local clone (no token needed).

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

TIERED TRUST DATA POLICY (v2.2):
  - Prioritise Tier 1 leads: the signal has a real public source link (news/web URL,
    from fetch-businesses-events data.link). The card renders a clickable
    "Verify this signal" link.
  - Backfill with Tier 2 only when Tier 1 is short: a genuine detected signal with
    no public article, but with structured evidence (signal_proof: event type, date,
    and specifics such as a court/case, headcount change, or partner). The card
    renders that evidence inline as "Signal evidence" instead of a link.
  - Drop any lead with NEITHER a source link NOR signal_proof. Never fabricate.
  - Tier 1 always ranks above Tier 2. Same logic for DEMO and LIVE.

What this script NEVER does:
  - Call api.github.com (blocked by the cloud network proxy)
  - Hardcode a token in this file (the repo is public; GH_TOKEN comes from the
    environment only, and is never printed or written into the repo)
  - Search the web
  - Enrich phone numbers (email only)
  - Deploy a lead with no provenance (neither a source link nor signal evidence)
  - Exceed the context credit_cap (fetch size is derived from it)
  - Edit template.html
  - Deploy a file under 50,000 bytes
  - Ask questions or pause for permission
"""

import sys
import os
import json
import shutil
import tempfile
import subprocess
import re
from datetime import datetime


# -- Constants ---------------------------------------------------------------

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


# -- Repo I/O helpers ---------------------------------------------------------
# This routine runs inside a fresh clone of the repo. All READS come from the
# local working tree (no network, no token). All WRITES are staged locally and
# then published to `main` by perform_git_deploy() via a git push to github.com
# using GH_TOKEN (api.github.com is proxy-blocked and the GitHub App is read-only
# in cloud Routines, so a token git push is the one working write path).

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files staged for deployment, drained into deploy_manifest.json at the end.
_DEPLOY_ACTIONS = []


def _local_path(path):
    return os.path.join(REPO_ROOT, path)


def gh_read(path):
    """Read a file from the local clone. Returns (text, None).
    Falls back to origin/main via git (no HTTP API) if the file is not in the
    working tree. Raises FileNotFoundError if it exists in neither place."""
    local = _local_path(path)
    if os.path.isfile(local):
        with open(local, "r", encoding="utf-8") as f:
            return f.read(), None
    try:
        out = subprocess.run(
            ["git", "-C", REPO_ROOT, "show", f"origin/main:{path}"],
            capture_output=True, text=True,
        )
        if out.returncode == 0:
            return out.stdout, None
    except Exception:
        pass
    raise FileNotFoundError(
        f"'{path}' not found in the working tree ({local}) or on origin/main. "
        f"Make sure it is committed and the clone is up to date."
    )


def gh_read_json(path, default=None):
    """Read a JSON file from the local clone. Returns default if it does not exist."""
    try:
        text, _ = gh_read(path)
        return json.loads(text)
    except FileNotFoundError:
        return default if default is not None else []


def queue_deploy(path, content_str, commit_message):
    """Stage a file for deployment to `main`.
    Writes the content into the local repo tree and records the action so
    perform_git_deploy() can publish it. Returns the local path written."""
    local = _local_path(path)
    os.makedirs(os.path.dirname(local), exist_ok=True)
    with open(local, "w", encoding="utf-8") as f:
        f.write(content_str)
    _DEPLOY_ACTIONS.append({
        "repo_path": path,
        "local_path": local,
        "message": commit_message,
        "bytes": len(content_str.encode("utf-8")),
    })
    return local


def _git_env():
    """Environment for git that trusts the agent-proxy CA when present."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    ca = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(ca):
        env["GIT_SSL_CAINFO"] = ca
    return env


def _run_git(args, env, cwd=None):
    """Run a git command, raising with a token-scrubbed message on failure."""
    proc = subprocess.run(
        ["git"] + args, env=env, cwd=cwd,
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        token = os.environ.get("GH_TOKEN", "")
        msg = (proc.stderr or proc.stdout or "").strip()
        if token:
            msg = msg.replace(token, "***")
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {msg}")
    return proc


def perform_git_deploy(actions, commit_message):
    """Publish the staged files to `main` by pushing over git to github.com.

    Why git and not the API: in cloud Routines, direct api.github.com is blocked
    by the network proxy and the connected GitHub App is read-only. git-over-HTTPS
    to github.com IS reachable, so a token push is the one working write path.

    The token comes ONLY from the GH_TOKEN environment variable (set it in the
    cloud environment config, never in the repo). The repo is public, so the
    clone reads without the token; the token is used only for the push and is
    never written into the repo or printed.
    """
    if not actions:
        print("  Nothing to deploy.")
        return

    token = os.environ.get("GH_TOKEN")
    if not token:
        print(
            "  DEPLOY SKIPPED: GH_TOKEN is not set.\n"
            "  Set GH_TOKEN in the cloud environment's Environment Variables so the\n"
            "  routine can push to github.com (api.github.com is blocked here and the\n"
            "  GitHub App is read-only). Staged files remain in deploy_manifest.json."
        )
        raise SystemExit(1)

    env = _git_env()
    clone_url = f"https://github.com/{REPO}.git"
    push_url = f"https://x-access-token:{token}@github.com/{REPO}.git"
    tmp = tempfile.mkdtemp(prefix="pl_deploy_")
    try:
        _run_git(["clone", "--depth", "1", "--branch", "main", clone_url, tmp], env)
        for a in actions:
            dest = os.path.join(tmp, a["repo_path"])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(a["local_path"], dest)
        _run_git(["-C", tmp, "add", "-A"], env)
        # Nothing changed vs main? Then there is nothing to deploy.
        if subprocess.run(["git", "-C", tmp, "diff", "--cached", "--quiet"],
                          env=env).returncode == 0:
            print("  No changes to deploy (main already up to date).")
            return
        _run_git([
            "-C", tmp,
            "-c", f"user.email={COMMITTER['email']}",
            "-c", f"user.name={COMMITTER['name']}",
            "commit", "-m", commit_message,
        ], env)
        _run_git(["-C", tmp, "push", push_url, "HEAD:main"], env)
        print(f"  Deployed {len(actions)} file(s) to main via git push to github.com.")
        for a in actions:
            print(f"    - {a['repo_path']}  ({a['bytes']:,} bytes)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# -- Context parser -----------------------------------------------------------

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


# -- Signal plain-language mapping --------------------------------------------

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
        "new_partnership": "New strategic partnership",
        "lawsuits_and_legal_issues": "Legal or regulatory matter",
        "new_product": "New product launch",
        "new_funding_round": "Recent funding round",
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


# -- ICP settings (data-driven, never hardcoded in the template) --------------

_TITLE_EXPAND = {
    "chief executive officer": "CEO",
    "chief operating officer": "COO",
    "chief financial officer": "CFO",
    "chief operations officer": "COO",
}


def _pretty_list(csv, expand=False):
    """Turn a comma string from the frozen filter into a clean display string."""
    out = []
    for part in str(csv or "").split(","):
        p = part.strip()
        if not p:
            continue
        if expand and p.lower() in _TITLE_EXPAND:
            out.append(_TITLE_EXPAND[p.lower()])
        else:
            out.append(p.title() if p.islower() else p)
    return ", ".join(out)


def build_icp_settings(vibe_filter, events_window):
    """Build the ICP Settings rows from the client's frozen filter so the report
    shows THIS client's real targeting, never a hardcoded generic ICP.
    Returns a list of [label, value] pairs the template renders."""
    titles = _pretty_list(vibe_filter.get("job_title", ""), expand=True)
    industries = _pretty_list(vibe_filter.get("linkedin_category", ""))
    geo = (vibe_filter.get("company_country_code", "") or "").upper()
    size = (vibe_filter.get("company_size", "") or "").strip()
    revenue = (vibe_filter.get("revenue_floor", "") or "").strip()
    events = [e.strip() for e in str(vibe_filter.get("events", "")).split(",") if e.strip()]
    signal_types = ", ".join(signal_to_plain(e) for e in events)
    return [
        ["Target Titles", titles or "Not set"],
        ["Industries", industries or "Not set"],
        ["Geography", geo or "Not set"],
        ["Company Size", (size + " employees") if size else "Not set"],
        ["Revenue Band", (revenue + " and up") if revenue else "Not set"],
        ["Signal Types", signal_types or "Not set"],
        ["Signal Window", f"0-30 days HOT / 31-{events_window} days WARM"],
    ]


def build_coverage_notes(kept_leads, geo_counts, industry_counts, events_window):
    """Data-driven Markets coverage notes (never hardcoded SaaS/venture copy)."""
    n = len(kept_leads)
    countries = sorted(geo_counts, key=lambda c: -geo_counts[c])
    geo_phrase = countries[0] if len(countries) == 1 else (
        ", ".join(countries[:-1]) + " and " + countries[-1]) if countries else "the target market"
    top_inds = sorted(industry_counts, key=lambda i: -industry_counts[i])[:3]
    ind_phrase = "; ".join(top_inds) if top_inds else "the target sectors"
    return (
        f"This week's pipeline covers {n} verified profile{'s' if n != 1 else ''} "
        f"in {geo_phrase}, concentrated in {ind_phrase}. Every profile carries a "
        f"detected operating signal inside the {events_window}-day window, ranked "
        f"by recency and signal strength."
    )


# -- Data shape builders (matching template exactly) --------------------------

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


# -- Validation helpers -------------------------------------------------------

def normalize_personal_linkedin(raw):
    """Return a canonical personal LinkedIn profile URL, or '' if the value is
    not a real personal profile.

    A lead is a decision-maker, so the only acceptable LinkedIn is their personal
    profile: linkedin.com/in/<slug>. Company pages (linkedin.com/company/...),
    school/showcase pages, search/feed URLs, masked placeholders, or a bare name
    are all rejected (return ''), so the report never links a person to the wrong
    page. This is what prevents the 'company page instead of the person' bug.
    """
    if not raw:
        return ""
    url = str(raw).strip()
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url.lstrip("/")
    m = re.match(
        r'^https?://([a-z0-9-]+\.)?linkedin\.com/in/([A-Za-z0-9_%\-\.]+)/?',
        url, re.I,
    )
    if not m:
        return ""
    slug = m.group(2).strip(".-")
    if not slug or slug.lower() in ("unknown", "masked", "n-a", "na", "none", "null"):
        return ""
    return f"https://www.linkedin.com/in/{slug}"


def validate_linkedin_in_leads(lead_cards):
    """Belt-and-suspenders: every deployed lead must carry a personal /in/ profile.
    Raises if any card slipped through with a non-personal or empty LinkedIn."""
    bad = []
    for c in lead_cards:
        li = c.get("linkedin", "")
        if not normalize_personal_linkedin(li):
            bad.append(f"{c.get('name', '?')} -> {li or '(empty)'}")
    if bad:
        raise ValueError(
            "These deployed leads do not have a valid personal LinkedIn profile "
            "(linkedin.com/in/...): " + "; ".join(bad)
        )


def validate_no_em_dash(text):
    if "\u2014" in text:
        raise ValueError("data.json contains an em dash (-). Remove it before deploying.")
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


# -- Main routine -------------------------------------------------------------

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

    # -- STEP 1: Read client context ------------------------------------------
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

    # -- STEP 2: Read build script and template --------------------------------
    print("\n[Step 2] Reading build_report.py and template from local clone ...")
    builder_text, _ = gh_read("skills/build_report.py")
    template_text, _ = gh_read("assets/templates/pipeline-report/index.html")

    with open("build_report.py", "w", encoding="utf-8") as f:
        f.write(builder_text)
    with open("template.html", "w", encoding="utf-8") as f:
        f.write(template_text)

    print("  build_report.py and template.html ready.")

    # -- STEP 3: Vibe Prospecting ----------------------------------------------
    # Email-only enrichment for BOTH DEMO and LIVE (phone is never enriched).
    # Cost model (email-only):
    #   show-sample   = flat 5 credits, returns up to ~5 unmasked rows   (DEMO path)
    #   export-to-csv = ~4 credits/row (2 fetch + 2 email enrich), returns ALL rows (LIVE path)
    # The fetch size is derived from the credit cap so a run can NEVER exceed budget.
    COST_PER_ROW = 4
    target_leads = 5 if MODE == "DEMO" else 10
    enrich_types = '["email"]'  # email only, both modes - no phone
    credit_cap = run_control["credit_cap"]
    events_window = vibe_filter.get("events_window_days", "90")

    # Verified+emailable owner-level decision-makers are sparse: only ~3% of the
    # companies that match a news event also have a reachable C-suite email. So the
    # BUSINESS pool must be heavily oversampled (it is free exploration) to surface
    # enough verified leads. Only the final email enrich/export costs credits.
    business_pool = max(200, target_leads * 30)

    # Headroom fallback (LIVE fills target_leads cards): if the tight ICP filter is
    # short, broaden size then sector. Configurable per client in context.md.
    broaden_size = vibe_filter.get("broaden_size", "501-1000, 1001-5000")
    broaden_categories = vibe_filter.get("broaden_categories", "")
    broaden_sector_text = broaden_categories or (
        "the adjacent sectors the client credibly serves "
        "(e.g. manufacturing, logistics, professional services, hospitality)")

    if MODE == "DEMO":
        # Cheapest reliable path: show-sample unmasks ~5 rows for a flat 5 credits.
        retrieval = "show-sample"
        target_fetch = 8
        projected_cost = 5
    else:
        # LIVE: export the verified enriched set, sized so spend never exceeds the cap.
        affordable_rows = max(credit_cap // COST_PER_ROW, 5)
        target_fetch = min(target_leads + 2, affordable_rows)  # +2 buffer for dedup
        projected_cost = COST_PER_ROW * target_fetch
        retrieval = "export-to-csv"

    print(f"\n[Step 3] Vibe Prospecting | Target: {target_leads} leads | "
          f"Retrieval: {retrieval} | Projected: ~{projected_cost}/{credit_cap} credits")

    if not os.path.exists("vibe_results.json"):
        if retrieval == "show-sample":
            retrieval_block = (
                "STEP D - unmask the rows (cheapest path):\n"
                "  show-sample  (flat 5 credits, returns the unmasked rows)\n"
                "  Use the rows it returns. Do NOT call export-to-csv in DEMO mode."
            )
        else:
            retrieval_block = (
                f"STEP D - retrieve the full enriched set:\n"
                f"  export-to-csv  limit={target_fetch}  (~{projected_cost} credits)\n"
                f"  Download the CSV and read every row. This stays within the "
                f"{credit_cap}-credit cap.\n"
                f"  If the live cost estimate ever exceeds {credit_cap}, lower limit until it fits."
            )

        print(f"""
CLAUDE CODE - VIBE MCP CALLS REQUIRED (do these now, then re-run this script):
=============================================================
Email-only enrichment. No phone. Budget cap: {credit_cap} credits. Projected spend: ~{projected_cost}.

STEP A - fetch a LARGE pool of BUSINESSES with the event signals
  (events filter ONLY works on entity_type "businesses"; oversample because verified+
   emailable decision-makers are sparse - this fetch is free exploration):
  fetch-entities
    entity_type: "businesses"
    number_of_results: {business_pool}
    filters:
      company_size: {vibe_filter.get('company_size', '')}
      company_country_code: {vibe_filter.get('company_country_code', '')}
      linkedin_category: {vibe_filter.get('linkedin_category', '')}   (resolve via autocomplete first)
      events: values=[{vibe_filter.get('events', '')}] last_occurrence={events_window} days
  -> SAVE the businesses_reference_table from the response for STEP B.

STEP B - fetch decision-maker PROSPECTS from those businesses (also free):
  fetch-entities
    entity_type: "prospects"
    businesses_reference_table: <the table returned by STEP A>
    number_of_results: {business_pool}
    filters:
      job_title: {vibe_filter.get('job_title', '')}   (resolve via autocomplete first)
      job_level: {vibe_filter.get('job_level', '')}
  -> drop AI/tech/venture companies (exclude_company_keywords) and any over the size ceiling.
     Enrich + retrieve only the top {target_fetch} survivors so spend stays within the cap.

STEP C - VERIFY the signals (mandatory - real provenance only, never fabricate):
  Run fetch-businesses-events on the businesses_reference_table from STEP A,
  event_types = your event list, timestamp_from = {events_window} days ago.
  Each record has data.description, data.title, data.link, and type-specific
  fields (court/case, partner_company, department_change, etc.).
  Classify each company into a TRUST TIER:
   - Tier 1 (preferred): the event has a real public data.link (http...). Keep the link.
   - Tier 2 (fallback, high-intent): a genuine detected event with NO usable public
     link, but real structured detail. Build a short signal_proof string from that
     detail (event type + date + specifics, noting it is a detected business signal).
   - Drop a company only if it has neither a link nor any structured detail.

STEP D - enrich EMAIL only (never phone) for the surviving companies:
  enrich-prospects  enrichments=["enrich-prospects-contacts"]  contact_types={enrich_types}

{retrieval_block}

STEP E - FILL THE REPORT IF SHORT (only if you have fewer than {target_leads} deliverable leads):
  Quality first: the tight filter above is the primary pass. ONLY if it yields fewer
  than {target_leads} leads (Tier 1 + Tier 2, after dedup) do you broaden, repeating
  A-D to backfill the gap in this order, and stopping the MOMENT you reach {target_leads}:
    Round 1 - broaden SIZE: add company_size bands [{broaden_size}] (keep sectors + events).
    Round 2 - broaden SECTOR: also add linkedin_category [{broaden_sector_text}].
  Every broadened lead still needs provenance (source link or signal_proof) and a real
  email, still excludes AI/tech/venture, ranks Tier 1 above Tier 2, and dedups against
  earlier rounds and dedup.json. Enrich/export only the incremental rows you keep so you
  never exceed the {credit_cap}-credit cap. If even the broadened pool runs out, deliver
  what qualifies - never fabricate or pad to hit the number.

LINKEDIN URL RULE (mandatory - this is the prospect's personal profile):
  linkedin_url MUST be the DECISION-MAKER's personal profile from the unmasked
  prospect row (prospect_linkedin), i.e. linkedin.com/in/<slug>. NEVER put the
  company page (linkedin.com/company/...) or a guessed/constructed URL there.
  If show-sample/export does not return a personal /in/ profile for a prospect,
  leave linkedin_url empty - the build will drop that lead rather than link the
  wrong page. Do not fabricate or infer a profile URL.

AFTER RETRIEVAL - write every lead that has a real email to vibe_results.json (JSON array),
  Tier 1 first, then Tier 2 only to backfill toward {target_leads}.
  Each item: name, title, company, country, industry, employees, revenue,
  linkedin_url (the personal linkedin.com/in/ profile - see LINKEDIN URL RULE),
  website, email, signals (list), signal_days_ago,
  signal_description (the event detail, stated as plain fact),
  AND provenance - at least ONE of:
    source       (Tier 1: the event data.link, a real public URL) + source_title, OR
    signal_proof (Tier 2: the structured detection evidence, e.g.
                  "Detected signal: legal matter, NSW Supreme Court [case], recorded 14 Apr 2026").
  A lead with NEITHER source nor signal_proof must NOT be written. Never invent a URL.

SOURCE OF TRUTH (no fabrication, ever):
  EVERY lead written to vibe_results.json MUST come from an unmasked Vibe row
  (show-sample in DEMO, export in LIVE). The name, title, company, employees,
  revenue, industry, signals, signal dates and linkedin_url must be the values
  Vibe returned for that exact row. Do NOT add a company or person from memory,
  prior knowledge, or the web. Do NOT invent or "improve" any field. If a real
  row is not available, deliver fewer leads - never pad with invented ones.
  (The build enforces this: it drops any lead without a real personal /in/
  profile and without provenance, so fabricated/placeholder leads will not ship.)

BANNED during Vibe calls:
  - Do not use any GitHub connector or MCP tool
  - Do not search the web (except to confirm a real public source URL you will cite)
  - Do not enrich phone numbers
  - Do not write any lead with no provenance (no link and no signal evidence)
  - Do not write any lead that did not come from a real unmasked Vibe row

THEN: re-run this script: python3 routine.py {MODE} {SLUG} {DATE}
=============================================================
""")
        sys.exit(0)

    print("  vibe_results.json found.")
    with open("vibe_results.json", "r", encoding="utf-8") as f:
        raw_leads = json.load(f)
    print(f"  Vibe returned {len(raw_leads)} raw leads.")

    # -- STEP 4: Filter, dedup (LIVE), select ---------------------------------
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
    dropped_unverified = 0
    dropped_bad_linkedin = 0
    for lead in raw_leads:
        # A lead must have a REAL personal LinkedIn profile (linkedin.com/in/...).
        # Company pages / masked / malformed values are rejected so the report
        # never links a decision-maker to the wrong page.
        linkedin = normalize_personal_linkedin(
            lead.get("linkedin_url", lead.get("linkedin", "")))
        lead["linkedin_url"] = linkedin
        if not linkedin:
            dropped_bad_linkedin += 1
            continue

        if MODE == "LIVE" and linkedin in delivered_set:
            continue

        company_name = (lead.get("company", lead.get("company_name", "")) or "").lower()
        if exclude_keywords and any(kw in company_name for kw in exclude_keywords):
            continue

        # TIERED TRUST POLICY (prioritise verified-source leads, never fabricate):
        #   Tier 1 = signal has a public source link (http...). Clickable proof.
        #   Tier 2 = no public article, but a real detected signal with structured
        #            evidence (signal_proof). Shown as on-card evidence, transparently.
        #   Drop only leads with NEITHER a source link NOR signal_proof.
        # Tier 1 always ranks above Tier 2; Tier 2 backfills only if Tier 1 is short.
        src = (lead.get("source", lead.get("source_url", "")) or "").strip()
        proof = (lead.get("signal_proof", lead.get("signalProof",
                 lead.get("evidence", ""))) or "").strip()
        has_source = src.startswith("http")
        has_proof = bool(proof)
        if not (has_source or has_proof):
            dropped_unverified += 1
            continue
        lead["_tier"] = 0 if has_source else 1
        candidates.append(lead)

    if dropped_bad_linkedin:
        print(f"  LinkedIn policy: dropped {dropped_bad_linkedin} lead(s) without a valid personal profile (linkedin.com/in/...).")
    if dropped_unverified:
        print(f"  Trust policy: dropped {dropped_unverified} lead(s) with neither a source link nor signal evidence.")
    tier1 = sum(1 for c in candidates if c.get("_tier") == 0)
    tier2 = len(candidates) - tier1
    print(f"  Candidates: {tier1} verified-source (Tier 1), {tier2} evidence-only (Tier 2).")

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
        tier = lead.get("_tier", 1)  # 0 = verified source first, 1 = evidence-only
        return (tier, -dual, days_ago)

    candidates.sort(key=sort_key)
    kept_leads = candidates[:target_leads]

    if len(kept_leads) == 0:
        print("ERROR: No verifiable leads after filtering.")
        print("Trust policy: every delivered lead needs a public source link OR signal evidence.")
        print("Either widen to event types that carry public sources (M&A, funding,")
        print("partnerships, product launches, lawsuits) or re-run a fresh search.")
        print("Delivering nothing is correct here: never deploy an unverifiable claim.")
        sys.exit(1)

    if len(kept_leads) < target_leads:
        print(f"  WARNING: Only {len(kept_leads)} verified leads (target: {target_leads}). Delivering only what is source-backed.")

    print(f"  Selected {len(kept_leads)} leads.")

    # -- STEP 5: Build data.json -----------------------------------------------
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
        source = lead.get("source", lead.get("source_url", "")) or ""
        source_title = lead.get("source_title", lead.get("sourceTitle", "")) or ""
        signal_desc = lead.get("signal_description", lead.get("recent_news", "")) or ""
        signal_proof = lead.get("signal_proof", lead.get("signalProof", lead.get("evidence", ""))) or ""

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
            "recentNews": signal_desc or signal_plain,
            "founderFocus": founder_focus,
            "teamTrajectory": team_trajectory,
            "whyFit": why_fit,
            "whyNow": why_now,
            "connNote": conn_note,
            "emailSubj": email_subj,
            "emailBody": email_body,
            "source": source,
            "sourceTitle": source_title,
            "signalProof": signal_proof,
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

    # -- Build all data shapes matching template exactly --
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
            "notes": build_coverage_notes(kept_leads, geo_counts, industry_counts, events_window),
        },
        # ICP Settings tab - built from THIS client's frozen filter, not hardcoded
        "icp": build_icp_settings(vibe_filter, events_window),
    }

    # Validate
    data_str = json.dumps(data, ensure_ascii=False, indent=2)
    validate_no_em_dash(data_str)
    validate_no_exclamation(data_str)
    validate_no_tool_names_in_leads(lead_cards)
    validate_linkedin_in_leads(lead_cards)

    with open("data.json", "w", encoding="utf-8") as f:
        f.write(data_str)
    print(f"  data.json written. {len(lead_cards)} leads | {hot_count} HOT | {warm_count} WARM")
    print(f"  Stats: array[{len(stats_array)}] | Sig: array[{len(sig_array)}] | Signals: array[{len(signals_full)}]")
    print(f"  Geo: array[{len(geo_bars)}] | Stage: array[{len(stage_bars)}] | Industry: array[{len(ind_donut)}]")

    # -- STEP 6: Run build_report.py ------------------------------------------
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

    # -- STEP 7: Validate output.html -----------------------------------------
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

    # -- STEP 8: Deploy to GitHub ----------------------------------------------
    if MODE == "DEMO":
        deploy_path = f"demo/{DATE}/{prospect_first.lower()}/index.html"
        live_url = f"https://pipelind.com/demo/{DATE}/{prospect_first.lower()}/"
    else:
        deploy_path = f"prod/{SLUG}/pipeline/index.html"
        live_url = f"https://pipelind.com/prod/{SLUG}/pipeline/"

    print(f"\n[Step 8] Staging deploy to {deploy_path} ...")
    queue_deploy(deploy_path, html_content, f"Pipeline report - {MODE} - {SLUG} - {DATE}")
    print(f"  Staged {len(html_content.encode('utf-8')):,} bytes for {deploy_path}")
    print(f"  Will be live at {live_url} (allow 30-90s for Vercel CDN after deploy)")

    # -- STEP 9: Update dedup.json (LIVE only) --------------------------------
    if MODE == "LIVE":
        print(f"\n[Step 9] Updating dedup.json ...")
        new_urls = [card["linkedin"] for card in lead_cards if card.get("linkedin")]
        existing_dedup = gh_read_json(f"inputs/prod/{SLUG}/dedup.json", default=[])
        updated_dedup = sorted(set(existing_dedup) | set(new_urls))
        queue_deploy(
            f"inputs/prod/{SLUG}/dedup.json",
            json.dumps(updated_dedup, indent=2),
            f"Dedup update - {SLUG} - {DATE}",
        )
        print(f"  dedup.json staged. Total delivered: {len(updated_dedup)}")
    else:
        print(f"\n[Step 9] DEMO mode - no dedup update.")

    # -- Record a deploy manifest (audit trail / manual fallback) --------------
    manifest_path = os.path.join(os.getcwd(), "deploy_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(_DEPLOY_ACTIONS, f, indent=2)

    # -- STEP 10: Deploy to main via git push to github.com -------------------
    deploy_msg = f"Pipeline report - {MODE} - {SLUG} - {DATE}"
    perform_git_deploy(_DEPLOY_ACTIONS, deploy_msg)

    # -- Final status ----------------------------------------------------------
    print(f"\n{'=' * 60}")
    print(
        f"PIPELINE REPORT COMPLETE - {MODE} - {prospect_full} - {firm} - "
        f"Leads {len(kept_leads)} - HOT {hot_count} - WARM {warm_count} - "
        f"Live URL: {live_url} (allow 30-90s for the Vercel CDN)"
    )
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
