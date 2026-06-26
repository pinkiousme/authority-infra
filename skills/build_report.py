#!/usr/bin/env python3
"""
build_report.py (v7, hardened) - deterministic placeholder injection.

Difference from v6.0: injection sites are explicit __PL_* tokens, not the
template's seed data. Every replace asserts its token existed, and the build
fails loudly if any token is missing, any __PL_ token survives, the lead count
is wrong, or any seed identifier leaks. A template edit can no longer cause a
silent wrong-data deploy.

Usage: python3 build_report.py data.json template.html output.html
"""
import json, sys, re, subprocess, tempfile, os, shutil


class BuildError(Exception):
    pass


def js(obj):
    """JSON literal, valid as a JS value. Deterministic escaping."""
    return json.dumps(obj, ensure_ascii=False)


def esc_html(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def esc_js(s):
    """Safe inside a JS string literal of either quote style."""
    return (str(s).replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
            .replace("\r", "").replace("\n", "\\n"))


def repl(tpl, token, value):
    if token not in tpl:
        raise BuildError("placeholder missing from template: " + token)
    return tpl.replace(token, value)


def build(data_path, template_path, output_path):
    with open(data_path, encoding="utf-8") as f:
        D = json.load(f)
    with open(template_path, encoding="utf-8") as f:
        tpl = f.read()

    mode = D["mode"]
    client = D["client"]
    db = D["dashboard"]
    mk = D["markets"]

    # ---- data arrays (JSON literals are valid JS) ----
    tpl = repl(tpl, "__PL_LEADS__", js(D["leads"]))
    tpl = repl(tpl, "__PL_STATS__", js(db["stats"]))
    tpl = repl(tpl, "__PL_SIG__", js(db["sig"]))
    tpl = repl(tpl, "__PL_DB_GEO__", js(db["geo"]))
    tpl = repl(tpl, "__PL_DB_STAGE__", js(db["stage"]))
    tpl = repl(tpl, "__PL_SIGNALS__", js(D["signals"]))
    tpl = repl(tpl, "__PL_MK_GEO__", js(mk["geo"]))
    tpl = repl(tpl, "__PL_MK_IND__", js(mk["ind"]))

    # ---- ICP settings: data-driven from the client's context (JS value) ----
    tpl = repl(tpl, "__PL_ICP__", js(D.get("icp", [])))

    # ---- strings inside single-quoted JS string literals ----
    tpl = repl(tpl, "__PL_PULSE__", esc_js(db["pulse"]))
    tpl = repl(tpl, "__PL_MK_NOTES__", esc_js(mk.get("notes", "")))

    # ---- scalar JS vars: token sits unquoted, inject a full JSON literal ----
    tpl = repl(tpl, "__PL_MODE__", js(mode))
    tpl = repl(tpl, "__PL_CLIENT_FIRST__", js(client["firstName"]))
    tpl = repl(tpl, "__PL_CALENDLY__", js(D.get("calendly", "https://calendly.com/saurabh_zentro/30-min")))

    # ---- name / firm ----
    tpl = repl(tpl, "__PL_FULLNAME_JS__", esc_js(client["fullName"]))
    tpl = repl(tpl, "__PL_FIRM_JS__", esc_js(client["firm"]))
    tpl = repl(tpl, "__PL_FULLNAME_HTML__", esc_html(client["fullName"]))
    tpl = repl(tpl, "__PL_FIRM_HTML__", esc_html(client["firm"]))

    # ---- dates (HTML context) ----
    tpl = repl(tpl, "__PL_WEEK__", esc_html(D["week"]))
    tpl = repl(tpl, "__PL_GENERATED__", esc_html(D["generated"]))

    # ---- test banner: strip ----
    tpl = repl(tpl, "<!--__PL_TESTBANNER__-->", "")

    # ---- per-card foot label (single-quoted JS string) ----
    foot = ("Personalized demo for " + client["firstName"]) if mode == "DEMO" \
        else ("Live pipeline · " + client["firm"])
    tpl = repl(tpl, "__PL_FOOTER__", esc_js(foot))

    # ---- self-validation: never write a broken or wrong-data report ----
    errors = validate_output(tpl, D)
    if errors:
        raise BuildError("Refusing to write report. Failures:\n  - " + "\n  - ".join(errors))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(tpl)
    return tpl


def validate_output(tpl, D):
    errors = []

    # 1. no placeholder may survive
    leftover = re.findall(r'__PL_[A-Z_]+__', tpl)
    if leftover:
        errors.append("Unreplaced placeholder(s): " + ", ".join(sorted(set(leftover))))

    # 2. script block must be valid JS
    m = re.search(r'<script>([\s\S]*?)</script>', tpl)
    if not m:
        errors.append("No <script> block found.")
    else:
        node = shutil.which("node")
        if node:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                f.write(m.group(1)); jspath = f.name
            try:
                r = subprocess.run([node, "--check", jspath], capture_output=True, text=True)
                if r.returncode != 0:
                    first = (r.stderr.strip().split("\n")[0] if r.stderr else "syntax error")
                    errors.append("Script block is not valid JavaScript: " + first)
            finally:
                os.unlink(jspath)

    # 3. lead count must match the data (each lead emits one connNote)
    target = 5 if D.get("mode") == "DEMO" else 10
    n_data = len(D.get("leads", []))
    n_rendered = tpl.count('"connNote"')
    if n_rendered != n_data:
        errors.append("Rendered lead count %d != data lead count %d" % (n_rendered, n_data))
    if n_data == 0:
        errors.append("No leads in data.")

    # 4. required structural tokens
    for token in ["var LEADS", "function toggleLead", "function render",
                  "donutSVG", "areaSVG", "barsSVG"]:
        if token not in tpl:
            errors.append("Missing required token: " + token)
    for tab in ["Pipeline", "Dashboard", "Signals", "Markets", "Content", "Settings"]:
        if tab not in tpl:
            errors.append("Missing tab: " + tab)

    # 5. size, em dash, tool-name leak
    if len(tpl) < 50000:
        errors.append("Output too small (%d bytes); template likely not used." % len(tpl))
    if "\u2014" in tpl:
        errors.append("Em dash present in output.")
    for tool in ["Vibe Prospecting", "Explorium"]:
        if tool in tpl:
            errors.append("Tool name leaked into output: " + tool)

    # 6. seed identifiers must not survive
    for seed in ['Dave Cotter', 'Kelsor Ventures', '{c:"US",n:2}', 'Test data \u00b7 Illustrative only']:
        if seed in tpl:
            errors.append("Seed identifier leaked: " + seed)

    # 7. hardcoded generic/tech ICP copy must never reappear (ICP + coverage notes
    #    are data-driven now; these strings would mean a template regression).
    for phrase in ['Healthtech', 'B2B SaaS', 'Seed through Series B',
                   'Co-Founder, CEO, Founder, COO']:
        if phrase in tpl:
            errors.append("Hardcoded generic-ICP copy leaked (must be data-driven): " + phrase)

    return errors


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 build_report.py data.json template.html output.html")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2], sys.argv[3])
    print("Built", sys.argv[3])
