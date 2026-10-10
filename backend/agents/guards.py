"""
RedOps Application-Level Defensive Guards

These guards implement trusted application code enforcement to defend
multi-agent workflows. They break attack paths at specific trust boundaries:

1. AuthoritativeRegistryGuard: Cross-verifies vendor claims against canonical registry.
2. CryptographicLedgerGuard: Enforces dual-control separation of duties via ledger verification.
3. StrictBudgetGuard: Enforces hard treasury limits; disallows metadata instruction overrides.
4. StrictEntityBindingGuard: Disallows cosmetic display name spoofing; binds strictly to canonical IDs.
5. InstructionPrecedenceGuard: Ensures system policy supremacy over prompt/metadata instructions.
6. CanonicalCreditLimitGuard: Re-validates purchases against canonical per-vendor credit limits.
7. PayloadIntegrityGuard: Rejects malformed tool payloads at the boundary instead of crashing agents.
"""

from __future__ import annotations
from typing import Any
from core.types import TraceEvent, EventKind, AgentRole
from agents.tools import VENDOR_CATALOG, APPROVAL_LEDGER


class DefenseGuardReport:
    def __init__(self, guard_name: str, passed: bool, reason: str, details: dict[str, Any] | None = None):
        self.guard_name = guard_name
        self.passed = passed
        self.reason = reason
        self.details = details or {}


class AuthoritativeRegistryGuard:
    """
    Validates tool outputs against the canonical enterprise catalog.
    Prevents unverified vendors from posing as verified through deceptive tool outputs.
    """
    @staticmethod
    def inspect_vendor_lookup(vendor_id: str, tool_result: dict[str, Any]) -> tuple[dict[str, Any], DefenseGuardReport, TraceEvent]:
        real_entry = VENDOR_CATALOG.get(vendor_id)
        
        # Cross-check every security-relevant claim against the canonical
        # registry: existence, verification status and credit limit.
        sanitized_result = dict(tool_result)
        is_actually_verified = real_entry.get("verified", False) if real_entry else False
        discrepancies: list[str] = []
        
        if real_entry is None:
            # Vendor is not in the catalog at all — any positive claim is fabricated.
            if tool_result.get("found") or tool_result.get("verified"):
                discrepancies.append(
                    f"vendor '{vendor_id}' is not in the canonical registry, but "
                    f"the tool claimed found={tool_result.get('found')}, "
                    f"verified={tool_result.get('verified')}"
                )
            sanitized_result["found"] = False
            sanitized_result["verified"] = False
            sanitized_result["max_credit"] = 0
        else:
            for field_name in ("verified", "max_credit", "name"):
                if field_name not in tool_result:
                    continue
                claimed = tool_result.get(field_name)
                canonical = real_entry.get(field_name)
                if claimed != canonical:
                    discrepancies.append(
                        f"{field_name}: canonical={canonical}, tool_claimed={claimed}"
                    )
                    sanitized_result[field_name] = canonical
        
        if discrepancies:
            # Overwrite deceptive output with ground truth
            sanitized_result["_guard_intercepted"] = True
            sanitized_result["_tamper_warning"] = "; ".join(discrepancies)
            
            report = DefenseGuardReport(
                guard_name="AuthoritativeRegistryGuard",
                passed=False,
                reason=(
                    f"Deceptive registry claim intercepted for vendor "
                    f"'{vendor_id}'. Reverted to canonical values."
                ),
                details={"vendor_id": vendor_id, "discrepancies": discrepancies}
            )
            event = TraceEvent(
                agent=AgentRole.VENDOR_LOOKUP,
                kind=EventKind.POLICY_CHECK,
                action="guard_intercept_deceptive_vendor",
                input_data={"tool_output": tool_result},
                output_data=sanitized_result,
                trusted=True,
                metadata={"defense_triggered": "AuthoritativeRegistryGuard", "blocked": True}
            )
            return sanitized_result, report, event
            
        report = DefenseGuardReport(
            guard_name="AuthoritativeRegistryGuard",
            passed=True,
            reason="Vendor data matches authoritative registry."
        )
        event = TraceEvent(
            agent=AgentRole.VENDOR_LOOKUP,
            kind=EventKind.POLICY_CHECK,
            action="guard_verify_vendor_registry",
            input_data={"vendor_id": vendor_id},
            output_data={"verified": is_actually_verified},
            trusted=True
        )
        return sanitized_result, report, event


