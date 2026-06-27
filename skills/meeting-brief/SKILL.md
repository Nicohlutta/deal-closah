---
name: meeting-brief
description: >-
  Extracts key insights from raw meeting notes, generates pre-meeting briefing
  documents, and manages CRM records. Use whenever the task involves logging
  meeting notes, generating a pre-meeting brief, reviewing client history,
  scheduling a meeting, or checking CRM pipeline status.
license: MIT
---

# Meeting Brief

Processes raw meeting notes to extract decisions, action items, and risks. Generates
sharp pre-meeting briefs that surface what happened before, what needs to be discussed
now, and the strategic angle to lock in the next step with the client.

## Defaults (do not present options)

- Pre-meeting brief covers: last 3 meetings + all outreach history.
- Action items are always assigned to a named person (not "we" or "the team").
- Action items are always written as a numbered list, never prose or bullets.
- Pre-brief includes one "closing angle" — the single most important thing to accomplish.
- Meeting notes are saved immediately after extraction, before generating any output.
- Pre-meeting briefs are written in the second person ("you met with...", "your next step is...").
- Keep the tone sharp and sales-focused — concrete next moves and angles, never generic filler.

## Workflow

1. If logging notes: call `log_meeting_notes(client, date, raw_notes)` first, then extract.
2. If generating a pre-brief: call `get_client_history(client)` to pull full timeline.
3. Identify: open action items, unresolved objections, last sentiment, and next logical step.
4. Produce the output below.

## Gotchas

- Raw notes are messy — extract intent, not transcription.
- If action items lack owners, flag them explicitly ("unassigned — assign before next call").
- Always include all four core brief sections even when data is sparse — never drop one:
  Relationship Summary (Situation), Open Action Items (Open Items), What To Push On Today
  (Agenda Suggestion), and Closing Strategy (Closing Angle).
- Flag unresolved action items carried over from previous meetings prominently at the top of
  the Open Action Items / Open Items section — do not bury a stale commitment in the list.
- Pre-meeting brief is NOT a summary of past meetings — it's a strategy doc for the NEXT meeting.
- Never fabricate a meeting detail that wasn't in the notes.
- If meeting history is empty, generate a first-meeting brief using only the company profile.

## Output template for pre-meeting brief

Produce EXACTLY these sections, in this order:

**Pre-Meeting Brief — [Client] · [Date]**

**Situation** (2–3 sentences: where things stand right now)

**Key History**
- [Date]: [1-line summary of most important prior interaction]
- [Date]: [1-line summary]

**Open Items**
- [ ] [Action item] — Owner: [name] — Due: [date]

**Agenda Suggestion**
1. [Topic 1 — why it matters]
2. [Topic 2]
3. [The ask / close]

**Closing Angle**
[One paragraph: the single strategic move to make in this meeting]

**Risks / Watch-outs**
- [Anything that could derail the meeting]

---

## Output template for meeting notes extraction

**Meeting Notes — [Client] · [Date]**

**Decisions Made**
- [Decision]

**Action Items**
- [ ] [Item] — Owner: [name] — Due: [date]

**Open Questions**
- [Question]

**Sentiment / Signals**
[1–2 sentences: buying signals, objections, relationship temperature]

**Next Step**
[Specific, dated, owned next action]
