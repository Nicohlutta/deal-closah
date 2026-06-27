"""Local pitch-deck demo server for Arman's pitch-deck skill.

Run from the repo root:
    python skills/pitch-deck/assets/webapp/server.py

This intentionally lives under skills/pitch-deck instead of app/ because
CLAUDE.md marks app/ as another teammate's frontend lane.
"""

from __future__ import annotations

import json
import mimetypes
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[4]
WEB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agents import deck_builder
from interfaces import CompanyProfile, MeetingNote, OutreachRecord, PitchDeck


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if not length:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def _write_json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _company_from_payload(payload: dict) -> str:
    return (payload.get("prospect_company") or payload.get("company_name") or "Target Account").strip()


def _save_context(payload: dict) -> str:
    company = _company_from_payload(payload)
    deck_builder._ensure_data_dirs()

    profile = CompanyProfile(
        name=company,
        industry=payload.get("industry", "target market"),
        size=payload.get("company_size", "unknown size"),
        location=payload.get("location", "unknown location"),
        website=payload.get("website", ""),
        decision_maker=payload.get("decision_maker", ""),
        decision_maker_title=payload.get("buyer_role", "decision maker"),
        description=payload.get("problem_solved", ""),
        source="pitch-deck-web-demo",
    )
    profile.save()

    notes = (payload.get("meeting_notes") or "").strip()
    if notes:
        MeetingNote(
            client=company,
            date=payload.get("meeting_date", "2026-06-27"),
            raw_notes=notes,
            extracted_insights=notes,
            next_steps=payload.get("cta", ""),
        ).save()

    outreach = (payload.get("outreach_history") or "").strip()
    if outreach:
        OutreachRecord(
            company_name=company,
            contact_name=payload.get("decision_maker", "buyer"),
            channel="email",
            date=payload.get("meeting_date", "2026-06-27"),
            message=outreach,
            status="drafted",
        ).save()

    return company


def _load_latest(company: str) -> dict:
    deck = PitchDeck.load_latest(company)
    return {
        "company_name": company,
        "created_date": deck.created_date if deck else "",
        "slides": deck.slides if deck else [],
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            path = "/index.html"
        file_path = (WEB / unquote(path.lstrip("/"))).resolve()
        if WEB not in file_path.parents and file_path != WEB:
            self.send_error(403)
            return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        try:
            if self.path == "/api/deck":
                payload = _read_json(self)
                company = _save_context(payload)
                focus = payload.get("problem_solved", "") or payload.get("meeting_notes", "")
                slides = json.loads(deck_builder.generate_deck(company, focus))
                deck_builder.save_deck(company, json.dumps(slides))
                _write_json(self, {"company_name": company, "slides": slides})
                return

            if self.path == "/api/chat":
                payload = _read_json(self)
                company = _company_from_payload(payload)
                message = payload.get("message", "")
                reply = deck_builder.apply_deck_edit(company, message)
                _write_json(self, {"reply": reply, "deck": _load_latest(company)})
                return

            if self.path == "/api/export":
                payload = _read_json(self)
                company = _company_from_payload(payload)
                result = deck_builder.export_to_pptx(company)
                match = re.search(r"PPTX exported:\s*(.+)$", result)
                if not match:
                    _write_json(self, {"error": result}, 500)
                    return
                pptx_path = Path(match.group(1).strip())
                body = pptx_path.read_bytes()
                filename = pptx_path.name
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            self.send_error(404)
        except Exception as exc:
            _write_json(self, {"error": str(exc)}, 500)


def main() -> None:
    host, port = "127.0.0.1", 5173
    print(f"Pitch Deck Maker running at http://{host}:{port}/")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
