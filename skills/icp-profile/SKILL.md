---
name: icp-profile
description: >-
  Finds and profiles ideal customer companies via Google/SerpAPI based on
  industry, location, company size, and decision-maker type. Use whenever the
  task involves finding prospects, building a target list, searching for companies,
  filtering ICPs, or identifying decision makers for outreach.
license: MIT
---

# ICP Profile

Searches Google via SerpAPI to build a structured list of ideal customer profiles
matching the user's targeting criteria. Returns company profiles with contact
details, decision maker names and titles, and enriched metadata ready for outreach.

## Defaults (do not present options)

- Default company size: 50–500 employees unless specified.
- Default decision maker targets: VP Sales, CRO, Head of Revenue, or Founder.
- Always return email pattern even when direct email is unavailable.
- Label email patterns as patterns — never present inferred emails as verified.
- Limit results to 10 companies per search unless the user specifies more.
- Call `verify_email` only when you have a specific email to check (Hunter.io, 25/mo free).

## Workflow

1. Call `search_companies(query)` once with a descriptive query including industry, location, and size signal.
2. Check the results: if each entry already has `decision_maker`, `decision_maker_title`, and `linkedin_url` fields, **skip step 3** and go directly to the output template.
3. Only if those fields are missing: call `get_company_details(company_name)` for each company that needs enrichment.
4. Assemble the final list in the Output template below.

## Gotchas

- SerpAPI returns web results, not structured databases — extract company name and domain from snippets carefully.
- Never invent email addresses — use the pattern format (firstname.lastname@domain.com) and label it as a pattern.
- Decision maker titles vary by company stage: early-stage = Founder/CEO, mid-stage = VP, late-stage = CRO/CCO.
- Always surface at least 2 decision makers per company with different seniority levels.
- If a result looks like a directory listing (e.g. G2, Clutch, Crunchbase), extract the companies listed — don't cite the directory itself as a company.

## Output template

Produce EXACTLY these sections, in this order:

**ICP Search Results**
*Filters: [industry] · [location] · [size range] · [decision maker target]*

| # | Company | Industry | Size | Location | Decision Maker | Title | Email Pattern | Source |
|---|---------|----------|------|----------|----------------|-------|---------------|--------|
| 1 | ...     | ...      | ...  | ...      | ...            | ...   | ...           | ...    |

**Top 3 Picks** (with brief rationale for each)
1. [Company] — [why they're the best fit]

**Caveats**
- [Any data quality issues, e.g. inferred employee counts, unverified emails]

*Sourced via SerpAPI on [date]. Run `search_companies` again for fresh data.*
