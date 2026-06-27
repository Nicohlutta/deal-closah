---
name: event-scout
description: >-
  Finds upcoming events (conferences, summits, meetups) that the ideal customer
  profile attends or hosts via SerpAPI, then drafts pre-event outreach messages.
  Use whenever the task involves finding events, conference outreach, or
  connecting with prospects before a specific event.
license: MIT
---

# Event Scout

Discovers upcoming events relevant to the ICP by searching Google via SerpAPI
with targeted queries (industry + location + year). Returns a structured event
list with attendee profiles and drafts warm pre-event outreach tailored to each
event context.

## Defaults (do not present options)

- Default search window: next 90 days.
- Default event types: conferences, trade shows, industry summits (not webinars unless specified).
- Pre-event outreach sent 7–14 days before the event — never same-day.
- Outreach asks for a specific 15-min coffee at the event, not a general connection.
- Apply the cold-email No-Dump Rule to all pre-event outreach: one hook, one value offer, one CTA.

## Workflow

1. Call `find_events(industry, location)` — this runs 3 SerpAPI queries and deduplicates results.
2. Review the returned event list and identify which ones your ICP is most likely to attend.
3. For each matched prospect in data/prospects/, call `get_company_details(company_name)` to confirm the contact.
4. Draft pre-event outreach for the top 3–5 events using the output template below.
5. Lead each outreach with a specific detail about the event — not a generic conference pitch.

## Gotchas

- SerpAPI returns landing pages and news articles, not a structured event database — parse dates from snippets.
- If no date is visible in the snippet, label the event date as "TBD — verify before outreach."
- Pre-event outreach has a higher open rate than cold email — always personalize with a specific event detail.
- Never reach out to the same contact about the same event twice — check data/outreach/ first.
- Keep SerpAPI calls to 3 query variations maximum (respect the budget limit in find_events).

## Output template

Produce EXACTLY these sections, in this order:

**Upcoming Events for [ICP Industry] — [Location]**

| # | Event | Date | Type | Why Your ICP Attends | URL |
|---|-------|------|------|----------------------|-----|
| 1 | ...   | ...  | ...  | ...                  | ... |

**Pre-Event Outreach Drafts**

For each event with a matched prospect:

> **To:** [Name], [Title] at [Company]
> **Subject:** [Event Name] next [date] — quick coffee?
>
> Hi [Name],
>
> [One sentence about a pattern or challenge in their world relevant to this event.]
>
> I'm mapping this across the industry — everyone I speak with gets the aggregated findings.
> Given your work at [Company], your read would be useful.
>
> Are you headed to [Event]? Would a 15-min coffee work while we're both there?
>
> [Sender first name]

*Events sourced via SerpAPI on [date]. Fixtures used: [yes/no].*
