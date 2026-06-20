# Prospect Context · Stjepan (Stephen) Vidovic
# Mode input file for pipeline-builder skill · schema v3

PROSPECT_FIRST_NAME: Stjepan
PROSPECT_FULL_NAME: Stjepan (Stephen) Vidovic
TITLE: Fractional COO & AI Integration Specialist
FIRM: SV Media
WEBSITE: www.svmedia.hr
LOCATION: San Mateo, California, United States
LINKEDIN: https://www.linkedin.com/in/stjepan-vidovic

## SELECTION FLAGS
BUYER_PROFILE: operator
ADVISOR_FUNCTION: operations

## WHAT THE PROSPECT DOES
Stjepan is a Fractional COO and AI automation specialist operating through SV Media, working with founder-led companies in the $500K-$2M revenue range. He embeds hands-on inside client operations to fix broken processes, build reporting visibility, and layer in AI-powered workflows using tools like n8n, Monday, Claude, and GHL. He holds a Master's in Economics and Financial Markets and brings background as CFO/COO at a city parking firm, plus 4 years as Finance & Business Intelligence Analyst at Velocity Sellers.

## THE PROSPECT'S ICP (who their buyers are)
- Buyer titles (decision-makers only): CEO, Founder, Co-Founder, Owner, President
- Partner/secondary titles (not buyers): none
- Company stage: established and operating, generating revenue, NOT pre-revenue or venture-backed
- Company size: 1-50 employees (focus on founder-led companies running lean)
- Industries: agencies, eCommerce, professional services, small remote-first businesses
- Geography: US, CA, GB, AU
- Buyer pain: ops are quietly killing growth, money is leaking through undocumented processes and manual work, and the team is too small to afford full-time COO-level oversight

## FROZEN VIBE FILTER (routine uses verbatim, no derivation)
job_title: "chief executive officer", "founder", "co-founder", "owner", "president"
job_level: founder, owner, president
company_size: 1-10, 11-50
company_country_code: US, CA, GB, AU
linkedin_category: marketing and advertising, internet publishing, business consulting and services, retail, professional services
revenue_floor: $500K
events: leadership_change_operations, hiring_in_operations_department, office_expansion, merger_and_acquisitions
events_window_days: 90
exclude_company_keywords: AI, robotics, SaaS, platform, marketplace, -tech, venture, startup
autocomplete_resolved: false

## RUN CONTROL
credit_cap: 35
web_mode: off
deploy_path: demo/[DATE]/[stjepan]/index.html

## PROSPECT VOICE (for outreach copy matching)
- Direct and diagnostic, leads with the problem before the solution
- Uses short declarative sentences, no filler, confident but not pushy
- Opens with an observation about what is quietly going wrong ("Your company is generating revenue. But somewhere between the invoices that don't get sent, the processes nobody follows...")
- Positions himself as someone who sits inside the problem, not above it
- Example line: "I don't hand you a strategy deck and disappear. I sit inside your operations, find where the money is leaking, fix the broken processes."
