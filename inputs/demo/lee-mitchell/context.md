# Prospect Context · Lee Mitchell
# Mode input file for pipeline-builder skill · schema v3

PROSPECT_FIRST_NAME: Lee
PROSPECT_FULL_NAME: Lee Mitchell
TITLE: Fractional CFO | Senior Executive Advisor | CEO and Founder, MITCOM Enterprises
FIRM: MITCOM Enterprises Limited
WEBSITE: Not on record
LOCATION: New Maryland, New Brunswick, Canada
LINKEDIN: https://www.linkedin.com/in/lee-mitchell

## SELECTION FLAGS
BUYER_PROFILE: operator
ADVISOR_FUNCTION: finance

## WHAT THE PROSPECT DOES
Lee is a senior finance and risk executive offering fractional CFO leadership to owner-led and multi-entity organizations. He holds CPA, CMA, CISA, and CRISC designations and has delivered $2B+ in financial and operational improvements across private industry, government, and non-profit environments. His work spans FP&A, cash flow, governance, ERP transformation, M&A diligence, and cybersecurity risk controls, with a strong emphasis on helping CEOs and boards make confident decisions at the intersection of finance and risk.

## THE PROSPECT'S ICP (who their buyers are)
- Buyer titles (decision-makers only): CEO, Founder, Co-founder, Owner, President, Managing Director, Managing Partner
- Partner/secondary titles (not buyers): Board Chair, VP Finance, COO (referral paths, not budget holders for fractional CFO)
- Company stage: Established and operating, privately-owned or owner-led, NOT pre-revenue or venture-backed
- Company size: 11 to 200 employees
- Industries: Professional services, construction, manufacturing, logistics, distribution, healthcare, financial services (boutique), non-profit
- Geography: CA, US
- Buyer pain: CEOs and owners of growing or complex businesses who lack senior finance leadership and need fractional CFO support for FP&A, governance, controls, and strategic decision-making

## FROZEN VIBE FILTER (routine uses verbatim, no derivation)
job_title: "chief executive officer", "owner", "founder", "president", "managing director", "managing partner"
job_level: founder, owner, president
company_size: 11-50, 51-200
company_country_code: CA, US
linkedin_category: professional services, construction, manufacturing, logistics, distribution, healthcare, accounting, management consulting, non-profit management
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
- Measured and credential-forward: leads with designations and track record, no hype or filler
- Uses short declarative sentences and structured bullet lists; avoids vague language
- Grounded in specific outcomes: "$2B+ in measurable improvements," "board-ready dashboards," "close acceleration"
- Closes warmly without overselling: "If you need a steady, practical leader to navigate complexity across finance and risk, let us connect."
- Example line: "I bring a rare blend of CFO leadership and governance, risk and compliance expertise."
