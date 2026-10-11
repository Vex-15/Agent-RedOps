"""Generate bundled demo data for the frontend from the real pipeline.

Usage: python scripts_gen_demo_data.py <output.json>
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

import main  # noqa: F401  (app + lifespan seeding)

OUT = sys.argv[1] if len(sys.argv) > 1 else "demo_data.json"

# Dev-only harness: writes demo_data.json for the frontend fallback story.
# Do NOT commit demo_data.json — it is regenerated locally and is not part
# of the shipped repo. Put it under .gitignore, not in version control.


def dashboard_metrics(runs, details, scenario_count):
    total_violations = 0
    blocked = bypassed = 0
    latencies = []
    by_outcome: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    for r in runs:
        d = details[r["run_id"]]
        violations = d["violations"]
        total_violations += len(violations)
        latencies.append(r["latency_ms"])
        for v in violations:
            by_category[v["category"]] = by_category.get(v["category"], 0) + 1
            by_severity[v["severity"]] = by_severity.get(v["severity"], 0) + 1
        for dfc in d["defenses"]:
            if dfc["verdict"] == "blocked":
                blocked += 1
            elif dfc["verdict"] == "bypassed":
                bypassed += 1
        if (r.get("status") or "").lower() == "failed":
            outcome = "failed"
        elif len(violations) == 0:
            outcome = "clean"
        elif d["defenses"] and all(x["verdict"] == "blocked" for x in d["defenses"]):
            outcome = "defended"
        else:
            outcome = "vulnerable"
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1

    return {
        "total_scenarios": scenario_count,
        "total_runs": len(runs),
        "total_violations": total_violations,
        "blocked_by_defense": blocked,
        "bypassed_defense": bypassed,
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 1),
        "scenarios_by_outcome": by_outcome,
        "violations_by_category": by_category,
        "violations_by_severity": by_severity,
    }


with TestClient(main.app) as client:
    scenarios_raw = client.get("/api/scenarios").json()
    # Re-run every scenario once so demo data reflects current behavior
    client.post("/api/runs/execute-all")
    summaries = client.get("/api/runs").json()

    # Latest run per scenario name
    chosen = {}
    for s in summaries:
        chosen.setdefault(s["scenario_name"], s)
    runs = list(chosen.values())

    details = {}
    for r in runs:
        d = client.get(f"/api/runs/{r['run_id']}").json()
        # Drop the bulky before/after traces kept for defense verification
        for dfc in d["defenses"]:
            dfc.pop("trace_before", None)
            dfc.pop("trace_after", None)
        details[r["run_id"]] = d

    scenarios = [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "tool_overrides": s.get("tool_overrides") or {},
            "expected_violations": s.get("expected_violations") or [],
            "expected_outcome": s.get("expected_outcome") or "",
        }
        for s in scenarios_raw
    ]

    metrics = dashboard_metrics(runs, details, len(scenarios))

    payload = {
        "scenarios": scenarios,
        "runs": runs,
        "details": details,
        "metrics": metrics,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

print(f"wrote {OUT}: {os.path.getsize(OUT)} bytes, {len(runs)} runs, {len(scenarios)} scenarios")
