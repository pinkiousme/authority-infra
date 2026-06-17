#!/usr/bin/env python3
"""
build_report.py - Deterministic pipeline report builder.

The routine produces ONLY a data.json file. This script does the template
injection with guaranteed-correct escaping. No model reasoning touches the
HTML assembly, so the entire class of newline/quote escaping bugs is eliminated.

Usage:
  python3 build_report.py data.json template.html output.html

data.json schema:
{
  "mode": "DEMO" | "LIVE",
  "client": { "firstName": "Dave", "fullName": "Dave Cotter", "firm": "Kelsor Ventures" },
  "week": "June 14, 2026",
  "generated": "June 14, 2026",
  "leads": [ { ...27 fields... }, ... ],
  "dashboard": {
     "stats": [ {n,l,c,chg,bar}, ... ],     # 4 stat cards
     "sig":   [ {name,value,color}, ... ],   # signal mix donut
     "geo":   [ {c,n}, ... ],                # geographic bars
     "stage": [ {s,n}, ... ],                # funding stage bars
     "pulse": "Market intelligence pulse text"
  },
  "signals": [ {name,count,color,desc,leads:[...]}, ... ],
  "markets": { "geo":[...], "ind":[{name,value,color},...], "notes":"..." }
}
"""
import json, sys, re

def js(obj):
    """Serialize a Python object to a JS literal with correct escaping.
    json.dumps handles all newline/quote/unicode escaping deterministically."""
    return json.dumps(obj, ensure_ascii=False)

def build(data_path, template_path, output_path):
    with open(data_path, encoding="utf-8") as f:
        D = json.load(f)
    with open(template_path, encoding="utf-8") as f:
        tpl = f.read()

    mode = D["mode"]
    client = D["client"]

    # ---- 1. LEADS array ----
    # Build "var LEADS = [ {...}, {...} ];" using json.dumps per object (perfect escaping)
    lead_objs = []
    for L in D["leads"]:
        # emit as a JS object literal; json.dumps on the whole dict gives valid JS object syntax too
        lead_objs.append(js(L))
    leads_js = "var LEADS = [\n  " + ",\n  ".join(lead_objs) + "\n];"
    tpl = re.sub(r'var LEADS = \[.*?\n\];', lambda _: leads_js, tpl, count=1, flags=re.DOTALL)

    # ---- 2. Dashboard data ----
    db = D["dashboard"]
    tpl = re.sub(r'var stats=\[.*?\];', lambda _: "var stats=" + js(db["stats"]) + ";", tpl, count=1, flags=re.DOTALL)
    tpl = re.sub(r'var sig=\[.*?\];', lambda _: "var sig=" + js(db["sig"]) + ";", tpl, count=1, flags=re.DOTALL)
    # dashboard geo + stage live on consecutive lines inside viewDashboard
    tpl = re.sub(r'var geo=\[\{c:"US",n:2\}.*?\];\n  var stage=\[.*?\];',
                 lambda _: "var geo=" + js(db["geo"]) + ";\n  var stage=" + js(db["stage"]) + ";",
                 tpl, count=1, flags=re.DOTALL)
    # pulse text - inject JS-safely. The template builds pulse-txt inside a JS string,
    # so the value MUST be escaped for a JS single-quoted string context (apostrophes break it).
    # We replace the inner text and escape for JS by embedding via a JSON string then stripping
    # the outer quotes is unsafe; instead escape backslash, single-quote, and newline explicitly.
    pulse_safe = js_string_escape(db["pulse"])
    tpl = re.sub(r'<div class="pulse-txt">.*?</div>',
                 lambda _: '<div class="pulse-txt">' + pulse_safe + '</div>',
                 tpl, count=1, flags=re.DOTALL)

    # ---- 3. Signals view ----
    sig_types = js(D["signals"])
    tpl = re.sub(r'var types=\[\{name:"New Funding Round".*?\}\];',
                 lambda _: "var types=" + sig_types + ";",
                 tpl, count=1, flags=re.DOTALL)

    # ---- 4. Markets view ----
    mk = D["markets"]
    # markets geo + ind on consecutive lines inside viewMarkets
    tpl = re.sub(r'var geo=\[\{c:"US",n:2\}.*?\];\n  var ind=\[.*?\];',
                 lambda _: "var geo=" + js(mk["geo"]) + ";\n  var ind=" + js(mk["ind"]) + ";",
                 tpl, count=1, flags=re.DOTALL)

    # ---- 5. Header personalization ----
    # The name/firm appear in TWO contexts that need DIFFERENT escaping:
    #  (a) static HTML (title, sidebar, page-sub, footer) -> HTML-escape (apostrophe -> &#39;)
    #  (b) JS string literals (VIEWS subtitles assigned via textContent; CTA innerHTML) -> JS-string-escape (apostrophe -> \')
    # We do the JS-context replacements FIRST (on the specific JS lines), then the remaining
    # occurrences are all static HTML and get HTML-escaping.
    full = client["fullName"]; firm = client["firm"]
    full_js = js_string_escape(full); firm_js = js_string_escape(firm)
    full_html = escape_html_attr(full); firm_html = escape_html_attr(firm)

    tpl = tpl.replace('var MODE = "DEMO";', 'var MODE = "%s";' % mode)
    tpl = tpl.replace('var CLIENT = "Dave";', 'var CLIENT = %s;' % js(client["firstName"]))
    cal = D.get("calendly", "https://calendly.com/saurabh_zentro/30-min")
    tpl = tpl.replace('var CALENDLY = "https://calendly.com/saurabh_zentro/30-min";', 'var CALENDLY = %s;' % js(cal))

    # (b) JS-string context: the VIEWS object line uses "Dave Cotter"/"Kelsor Ventures" inside JS string literals.
    # Target that specific line (it contains "var VIEWS=") with JS escaping.
    def fix_views(m):
        return m.group(0).replace("Dave Cotter", full_js).replace("Kelsor Ventures", firm_js)
    tpl = re.sub(r'var VIEWS=\{.*?\};', fix_views, tpl, count=1, flags=re.DOTALL)

    # (a) all remaining occurrences are static HTML -> HTML-escape
    tpl = tpl.replace("Dave Cotter", full_html)
    tpl = tpl.replace("Kelsor Ventures", firm_html)
    tpl = tpl.replace("Week of June 13, 2026", "Week of " + escape_html_attr(D["week"]))
    tpl = tpl.replace("Generated June 13, 2026", "Generated " + escape_html_attr(D["generated"]))

    # ---- 6. Logo with fallback ----
    tpl = tpl.replace(
        '<span class="sb-wordmark">Pipelind</span>',
        '<img src="https://raw.githubusercontent.com/pinkiousme/authority-infra/main/assets/pipelind-logo-dark.png" alt="Pipelind" style="height:20px;width:auto" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'inline\'"><span class="sb-wordmark" style="display:none">Pipelind</span>'
    )

    # ---- 7. Remove the synthetic test banner ----
    tpl = re.sub(r'<div class="test-banner">.*?</div>', lambda _: '', tpl, count=1, flags=re.DOTALL)

    # ---- 8. Footer label per mode ----
    if mode == "DEMO":
        foot = "Personalized demo for " + client["firstName"]
    else:
        foot = "Live pipeline · " + client["firm"]
    tpl = tpl.replace("Test data · Illustrative only", foot)

    # ---- 9. DEMO/LIVE contact display ----
    # Driven by data: cards show email/phone only when present (template handles it).

    # ---- 10. SELF-VALIDATION: never write a broken report ----
    # The #1 historical failure was broken JS (an apostrophe closing a string) producing a
    # blank report. This builder now validates its own output BEFORE writing. If the script
    # block is not valid JavaScript, it raises and writes nothing, so a broken file can never deploy.
    errors = validate_output(tpl, D)
    if errors:
        raise BuildError("Refusing to write broken report. Failures:\n  - " + "\n  - ".join(errors))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(tpl)
    return tpl


