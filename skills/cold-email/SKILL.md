---
name: cold-email
description: >-
  Writes personalized cold outreach emails using the Awareness-stage framework:
  lead with the prospect's problem, one data point, one reciprocal value offer,
  one CTA. Never pitch the product. Applies to initial cold emails, LinkedIn
  connection requests, and post-call thank-you follow-ups.
license: MIT
---

# Cold Email

Crafts cold outreach that converts at the Awareness stage. The only goal of a
cold email is a **reply or a connection** — not a demo booking. Every draft leads
with the prospect's specific problem, frames the sender as a peer researcher, and
offers aggregated industry intelligence in exchange for 15 minutes.

## Defaults (do not present options)

- Stage target: Awareness only. Do not attempt to achieve Preference or Conviction in a first message.
- Default length: under 180 words for initial email; under 300 characters for LinkedIn request.
- Default CTA: 15-minute conversation — never a demo, never a proposal, never a "quick call."
- Follow-up schedule: Day 4 (gentle bump), Day 8 (new value angle), Day 14 (breakup).
- Never pitch the product in the first email.
- Never open with "My name is..." or "I hope this finds you well."
- Never write "I am not selling anything" — it plants exactly the wrong idea.

## Workflow

1. Call `load_prospect(company_name)` to get company details and role/pain context.
2. Call `load_outreach_history(company_name)` — if 3+ unanswered messages, draft a breakup email, not another bump.
3. Identify the specific problem this role faces (pipeline visibility, conversion drops, churn signals, etc.).
4. Apply the No-Dump Rule: **one insight + one positioning sentence + one value offer + one CTA**. Nothing else.
5. Run the self-check below before producing any draft.
6. Call `draft_cold_email` or `draft_follow_up` with the right parameters.
7. Call `save_outreach_record` to log the draft.

## No-Dump Rule

Every cold email contains **only these four elements**, in this order:

1. One insight or data point that names the prospect's problem (not the sender's solution)
2. One sentence positioning the sender as a researcher with relevant data, not a vendor
3. One reciprocal value offer — the aggregated report they receive for participating
4. One low-friction CTA — a question or an ask for 15 minutes

No company backstory. No product description. No feature list. No pre-emptive objection handling.

## Subject Line Rules

Subject lines must signal relevance to a problem the prospect **already has**.

**Banned patterns:**
- "Schedule time to chat about X" — seller's ask, not buyer-relevant
- "Quick question about X" — generic, signals low value
- "Introduction — [Your Name], [Company]" — zero relevance signal

**Approved patterns:**
- **Insight-forward:** names a behavior or pattern they are already seeing in their data
- **Curiosity-gap:** implies you have data on something they suspect but cannot measure
- **Peer-signal:** implies other industry peers are engaging with this topic

## Reciprocal Value (required in every cold email)

Place in **paragraph 2**, before the CTA — not the closing.
Frame as peer intelligence exchanged between professionals, not a marketing deliverable.

> "I'm mapping this across the industry through conversations with [role] leaders.
> Everyone who participates receives the full anonymized insight report — no pitch attached."

Adapt the role descriptor to the stakeholder. This offer is the primary reason to reply.

## Emotional Register

Tone: **peer-to-peer researcher**, not vendor-to-buyer. The prospect is the domain expert.
The sender is a researcher collecting field intelligence.

**Approved language:**
- "Your perspective on [specific domain] would directly shape how we interpret this data."
- "Given your work at [Company], your read on this would be particularly grounding."

**Banned language:**
- "I am not selling anything" — defensive, plants the wrong idea
- "I would love to pick your brain" — informal, undervalues their expertise
- "We would heavily value your insights" — generic flattery

## Self-check (run before every draft)

**Cold Email:**
- [ ] Opener does NOT start with "My name is" or lead with the company name
- [ ] Subject line does NOT use banned patterns above
- [ ] Reciprocal value offer appears in paragraph 2 (before the CTA)
- [ ] Only one data point used across the entire email
- [ ] "I am not selling anything" is absent
- [ ] CTA is a single low-friction question
- [ ] Total body is under 180 words

**LinkedIn Request:**
- [ ] Character count is 300 or under (count before writing)
- [ ] Leads with a hook about their world, not the product
- [ ] Ends with sender's first name only

## Output template

Produce EXACTLY these sections, in this order:

**Outreach Draft — [Company] / [Contact Name]**
*Type: [Initial / Follow-up Day N / Event / Breakup] · [Channel: Email / LinkedIn]*

> **Subject:** [insight-forward or curiosity-gap subject line]
>
> Hi [Name],
>
> [One sentence naming a pattern or behavior their role is already dealing with —
> use one industry data point or signal. No product mention.]
>
> [One sentence connecting that pattern to their specific role's cost.]
>
> I'm mapping this across the industry through conversations with [role] leaders.
> Everyone who participates receives the aggregated findings — no pitch attached.
> Given your work at [Company], your read on this would be particularly useful.
>
> Would a 15-minute call work for you next week?
>
> [Sender first name]

**Why This Works**
- Hook: [specific problem or trigger you led with]
- CTA: [exact ask]
- Personalization: [company-specific detail used]

**Follow-up Schedule**
- Day 4: [brief description of follow-up angle]
- Day 8: [value-add angle — new data point or insight, not "checking in"]
- Day 14: [breakup email]

*Saved to data/outreach/ — follow-up due [date].*
