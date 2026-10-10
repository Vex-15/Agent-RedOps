"""
RedOps API

Endpoints:
  GET  /api/scenarios         — list all loaded scenarios
  GET  /api/runs              — list all run summaries
  GET  /api/runs/{run_id}     — full run detail (trace, violations, paths, defenses)
  POST /api/runs/execute/{id} — execute a scenario by id
  POST /api/runs/execute-all  — execute all scenarios
  GET  /api/dashboard         — aggregated metrics
"""

from __future__ import annotations
import sys, os, json, dataclasses
from datetime import datetime
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

import database
import models
import schemas
from scenarios.builtin import BUILTIN_SCENARIOS
from scenarios.runner import run_scenario
from core.types import PipelineResult

# ── Neatlogs ───────────────────────────────────────────────────────────
# Load backend/.env (NEATLOGS_API_KEY) before init(); the key is never
# committed. init() runs once at process startup — never per request. The
# scenario pipeline is instrumented with manual @span()s (agent runs, tool
# calls, guard checks, findings); this simulator makes no LLM calls, so
# there are no token/cost metrics to report — spans carry real latency.
NEATLOGS_WORKFLOW = "redops-scenario-eval"
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

try:
    import neatlogs

    neatlogs.init(
        api_key=os.environ.get("NEATLOGS_API_KEY"),
        endpoint="https://ingest.neatlogs.com",
        workflow_name=NEATLOGS_WORKFLOW,
        capture_logs=True,
    )
    _neatlogs_ok = True
except Exception as e:
    print(f"[redops] neatlogs init skipped: {e}")
    _neatlogs_ok = False


# ── App lifecycle ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables, apply additive migrations, seed scenarios on startup
    models.Base.metadata.create_all(bind=database.engine)
    _migrate_schema()
    _seed_scenarios()
    yield
    # Long-running server: flush + shut down once at process exit (never
    # per request) so batched spans are exported instead of dropped.
    if _neatlogs_ok:
        try:
            import neatlogs
            neatlogs.flush()
            neatlogs.shutdown()
        except Exception as e:
            print(f"[redops] neatlogs shutdown skipped: {e}")