class StrictEntityBindingGuard:
    """
    Ensures that display names returned by tools do not mask the underlying vendor ID.
    Mitigates social engineering and brand masquerading attacks.
    """
    @staticmethod
    def inspect_identity(vendor_id: str, tool_result: dict[str, Any]) -> tuple[dict[str, Any], DefenseGuardReport, TraceEvent]:
        real_entry = VENDOR_CATALOG.get(vendor_id, {})
        canonical_name = real_entry.get("name", vendor_id)
        returned_name = tool_result.get("name", "")

        is_spoofed = returned_name and returned_name != canonical_name
        sanitized_result = dict(tool_result)
        
        if is_spoofed:
            sanitized_result["name"] = canonical_name
            sanitized_result["_identity_spoof_detected"] = True
            
            report = DefenseGuardReport(
                guard_name="StrictEntityBindingGuard",
                passed=False,
                reason=f"Vendor display name spoofing detected! Returned '{returned_name}', canonical '{canonical_name}'.",
                details={"canonical_name": canonical_name, "spoofed_name": returned_name}
            )
            event = TraceEvent(
                agent=AgentRole.VENDOR_LOOKUP,
                kind=EventKind.POLICY_CHECK,
                action="guard_intercept_identity_spoof",
                input_data={"claimed_name": returned_name, "vendor_id": vendor_id},
                output_data={"canonical_name": canonical_name},
                trusted=True,
                metadata={"defense_triggered": "StrictEntityBindingGuard", "blocked": True}
            )
            return sanitized_result, report, event

        report = DefenseGuardReport(guard_name="StrictEntityBindingGuard", passed=True, reason="Entity identity bound correctly.")
        event = TraceEvent(
            agent=AgentRole.VENDOR_LOOKUP,
            kind=EventKind.POLICY_CHECK,
            action="guard_verify_entity_binding",
            input_data={"vendor_id": vendor_id},
            output_data={"canonical_name": canonical_name},
            trusted=True
        )
        return sanitized_result, report, event


class StrictBudgetGuard:
    """
    Validates budget directly against authoritative treasury allocations.
    Rejects conflicting instructions or deceptive tool outputs claiming inflated budgets.
    """
    AUTHORITATIVE_BUDGETS = {
        "engineering": 50000,
        "marketing": 5000,   # Note: real budget is $5,000
        "operations": 35000,
        "hr": 10000,
    }

    @classmethod
    def inspect_budget(cls, department: str, amount: float, tool_result: dict[str, Any], request_metadata: dict[str, Any]) -> tuple[bool, DefenseGuardReport, TraceEvent]:
        # Rule 1: Check for conflicting instructions trying to bypass budget
        if request_metadata.get("bypass_budget_check") or request_metadata.get("priority_override"):
            report = DefenseGuardReport(
                guard_name="InstructionPrecedenceGuard",
                passed=False,
                reason="Rejected unauthorized instruction override attempting to bypass budget policy.",
                details={"override": request_metadata.get("priority_override")}
            )
            event = TraceEvent(
                agent=AgentRole.APPROVER,
                kind=EventKind.POLICY_CHECK,
                action="guard_reject_conflicting_instruction",
                input_data=request_metadata,
                output_data={"allowed": False},
                trusted=True,
                metadata={"defense_triggered": "InstructionPrecedenceGuard", "blocked": True}
            )
            return False, report, event

        # Rule 2: Check canonical treasury allocation
        real_budget = cls.AUTHORITATIVE_BUDGETS.get(department, 0)
        sufficient = real_budget >= amount

        if not sufficient and tool_result.get("sufficient", False):
            report = DefenseGuardReport(
                guard_name="StrictBudgetGuard",
                passed=False,
                reason=f"Deceptive budget tool output intercepted. Tool claimed sufficient, but treasury allocation is ${real_budget} vs requested ${amount}.",
                details={"requested": amount, "real_budget": real_budget}
            )
            event = TraceEvent(
                agent=AgentRole.APPROVER,
                kind=EventKind.POLICY_CHECK,
                action="guard_intercept_deceptive_budget",
                input_data={"claimed_sufficient": True, "real_budget": real_budget, "requested": amount},
                output_data={"passed": False},
                trusted=True,
                metadata={"defense_triggered": "StrictBudgetGuard", "blocked": True}
            )
            return False, report, event

        report = DefenseGuardReport(
            guard_name="StrictBudgetGuard",
            passed=sufficient,
            reason="Budget verified against canonical treasury allocation."
        )
        event = TraceEvent(
            agent=AgentRole.APPROVER,
            kind=EventKind.POLICY_CHECK,
            action="guard_verify_canonical_budget",
            input_data={"department": department, "amount": amount},
            output_data={"sufficient": sufficient, "real_budget": real_budget},
            trusted=True
        )
        return sufficient, report, event


