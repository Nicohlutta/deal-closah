"""Shared data contracts between all agents.

Each agent reads/writes these types. Don't change field names without
coordinating with the team — the orchestrator depends on them.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass
class CompanyProfile:
    """Output of icp_scout. Input to outreach and deck_builder."""
    name: str
    industry: str
    size: str               # e.g. "50-200 employees"
    location: str
    website: str
    email: Optional[str] = None
    decision_maker: Optional[str] = None
    decision_maker_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    source: str = "crunchbase"  # crunchbase | g2 | manual

    def save(self):
        out = DATA_DIR / "prospects" / f"{self.name.lower().replace(' ', '_')}.json"
        out.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, name: str) -> "CompanyProfile":
        path = DATA_DIR / "prospects" / f"{name.lower().replace(' ', '_')}.json"
        return cls(**json.loads(path.read_text()))

    @classmethod
    def load_all(cls) -> list["CompanyProfile"]:
        return [cls(**json.loads(p.read_text()))
                for p in (DATA_DIR / "prospects").glob("*.json")]


@dataclass
class OutreachRecord:
    """Written by outreach agent. Tracks every touchpoint with a prospect."""
    company_name: str
    contact_name: str
    channel: str            # email | linkedin | event
    date: str               # ISO: 2026-06-27
    message: str
    subject: Optional[str] = None
    status: str = "drafted" # drafted | sent | replied | followed_up | meeting_booked
    follow_up_due: Optional[str] = None  # ISO date

    def save(self):
        slug = f"{self.company_name}_{self.date}".lower().replace(" ", "_")
        out = DATA_DIR / "outreach" / f"{slug}.json"
        out.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load_for_company(cls, company_name: str) -> list["OutreachRecord"]:
        records = []
        for p in (DATA_DIR / "outreach").glob("*.json"):
            r = cls(**json.loads(p.read_text()))
            if r.company_name.lower() == company_name.lower():
                records.append(r)
        return sorted(records, key=lambda x: x.date)


@dataclass
class MeetingNote:
    """Written by meeting_intel agent. Source of truth for client history."""
    client: str
    date: str               # ISO: 2026-06-27
    raw_notes: str
    extracted_insights: Optional[str] = None
    next_steps: Optional[str] = None
    action_items: list = field(default_factory=list)

    def save(self):
        slug = f"{self.client}_{self.date}".lower().replace(" ", "_")
        out = DATA_DIR / "meetings" / f"{slug}.json"
        out.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load_for_client(cls, client: str) -> list["MeetingNote"]:
        notes = []
        for p in (DATA_DIR / "meetings").glob("*.json"):
            n = cls(**json.loads(p.read_text()))
            if n.client.lower() == client.lower():
                notes.append(n)
        return sorted(notes, key=lambda x: x.date)


@dataclass
class PitchDeck:
    """Written by deck_builder agent."""
    company_name: str
    created_date: str
    slides: list            # list of {title, content} dicts
    format: str = "markdown" # markdown | pptx

    def save(self):
        slug = f"{self.company_name}_{self.created_date}".lower().replace(" ", "_")
        out = DATA_DIR / "decks" / f"{slug}.json"
        out.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load_latest(cls, company_name: str) -> Optional["PitchDeck"]:
        matches = sorted(
            (DATA_DIR / "decks").glob(f"{company_name.lower().replace(' ', '_')}*.json"),
            reverse=True
        )
        return cls(**json.loads(matches[0].read_text())) if matches else None
