"""Outreach Agent — drafts emails, follow-ups, event messages. OWNER: Teammate 2.

Tools to implement:
  load_prospect(company_name)         — read from data/prospects/
  load_outreach_history(company_name) — read from data/outreach/
  draft_cold_email(company_name, contact, problem, solution)
  draft_follow_up(company_name, contact, days_since_last)
  draft_event_outreach(company_name, contact, event_name, event_date)
  save_outreach(record_json)          — write to data/outreach/
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(HERE))

from agentkit import AgentResult, run_agent, self_grade, tool
from interfaces import CompanyProfile, OutreachRecord

# Cascade: granite4:micro answers first; escalates to strong tier if self-confidence
# falls below this threshold. Cold email tone/quality is the sensitive dimension here.
# granite4:micro self-grades 0.90–1.00 on most tasks, so set threshold above 0.92
# to see real escalation on complex drafts. Override with CASCADE_THRESHOLD env var.
_CASCADE_THRESHOLD = float(os.getenv("CASCADE_THRESHOLD", "0.90"))

SYSTEM = """You are an Outreach specialist — an expert sales development rep (SDR).
You write personalized, concise outreach emails that lead with the prospect's
problem (not your product), offer a clear solution, and end with a single CTA.
You never pitch in the first email. Default tone: warm, direct, human. No fluff."""


# ── tools ─────────────────────────────────────────────────────────────────────

@tool
def load_prospect(company_name: str) -> str:
    """Load a company profile from the prospects database.
    Returns a JSON company profile with industry, size, decision maker details.
    Call this first before drafting any outreach so emails are personalized.
    """
    try:
        profile = CompanyProfile.load(company_name)
        return json.dumps(profile.__dict__, indent=2)
    except Exception:
        return json.dumps({"error": f"No profile found for {company_name}. Run ICP scout first."})


@tool
def load_outreach_history(company_name: str) -> str:
    """Load all previous outreach records for a company.
    Returns a JSON list of past messages, dates, channels, and statuses.
    Call before drafting follow-ups to know what was already sent and when.
    """
    records = OutreachRecord.load_for_company(company_name)
    if not records:
        return json.dumps({"history": [], "message": "No prior outreach found."})
    return json.dumps([r.__dict__ for r in records], indent=2)


@tool
def draft_cold_email(company_name: str, contact_name: str, problem: str, solution: str) -> str:
    """Draft a personalized cold outreach email using the problem/solution framework.
    The email leads with the prospect's pain point, not your product.
    Returns a JSON object with subject and body fields.
    """
    # The model will generate this — this tool provides structure to ground it
    return json.dumps({
        "instructions": (
            f"Draft a cold email to {contact_name} at {company_name}. "
            f"Lead with this problem they likely have: {problem}. "
            f"Offer this solution: {solution}. "
            "Keep it under 150 words. One clear CTA (a 15-min call). "
            "No attachments, no features list. Human, not corporate."
        )
    })


@tool
def draft_follow_up(company_name: str, contact_name: str, days_since_last: int) -> str:
    """Draft a follow-up email for a prospect who hasn't responded.
    Adjust tone based on days_since_last (3 days = gentle bump, 7+ = value add).
    Returns a JSON object with subject and body fields.
    """
    due = date.today() + timedelta(days=3)
    return json.dumps({
        "follow_up_due": str(due),
        "instructions": (
            f"Draft a follow-up email to {contact_name} at {company_name}. "
            f"It has been {days_since_last} days since the last message. "
            "If 3 days: short, friendly bump (2 sentences). "
            "If 7+ days: add a new piece of value (stat, insight, or relevant news). "
            "Never be pushy. End with a soft CTA."
        ),
    })


@tool
def draft_event_outreach(company_name: str, contact_name: str, event_name: str, event_date: str) -> str:
    """Draft an outreach message for connecting at an upcoming event.
    References the event to create a natural, warm reason to connect.
    Returns a JSON object with subject and body fields.
    """
    return json.dumps({
        "instructions": (
            f"Draft an event-based outreach message to {contact_name} at {company_name}. "
            f"Reference that you're both attending {event_name} on {event_date}. "
            "Keep it to 3 sentences. Ask for a quick 10-min coffee at the event. "
            "Include one relevant fact about their company to show research."
        ),
    })


@tool
def save_outreach_record(company_name: str, contact_name: str, channel: str,
                         subject: str, message: str) -> str:
    """Save a drafted outreach message to the outreach database.
    Call after finalizing any email or message draft to track it.
    Returns confirmation with the file path.
    """
    record = OutreachRecord(
        company_name=company_name,
        contact_name=contact_name,
        channel=channel,
        date=str(date.today()),
        subject=subject,
        message=message,
        status="drafted",
        follow_up_due=str(date.today() + timedelta(days=3)),
    )
    record.save()
    return f"Saved outreach record for {company_name} / {contact_name}"


# ── agent entry point (cascade) ───────────────────────────────────────────────

_TOOLS = [
    load_prospect,
    load_outreach_history,
    draft_cold_email,
    draft_follow_up,
    draft_event_outreach,
    save_outreach_record,
]


def run(task: str, skill=None) -> AgentResult:
    """Draft outreach with cascade: granite4:micro first, escalate if quality is low.

    Cold email tone is the most quality-sensitive task in the pipeline. Cascade
    lets granite4 handle simple follow-up bumps for $0; complex initial drafts
    that need the No-Dump Rule and Stage Calibration escalate to the strong tier.
    """
    # Step 1: always try cheap local first (granite4:micro — $0, private, fast)
    cheap = run_agent(
        task, tools=_TOOLS, skill=skill, system=SYSTEM,
        provider="local", tier="default",
    )

    # Step 2: self-grade — local model rates its own output quality (0.0–1.0)
    confidence, _ = self_grade(task, cheap.text, provider="local")

    # Step 3: escalate to strong tier when confidence is low (skip in offline mode)
    if confidence < _CASCADE_THRESHOLD and os.getenv("AGENT_OFFLINE") != "1":
        try:
            strong = run_agent(task, tools=_TOOLS, skill=skill, system=SYSTEM, tier="strong")
            print(
                f"  [cascade] granite4:micro → strong (confidence {confidence:.2f} < {_CASCADE_THRESHOLD})",
                file=sys.stderr,
            )
            return strong
        except Exception as e:
            print(
                f"  [cascade] escalation unavailable ({type(e).__name__}) — staying local",
                file=sys.stderr,
            )
    else:
        print(
            f"  [cascade] resolved locally — confidence {confidence:.2f} >= {_CASCADE_THRESHOLD}",
            file=sys.stderr,
        )

    return cheap