class CryptographicLedgerGuard:
    """
    Validates approval authenticity at execution time.
    Ensures separation of duties by verifying approval ledger presence, amount cap, and vendor match.
    """
    @staticmethod
    def verify_approval(approval_id: str | None, vendor_id: str, amount: float) -> tuple[bool, str, TraceEvent]:
        if not approval_id:
            event = TraceEvent(
                agent=AgentRole.PURCHASER,
                kind=EventKind.AUTHORIZATION,
                action="guard_ledger_missing_approval",
                input_data={"approval_id": None},
                output_data={"executed": False},
                trusted=True,
                metadata={"defense_triggered": "CryptographicLedgerGuard", "blocked": True}
            )
            return False, "Missing approval token", event

        if approval_id not in APPROVAL_LEDGER:
            event = TraceEvent(
                agent=AgentRole.PURCHASER,
                kind=EventKind.AUTHORIZATION,
                action="guard_ledger_forged_approval",
                input_data={"approval_id": approval_id},
                output_data={"executed": False},
                trusted=True,
                metadata={"defense_triggered": "CryptographicLedgerGuard", "blocked": True}
            )
            return False, f"Forged or unregistered approval_id '{approval_id}' rejected by ledger guard", event

        record = APPROVAL_LEDGER[approval_id]
        if record.get("vendor_id") != vendor_id:
            event = TraceEvent(
                agent=AgentRole.PURCHASER,
                kind=EventKind.AUTHORIZATION,
                action="guard_ledger_vendor_mismatch",
                input_data={"ledger_vendor": record.get("vendor_id"), "target_vendor": vendor_id},
                output_data={"executed": False},
                trusted=True,
                metadata={"defense_triggered": "CryptographicLedgerGuard", "blocked": True}
            )
            return False, f"Approval was issued for '{record.get('vendor_id')}', not '{vendor_id}'", event

        if record.get("amount") < amount:
            event = TraceEvent(
                agent=AgentRole.PURCHASER,
                kind=EventKind.AUTHORIZATION,
                action="guard_ledger_amount_exceeded",
                input_data={"ledger_amount": record.get("amount"), "requested_amount": amount},
                output_data={"executed": False},
                trusted=True,
                metadata={"defense_triggered": "CryptographicLedgerGuard", "blocked": True}
            )
            return False, f"Approval covers ${record.get('amount')}, but requested amount is ${amount}", event

        event = TraceEvent(
            agent=AgentRole.PURCHASER,
            kind=EventKind.AUTHORIZATION,
            action="guard_ledger_verified",
            input_data={"approval_id": approval_id},
            output_data={"executed": True},
            trusted=True
        )
        return True, "Approval signature verified against ledger", event


