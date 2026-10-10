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

import neatlogs
from opentelemetry import trace as otel_trace

from core.types import (
    PipelineResult, RunStatus, TraceEvent, PolicyViolation,
    AttackPath, Defense, DefenseResult, DefenseVerdict,
    ViolationCategory, Severity, EventKind,
)
from agents.pipeline import run_procurement_pipeline, PipelineError
from agents.tools import APPROVAL_LEDGER
from analyzer.trace_analyzer import analyze_trace, build_attack_paths
from analyzer.remediation import recommend_defenses


def _active_span():
    """The recording Neatlogs span for this call, or None (SDK off)."""
    span = otel_trace.get_current_span()
    return span if span.is_recording() else None


def _link_findings(result: PipelineResult) -> None:
    """
    Attach the run and its findings to the active Neatlogs trace.

    Span attributes (redops.run_id, redops.violation_*, ...) make every
    trace searchable by run and finding, and each violation/defense emits
    a LOG span so findings appear inline in the trace timeline.
    """
    span = _active_span()
    if span is not None:
        span.set_attribute("redops.run_id", result.run_id)
        span.set_attribute("redops.scenario", result.scenario_name)
        span.set_attribute(
            "redops.status", getattr(result.status, "value", str(result.status))
        )
        span.set_attribute("redops.latency_ms", result.latency_ms)
        span.set_attribute("redops.violation_count", len(result.violations))
        span.set_attribute(
            "redops.violation_categories",
            [v.category.value for v in result.violations],
        )
        span.set_attribute(
            "redops.violation_severities",
            [v.severity.value for v in result.violations],
        )
        span.set_attribute("redops.attack_path_count", len(result.attack_paths))
        span.set_attribute(
            "redops.defense_verdicts", [d.verdict.value for d in result.defenses]
        )
        if result.error:
            span.set_attribute("redops.error", result.error)

    # One LOG span per finding, inline in the trace timeline.
    for v in result.violations:
        neatlogs.log(
            "finding {category} ({severity}): {title}",
            level="warning",
            category=v.category.value,
            severity=v.severity.value,
            title=v.title,
            root_cause=v.root_cause,
            run_id=result.run_id,
        )
    for d in result.defenses:
        neatlogs.log(
            "defense {defense} -> {verdict}",
            level="info" if d.verdict == DefenseVerdict.BLOCKED else "error",
            defense=d.defense.name,
            verdict=d.verdict.value,
            explanation=d.explanation,
        )
    if result.error:
        neatlogs.log(
            "scenario run failed: {error}",
            level="error",
            error=result.error,
            run_id=result.run_id,
        )


@neatlogs.span(kind="WORKFLOW", name="evaluate_scenario", capture_output=False)
def run_scenario(scenario: dict) -> PipelineResult:
    """
    Execute a single scenario through the full RedOps pipeline:

    1. Run the INSECURE procurement pipeline
    2. Analyze the trace for policy violations
    3. Build attack paths
    4. Recommend defenses
    5. Re-run with defenses and verify the attack is blocked

    Returns a PipelineResult with everything populated.  A crash in the
    insecure pipeline is captured (status=FAILED + error) and recorded as
    a finding, and the defended re-run doubles as the recovery check.
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

    try:
        # ── Phase 1: Run INSECURE pipeline ─────────────────────────
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

        # ── Phase 2: Analyze trace ─────────────────────────────────
        result.violations = analyze_trace(trace, scenario, final_request)

        # ── Phase 3: Build attack paths ────────────────────────────
        result.attack_paths = build_attack_paths(trace, result.violations)

    except PipelineError as exc:
        # A crashed execution is itself a finding: keep the partial trace
        # and let the defended re-run below act as the recovery check.
        result.trace = exc.trace
        result.status = RunStatus.FAILED
        result.error = str(exc)
        result.violations = [_crash_finding(exc, exc.trace)]
        result.attack_paths = build_attack_paths(result.trace, result.violations)
    except Exception as exc:  # pragma: no cover - defensive last resort
        result.status = RunStatus.FAILED
        result.error = f"{type(exc).__name__}: {exc}"
        result.violations = [_crash_finding(exc, result.trace)]
        result.attack_paths = build_attack_paths(result.trace, result.violations)

    # ── Phase 4: Recommend defenses (also for failed executions) ──
    defenses = recommend_defenses(result.violations)

    # ── Phase 5: Verify defenses ────────────────────────────────
    # The defended re-run doubles as the recovery check: a payload that
    # crashed the insecure pipeline must be rejected at the boundary.
    result.defenses = [
        _verify_defense(scenario, defense, result.trace, result.violations)
        for defense in defenses
    ]

    elapsed = time.perf_counter() - t0
    result.latency_ms = int(elapsed * 1000)
    result.finished_at = datetime.utcnow().isoformat()
    if result.status != RunStatus.FAILED:
        result.status = RunStatus.COMPLETED
    _link_findings(result)

    return result


def _crash_finding(exc: Exception, trace: list[TraceEvent]) -> PolicyViolation:
    """Turn a mid-pipeline crash into an actionable finding."""
    return PolicyViolation(
        category=ViolationCategory.MISSING_VALIDATION,
        severity=Severity.CRITICAL,
        title="Pipeline crashed on malformed tool payload",
        description=(
            f"The insecure pipeline crashed mid-run: {exc}. Tool output "
            f"was consumed without validating its shape."
        ),
        evidence_event_ids=[e.id for e in trace if e.kind == EventKind.ERROR],
        root_cause=(
            "Tool responses cross a trust boundary without shape or type "
            "validation, so a malformed payload crashes the agent that "
            "consumes it instead of failing closed."
        ),
    )


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
        agent_approver, agent_purchaser, agent_auditor,
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

    # Stage 5: Auditor (post-execution review)
    request, events = agent_auditor(request, overrides, defended=False)
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
            agent_approver, agent_purchaser, agent_auditor,
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
        request2, ev = agent_auditor(request2, overrides, defended=True)
        all_events2.extend(ev)
        trace_after = all_events2
        final_request = request2
    else:
        final_request, trace_after = run_procurement_pipeline(
            request, tool_overrides=overrides, defended=True,
        )

    # Re-analyze.  `defended=True` lets the analyzer credit the guards:
    # violations they demonstrably intercepted are no longer reported.
    violations_after = analyze_trace(
        trace_after, scenario, final_request, defended=True,
    )

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
