# Client Context · Nathan Preyser
# Mode input file for pipeline-builder skill · LIVE mode
# Updated: June 2026 · v3 (call-confirmed filters · Melbourne-first · verified signals only)

PROSPECT_FIRST_NAME: Nathan
PROSPECT_FULL_NAME: Nathan Preyser
TITLE: Fractional CFO & Advisor, Founder of Strategin Advisory
FIRM: Strategin Advisory
WEBSITE: strateginadvisory.com
LOCATION: Greater Melbourne Area, Australia
LINKEDIN: https://www.linkedin.com/in/nathan-preyser
DEPLOY_PATH: prod/nathan-preyser/pipeline/index.html
DEPLOY_URL: https://pipelind.com/prod/nathan-preyser/pipeline

## SELECTION FLAGS
BUYER_PROFILE: operator
ADVISOR_FUNCTION: finance

## WHAT THE CLIENT DOES
Nathan is the founder of Strategin Advisory, working as a Fractional CFO and Advisor for SMEs and not-for-profits across Australia. He has 35+ years of experience as a CFO, COO, GM Procurement and NFP board chair across ASX-listed corporates, mid-market businesses and national not-for-profits. His track record spans M&A due diligence and integration, cashflow turnaround, governance uplift (including NDIS Act, Disability Discrimination Act and Quality & Safeguards compliance), ERP and WMS optimisation, and operational transformation. Notable work includes COO/CFO at Fight Cancer Foundation and lead M&A advisor on the merger that formed the $360M Possability/Lifestyle Solutions group. He holds an FCPA (Fellow CPA) and Certified Professional Business Advisor credential, with a Bachelor of Business (Accounting) and Masters of Marketing from Monash University.

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
- Company size: 10 to 200 employees. Revenue $1M to $200M AUD. No startups. Established operating businesses only. (Rationale confirmed by client: salary-to-revenue ratio means 200 employees implies ~$60M+ revenue; upper bound of $200M keeps target inside SME/mid-market band before major consulting firms take over)
- Industries (confirmed by client on 26 June 2026 call, priority order):
  1. Healthcare: aged care, allied health, disability services (NDIS providers, supported accommodation), hospitals, private hospitals, community health services
  2. Non-for-profits and Social Enterprises: charities, community services, YMCA and similar, universities operating social programs
  3. Retail and Family Business: retail, manufacturing, service-based family businesses
  4. Local Government and Councils: local councils and shire councils in Melbourne metro and surrounds
- Geography: Melbourne, Australia ONLY for the validation phase. (Client confirmed 26 June 2026: start Melbourne, validate 2-3 weeks, then expand nationally, then internationally. Do not expand geography until client explicitly confirms validation is complete)
- Buyer pain: Founders, boards, and executive directors facing a cashflow crisis, turnaround pressure, M&A complexity, or governance gap that requires experienced fractional CFO or COO leadership, without yet justifying a full-time hire

## BUYING SIGNALS THAT INDICATE ACTIVE NEED
VERIFIED-ONLY RULE (mandatory, confirmed by client on 26 June 2026 call): Every lead delivered MUST have a publicly verifiable signal with a cited source link. If no public source exists for the signal, exclude the lead entirely. Do not include leads where the signal is workforce-only or AI-inferred without a cited public source. Client will independently verify every company before outreach.

Primary signals:
- merger_and_acquisitions: businesses undergoing M&A, due diligence, post-merger integration or business combination. Must have a public announcement or news source
- restructuring: active restructure signals cashflow stress or governance gap. Must have a public announcement or news source
- cost_cutting: publicly reported cost cutting matches his cashflow recovery offer. Must have a public news article

Secondary signals (use only if primary signals return fewer than 10 leads after dedup):
- lawsuits_and_legal_issues: publicly reported legal or regulatory issues signal a governance, risk or audit-readiness gap
- new_partnership: publicly announced major partnership that surfaces integration or finance questions

## PERSONALIZATION ANCHOR (why this fits the client)
Nathan's buyers are not posting "we need a fractional CFO" on LinkedIn. They are identifiable by what they are doing operationally: mergers, restructures, cost resets. Pipelind surfaces Melbourne-based companies in those active windows so Nathan can reach them before the need is fully defined. Every lead card must open with the company's situation (the signal and the public source link), not with a description of Nathan's services.

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
job_title: "chief executive officer", "ceo", "founder", "owner", "managing director", "executive director", "board chair"
job_level: founder, owner, president, c-suite
company_size: 11-50, 51-200
company_country_code: AU
city: Melbourne
revenue_range: $1M to $200M AUD
linkedin_category: hospitals and health care, individual and family services, disability services, health wellness and fitness, medical and diagnostic laboratories, non-profit organization management, civic and social organizations, retail, consumer goods, manufacturing, government administration
events: merger_and_acquisitions, restructuring, cost_cutting, lawsuits_and_legal_issues
events_window_days: 90
number_of_results: 12

## RUN CONTROL
credit_cap: 50
web_mode: off
deploy_path: prod/nathan-preyser/pipeline/index.html
geography_phase: validation (Melbourne only — do not expand until client confirms)
