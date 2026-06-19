# Prospect Context · Diane Maistros
# Mode input file for pipeline-builder skill · schema v3

PROSPECT_FIRST_NAME: Diane
PROSPECT_FULL_NAME: Diane Maistros
TITLE: Fractional COO / Executive Director Leadership
FIRM: Artemai Solutions
WEBSITE: Not on record
LOCATION: United States
LINKEDIN: https://www.linkedin.com/in/diane-maistros

## SELECTION FLAGS
BUYER_PROFILE: operator
ADVISOR_FUNCTION: operations

## WHAT THE PROSPECT DOES
Diane Maistros is a fractional COO and Executive Director leadership advisor specializing in operational stabilization, leadership infrastructure strengthening, and organizational resilience for nonprofits. She brings 30+ years of senior operations and administrative leadership at Sheppard Pratt, one of the largest nonprofit behavioral health systems in the US, including roles as Chief Administrative Officer and Chief of Integrated Operations. Her proprietary ARTEMAI Resilience Architecture Diagnostic identifies hidden operational pressure points and defines a path toward stability and long-term resilience.

## THE PROSPECT'S ICP (who their buyers are)
- Buyer titles (decision-makers only): Executive Director, CEO, President, Board Chair, Founder
- Partner/secondary titles (not buyers): Chief of Staff, COO, VP of Operations
- Company stage: established and operating nonprofits, NOT pre-revenue, NOT venture-backed
- Company size: 11-200 employees
- Industries: behavioral health, human services nonprofits, community services, nonprofit organizations
- Geography: US
- Buyer pain: growth outpacing infrastructure, Executive Director pulled into every operational issue, leadership teams misaligned, organizational fragility during transitions

## FROZEN VIBE FILTER (routine uses verbatim, no derivation)
job_title: "executive director", "chief executive officer", "president", "board chair", "founder"
job_level: owner, president, founder
company_size: 11-50, 51-200
company_country_code: US
linkedin_category: nonprofit organization management, mental health care, individual and family services, civic and social organization
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
- Direct and declarative opener; leads with a bold provocation before explaining
- Short punchy sentences followed by structured bullet lists; no fluff
- Speaks from operational authority, not coaching posture -- diagnosis-first framing
- Uses contrast to make points land: "boards work harder but not always in alignment"
- Example line: "Strong nonprofits don't fail because of weak missions. They struggle when growth outpaces infrastructure and execution begins to fracture beneath the surface."
