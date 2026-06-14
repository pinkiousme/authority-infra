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
    # pulse text
    tpl = re.sub(r'<div class="pulse-txt">.*?</div>',
                 lambda _: '<div class="pulse-txt">' + escape_html(db["pulse"]) + '</div>',
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
    tpl = tpl.replace('var MODE = "DEMO";', 'var MODE = "%s";' % mode)
    tpl = tpl.replace('var CLIENT = "Dave";', 'var CLIENT = %s;' % js(client["firstName"]))
    cal = D.get("calendly", "https://calendly.com/saurabh_zentro/30-min")
    tpl = tpl.replace('var CALENDLY = "https://calendly.com/saurabh_zentro/30-min";', 'var CALENDLY = %s;' % js(cal))
    tpl = tpl.replace("Dave Cotter", client["fullName"])
    tpl = tpl.replace("Kelsor Ventures", client["firm"])
    tpl = tpl.replace("Week of June 13, 2026", "Week of " + D["week"])
    tpl = tpl.replace("Generated June 13, 2026", "Generated " + D["generated"])

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
    # In DEMO, leads have empty email/phone -> the template already shows buttons;
    # we hide email/phone buttons + contact strip when email is empty (handled in template JS via field checks if present).
    # No structural edit needed here; data drives it.

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(tpl)
    return tpl

def escape_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 build_report.py data.json template.html output.html")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2], sys.argv[3])
    print("Built", sys.argv[3])
