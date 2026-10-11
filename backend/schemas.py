from pydantic import BaseModel
from typing import Any, Optional


# ── Scenario schemas ───────────────────────────────────────────────────

class ScenarioOut(BaseModel):
    id: int
    name: str
    description: str
    request_data: dict[str, Any]
    tool_overrides: dict[str, Any]
    pre_inject: dict[str, Any] | None
    expected_violations: list[str]
    expected_outcome: str

    class Config:
        from_attributes = True


# ── Run schemas ────────────────────────────────────────────────────────

class RunSummary(BaseModel):
    id: int
    run_id: str
    scenario_name: str
    status: str
    violation_count: int
    attack_path_count: int
    defense_verdict: str | None
    latency_ms: int
    error: str = ""
    started_at: str
    finished_at: str


class TraceEventOut(BaseModel):
    id: str
    timestamp: str
    agent: str
    kind: str
    action: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    metadata: dict[str, Any]
    trusted: bool
    unverified_source: bool = False


class ViolationOut(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    description: str
    evidence_event_ids: list[str]
    root_cause: str


class AttackPathOut(BaseModel):
    id: str
    events: list[TraceEventOut]
    violation: ViolationOut | None
    entry_point: str
    impact: str
    length: int


class DefenseOut(BaseModel):
    id: str
    name: str
    description: str
    code_location: str
    fix_description: str
    category: str


class DefenseResultOut(BaseModel):
    defense: DefenseOut
    verdict: str
    violation_before: ViolationOut | None
    violation_after: ViolationOut | None
    explanation: str


class RunDetail(BaseModel):
    id: int
    run_id: str
    scenario_name: str
    status: str
    trace: list[TraceEventOut]
    violations: list[ViolationOut]
    attack_paths: list[AttackPathOut]
    defenses: list[DefenseResultOut]
    latency_ms: int
    error: str = ""
    started_at: str
    finished_at: str


# ── Dashboard metrics ──────────────────────────────────────────────────

class DashboardMetrics(BaseModel):
    total_scenarios: int
    total_runs: int
    total_violations: int
    blocked_by_defense: int
    bypassed_defense: int
    avg_latency_ms: float
    scenarios_by_outcome: dict[str, int]
    violations_by_category: dict[str, int]
    violations_by_severity: dict[str, int]


class RealAgentRequest(BaseModel):
    name: str = "Real agent test"
    url: str
    method: str = "POST"
    headers: dict[str, str] = {}
    payload: Any = {}
    timeout_seconds: float = 30


class OpenAIRequest(BaseModel):
    name: str = "OpenAI-compatible agent test"
    base_url: str
    api_key: str
    model: str
    prompt: str
    system_prompt: str = ""
    temperature: float = 0
    timeout_seconds: float = 60
