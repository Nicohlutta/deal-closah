"""Meeting Intel — CRM, meeting notes, pre-meeting briefs, scheduling. OWNER: Teammate 3.

Tools to implement:
  log_meeting_notes(client, date, raw_notes)   — extract + save to data/meetings/
  get_client_history(client)                   — full history: prospects + outreach + meetings
  generate_pre_brief(client)                   — pre-meeting briefing doc
  schedule_meeting(client, datetime, platform) — create calendar invite
  get_crm_summary()                            — all prospects and their status
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(HERE))

from agentkit import AgentResult, run_agent, tool
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
