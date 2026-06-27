"""ICP Scout — finds companies, decision makers, and events via SerpAPI. OWNER: Nicholas.

Tools:
  search_companies(query)           — Google search via SerpAPI for matching companies
  get_company_details(company_name) — SerpAPI enrichment + LinkedIn lookup
  verify_email(email)               — Hunter.io email verification (25/mo free)
  find_events(industry, location)   — SerpAPI event search for ICP conferences/meetups

Offline fallback: set AGENT_OFFLINE=1 or omit SERPAPI_API_KEY → uses fixtures/.
"""

from __future__ import annotations

import json
import os
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(HERE))

from agentkit import AgentResult, run_agent, tool

FIXTURES = HERE / "fixtures"

SYSTEM = """You are an ICP Scout — an expert at finding ideal customer profiles.
You search for companies matching specific criteria (industry, location, size,
decision-maker type) via Google/SerpAPI. Return structured company profiles with
contact details. Be precise and honest about data quality — never invent emails."""


# ── helpers ────────────────────────────────────────────────────────────────────

def _use_fixtures() -> bool:
    """True when offline mode is active OR no SerpAPI key is configured."""
    return os.getenv("AGENT_OFFLINE") == "1" or not os.getenv("SERPAPI_API_KEY", "")


_SERP_CALLS = 0
_SERP_LIMIT = 20


def _serpapi(query: str, num: int = 5) -> list[dict]:
    global _SERP_CALLS
    if _SERP_CALLS >= _SERP_LIMIT:
        return [{"error": "SerpAPI call limit reached"}]

    api_key = os.getenv("SERPAPI_API_KEY", "")
    params = urllib.parse.urlencode({"q": query, "api_key": api_key, "num": num, "engine": "google"})
    url = f"https://serpapi.com/search.json?{params}"

    time.sleep(random.uniform(2, 5))

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
        _SERP_CALLS += 1
        print(f"  [SerpAPI {_SERP_CALLS}/{_SERP_LIMIT}] {query[:60]}", flush=True)
        return [
            {
                "title": r.get("title", ""),
                "link": r.get("link", ""),
                "snippet": r.get("snippet", ""),
            }
            for r in data.get("organic_results", [])[:num]
        ]
    except Exception as e:
        return [{"error": str(e)}]


def _fixture_companies(query: str = "") -> list[dict]:
    data = json.loads((FIXTURES / "crunchbase_sample.json").read_text())
    if query:
        q = query.lower()
        filtered = [
            c for c in data
            if any(w in c.get("industry", "").lower() or w in c.get("location", "").lower()
                   for w in q.split() if len(w) > 3)
        ]
        return filtered[:5] if filtered else data[:5]
    return data[:5]


# ── tools ─────────────────────────────────────────────────────────────────────

@tool
def search_companies(query: str) -> str:
    """Search Google via SerpAPI for companies matching an ICP description.

    Build the query with industry, location, size signal, and decision-maker target.
    Example: "B2B SaaS companies Boston 50-200 employees VP Sales fintech"
    Returns JSON list of company profiles. Each profile already contains
    decision_maker, decision_maker_title, linkedin_url, and website when in
    offline/fixture mode — skip get_company_details if those fields are present.
    Use this as the first and primary step to surface candidate companies.
    """
    if _use_fixtures():
        return json.dumps(_fixture_companies(query), indent=2)

    results = _serpapi(query, num=8)
    return json.dumps(results, indent=2)


@tool
def get_company_details(company_name: str) -> str:
    """Look up specific company details via SerpAPI: LinkedIn, email pattern, key contacts.

    Searches for the company's LinkedIn page and leadership team.
    Returns JSON with name, website, linkedin URL, email_pattern, and decision_makers.
    Always label inferred fields — never present guessed data as verified.
    Only call this when a search_companies result is missing decision_maker or linkedin_url.
    If search_companies already returned complete profiles, skip this and go to output.
    """
    if _use_fixtures():
        data = json.loads((FIXTURES / "crunchbase_sample.json").read_text())
        name_lower = company_name.lower()
        match = next((c for c in data if c.get("name", "").lower() == name_lower), data[0])
        result = {
            "name": company_name,
            "website": match.get("website", f"https://{name_lower.replace(' ', '')}.com"),
            "linkedin": match.get("linkedin_url", f"https://linkedin.com/company/{name_lower.replace(' ', '-')}"),
            "email_pattern": f"firstname.lastname@{name_lower.replace(' ', '')}.com",
            "decision_makers": [
                {
                    "name": match.get("decision_maker", "Alex Rivera"),
                    "title": match.get("decision_maker_title", "VP of Sales"),
                    "linkedin": "",
                },
            ],
            "source": "fixture",
        }
        return json.dumps(result, indent=2)

    results = _serpapi(f'"{company_name}" site:linkedin.com/company OR leadership team employees', num=5)
    return json.dumps({"company": company_name, "search_results": results}, indent=2)


@tool
def verify_email(email: str) -> str:
    """Verify an email address via Hunter.io (25 verifications/month on free tier).

    Returns deliverability status (valid/risky/undeliverable) and confidence score.
    Only call when you have a specific email address to verify before outreach.
    Requires HUNTER_API_KEY in .env — returns fixture score when key is absent.
    """
    if _use_fixtures() or not os.getenv("HUNTER_API_KEY", ""):
        return json.dumps({"email": email, "status": "valid", "score": 82, "source": "fixture"})

    api_key = os.getenv("HUNTER_API_KEY", "")
    url = (
        f"https://api.hunter.io/v2/email-verifier"
        f"?email={urllib.parse.quote(email)}&api_key={api_key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        r = data.get("data", {})
        return json.dumps(
            {
                "email": email,
                "status": r.get("result"),
                "score": r.get("score"),
                "mx_records": r.get("mx_records"),
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def find_events(industry: str, location: str) -> str:
    """Find upcoming industry events (conferences, summits, meetups) via SerpAPI.

    Searches Google for events that the ICP attends in the given industry and location.
    Returns JSON list of events with title, URL, snippet, and the search query that found it.
    Use when building event-based outreach — cross-reference with data/prospects/ contacts.
    Searches 3 query variations; falls back to fixtures when offline or no API key.
    """
    if _use_fixtures():
        data = json.loads((FIXTURES / "events_sample.json").read_text())
        return json.dumps(data, indent=2)

    import datetime
    year = datetime.date.today().year

    queries = [
        f"{industry} conference {location} {year}",
        f"{industry} summit {year} {location}",
        f"{industry} meetup {location} {year}",
    ]

    all_events: list[dict] = []
    seen: set[str] = set()

    for q in queries:
        for r in _serpapi(q, num=5):
            link = r.get("link", "")
            if link and link not in seen and "error" not in r:
                seen.add(link)
                all_events.append({
                    "title": r.get("title", ""),
                    "url": link,
                    "snippet": r.get("snippet", ""),
                    "query": q,
                })

    return json.dumps(all_events[:10], indent=2)


# ── agent entry points ────────────────────────────────────────────────────────

def run(task: str, skill=None) -> AgentResult:
    """Find companies matching the ICP described in the task."""
    return run_agent(
        task,
        tools=[search_companies, get_company_details, verify_email],
        skill=skill,
        system=SYSTEM,
        tier="cheap",
    )


def run_events(task: str, skill=None) -> AgentResult:
    """Find events the ICP attends."""
    return run_agent(
        task,
        tools=[find_events, get_company_details],
        skill=skill,
        system=SYSTEM,
        tier="cheap",
    )
