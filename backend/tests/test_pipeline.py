"""
Pipeline integration tests.

Run with: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scenarios.builtin import BUILTIN_SCENARIOS
from scenarios.runner import run_scenario
from core.types import RunStatus, DefenseVerdict, ViolationCategory, AgentRole


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
            audit_events = [e for e in result.trace if e.agent == AgentRole.AUDITOR]
            assert len(audit_events) == 1, f"scenario '{scenario['name']}' missing audit event"
            assert audit_events[0].trusted is True

    def test_audit_records_buyer_result(self):
        result = run_scenario(BUILTIN_SCENARIOS[3])
        audit = [e for e in result.trace if e.agent == AgentRole.AUDITOR][0]
        assert audit.output_data["purchase_status"] == "executed"
        assert audit.output_data["vendor_verified_per_catalog"] is True
