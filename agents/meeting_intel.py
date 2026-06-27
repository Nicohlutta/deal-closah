"""Meeting Intel — CRM, meeting notes, pre-meeting briefs, scheduling. OWNER: Teammate 3.

Tools to implement:
  log_meeting_notes(client, date, raw_notes)   — extract + save to data/meetings/
  get_client_history(client)                   — full history: prospects + outreach + meetings
  generate_pre_brief(client)                   — pre-meeting briefing doc
  schedule_meeting(client, datetime, platform) — create calendar invite
  get_crm_summary()                            — all prospects and their status
"""

from __future__ import annotations

import datetime
import json
import os
import re
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(HERE))

from agentkit import AgentResult, chat, run_agent, tool
from interfaces import CompanyProfile, MeetingNote, OutreachRecord

OFFLINE = os.getenv("AGENT_OFFLINE", "0") == "1"

SYSTEM = """You are a Meeting Intelligence specialist — a chief of staff who knows
every client interaction, extracts what matters from raw notes, and prepares
sharp pre-meeting briefs. You surface action items, risks, and opportunities.
You are concise, structured, and never miss a follow-up."""


# ── tools ─────────────────────────────────────────────────────────────────────

@tool
def log_meeting_notes(client: str, meeting_date: str, raw_notes: str) -> str:
    """Extract key insights from raw meeting notes and save them to the CRM.
    Identifies: decisions made, action items, open questions, sentiment.
    Returns a structured summary and confirms save to data/meetings/.
    """
    # The model will extract from raw_notes — we just save what it produces
    note = MeetingNote(
        client=client,
        date=meeting_date or str(date.today()),
        raw_notes=raw_notes,
    )
    note.save()
    return json.dumps({
        "saved": True,
        "client": client,
        "date": note.date,
        "instructions": (
            f"Extract from these notes for {client}: "
            "1) Key decisions made, 2) Action items with owners, "
            "3) Open questions, 4) Next steps, 5) Sentiment/risks. "
            f"Raw notes: {raw_notes}"
        ),
    })


@tool
def get_client_history(client: str) -> str:
    """Retrieve the full history for a client: profile, all outreach, all meeting notes.
    Returns a comprehensive JSON timeline sorted by date.
    Call this before generating a pre-meeting brief.
    """
    profile = None
    try:
        p = CompanyProfile.load(client)
        profile = p.__dict__
    except Exception:
        pass

    outreach = [r.__dict__ for r in OutreachRecord.load_for_company(client)]
    meetings = [n.__dict__ for n in MeetingNote.load_for_client(client)]

    return json.dumps({
        "profile": profile,
        "outreach_history": outreach,
        "meeting_notes": meetings,
        "total_touchpoints": len(outreach) + len(meetings),
    }, indent=2)


@tool
def get_crm_summary() -> str:
    """Return a summary of all prospects in the CRM with their current status.
    Shows: company name, last contact date, outreach count, meeting count.
    Use for pipeline overview or to find who needs follow-up.
    """
    profiles = CompanyProfile.load_all()
    summary = []
    for p in profiles:
        outreach = OutreachRecord.load_for_company(p.name)
        meetings = MeetingNote.load_for_client(p.name)
        summary.append({
            "company": p.name,
            "industry": p.industry,
            "last_outreach": outreach[-1].date if outreach else None,
            "outreach_count": len(outreach),
            "meeting_count": len(meetings),
            "status": outreach[-1].status if outreach else "not_contacted",
        })
    return json.dumps(summary, indent=2) if summary else "No prospects in CRM yet."


@tool
def schedule_meeting(client: str, datetime_str: str, platform: str) -> str:
    """Create a calendar invite for a meeting with a client.
    platform: 'google_meet' | 'zoom' | 'in_person'
    Returns a calendar event JSON and an .ics file path.
    """
    # TODO Teammate 3: integrate with Google Calendar API or output .ics file
    # Google Calendar API: https://developers.google.com/calendar/api
    # Simple .ics output works for offline demo:
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Meeting with {client}
DTSTART:{datetime_str.replace('-', '').replace(':', '').replace(' ', 'T')}
DURATION:PT30M
DESCRIPTION:Sales meeting — deal-closah
END:VEVENT
END:VCALENDAR"""

    ics_path = HERE / "data" / "meetings" / f"{client.lower().replace(' ', '_')}_invite.ics"
    ics_path.write_text(ics_content)

    return json.dumps({
        "client": client,
        "datetime": datetime_str,
        "platform": platform,
        "ics_saved": str(ics_path),
        "note": "Add GOOGLE_CALENDAR_API_KEY to .env for live calendar integration",
    })


# ── agent entry point ─────────────────────────────────────────────────────────

def run(task: str, skill=None) -> AgentResult:
    """Handle meeting notes, CRM queries, briefs, and scheduling."""
    return run_agent(
        task,
        tools=[
            log_meeting_notes,
            get_client_history,
            get_crm_summary,
            schedule_meeting,
        ],
        skill=skill,
        system=SYSTEM,
        tier="cheap",
    )


# ── direct-call functions (orchestrator calls these for explicit commands) ─────

_EXTRACT_PROMPT = """Extract structured intelligence from these raw meeting notes.

