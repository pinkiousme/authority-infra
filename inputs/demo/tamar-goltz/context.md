# Prospect Context · Tamar Goltz
# Mode input file for pipeline-builder skill · schema v3

PROSPECT_FIRST_NAME: Tamar
PROSPECT_FULL_NAME: Tamar Goltz
TITLE: Fractional COO
FIRM: Freedom Built Business Solutions
WEBSITE: Not on record
LOCATION: United States
LINKEDIN: linkedin.com/in/freedombuilt

## SELECTION FLAGS
BUYER_PROFILE: operator
ADVISOR_FUNCTION: operations

## WHAT THE PROSPECT DOES
Tamar Goltz is a Fractional COO and Founder of Freedom Built Business Solutions, providing operational diagnostics, process optimization consulting, and implementation support to mid market companies in the $5M to $50M revenue range. She applies Lean and Six Sigma methodologies across construction, manufacturing, and logistics, building SOPs, KPI frameworks, and change management strategies, with prior leadership in national process standardization across 256 branches at a $2B private equity backed services company.

## THE PROSPECT'S ICP (who their buyers are)
- Buyer titles (decision-makers only): CEO, Founder, Owner, President, Managing Partner
- Partner/secondary titles (not buyers): none
- Company stage: established and operating, NOT pre-revenue or venture-backed
- Company size: 11 to 200 employees
- Industries: Construction, Manufacturing, Logistics, Distribution, Building Materials, Trades and Services
- Geography: United States
- Buyer pain: operational chaos, broken handoffs, no metrics, and teams burning out from messy workflows that have outgrown ad hoc processes

## FROZEN VIBE FILTER (routine uses verbatim, no derivation)
job_title: "chief executive officer", "founder", "owner", "president", "managing partner"
job_level: founder, owner, president
company_size: 11-50, 51-200
company_country_code: US
linkedin_category: construction, manufacturing, logistics, building materials, distribution
revenue_floor: $5M
events: merger_and_acquisitions, leadership_change_operations, hiring_in_operations_department, office_expansion
events_window_days: 90
exclude_company_keywords: AI, robotics, SaaS, platform, marketplace, -tech, venture, startup
autocomplete_resolved: false

## RUN CONTROL
credit_cap: 35
web_mode: off
deploy_path: demo/[DATE]/[firstname]/index.html

## PROSPECT VOICE (for outreach copy matching)
- Short punchy lines, often one sentence per line, building rhythm through repetition
- Opens with a direct diagnostic claim about the reader's problem before introducing herself
- Uses bullet fragments to break down a concept into parts (blips, road blocks, landslides)
- Closes with a plain, low pressure invitation to talk rather than a hard pitch
- Example line: "I fix operational chaos."
