---
name: icp-profile
description: >-
  Finds and profiles ideal customer companies from Crunchbase and G2 based on
  industry, location, company size, and decision-maker type. Use whenever the
  task involves finding prospects, building a target list, searching for companies,
  filtering ICPs, or identifying decision makers for outreach.
license: MIT
---

# ICP Profile

Searches Crunchbase and G2 to build a structured list of ideal customer profiles
matching the user's targeting criteria. Returns company profiles with contact
details, decision maker names and titles, and enriched metadata ready for outreach.

## Defaults (do not present options)

- Default company size: 50–500 employees unless specified.
- Default decision maker targets: VP Sales, CRO, Head of Revenue, or Founder.
- Always return email pattern even when direct email is unavailable.
- Limit results to 10 companies per search unless the user specifies more.
- Source preference: Crunchbase first, G2 second, manual last.

## Workflow

1. Call `search_crunchbase(industry, location, min_employees, max_employees)` with the user's filters.
2. If category is software-specific, also call `search_g2(category, location)`.
3. For each result, call `get_company_details(company_name)` to enrich with email and decision makers.
4. Assemble the final list in the Output template below.

## Gotchas

- Crunchbase employee counts are often outdated by 6–12 months — note this in caveats.
- G2 lists vendors, not buyers. Use G2 to find companies *in* a software category as buyers.
- Never invent email addresses — use the pattern format (firstname.lastname@domain.com) and label it as a pattern.
- Decision maker titles vary by company stage: early-stage = Founder/CEO, mid-stage = VP, late-stage = CRO/CCO.
- Always surface at least 2 decision makers per company with different seniority levels.

## Output template

Produce EXACTLY these sections, in this order:

**ICP Search Results**
*Filters: [industry] · [location] · [size range] · [decision maker target]*

| # | Company | Industry | Size | Location | Decision Maker | Title | Email Pattern | Source |
|---|---------|----------|------|----------|---------------|-------|--------------|--------|
| 1 | ...     | ...      | ...  | ...      | ...           | ...   | ...          | ...    |

**Top 3 Picks** (with brief rationale for each)
1. [Company] — [why they're the best fit]

**Caveats**
- [Any data quality issues, e.g. stale employee counts]

*Sourced from Crunchbase/G2 on [date]. Run `search_crunchbase` again for fresh data.*