Client: {client}
Date: {meeting_date}
Raw notes:
{raw_notes}

Return ONLY valid JSON with these exact keys:
{{
  "decisions": ["each key decision made", "..."],
  "action_items": ["plain phrase, NO numbering — one item per entry", "..."],
  "next_steps": "the single most important next step",
  "sentiment": "one line on relationship temperature / buying signals / risks"
}}
Extract intent, not transcription. Never invent details that are not in the notes."""


def log_meeting(client: str, date: str, raw_notes: str) -> MeetingNote:
    """Extract decisions, action items, next steps, and sentiment from raw
    meeting notes using the model, persist the result to data/meetings/, and
    return the populated MeetingNote.

    Fails soft: if extraction or save fails, the note is still returned with a
    note about what went wrong — this never raises.
    """
    meeting_date = (date or "").strip() or str(datetime.date.today())
    note = MeetingNote(client=client, date=meeting_date, raw_notes=raw_notes)

    try:
        result = chat(
            _EXTRACT_PROMPT.format(
                client=client, meeting_date=meeting_date, raw_notes=raw_notes
            ),
            system=SYSTEM,
            tier="cheap",
            json_mode=True,
        )
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", result.text).strip()
        data = json.loads(raw)
        decisions = data.get("decisions") or []
        items = data.get("action_items") or []
        note.action_items = [
            f"{i}. {str(a).strip()}" for i, a in enumerate(items, 1) if str(a).strip()
        ]
        note.next_steps = (data.get("next_steps") or "").strip() or None
        sentiment = (data.get("sentiment") or "").strip()
        parts = []
        if decisions:
            parts.append("Decisions: " + "; ".join(str(d).strip() for d in decisions))
        if sentiment:
            parts.append("Sentiment: " + sentiment)
        note.extracted_insights = "\n".join(parts) or None
    except Exception as e:  # fail soft — keep the raw note, flag the failure
        note.extracted_insights = f"(automatic extraction failed: {e})"

    try:
        (HERE / "data" / "meetings").mkdir(parents=True, exist_ok=True)
        note.save()
    except Exception as e:  # save failed — still hand back the populated note
        note.extracted_insights = (note.extracted_insights or "") + f"\n(save failed: {e})"

    return note


_BRIEF_PROMPT = """You are preparing the sales rep to walk into a meeting with {client}.

Everything on record for this client (past meeting notes + outreach history):
{context}

Write a sharp, sales-focused pre-meeting brief addressed to the rep in the SECOND
PERSON ("you met with...", "your next step is..."). Use EXACTLY these four
sections, in this order, and include every section even when data is sparse:

1. Relationship Summary — what has happened so far with this client.
2. Open Action Items — unresolved items from all past meetings, as a numbered
   list. Flag anything carried over and still unresolved prominently at the top.
3. What To Push On Today — specific talking points for the next meeting.
4. Closing Strategy — concrete moves to advance toward a signed deal.

Keep every point concrete and tactical. No generic filler."""


def generate_brief(client: str) -> str:
    """Assemble all meeting + outreach history for a client and produce a
    four-section pre-meeting brief as a formatted string.

    Returns a clear message if no history exists. Fails soft: returns an error
    string instead of raising.
    """
    try:
        meetings = MeetingNote.load_for_client(client)
    except Exception:
        meetings = []
    try:
        outreach = OutreachRecord.load_for_company(client)
    except Exception:
        outreach = []

    if not meetings and not outreach:
        return (
            f"No history found for {client}. "
            "Log a meeting or some outreach for this client first, then I can build a brief."
        )

    context = json.dumps(
        {
            "client": client,
            "meeting_notes": [n.__dict__ for n in meetings],
            "outreach_history": [r.__dict__ for r in outreach],
        },
        indent=2,
    )

    try:
        result = chat(
            _BRIEF_PROMPT.format(client=client, context=context),
            system=SYSTEM,
            tier="cheap",
        )
        return result.text
    except Exception as e:  # fail soft
        return f"Could not generate a brief for {client}: {e}"
