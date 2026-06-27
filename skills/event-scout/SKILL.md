---
name: event-scout
description: >-
  Finds upcoming events (conferences, meetups, trade shows) that the ideal customer
  profile attends or hosts, then drafts pre-event outreach messages. Use whenever
  the task involves finding events, scraping company event pages, LinkedIn events,
  conference outreach, or connecting with prospects before an event.
license: MIT
---

# Event Scout

Discovers upcoming events relevant to the ICP by searching Eventbrite, Luma,
LinkedIn, and company event pages. Returns a structured event list with attendee
profiles and drafts warm pre-event outreach tailored to each event context.

## Defaults (do not present options)

- Default search window: next 90 days.
- Default event types: conferences, trade shows, industry meetups (not webinars unless specified).
- Pre-event outreach sent 7–14 days before the event — never same-day.
- Outreach asks for a specific 15-min coffee at the event, not a general connection.

## Workflow

1. Call `find_events(industry, location)` to get the upcoming event list.
2. For each target company, call `scrape_company_events(website)` to find events they're promoting.
3. Cross-reference ICP profiles from data/prospects/ with event attendee types.
4. Draft pre-event outreach using `draft_event_outreach(company, contact, event_name, event_date)`.
5. Produce the output below.

## Gotchas

- LinkedIn event scraping is legally grey — use Luma and Eventbrite as primary sources.
- Scraping company event pages can fail on JS-heavy sites — fall back to fixtures on errors.
- Pre-event outreach has a higher open rate than cold email — personalize with a specific event detail.
- Never reach out to the same contact about the same event twice.

## Output template

Produce EXACTLY these sections, in this order:

**Upcoming Events for [ICP Industry] — [Location]**

| # | Event | Date | Type | Why Your ICP Attends | URL |
|---|-------|------|------|---------------------|-----|
| 1 | ...   | ...  | ...  | ...                 | ... |

**Pre-Event Outreach Drafts**

For each event with a matched prospect:

> **To:** [Name], [Title] at [Company]
> **Subject:** [Event Name] next [date] — quick coffee?
> **Body:** [3-sentence personalized message]

*Events sourced from [sources] on [date]. Fixtures used: [yes/no].*