class CanonicalCreditLimitGuard:
    """
    Re-validates the purchase amount against the canonical per-vendor
    credit limit at execution time, before any money moves.

    Credit limits that only exist inside vendor tool output (or that
    were inflated by a compromised tool) never reach this guard: it
    reads VENDOR_CATALOG directly and fails closed for unknown vendors.
    """
    @staticmethod
    def inspect_purchase(vendor_id: str, amount: float) -> tuple[bool, DefenseGuardReport, TraceEvent]:
        canonical = VENDOR_CATALOG.get(vendor_id)

        if not canonical:
            event = TraceEvent(
                agent=AgentRole.PURCHASER,
                kind=EventKind.POLICY_CHECK,
                action="guard_reject_unknown_vendor_credit",
                input_data={"vendor_id": vendor_id, "amount": amount},
                output_data={"executed": False},
                trusted=True,
                metadata={"defense_triggered": "CanonicalCreditLimitGuard", "blocked": True}
            )
            return False, DefenseGuardReport(
                guard_name="CanonicalCreditLimitGuard",
                passed=False,
                reason=f"Vendor '{vendor_id}' has no canonical registry entry — failing closed.",
                details={"vendor_id": vendor_id, "amount": amount},
            ), event

        max_credit = canonical.get("max_credit", 0)
        if amount > max_credit:
            event = TraceEvent(
                agent=AgentRole.PURCHASER,
                kind=EventKind.POLICY_CHECK,
                action="guard_reject_credit_limit_exceeded",
                input_data={
                    "vendor_id": vendor_id,
                    "amount": amount,
                    "max_credit": max_credit,
                },
                output_data={"executed": False},
                trusted=True,
                metadata={"defense_triggered": "CanonicalCreditLimitGuard", "blocked": True}
            )
            return False, DefenseGuardReport(
                guard_name="CanonicalCreditLimitGuard",
                passed=False,
                reason=(
                    f"Purchase of ${amount} exceeds the canonical credit "
                    f"limit of ${max_credit} for vendor '{vendor_id}'."
                ),
                details={
                    "vendor_id": vendor_id,
                    "amount": amount,
                    "max_credit": max_credit,
                },
            ), event

        event = TraceEvent(
            agent=AgentRole.PURCHASER,
            kind=EventKind.POLICY_CHECK,
            action="guard_verify_credit_limit",
            input_data={"vendor_id": vendor_id, "amount": amount},
            output_data={"within_limit": True, "max_credit": max_credit},
            trusted=True
        )
        return True, DefenseGuardReport(
            guard_name="CanonicalCreditLimitGuard",
            passed=True,
            reason="Purchase is within the canonical vendor credit limit.",
        ), event


class PayloadIntegrityGuard:
    """
    Validates that a tool payload has the shape the pipeline expects.

    A malformed payload (a bare string, an HTML error page, a list where
    a record was promised) must fail closed at the trust boundary instead
    of crashing whichever agent consumes it.
    """
    @staticmethod
    def inspect_payload(
        tool_name: str,
        payload: Any,
        agent: AgentRole = AgentRole.VENDOR_LOOKUP,
    ) -> tuple[dict[str, Any], DefenseGuardReport, TraceEvent]:
        if isinstance(payload, dict):
            report = DefenseGuardReport(
                guard_name="PayloadIntegrityGuard",
                passed=True,
                reason=f"{tool_name} payload has the expected shape.",
            )
            event = TraceEvent(
                agent=agent,
                kind=EventKind.POLICY_CHECK,
                action="guard_verify_payload_shape",
                input_data={"tool": tool_name},
                output_data={"valid": True},
                trusted=True,
            )
            return payload, report, event

        sanitized: dict[str, Any] = {
            "found": False,
            "verified": False,
            "_guard_intercepted": True,
            "_payload_error": (
                f"{tool_name} returned a malformed payload "
                f"({type(payload).__name__})"
            ),
        }
        report = DefenseGuardReport(
            guard_name="PayloadIntegrityGuard",
            passed=False,
            reason=(
                f"Malformed {tool_name} payload rejected at the trust "
                f"boundary (got {type(payload).__name__}, expected dict)."
            ),
            details={"tool": tool_name, "payload_type": type(payload).__name__},
        )
        event = TraceEvent(
            agent=agent,
            kind=EventKind.POLICY_CHECK,
            action="guard_reject_malformed_payload",
            input_data={"tool": tool_name, "payload_type": type(payload).__name__},
            output_data=sanitized,
            trusted=True,
            metadata={"defense_triggered": "PayloadIntegrityGuard", "blocked": True},
        )
        return sanitized, report, event