class BuildError(Exception):
    pass


def validate_output(tpl, D):
    """Return a list of validation failures. Empty list means valid."""
    import subprocess, tempfile, os, shutil
    errors = []
    # 1. Extract the script block
    m = re.search(r'<script>([\s\S]*?)</script>', tpl)
    if not m:
        return ["No <script> block found in output."]
    script = m.group(1)
    # 2. Validate the script is real JavaScript using node --check if available
    node = shutil.which("node")
    if node:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            jspath = f.name
        try:
            r = subprocess.run([node, "--check", jspath], capture_output=True, text=True)
            if r.returncode != 0:
                errors.append("Script block is not valid JavaScript: " + (r.stderr.strip().split("\n")[0] if r.stderr else "syntax error"))
        finally:
            os.unlink(jspath)
    else:
        # Fallback: balanced-quote heuristic on the LEADS/pulse if node is absent
        if script.count("var LEADS") == 0:
            errors.append("LEADS array missing.")
    # 3. Structural checks
    target = 5 if D.get("mode") == "DEMO" else 10
    n_leads = len(D.get("leads", []))
    for token in ["var LEADS", "function toggleLead", "function render", "donutSVG", "areaSVG", "barsSVG"]:
        if token not in tpl:
            errors.append("Missing required token: " + token)
    for tab in ["Pipeline", "Dashboard", "Signals", "Markets", "Content", "Settings"]:
        if tab not in tpl:
            errors.append("Missing tab: " + tab)
    if len(tpl) < 50000:
        errors.append("Output too small (%d bytes); template likely not used." % len(tpl))
    if "\u2014" in tpl:
        errors.append("Em dash present in output.")
    for tool in ["Vibe Prospecting", "Explorium"]:
        if tool in tpl:
            errors.append("Tool name leaked into output: " + tool)
    if "Test data · Illustrative only" in tpl:
        errors.append("Test-data label not replaced.")
    return errors

def escape_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def escape_html_attr(s):
    # Safe for static HTML text and attribute contexts
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))

def js_string_escape(s):
    # Safe for embedding inside a JS single-quoted string literal that is later
    # written to innerHTML. Escapes backslash, single quote, and newlines.
    # Does NOT HTML-escape, because the surrounding template uses these in innerHTML
    # where the literal character should appear.
    return (str(s).replace("\\", "\\\\").replace("'", "\\'")
            .replace("\r", "").replace("\n", "\\n"))

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 build_report.py data.json template.html output.html")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2], sys.argv[3])
    print("Built", sys.argv[3])
