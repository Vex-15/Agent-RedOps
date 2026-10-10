"""
Scenario Runner

Executes a scenario against the procurement pipeline, producing
a PipelineResult with full trace, violations, attack paths, and
defense verification.
"""

from __future__ import annotations
import copy
import time
from datetime import datetime

from core.types import (
    PipelineResult, RunStatus, TraceEvent, PolicyViolation,
    AttackPath, Defense, DefenseResult, DefenseVerdict,
    ViolationCategory, Severity, EventKind,
)
from agents.pipeline import run_procurement_pipeline
from agents.tools import APPROVAL_LEDGER
from analyzer.trace_analyzer import analyze_trace, build_attack_paths
from analyzer.remediation import recommend_defenses


def run_scenario(scenario: dict) -> PipelineResult:
    """
    Execute a single scenario through the full RedOps pipeline:

    1. Run the INSECURE procurement pipeline
    2. Analyze the trace for policy violations
    3. Build attack paths
    4. Recommend defenses
    5. Re-run with defenses and verify the attack is blocked

    Returns a PipelineResult with everything populated.
    """
    result = PipelineResult(
        scenario_name=scenario["name"],
        status=RunStatus.RUNNING,
        started_at=datetime.utcnow().isoformat(),
    )

    request = copy.deepcopy(scenario["request"])
    overrides = scenario.get("tool_overrides", {})
    pre_inject = scenario.get("pre_inject")

    t0 = time.perf_counter()

    # ── Phase 1: Run INSECURE pipeline ─────────────────────────────
    # Clear the approval ledger before each run
    APPROVAL_LEDGER.clear()

    if pre_inject:
        # Some scenarios inject state (like a forged approval)
        # between agents.  We handle this by running the pipeline
        # in stages.
        final_request, trace = _run_with_injection(
            request, overrides, pre_inject,
        )
    else:
        final_request, trace = run_procurement_pipeline(
            request, tool_overrides=overrides, defended=False,
        )

    result.trace = trace

    # ── Phase 2: Analyze trace ─────────────────────────────────────
    violations = analyze_trace(trace, scenario, final_request)
    result.violations = violations

    # ── Phase 3: Build attack paths ────────────────────────────────
    attack_paths = build_attack_paths(trace, violations)
    result.attack_paths = attack_paths

    # ── Phase 4: Recommend defenses ────────────────────────────────
    defenses = recommend_defenses(violations)

    # ── Phase 5: Verify defenses ───────────────────────────────────
    defense_results = []
    for defense in defenses:
        dr = _verify_defense(scenario, defense, trace, violations)
        defense_results.append(dr)

    result.defenses = defense_results

    elapsed = time.perf_counter() - t0
    result.latency_ms = int(elapsed * 1000)
    result.finished_at = datetime.utcnow().isoformat()
    result.status = RunStatus.COMPLETED

    return result


def _run_with_injection(
    request: dict,
    overrides: dict,
    pre_inject: dict,
) -> tuple[dict, list[TraceEvent]]:
    """
    Run the pipeline but inject state (like a forged approval)
    before the purchaser stage.  This simulates an upstream agent
    being tricked into setting bad state.
    """
    from agents.pipeline import (
        agent_requester, agent_vendor_lookup,
        agent_approver, agent_purchaser,
    )
    all_events: list[TraceEvent] = []

    # Stages 1-3 run normally
    request, events = agent_requester(request, overrides)
    all_events.extend(events)
    request, events = agent_vendor_lookup(request, overrides)
    all_events.extend(events)
    request, events = agent_approver(request, overrides)
    all_events.extend(events)

    # Inject the pre_inject data (e.g., forged approval)
    request.update(pre_inject)

    # Record the injection as a trace event
    all_events.append(TraceEvent(
        agent=request.get("_inject_agent", "requester"),
        kind=EventKind.AGENT_DECISION,
        action="inject_state",
        input_data=pre_inject,
        output_data={"injected": True},
        trusted=False,
        metadata={"source": "scenario_pre_inject"},
    ))

    # Stage 4: Purchaser runs with injected state
    request, events = agent_purchaser(request, overrides, defended=False)
    all_events.extend(events)

    return request, all_events


def _verify_defense(
    scenario: dict,
    defense: Defense,
    trace_before: list[TraceEvent],
    violations_before: list[PolicyViolation],
) -> DefenseResult:
    """
    Re-run the scenario with the defense enabled and check
    whether the violation is blocked.
    """
    APPROVAL_LEDGER.clear()

    request = copy.deepcopy(scenario["request"])
    overrides = scenario.get("tool_overrides", {})
    pre_inject = scenario.get("pre_inject")

    if pre_inject:
        final_request, trace_after = _run_with_injection(
            request, overrides, pre_inject,
        )
        # For the forged approval scenario, the defense is at the tool level,
        # so we re-run with defended=True on the purchaser
        from agents.pipeline import (
            agent_requester, agent_vendor_lookup,
            agent_approver, agent_purchaser,
        )
        request2 = copy.deepcopy(scenario["request"])
        APPROVAL_LEDGER.clear()
        all_events2: list[TraceEvent] = []
        request2, ev = agent_requester(request2, overrides)
        all_events2.extend(ev)
        request2, ev = agent_vendor_lookup(request2, overrides)
        all_events2.extend(ev)
        request2, ev = agent_approver(request2, overrides)
        all_events2.extend(ev)
        request2.update(pre_inject)
        all_events2.append(TraceEvent(
            agent="requester",
            kind=EventKind.AGENT_DECISION,
            action="inject_state",
            input_data=pre_inject,
            output_data={"injected": True},
            trusted=False,
        ))
        request2, ev = agent_purchaser(request2, overrides, defended=True)
        all_events2.extend(ev)
        trace_after = all_events2
        final_request = request2
    else:
        final_request, trace_after = run_procurement_pipeline(
            request, tool_overrides=overrides, defended=True,
        )

    # Re-analyze
    violations_after = analyze_trace(trace_after, scenario, final_request)

    # Determine verdict
    if len(violations_before) > 0 and len(violations_after) == 0:
        verdict = DefenseVerdict.BLOCKED
        explanation = (
            f"Defense '{defense.name}' successfully blocked the attack. "
            f"The {len(violations_before)} violation(s) found in the insecure "
            f"run are no longer present."
        )
    elif len(violations_before) == 0:
        verdict = DefenseVerdict.BLOCKED
        explanation = "No violations in either run — legitimate request handled correctly."
    else:
        verdict = DefenseVerdict.BYPASSED
        explanation = (
            f"Defense '{defense.name}' did NOT block the attack. "
            f"{len(violations_after)} violation(s) remain."
        )

    return DefenseResult(
        defense=defense,
        verdict=verdict,
        trace_before=trace_before,
        trace_after=trace_after,
        violation_before=violations_before[0] if violations_before else None,
        violation_after=violations_after[0] if violations_after else None,
        explanation=explanation,
    )
