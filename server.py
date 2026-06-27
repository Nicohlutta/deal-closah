"""FastAPI server — serves the static frontend and exposes POST /api/run.

Start with:
    python server.py
    python server.py --live     # uses Anthropic frontier models

Serves app/ at / and calls the real orchestrator pipeline on POST /api/run.
"""

import argparse
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
    os.environ.setdefault("AGENT_OFFLINE", "0")

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


@app.post("/api/run")
async def run_task(req: RunRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="task must not be empty")
    try:
        state = run_pipeline(req.task.strip())
        return {
            "routed_to": state.get("routed_to", "unknown"),
            "final_output": state.get("final_output", ""),
            "latencies": state.get("latencies", {}),
            "errors": state.get("errors", []),
            "model_calls": state.get("model_calls", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve the static frontend at /
app.mount("/", StaticFiles(directory=ROOT / "app", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    mode = "live (Anthropic)" if args.live else "local (granite4:micro)"
    print(f"  deal-closah server → http://{args.host}:{args.port}  [{mode}]")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
