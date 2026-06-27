# deal-closah frontend

Frontend for the sales command center. The root `server.py` serves this UI and
exposes `POST /api/run` for API mode.

## Run locally

```bash
uv sync
uv run python server.py --port 5173
```

Open `http://localhost:5173`.

## API contract

The UI API mode posts to:

```http
POST /api/run
Content-Type: application/json

{"task": "Find B2B SaaS companies in Boston, 50-200 employees"}
```

Expected response shape:

```json
{
  "task": "...",
  "classification": {"intent": "icp", "confidence": "high"},
  "routed_to": "icp",
  "final_output": "...",
  "latencies": {"orchestrator_classify": 0.4, "icp": 1.8},
  "errors": [],
  "model_calls": 2
}
```

The server sets `AGENT_OFFLINE=1` by default so demos use fixtures and do not
require live API keys. If the local model call takes more than 10 seconds, it
returns a structured demo-safe fallback so the UI stays responsive.
