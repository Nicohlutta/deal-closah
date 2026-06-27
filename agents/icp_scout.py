"""ICP Scout — finds companies, decision makers, and events. OWNER: Teammate 1.

Tools to implement:
  search_crunchbase(industry, location, min_employees, max_employees)
  search_g2(category, location)
  get_company_details(company_name)
  find_decision_maker(company_name, title_keywords)
  find_events(industry, location)
  scrape_company_events(company_website)

Offline: use fixtures/crunchbase_sample.json and fixtures/events_sample.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(HERE))

from agentkit import AgentResult, load_skill, run_agent, tool
from interfaces import CompanyProfile

FIXTURES = HERE / "fixtures"
OFFLINE = os.getenv("AGENT_OFFLINE", "0") == "1"

SYSTEM = """You are an ICP Scout — an expert at finding ideal customer profiles.
You search for companies that match specific criteria (industry, location, size,
decision maker type) using Crunchbase and G2. You return structured company
profiles with contact details. Be precise and honest about data quality."""


# ── tools ─────────────────────────────────────────────────────────────────────

@tool
def search_crunchbase(industry: str, location: str, min_employees: int, max_employees: int) -> str:
    """Search Crunchbase for companies matching the ICP criteria.
    Returns a JSON list of company profiles with name, size, location, website.
    Use for finding B2B SaaS, tech, or enterprise companies by industry and size.
    """
    if OFFLINE:
        data = json.loads((FIXTURES / "crunchbase_sample.json").read_text())
        results = [c for c in data if industry.lower() in c.get("industry", "").lower()]
        return json.dumps(results[:10], indent=2)

    # TODO Teammate 1: implement live Crunchbase API call
    # API docs: https://data.crunchbase.com/docs
    # Free tier: https://www.crunchbase.com/api (requires key in .env as CRUNCHBASE_API_KEY)
    # Fallback to fixtures on any error
    try:
        raise NotImplementedError("Implement Crunchbase API call")
    except Exception:
        data = json.loads((FIXTURES / "crunchbase_sample.json").read_text())
        return json.dumps(data[:5], indent=2)


@tool
def search_g2(category: str, location: str) -> str:
    """Search G2 for companies in a software category and location.
    Returns a JSON list with company name, website, employee count, and ratings.
    Use when targeting software buyers or SaaS companies specifically.
    """
    if OFFLINE:
        data = json.loads((FIXTURES / "crunchbase_sample.json").read_text())
        return json.dumps(data[:5], indent=2)

    # TODO Teammate 1: G2 doesn't have a public API — scrape https://www.g2.com/categories/
    # or use SerpAPI with site:g2.com searches. Fallback to fixtures.
    try:
        raise NotImplementedError("Implement G2 search (scrape or SerpAPI)")
    except Exception:
        data = json.loads((FIXTURES / "crunchbase_sample.json").read_text())
        return json.dumps(data[:5], indent=2)


@tool
def get_company_details(company_name: str) -> str:
    """Get detailed info for a specific company: email, LinkedIn, decision makers.
    Returns a JSON object with all available contact details.
    Use after search_crunchbase or search_g2 to enrich a result.
    """
    # TODO Teammate 1: implement via Crunchbase entity lookup or Hunter.io for emails
    # Hunter.io (free tier 25/mo): https://hunter.io/api
    # Clearbit (free tier): https://clearbit.com/docs
    sample = {
        "name": company_name,
        "email_pattern": f"firstname.lastname@{company_name.lower().replace(' ', '')}.com",
        "linkedin": f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
        "decision_makers": [
            {"name": "Jane Smith", "title": "VP of Sales", "linkedin": ""},
            {"name": "John Doe", "title": "CRO", "linkedin": ""},
        ],
    }
    return json.dumps(sample, indent=2)


@tool
def find_events(industry: str, location: str) -> str:
    """Find upcoming events that the ICP attends (conferences, meetups, trade shows).
    Returns a JSON list of events with name, date, location, URL, and attendee profile.
    Use when building event-based outreach sequences.
    """
    if OFFLINE:
        data = json.loads((FIXTURES / "events_sample.json").read_text())
        return json.dumps(data, indent=2)

    # TODO Teammate 1: scrape Eventbrite / Luma / LinkedIn Events
    # Eventbrite API (free): https://www.eventbrite.com/platform/api
    try:
        raise NotImplementedError("Implement live event search")
    except Exception:
        data = json.loads((FIXTURES / "events_sample.json").read_text())
        return json.dumps(data, indent=2)


@tool
def scrape_company_events(website: str) -> str:
    """Scrape a company's events or news page to find upcoming events they host or attend.
    Returns a JSON list of events found on their site.
    Use to find events a specific target company is promoting.
    """
    # TODO Teammate 1: implement with requests + BeautifulSoup or Playwright
    # pip install beautifulsoup4 playwright
    return json.dumps([
        {"event": "Annual SaaS Summit", "date": "2026-09-15", "url": website + "/events"},
        {"event": "Product Launch Webinar", "date": "2026-07-20", "url": website + "/webinar"},
    ], indent=2)


# ── agent entry points ────────────────────────────────────────────────────────

def run(task: str, skill=None) -> AgentResult:
    """Find companies matching the ICP described in the task."""
    return run_agent(
        task,
        tools=[search_crunchbase, search_g2, get_company_details],
        skill=skill,
        system=SYSTEM,
        tier="cheap",
    )


def run_events(task: str, skill=None) -> AgentResult:
    """Find events the ICP attends."""
    return run_agent(
        task,
        tools=[find_events, scrape_company_events, get_company_details],
        skill=skill,
        system=SYSTEM,
        tier="cheap",
    )
