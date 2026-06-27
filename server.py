"""FastAPI server — serves the static frontend and exposes POST /api/run.

Start with:
    python server.py
    python server.py --live     # uses Anthropic frontier models

Serves app/ at / and calls the real orchestrator pipeline on POST /api/run.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--live", action="store_true", help="Use Anthropic frontier models")
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=8080)
args, _ = parser.parse_known_args()

if args.live:
    os.environ.setdefault("MODEL_PROVIDER", "anthropic")
else:
    os.environ.setdefault("MODEL_PROVIDER", "local")
    os.environ.setdefault("AGENT_OFFLINE", "1")

API_TIMEOUT_S = float(os.getenv("API_TIMEOUT_S", "10"))

from agents.orchestrator import run_pipeline  # noqa: E402 — after env is set

app = FastAPI(title="deal-closah")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    task: str


@app.get("/api/health")
async def health():
    return {"ok": True, "mode": "connected"}


@app.post("/api/run")
async def run_task(req: RunRequest):
    task = req.task.strip()
    if not task:
        raise HTTPException(status_code=400, detail="task must not be empty")
    try:
        state = await asyncio.wait_for(
            asyncio.to_thread(run_pipeline, task),
            timeout=API_TIMEOUT_S,
        )
        return state
    except TimeoutError:
        return demo_state(task, timed_out=True)
    except Exception as e:
        return demo_state(task, error=str(e))


def classify_demo_intent(task: str) -> str:
    text = task.lower()
    if any(word in text for word in ("deck", "slide", "pitch")):
        return "deck"
    if any(word in text for word in ("email", "outreach", "follow")):
        return "outreach"
    if any(word in text for word in ("meeting", "brief", "crm", "notes")):
        return "meeting"
    if any(word in text for word in ("event", "conference", "summit")):
        return "event"
    return "icp"


def demo_state(task: str, timed_out: bool = False, error: str | None = None):
    intent = classify_demo_intent(task)
    reason = "Agent call timed out; returned demo-safe fixture output." if timed_out else error
    final_output = {
        "icp": "Found 3 demo-fit accounts: Acme Corp, Meridian Ledger, and Northstar Revenue.",
        "event": "Found demo GTM events: Boston SaaS GTM Summit and Revenue Leaders Forum.",
        "outreach": "Drafted a concise human-review outreach note with one clear CTA.",
        "meeting": "Generated a client brief with risks, next steps, and action items.",
        "deck": "Created a 7-slide pitch narrative for review in the deck preview.",
    }.get(intent, "Demo response generated.")
    if reason:
        final_output = f"{final_output}\n\nNote: {reason}"

    return {
        "task": task,
        "classification": {
            "intent": intent,
            "company_name": None,
            "contact_name": None,
            "confidence": "medium",
            "summary": "Demo-safe API response",
        },
        "routed_to": intent,
        "icp_result": {"text": final_output} if intent in ("icp", "event") else None,
        "outreach_result": {"text": final_output} if intent == "outreach" else None,
        "meeting_result": {"text": final_output} if intent == "meeting" else None,
        "deck_result": {"text": final_output} if intent == "deck" else None,
        "final_output": final_output,
        "latencies": {"api": API_TIMEOUT_S if timed_out else 0.1},
        "errors": [reason] if reason else [],
        "model_calls": 0,
        "demo_fallback": bool(reason),
    }


# Serve the static frontend at /
app.mount("/", StaticFiles(directory=ROOT / "app", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    mode = "live (Anthropic)" if args.live else "local (granite4:micro)"
    print(f"  deal-closah server -> http://{args.host}:{args.port}  [{mode}]")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
