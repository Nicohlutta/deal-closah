---
name: cold-email
description: >-
  Writes personalized cold outreach emails and follow-up sequences using the
  problem/solution framework. Use whenever the task involves drafting emails,
  writing outreach messages, creating follow-ups, sending LinkedIn messages,
  or contacting a prospect for the first time.
license: MIT
---

# Cold Email

Drafts highly personalized cold emails and follow-up sequences that lead with
the prospect's specific problem — never the sender's product. Each email has one
CTA, stays under 150 words, and reads like a human wrote it.

## Defaults (do not present options)

- Default tone: warm, direct, peer-to-peer (not vendor-to-buyer).
- Default length: 100–150 words for initial email, 50–80 words for follow-ups.
- Default CTA: a 15-minute call (not a demo, not a proposal).
- Follow-up sequence: Day 1 (initial), Day 4 (gentle bump), Day 8 (value-add), Day 14 (breakup).
- Never pitch the product in the first email — lead with their problem.

## Workflow

1. Call `load_prospect(company_name)` to get company details and decision maker info.
2. Call `load_outreach_history(company_name)` to check prior contact — never duplicate.
3. Identify the specific problem this company is likely facing based on their industry and size.
4. Call `draft_cold_email` or `draft_follow_up` with the right parameters.
5. Call `save_outreach_record` to log the drafted message.
6. Produce the output below.

## Gotchas

- Never start with "I hope this email finds you well" — delete on sight.
- Personalization must be specific: a recent company news item, a job posting, or a known pain.
- The subject line should create curiosity, not describe the email content.
- Follow-up emails should add NEW value — never just "checking in."
- If outreach history shows 3+ unanswered messages, draft a breakup email, not another bump.

## Output template

Produce EXACTLY these sections, in this order:

**Outreach Draft — [Company] / [Contact Name]**
*Type: [Initial / Follow-up Day N / Event / Breakup]*

> **Subject:** [subject line]
>
> [Email body — under 150 words]
>
> [Your name]

**Why This Works**
- Hook: [what specific problem or trigger you led with]
- CTA: [exact ask]
- Personalization: [what company-specific detail you used]

**Follow-up Schedule**
- Day 4: [brief description of what the follow-up will say]
- Day 8: [value-add angle]
- Day 14: [breakup email]

*Saved to data/outreach/ — follow-up due [date].*
