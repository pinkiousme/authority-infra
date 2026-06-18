# Prospect Context · Nicholas Giacobe
# Mode input file for pipeline-builder skill · schema v3

PROSPECT_FIRST_NAME: Nicholas
PROSPECT_FULL_NAME: Nicholas Giacobe
TITLE: Founder
FIRM: Blackridge CFO Advisory
WEBSITE: blackridgecfo.com
LOCATION: Washington, New Jersey, United States
LINKEDIN: linkedin.com/in/nicholas-blackridge-cfo

## SELECTION FLAGS
BUYER_PROFILE: operator
ADVISOR_FUNCTION: finance

## WHAT THE PROSPECT DOES
Nicholas Giacobe is the founder of Blackridge CFO Advisory, providing fractional CFO services to manufacturing, distribution, and trade services businesses generating $5M to $30M in revenue. He has over 20 years of experience inside PE-backed and privately owned businesses, building financial infrastructure, navigating lender relationships, and leading through capital events. He holds a BS in Accounting from Kean University and is a Certified Corporate Financial Planning and Analysis Professional through Wall Street Prep.

## THE PROSPECT'S ICP (who their buyers are)
- Buyer titles (decision-makers only): CEO, Founder, Owner, President
- Partner/secondary titles (not buyers): none
- Company stage: established and operating, owner-operated or PE-backed, NOT pre-revenue or venture-backed
- Company size: 11-200 employees
- Industries: manufacturing, distribution, trade services, professional services
- Geography: US
- Buyer pain: revenue growth has outpaced financial infrastructure, leaving cash flow unpredictable and margin visibility limited

## FROZEN VIBE FILTER (routine uses verbatim, no derivation)
job_title: "chief executive officer", "owner", "founder", "president"
job_level: founder, owner, president
company_size: 11-50, 51-200
company_country_code: US
linkedin_category: manufacturing, distribution, trade services, professional services
revenue_floor: $5M
events: merger_and_acquisitions, leadership_change_finance, hiring_in_finance_department
events_window_days: 90
exclude_company_keywords: AI, robotics, SaaS, platform, marketplace, -tech, venture, startup
autocomplete_resolved: false

## RUN CONTROL
credit_cap: 35
web_mode: off
deploy_path: demo/[DATE]/[firstname]/index.html

## PROSPECT VOICE (for outreach copy matching)
- Opens posts with a short, punchy contrarian claim that flips conventional wisdom
- Uses a problem then reveal structure, naming the visible pattern before explaining what's actually happening underneath
- Short declarative sentences, frequent line breaks, almost no qualifiers or hedging
- No em dashes, no exclamation marks, plain and direct tone throughout
- Example line: "Most owners think they need better financials. What they actually need is to stop trusting the ones they have."
