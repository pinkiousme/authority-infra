# Client Context · Nathan Preyser
# Mode input file for pipeline-builder skill · LIVE mode
# Created: June 2026

PROSPECT_FIRST_NAME: Nathan
PROSPECT_FULL_NAME: Nathan Preyser
TITLE: Fractional CFO & Advisor, Founder of Strategin Advisory
FIRM: Strategin Advisory
WEBSITE: Not on record
LOCATION: Greater Melbourne Area, Australia
LINKEDIN: https://www.linkedin.com/in/nathan-preyser
DEPLOY_PATH: prod/nathan-preyser/pipeline/index.html
DEPLOY_URL: https://pipelind.com/prod/nathan-preyser/pipeline

## SELECTION FLAGS
BUYER_PROFILE: operator
ADVISOR_FUNCTION: finance

## WHAT THE CLIENT DOES
Nathan is the founder of Strategin Advisory, working as a Fractional CFO and Advisor for SMEs and not-for-profits across Australia and New Zealand. He has 35+ years of experience as a CFO, COO, GM Procurement and NFP board chair across ASX-listed corporates, mid-market businesses and national not-for-profits. His track record spans M&A due diligence and integration, cashflow turnaround, governance uplift (including NDIS Act, Disability Discrimination Act and Quality & Safeguards compliance), ERP and WMS optimisation, and operational transformation. Notable work includes COO/CFO at Fight Cancer Foundation and lead M&A advisor on the merger that formed the $360M Possability/Lifestyle Solutions group. He holds an FCPA (Fellow CPA) and Certified Professional Business Advisor credential, with a Bachelor of Business (Accounting) and Masters of Marketing from Monash University.

His core delivery areas, in order of relevance to his buyers:
- Turnaround and stabilisation (90-180 day outcomes)
- Cashflow recovery and cost reset
- Governance uplift (Disability Discrimination Act, NDIS Act, Quality & Safeguards Commission)
- ERP and WMS optimisation and process redesign
- Growth strategy, pricing, and margin expansion
- Board reporting, risk management, and audit readiness
- Leadership coaching and capability building

## THE CLIENT'S ICP (who their buyers are)
- Buyer titles: CEO, Founder, Owner, Managing Director, Executive Director, Board Chair, Board Member
- Company size: Revenue up to $250M AUD. Employee count: 11-50 (small) through to 201-500 (mid-market). No startups. Established operating businesses only
- Industries (confirmed by client, priority order):
  1. Retail and Building Materials
  2. Health (hospitals, allied health, medical services, healthcare providers)
  3. Disability Services (NDIS providers, disability care, supported accommodation)
- Geography: Australia primary. New Zealand secondary
- Buyer pain: Founders and boards facing a cashflow crisis, turnaround pressure, M&A complexity, or governance gap that requires experienced fractional CFO or COO leadership, without yet justifying a full-time hire. Specifically: businesses under stress, restructuring, post-merger integration, or navigating NDIS/DDA compliance obligations

## BUYING SIGNALS THAT INDICATE ACTIVE NEED
VERIFIED-ONLY: every signal below is a news/web event that carries a public source link, so each delivered lead can be verified by the buyer. Workforce-only signals (e.g. headcount decreases) are deliberately excluded because they have no public source to cite.
Primary signals (run these first):
- merger_and_acquisitions: businesses undergoing M&A, due diligence, post-merger integration or business combination need experienced fractional CFO leadership. Directly matches Nathan's M&A background including the $360M Possability/LSS merger. Carries public sources
- cost_cutting: publicly reported cost cutting signals cashflow stress and a stabilisation need. Directly matches his turnaround and stabilisation offer. Carries public sources

Secondary signals (use only if primary signals return fewer than 10 leads after dedup):
- lawsuits_and_legal_issues: publicly reported legal or regulatory issues signal a governance, risk or audit-readiness gap, matching Nathan's governance and board-reporting strength
- new_partnership: a publicly announced major partnership often surfaces integration, margin and finance questions Nathan is positioned to advise on

## PERSONALIZATION ANCHOR (why this fits the client)
Nathan's buyers are not posting "we need a fractional CFO" on LinkedIn. They are identifiable by what they are doing operationally: mergers, restructures, cost resets. Pipelind surfaces companies in those active windows so Nathan can reach them before the need is fully defined and a full-time hire is being considered. Every lead card should open with the company's situation (the signal), not with a description of Nathan's services.

## CLIENT VOICE (for connection notes and outreach copy)
- Calm, structured, advisory tone. Decades of experience, credentials-backed. Never hypes outcomes
- Uses staged frameworks (Stabilise, Clarify, Execute) and numbered content series
- Speaks to founders and boards as a peer and partner, not as a vendor
- Declarative professional sentences. No exclamation marks. Pairs warmth with commercial precision
- Representative line in his style: "Why good businesses stall, and what founders must understand before they can scale"
- Connection notes should lead with the company situation (the signal), not with a pitch for Nathan's services

## DEDUP REFERENCE
Dedup file: inputs/prod/nathan-preyser/dedup.json
Append delivered LinkedIn URLs to this file after every weekly run. Never deliver the same lead twice.

## FROZEN VIBE FILTER (routine uses verbatim, no derivation)
job_title: "chief executive officer", "founder", "owner", "managing director", "executive director", "board chair"
job_level: founder, owner, president, c-suite
company_size: 11-50, 51-200, 201-500
company_country_code: AU, NZ
linkedin_category: retail, building materials, hospitals and health care, individual and family services, disability services, health wellness and fitness, medical and diagnostic laboratories, non-profit organization management
revenue_range: up to $250M AUD
events: merger_and_acquisitions, cost_cutting, lawsuits_and_legal_issues, new_partnership
events_window_days: 90
number_of_results: 12
broaden_size: 501-1000, 1001-5000
broaden_categories: manufacturing, wholesale, logistics and supply chain, food and beverage services, professional services, facilities services, transportation, warehousing

## RUN CONTROL
credit_cap: 50
web_mode: off
deploy_path: prod/nathan-preyser/pipeline/index.html
