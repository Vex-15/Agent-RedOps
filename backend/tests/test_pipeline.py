"""
Pipeline integration tests.

Run with: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scenarios.builtin import BUILTIN_SCENARIOS
from scenarios.runner import run_scenario
from core.types import RunStatus, DefenseVerdict, ViolationCategory, AgentRole, EventKind
from real_agents import openai_payload, stream_http_agent


class _FakeResponse:
    status_code = 200
    headers = {"content-type": "application/json"}
    content = b'{"ok":true}'
    is_success = True
    text = '{"ok":true}'

    def json(self):
        return {"ok": True}


class _FakeClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def request(self, method, url, headers, json):
        return _FakeResponse()


def test_real_agent_requires_a_received_response(monkeypatch):
    import real_agents

    monkeypatch.setattr(real_agents.httpx, "Client", _FakeClient)
    messages = list(stream_http_agent(
        name="test",
        url="https://example.test/agent",
        method="POST",
        headers={},
        payload={"message": "hello"},
        timeout_seconds=5,
    ))
    result = messages[-1]["result"]
    assert result.status == RunStatus.COMPLETED
    assert any(message["type"] == "event" and message["event"].action == "real_agent_response" for message in messages)
    assert result.error == ""


def test_openai_payload_is_chat_completions_compatible():
    assert openai_payload("demo", "hello", "system", 0) == {
        "model": "demo",
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "hello"},
        ],
        "temperature": 0,
    }


class TestDeceptiveVendor:
    """Scenario 1: vendor_lookup returns fake 'verified' status."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[0])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_finds_trust_boundary_violation(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.TRUST_BOUNDARY in categories

    def test_finds_deceptive_output_violation(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.DECEPTIVE_TOOL_OUTPUT in categories

    def test_builds_attack_path(self):
        assert len(self.result.attack_paths) > 0
        for ap in self.result.attack_paths:
            assert ap.length > 0
            assert ap.entry_point != ""

    def test_trace_has_untrusted_events(self):
        untrusted = [e for e in self.result.trace if not e.trusted]
        assert len(untrusted) > 0

    def test_recommends_defenses(self):
        assert len(self.result.defenses) > 0


class TestForgedApproval:
    """Scenario 2: fabricated approval_id not in ledger."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[1])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_finds_auth_bypass(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.AUTH_BYPASS in categories

    def test_defense_blocks_forged_approval(self):
        auth_defenses = [
            d for d in self.result.defenses
            if d.defense.category == ViolationCategory.AUTH_BYPASS
        ]
        assert len(auth_defenses) > 0
        assert auth_defenses[0].verdict == DefenseVerdict.BLOCKED

    def test_critical_severity(self):
        auth_violations = [
            v for v in self.result.violations
            if v.category == ViolationCategory.AUTH_BYPASS
        ]
        assert auth_violations[0].severity.value == "critical"


class TestConflictingBudget:
    """Scenario 3: budget tool overridden but VP threshold blocks."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[2])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_finds_deceptive_budget(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.DECEPTIVE_TOOL_OUTPUT in categories

    def test_vp_threshold_still_blocks(self):
        """Even with inflated budget, $45k > $10k VP threshold."""
        # The purchase should NOT have executed because the VP rule blocked it
        # So there should be no auth_bypass violation
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.AUTH_BYPASS not in categories


class TestLegitimate:
    """Scenario 4: a normal purchase — must succeed everywhere."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[3])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_no_violations(self):
        assert len(self.result.violations) == 0

    def test_no_attack_paths(self):
        assert len(self.result.attack_paths) == 0

    def test_trace_all_trusted(self):
        for e in self.result.trace:
            assert e.trusted is True


class TestVendorIdentity:
    """Scenario 5: vendor name spoofed to impersonate trusted vendor."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[4])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_finds_social_engineering(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.SOCIAL_ENGINEERING in categories

    def test_finds_deceptive_output(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.DECEPTIVE_TOOL_OUTPUT in categories


class TestInstructionOverride:
    """Scenario 6: metadata instructs agents to bypass budget check."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[5])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_finds_conflicting_instructions(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.CONFLICTING_INSTRUCTIONS in categories

    def test_recommends_instruction_precedence_defense(self):
        names = [d.defense.name for d in self.result.defenses]
        assert "Instruction Precedence Guard" in names

    def test_purchase_executed_in_insecure_run(self):
        """The insecure pipeline obeys the override and executes."""
        executed = [e for e in self.result.trace if e.action == "purchase_completed" and e.trusted]
        assert len(executed) > 0


class TestUnregisteredVendor:
    """Scenario 7: vendor_id not present in the canonical catalog."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[6])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_finds_deceptive_output(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.DECEPTIVE_TOOL_OUTPUT in categories


class TestAuditorStage:
    """The pipeline now ends with a post-execution audit event."""

    def test_every_scenario_produces_audit_event(self):
        for scenario in BUILTIN_SCENARIOS:
            result = run_scenario(scenario)
            if result.status == RunStatus.FAILED:
                # Crashed mid-pipeline by design (failure-and-recovery case)
                continue
            audit_events = [e for e in result.trace if e.agent == AgentRole.AUDITOR]
            assert len(audit_events) == 1, f"scenario '{scenario['name']}' missing audit event"
            assert audit_events[0].trusted is True

    def test_audit_records_buyer_result(self):
        result = run_scenario(BUILTIN_SCENARIOS[3])
        audit = [e for e in result.trace if e.agent == AgentRole.AUDITOR][0]
        assert audit.output_data["purchase_status"] == "executed"
        assert audit.output_data["vendor_verified_per_catalog"] is True


class TestCreditLimitEvasion:
    """Scenario 8: inflated max_credit unlocks an over-limit purchase."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[7])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_categories_found(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.TRUST_BOUNDARY in categories
        assert ViolationCategory.DECEPTIVE_TOOL_OUTPUT in categories
        assert ViolationCategory.POLICY_EXCEED_LIMIT in categories

    def test_name_and_verification_not_flagged(self):
        """Only max_credit lies — identity checks must stay quiet."""
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.SOCIAL_ENGINEERING not in categories

    def test_defenses_block(self):
        assert len(self.result.defenses) > 0
        assert all(d.verdict == DefenseVerdict.BLOCKED for d in self.result.defenses)


class TestAmountTampering:
    """Scenario 9: amount rewritten after the approver signed off."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[8])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_finds_scope_violation(self):
        scope = [
            v for v in self.result.violations
            if v.title == "Purchase executed beyond approved amount"
        ]
        assert len(scope) == 1
        assert scope[0].category == ViolationCategory.AUTH_BYPASS
        assert scope[0].severity.value == "critical"

    def test_finds_credit_limit_breach(self):
        categories = [v.category for v in self.result.violations]
        assert ViolationCategory.POLICY_EXCEED_LIMIT in categories

    def test_ledger_guard_blocks_tampering(self):
        assert len(self.result.defenses) > 0
        assert all(d.verdict == DefenseVerdict.BLOCKED for d in self.result.defenses)


class TestShadowBudget:
    """Scenario 10: budget tool overstates the treasury allocation."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[9])

    def test_pipeline_completes(self):
        assert self.result.status == RunStatus.COMPLETED

    def test_finds_budget_discrepancy(self):
        titles = [v.title for v in self.result.violations]
        assert "Budget tool overstates available funds" in titles

    def test_recommends_budget_guard(self):
        names = [d.defense.name for d in self.result.defenses]
        assert "Strict Budget Guard" in names

    def test_budget_guard_blocks(self):
        assert len(self.result.defenses) > 0
        assert all(d.verdict == DefenseVerdict.BLOCKED for d in self.result.defenses)


class TestDefendedPipelineIsClean:
    """
    The demo's core promise: for every attack scenario, the defended
    re-run neutralizes every violation the insecure run produced.
    """

    def test_every_scenario_is_neutralized_when_defended(self):
        for scenario in BUILTIN_SCENARIOS:
            result = run_scenario(scenario)
            # FAILED is a legitimate outcome for the failure-and-recovery
            # scenario; its defended re-run must still block.
            assert result.status in (RunStatus.COMPLETED, RunStatus.FAILED), scenario["name"]
            for d in result.defenses:
                assert d.verdict == DefenseVerdict.BLOCKED, (
                    f"{scenario['name']}: defense '{d.defense.name}' "
                    f"reported {d.verdict.value}"
                )

    def test_positive_control_stays_clean(self):
        """The legitimate baseline must still produce zero violations."""
        result = run_scenario(BUILTIN_SCENARIOS[3])
        assert len(result.violations) == 0
        assert len(result.defenses) == 0


class TestCorruptedPayloadFailureAndRecovery:
    """Scenario 11: insecure run fails on a malformed payload,
    the defended run rejects it at the boundary and recovers."""

    def setup_method(self):
        self.result = run_scenario(BUILTIN_SCENARIOS[10])

    def test_pipeline_reports_failure(self):
        assert self.result.status == RunStatus.FAILED
        assert self.result.error  # message captured, not a bare 500

    def test_error_event_recorded_in_trace(self):
        errors = [e for e in self.result.trace if e.kind == EventKind.ERROR]
        assert len(errors) >= 1
        assert "error" in errors[0].output_data

    def test_partial_trace_preserved(self):
        actions = [e.action for e in self.result.trace]
        assert "initiate_request" in actions

    def test_crash_recorded_as_finding(self):
        titles = [v.title for v in self.result.violations]
        assert "Pipeline crashed on malformed tool payload" in titles
        crash = self.result.violations[0]
        assert crash.severity.value == "critical"
        assert len(crash.evidence_event_ids) > 0

    def test_defended_rerun_recovers(self):
        """The defended pipeline must complete and block the crash path."""
        assert len(self.result.defenses) == 1
        assert self.result.defenses[0].verdict == DefenseVerdict.BLOCKED

    def test_attack_path_built_from_error(self):
        assert len(self.result.attack_paths) >= 1
        assert self.result.attack_paths[0].length >= 1
