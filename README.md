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
uvicorn main:app --reload --port 8000
```

Health check: `curl http://127.0.0.1:8000/api/health` →
`{"status":"ok","neatlogs":true,...}`.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173
```

The console talks to `http://127.0.0.1:8000/api` by default. When the backend is down
the header chip flips to **demo mode** and the console serves captured data from a real
earlier run — never silent mocks.

## API surface

| Method & path | Purpose |
|---|---|
| `GET /api/health` | status + Neatlogs configuration |
| `GET /api/scenarios` | the 11 built-in scenarios |
| `POST /api/runs` / `POST /api/runs/{id}/run` | execute one/all scenarios |
| `GET /api/runs` | run history (summary rows) |
| `GET /api/runs/{run_id}` | full detail: trace, violations, attack paths, defenses, error |
| `GET /api/metrics` | dashboard metrics |

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
cd backend && python scripts_gen_demo_data.py
```

## Neatlogs integration

Every scenario execution is traced: a `WORKFLOW` span per run plus `AGENT`, `TOOL`, and
`GUARD` spans inside the pipeline, carrying `run_id`/`scenario` attributes so findings in
the console correlate with trace entries in Neatlogs. Errors, guard verdicts, and
latency are captured as span events/attributes; token/cost metrics appear automatically
for any LLM-backed steps added later.

```bash
# backend/.env (gitignored)
NEATLOGS_API_KEY=...        # optional — tracing no-ops cleanly without it
NEATLOGS_WORKFLOW=redops-scenario-eval
```

Verify your setup with the SDK doctor:

```bash
python -m neatlogs.doctor
```

The backend reports its Neatlogs state at `/api/health`, and tests run with
`env -u NEATLOGS_API_KEY` to prove the no-key path.

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

The graph snapshot and checkpoint refs live alongside the run artifacts
(`.entire/` config in this repo).

## License & scope

Defensive research tooling. All purchases, vendors, and approvals in the simulation are
fabricated — no real transactions occur.
