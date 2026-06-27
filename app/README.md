# deal-closah frontend

Static frontend for the sales command center. It is intentionally dependency-free
so the frontend can ship while backend and agent endpoints are still in progress.

## Run locally

```bash
cd app
python -m http.server 5173
```

Open `http://localhost:5173`.

## API contract target

The UI already has an API mode that posts to:

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

Until that endpoint exists, Offline mode uses mock data based on the repo's
`CompanyProfile`, `OutreachRecord`, `MeetingNote`, and `PitchDeck` contracts.