app = FastAPI(title="RedOps API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schema migrations ──────────────────────────────────────────────────

def _migrate_schema():
    """Additive migrations for databases created before new columns existed."""
    with database.engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(runs)"))}
        if "error" not in cols:
            conn.execute(text("ALTER TABLE runs ADD COLUMN error TEXT DEFAULT ''"))


# ── Seed built-in scenarios ───────────────────────────────────────────

def _seed_scenarios():
    db = database.SessionLocal()
    try:
        existing_names = {
            r.name for r in db.query(models.ScenarioRecord.name)
        }
        added = 0
        for s in BUILTIN_SCENARIOS:
            if s["name"] in existing_names:
                continue
            rec = models.ScenarioRecord(
                name=s["name"],
                description=s["description"],
                request_data=s["request"],
                tool_overrides=s.get("tool_overrides", {}),
                pre_inject=s.get("pre_inject"),
                expected_violations=[v.value for v in s.get("expected_violations", [])],
                expected_outcome=s.get("expected_outcome", ""),
            )
            db.add(rec)
            added += 1
        db.commit()
        if added:
            print(f"[redops] seeded {added} new builtin scenario(s)")
    finally:
        db.close()


# ── Helpers ────────────────────────────────────────────────────────────

def _serialize_dataclass(obj):
    """Recursively convert dataclass instances to dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        d = {}
        for f in dataclasses.fields(obj):
            val = getattr(obj, f.name)
            d[f.name] = _serialize_dataclass(val)
        # Serialize plain properties too (e.g. AttackPath.length).
        for name in ('length',):
            prop = getattr(type(obj), name, None)
            if isinstance(prop, property):
                try:
                    d[name] = getattr(obj, name)
                except Exception:
                    pass
        return d
    elif isinstance(obj, list):
        return [_serialize_dataclass(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _serialize_dataclass(v) for k, v in obj.items()}
    elif hasattr(obj, 'value'):  # Enum
        return obj.value
    return obj


def _save_run(db: Session, result: PipelineResult) -> models.RunRecord:
    """Persist a PipelineResult to the database."""
    serialized = _serialize_dataclass(result)

    rec = models.RunRecord(
        run_id=result.run_id,
        scenario_name=result.scenario_name,
        status=result.status.value if hasattr(result.status, 'value') else result.status,
        trace_json=serialized.get("trace", []),
        violations_json=serialized.get("violations", []),
        attack_paths_json=serialized.get("attack_paths", []),
        defenses_json=serialized.get("defenses", []),
        latency_ms=result.latency_ms,
        error=result.error,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/scenarios", response_model=list[schemas.ScenarioOut])
def list_scenarios(db: Session = Depends(get_db)):
    return db.query(models.ScenarioRecord).all()


@app.get("/api/runs", response_model=list[schemas.RunSummary])
def list_runs(db: Session = Depends(get_db)):
    records = db.query(models.RunRecord).order_by(
        models.RunRecord.id.desc()
    ).limit(100).all()

    summaries = []
    for r in records:
        violations = r.violations_json or []
        attack_paths = r.attack_paths_json or []
        defenses = r.defenses_json or []

        # Determine aggregate defense verdict
        verdicts = [d.get("verdict", "") for d in defenses]
        if verdicts:
            if all(v == "blocked" for v in verdicts):
                defense_verdict = "all_blocked"
            elif any(v == "bypassed" for v in verdicts):
                defense_verdict = "some_bypassed"
            else:
                defense_verdict = verdicts[0]
        else:
            defense_verdict = None

        summaries.append(schemas.RunSummary(
            id=r.id,
            run_id=r.run_id,
            scenario_name=r.scenario_name,
            status=r.status,
            violation_count=len(violations),
            attack_path_count=len(attack_paths),
            defense_verdict=defense_verdict,
            latency_ms=r.latency_ms,
            error=r.error or "",
            started_at=r.started_at or "",
            finished_at=r.finished_at or "",
        ))

    return summaries


@app.get("/api/runs/{run_id}", response_model=schemas.RunDetail)
def get_run_detail(run_id: str, db: Session = Depends(get_db)):
    rec = db.query(models.RunRecord).filter(
        models.RunRecord.run_id == run_id
    ).first()
    if not rec:
        raise HTTPException(404, "Run not found")

    return schemas.RunDetail(
        id=rec.id,
        run_id=rec.run_id,
        scenario_name=rec.scenario_name,
        status=rec.status,
        trace=[
            schemas.TraceEventOut(
                **{k: v for k, v in e.items() if k in set(schemas.TraceEventOut.model_fields) },
            )
            for e in (rec.trace_json or [])
        ],
        violations=[schemas.ViolationOut(**v) for v in (rec.violations_json or [])],
        attack_paths=[
            schemas.AttackPathOut(
                **{k: v for k, v in ap.items() if k != "events" and k != "violation"},
                events=[
                    schemas.TraceEventOut(
                        **{k: v for k, v in e.items() if k in set(schemas.TraceEventOut.model_fields)},
                    )
                    for e in ap.get("events", [])
                ],
                violation=schemas.ViolationOut(**ap["violation"]) if ap.get("violation") else None,
            )
            for ap in (rec.attack_paths_json or [])
        ],
        defenses=[
            schemas.DefenseResultOut(
                defense=schemas.DefenseOut(**d["defense"]),
                verdict=d.get("verdict", ""),
                violation_before=(
                    schemas.ViolationOut(**d["violation_before"])
                    if d.get("violation_before") else None
                ),
                violation_after=(
                    schemas.ViolationOut(**d["violation_after"])
                    if d.get("violation_after") else None
                ),
                explanation=d.get("explanation", ""),
            )
            for d in (rec.defenses_json or [])
        ],
        latency_ms=rec.latency_ms,
        error=rec.error or "",
        started_at=rec.started_at or "",
        finished_at=rec.finished_at or "",
    )


@app.post("/api/runs/execute/{scenario_id}")
def execute_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Execute a single scenario and return the full result."""
    scenario_rec = db.query(models.ScenarioRecord).filter(
        models.ScenarioRecord.id == scenario_id
    ).first()
    if not scenario_rec:
        raise HTTPException(404, "Scenario not found")

    # Reconstruct scenario dict from DB record
    scenario_dict = {
        "name": scenario_rec.name,
        "description": scenario_rec.description,
        "request": scenario_rec.request_data,
        "tool_overrides": scenario_rec.tool_overrides or {},
        "pre_inject": scenario_rec.pre_inject,
        "expected_violations": scenario_rec.expected_violations or [],
        "expected_outcome": scenario_rec.expected_outcome,
    }

    result = run_scenario(scenario_dict)
    _save_run(db, result)

    serialized = _serialize_dataclass(result)
    return serialized


@app.post("/api/runs/execute-all")
def execute_all_scenarios(db: Session = Depends(get_db)):
    """Execute all scenarios and return summary results."""
    scenarios = db.query(models.ScenarioRecord).all()
    results = []

    for scenario_rec in scenarios:
        scenario_dict = {
            "name": scenario_rec.name,
            "description": scenario_rec.description,
            "request": scenario_rec.request_data,
            "tool_overrides": scenario_rec.tool_overrides or {},
            "pre_inject": scenario_rec.pre_inject,
            "expected_violations": scenario_rec.expected_violations or [],
            "expected_outcome": scenario_rec.expected_outcome,
        }

        result = run_scenario(scenario_dict)
        _save_run(db, result)

        results.append({
            "run_id": result.run_id,
            "scenario_name": result.scenario_name,
            "status": result.status.value,
            "violation_count": len(result.violations),
            "attack_path_count": len(result.attack_paths),
            "latency_ms": result.latency_ms,
            "defenses": [
                {"verdict": d.verdict.value, "name": d.defense.name}
                for d in result.defenses
            ],
        })

    return {"runs": results, "total": len(results)}


@app.get("/api/dashboard", response_model=schemas.DashboardMetrics)
def dashboard_metrics(db: Session = Depends(get_db)):
    """Aggregated metrics for the dashboard overview."""
    scenarios = db.query(models.ScenarioRecord).count()
    runs = db.query(models.RunRecord).all()

    total_violations = 0
    blocked = 0
    bypassed = 0
    latencies = []
    by_outcome: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    for r in runs:
        violations = r.violations_json or []
        total_violations += len(violations)
        latencies.append(r.latency_ms)

        for v in violations:
            cat = v.get("category", "unknown")
            sev = v.get("severity", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1

        defenses = r.defenses_json or []
        for d in defenses:
            if d.get("verdict") == "blocked":
                blocked += 1
            elif d.get("verdict") == "bypassed":
                bypassed += 1

        # Determine outcome
        if (r.status or "").lower() == "failed":
            outcome = "failed"
        elif len(violations) == 0:
            outcome = "clean"
        elif defenses and all(d.get("verdict") == "blocked" for d in defenses):
            outcome = "defended"
        else:
            outcome = "vulnerable"
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1

    return schemas.DashboardMetrics(
        total_scenarios=scenarios,
        total_runs=len(runs),
        total_violations=total_violations,
        blocked_by_defense=blocked,
        bypassed_defense=bypassed,
        avg_latency_ms=sum(latencies) / max(len(latencies), 1),
        scenarios_by_outcome=by_outcome,
        violations_by_category=by_category,
        violations_by_severity=by_severity,
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "neatlogs": _neatlogs_ok,
        "neatlogs_workflow": NEATLOGS_WORKFLOW if _neatlogs_ok else None,
        "neatlogs_api_key_configured": bool(os.environ.get("NEATLOGS_API_KEY")),
        "version": "0.2.0",
    }
