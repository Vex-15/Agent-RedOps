# RedOps

RedOps is a defensive AI-agent security analysis platform. It runs deterministic attack
scenarios against a simulated multi-agent procurement pipeline
(requester → vendor lookup → approver → purchaser → auditor), detects policy violations
in the execution trace, chains them into attack paths, and — the core promise —
**re-runs every attack with the recommended guard applied and verifies the attack is
blocked**.

**Everything in the demo is real execution.** The live backend executes every scenario
through the full pipeline, crashes and all; the console only falls back to captured demo
data (with a visible banner and a retry button) when the API is unreachable.

## What's inside

- **11 attack scenarios** — deceptive tool output, forged approval ids, budget
  overstatement, post-approval tampering, credit-limit evasion, instruction override,
  unregistered vendors, vendor identity confusion, conflicting budgets, inflated vendor
  records, and a **failure-and-recovery case** (the insecure pipeline crashes on a
  malformed tool payload; the defended pipeline rejects it at the trust boundary and
  completes).
- **7 composable guards** — ledger verification, budget/treasury reconciliation,
  vendor-catalog identity checks, approval-amount binding, instruction precedence,
  credit-limit re-validation, and payload shape validation. Every guard emits a trace
  span and a `defense_triggered` marker.
- **Trace-driven analyzer** — violations with severity, category, evidence event ids,
  and root-cause text; attack paths built from the evidence chain.
- **Remediation library** — every finding maps to a code-level guard with a file
  location and a concrete fix snippet, *verified by defended re-run*.
- **Agent console** — metrics, scenario runner, run history, finding inspector with
  nested execution-trace explorer (errors, guards, evidence highlighting), failure &
  recovery banner, and one-click JSON/Markdown report export.

## Architecture

```
Agent-RedOps/
├── backend/                  FastAPI + SQLite
│   ├── main.py               API app, Neatlogs init, run/metrics/scenario routes
│   ├── agents/
│   │   ├── pipeline.py       5-stage insecure/defended procurement pipeline
│   │   ├── tools.py          simulated tools (vendor_lookup, check_budget, ledger)
│   │   └── guards.py         7 defense guards (defended re-run)
│   ├── analyzer/
│   │   ├── trace_analyzer.py violation detection + attack-path builder
│   │   └── remediation.py    findings → recommended guards/fixes
│   ├── scenarios/
│   │   ├── builtin.py        the 11 scenarios
│   │   └── runner.py         executes a scenario end to end (WORKFLOW span)
│   ├── models.py / schemas.py / core/types.py
│   ├── scripts_gen_demo_data.py   regenerates captured demo data
│   └── tests/test_pipeline.py     48 pytest tests
└── frontend/                 React + Vite + Tailwind (TypeScript)
    ├── src/Landing.tsx       marketing page
    ├── src/Dashboard.tsx     agent console (inspector, trace explorer, exports)
    └── src/lib/api.ts        typed API client with live/demo mode detection
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Edit `backend/.env` (gitignored) and set the real `NEATLOGS_API_KEY`. Start the API:

```bash
uvicorn main:app --reload --port 8000
```

Health check: `curl http://127.0.0.1:8000/api/health` →
`{"status":"ok","neatlogs":true,...}`.

The shipped `run-dev.ps1` starts both halves in background jobs — `uvicorn main:app --reload --port 8000`
and `npm run dev` — with the frontend on `127.0.0.1:5173` and the backend on `127.0.0.1:8000`.
Press Ctrl+C to stop both. Do **not** commit `.env`.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173
```

The Vite proxy forwards `/api` to the backend on `127.0.0.1:8000`.
When the backend is down the header chip flips to **demo mode** and the console serves
captured data from a real earlier run — never silent mocks.

## API surface

| Method & path | Purpose |
|---|---|
| `GET /api/health` | status + Neatlogs configuration |
| `GET /api/scenarios` | the 11 built-in scenarios |
| `POST /api/runs/execute/{id}` | execute one scenario (blocking) |
| `POST /api/runs/execute-all` | execute all scenarios (blocking) |
| `POST /api/runs/stream/{id}` | stream a single scenario as NDJSON |
| `POST /api/runs/stream-all` | stream all scenarios in sequence |
| `GET /api/runs` | run history (summary rows) |
| `GET /api/runs/{run_id}` | full detail: trace, violations, attack paths, defenses, error |
| `GET /api/dashboard` | dashboard metrics |

## Testing

```bash
# Backend — 48 tests: per-scenario detection, every attack neutralized when defended,
# positive baseline stays clean, failure/recovery matrix for the corrupted-payload case
cd backend && python -m pytest tests/ -q

# Frontend — typecheck is part of build; lint is oxlint
cd frontend && npm run build && npm run lint
```

Regenerate the captured demo data (used when the API is unreachable) after backend
behavior changes:

```bash
cd backend && python scripts_gen_demo_data.py frontend/public/demo_data.json
```

`demo_data.json` is not committed — keep it out of version control.

## Neatlogs integration

Every scenario execution is traced: a `WORKFLOW` span per run plus `AGENT`, `TOOL`,
`GUARD`, and `GUARDRAIL` spans inside the pipeline, carrying `run_id`/`scenario`
attributes so findings in the console correlate with trace entries in Neatlogs.
Each violation emits a LOG span inline in the trace timeline; guard verdicts and
errors do too. Because this simulator makes no LLM calls, spans carry real
latency without token/cost metrics; adding an LLM-backed step later will surface
those automatically.

```bash
# backend/.env (gitignored)
NEATLOGS_API_KEY=...        # optional — tracing no-ops cleanly without it
NEATLOGS_WORKFLOW=redops-scenario-eval
```

Verify your setup with the SDK doctor:

```bash
python -m neatlogs.doctor
```

The backend reports its Neatlogs state at `/api/health`. Tests run with
`env -u NEATLOGS_API_KEY` to prove the no-key path; when the key is absent,
the SDK no-ops cleanly and the pipeline still executes fully.

## Entire integration

[Entire](https://docs.entire.io/) checkpoints agent-assisted commits and builds a
local repository graph, so every finding in a RedOps report can be traced back to the
agent session and code change that produced it.

```powershell
# Windows install (https://docs.entire.io/installation)
irm https://entire.io/install.ps1 | iex

# Link this repo to your agent session — commits become checkpoints
entire enable --agent codebuff

# Repository graph artifact (NDJSON) for evidence packages
entire plugin install graph
entire graph snapshot --repo . --format ndjson > repository-graph.ndjson

# Inspect checkpoints
entire checkpoint list
```

The graph snapshot and checkpoint refs live alongside the run artifacts.
The `.entire/` config in this repo configures the checkpoint runner; commit the
config and the generated `repository-graph.ndjson` evidence artifact, not the
`.entire/` runtime cache.

## License & scope

Defensive research tooling. All purchases, vendors, and approvals in the simulation are
fabricated — no real transactions occur.
### Test a real agent

Open `#/live` and choose **HTTP webhook** to send a real JSON request to any
HTTP(S) endpoint that accepts `POST`, `PUT`, or `PATCH`. RedOps streams the
request and response into the Trace Explorer and stores the run only after an
HTTP response is received. A timeout, connection error, or non-2xx response is
shown as a failed real request; it is never presented as a successful test.

Choose **OpenAI-compatible** to call an endpoint exposing `/chat/completions`.
Enter its base URL, API key, model, and prompt. API keys are sent to the
backend only for the request and are not included in trace headers or
persisted run data. Use HTTPS and a dedicated test agent in production.

The deterministic scenario controls remain available as **Deterministic demo**
mode and do not make external requests.
