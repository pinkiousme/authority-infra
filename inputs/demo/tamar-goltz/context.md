# Prospect Context · Tamar Goltz
# Mode input file for pipeline-builder skill · schema v3

PROSPECT_FIRST_NAME: Tamar
PROSPECT_FULL_NAME: Tamar Goltz
TITLE: Fractional COO · Operations and Process Optimization Consultant
FIRM: Freedom Built Business Solutions
WEBSITE: Not on record
LOCATION: United States
LINKEDIN: https://www.linkedin.com/in/freedombuilt

## SELECTION FLAGS
BUYER_PROFILE: operator
ADVISOR_FUNCTION: operations

## WHAT THE PROSPECT DOES
Fixes operational chaos in established companies. Maps how work actually flows, finds the bottlenecks, aligns departments, and builds internal systems that scale before layering on technology. Twenty-plus years across construction, manufacturing, and logistics, with deep ERP and process-standardization experience (SAP, Lean and Six Sigma). Works with mid-market operating companies in the $5M to $50M revenue range.

## THE PROSPECT'S ICP (who their buyers are)
- Buyer titles (decision-makers only): Owner, Founder, President, CEO, Managing Director
- Partner/secondary titles (not buyers): none
- Company stage: established and operating, NOT pre-revenue, NOT venture-backed startups
- Company size: 11-50 and 51-200 employees
- Industries: construction, manufacturing, transportation and logistics, distribution, building products, industrial services
- Geography: US, CA
- Buyer pain: growth has outpaced the operating system, so handoffs, accountability, and execution break before headcount or technology can fix them

## FROZEN VIBE FILTER (routine uses verbatim, no derivation)
job_title: ["chief executive officer", "ceo", "owner", "founder", "president", "managing director"]
job_level: ["founder", "owner", "president"]
company_size: ["11-50", "51-200"]
company_country_code: ["US", "CA"]
linkedin_category: ["construction", "manufacturing", "transportation and logistics", "building materials", "industrial machinery"]
revenue_floor: $5M
events: ["merger_and_acquisitions", "leadership_change_operations", "hiring_in_operations_department", "office_expansion"]
events_window_days: 90
exclude_company_keywords: ["AI", "robotics", "SaaS", "platform", "marketplace", "-tech", "venture", "startup"]
autocomplete_resolved: false   # resolve job_title, linkedin_category, events against Vibe autocomplete on the first real build, then set true

## RUN CONTROL
credit_cap: 35
web_mode: off
deploy_path: demo/[DATE]/tamar/index.html

## PROSPECT VOICE (for outreach copy matching)
- Plain, direct, operational. Short declarative sentences. Diagnoses the problem before naming the fix.
- Opens with an observation or a problem, not a pitch. Peer tone, occasionally wry and human.
- Frames work as clarity, structure, and follow-through, not magic or shortcuts.
- Example line in her style: "Growth causes problems to bubble to the surface. Some are blips. Some are road blocks. Some are landslides that push you in the wrong direction."
