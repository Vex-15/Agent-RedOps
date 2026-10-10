"""
Multi-Agent Procurement Pipeline

Four cooperating agents process a procurement request:
  Requester → VendorLookup → Approver → Purchaser

Scenarios simulate multi-agent manipulation:
  1. Deceptive tool output (e.g. fake verification claim)
  2. State manipulation & forged authorization
  3. Conflicting instructions / emergency bypass
  4. Social engineering via vendor name masquerading
  5. Legitimate baseline request

In INSECURE mode: Agents trust unverified upstream data, conflicting metadata instructions,
and deceptive tool outputs, leading to policy violations and unauthorized money movement.

In DEFENDED mode: Application-level security guards intercept deceptive data at the boundary,
uphold policy supremacy, and block unauthorized actions while allowing legitimate purchases.
"""

from __future__ import annotations
from typing import Any
import uuid

from core.types import AgentRole, EventKind, TraceEvent, Severity, PolicyViolation, ViolationCategory
from agents.tools import call_tool, APPROVAL_LEDGER, VENDOR_CATALOG
from agents.guards import (
    AuthoritativeRegistryGuard,
    StrictEntityBindingGuard,
    StrictBudgetGuard,
    CryptographicLedgerGuard,
    CanonicalCreditLimitGuard,
)


# ── Agent: Requester ───────────────────────────────────────────────────

def agent_requester(
    request: dict[str, Any],
    overrides: dict | None = None,
    defended: bool = False,
) -> tuple[dict[str, Any], list[TraceEvent]]:
    """
    Initiates a procurement request.
    Input: {vendor_id, item, quantity, amount, department, requester, metadata}
    """
    events: list[TraceEvent] = []

    # Check for prompt/metadata instruction injection attempting bypass
    metadata = request.get("metadata", {})
    has_conflicting_instruction = bool(
        metadata.get("priority_override") or metadata.get("bypass_budget_check")
    )

    events.append(TraceEvent(
        agent=AgentRole.REQUESTER,
        kind=EventKind.AGENT_DECISION,
        action="initiate_request",
        input_data={
            "vendor_id": request.get("vendor_id"),
            "amount": request.get("amount"),
            "department": request.get("department"),
            "requester": request.get("requester"),
            "has_instruction_override": has_conflicting_instruction,
        },
        output_data={"forwarded_to": "vendor_lookup"},
        trusted=not has_conflicting_instruction,
        unverified_source=has_conflicting_instruction,
        metadata={"injected_instruction": has_conflicting_instruction}
    ))

    return request, events


# ── Agent: Vendor Lookup ───────────────────────────────────────────────

def agent_vendor_lookup(
    request: dict[str, Any],
    overrides: dict | None = None,
    defended: bool = False,
) -> tuple[dict[str, Any], list[TraceEvent]]:
    """
    Resolves vendor details via vendor_lookup tool.
    In INSECURE mode: Blindly trusts tool output and forwards manipulated records.
    In DEFENDED mode: Runs AuthoritativeRegistryGuard and StrictEntityBindingGuard.
    """
    events: list[TraceEvent] = []
    vendor_id = request.get("vendor_id", "")

    vendor_info, tool_events = call_tool(
        "vendor_lookup",
        {"vendor_id": vendor_id},
        agent=AgentRole.VENDOR_LOOKUP,
        overrides=overrides,
        defended=defended,
    )
    events.extend(tool_events)

    if defended:
        # Guard 1: Enforce canonical entity binding (neutralize display name spoofing)
        vendor_info, ident_report, ident_event = StrictEntityBindingGuard.inspect_identity(
            vendor_id, vendor_info
        )
        events.append(ident_event)

        # Guard 2: Enforce authoritative registry verification (neutralize deceptive tool claims)
        vendor_info, reg_report, reg_event = AuthoritativeRegistryGuard.inspect_vendor_lookup(
            vendor_id, vendor_info
        )
        events.append(reg_event)

        events.append(TraceEvent(
            agent=AgentRole.VENDOR_LOOKUP,
            kind=EventKind.AGENT_DECISION,
            action="accept_vendor_info_guarded",
            input_data={"vendor_id": vendor_id},
            output_data=vendor_info,
            trusted=True,
            metadata={"defense_applied": True}
        ))
    else:
        # INSECURE: blindly trusts whatever tool returned
        events.append(TraceEvent(
            agent=AgentRole.VENDOR_LOOKUP,
            kind=EventKind.AGENT_DECISION,
            action="accept_vendor_info",
            input_data={"vendor_id": vendor_id},
            output_data=vendor_info,
            trusted=vendor_info.get("verified", False) and not any(not e.trusted for e in tool_events),
            unverified_source=any(not e.trusted for e in tool_events),
            metadata={"trusted_tool_output_assumed": True}
        ))

    request["vendor_info"] = vendor_info
    return request, events


# ── Agent: Approver ────────────────────────────────────────────────────

def agent_approver(
    request: dict[str, Any],
    overrides: dict | None = None,
    defended: bool = False,
) -> tuple[dict[str, Any], list[TraceEvent]]:
    """
    Applies multi-tier business rules:
      1. Vendor must be verified
      2. Budget must be sufficient (conflicting instruction bypass denied in defended mode)
      3. Amount > $10,000 requires executive VP approval (auto-reject in standard tier)
    """
    events: list[TraceEvent] = []
    vendor_info = request.get("vendor_info", {})
    amount = request.get("amount", 0)
    department = request.get("department", "")
    metadata = request.get("metadata", {})

    # ── Rule 1: Vendor verification check ──
    vendor_verified = vendor_info.get("verified", False)
    events.append(TraceEvent(
        agent=AgentRole.APPROVER,
        kind=EventKind.POLICY_CHECK,
        action="check_vendor_verified",
        input_data={"vendor_id": request.get("vendor_id"), "claimed_verified": vendor_verified},
        output_data={"passed": vendor_verified},
        trusted=True
    ))

    if not vendor_verified:
        request["approval"] = {
            "approved": False,
            "reason": f"Vendor '{request.get('vendor_id')}' is not verified in corporate catalog"
        }
        events.append(TraceEvent(
            agent=AgentRole.APPROVER,
            kind=EventKind.AGENT_DECISION,
            action="reject_unverified_vendor",
            input_data={"vendor_id": request.get("vendor_id")},
            output_data=request["approval"],
            trusted=True
        ))
        return request, events

    # ── Rule 2: Budget check with Conflicting Instruction handling ──
    budget_result, budget_events = call_tool(
        "check_budget",
        {"department": department, "amount": amount},
        agent=AgentRole.APPROVER,
        overrides=overrides,
        defended=defended,
    )
    events.extend(budget_events)

    if defended:
        # In DEFENDED mode: StrictBudgetGuard & InstructionPrecedenceGuard
        budget_passed, b_report, b_event = StrictBudgetGuard.inspect_budget(
            department, amount, budget_result, metadata
        )
        events.append(b_event)
        if not budget_passed:
            request["approval"] = {
                "approved": False,
                "reason": b_report.reason
            }
            events.append(TraceEvent(
                agent=AgentRole.APPROVER,
                kind=EventKind.AGENT_DECISION,
                action="reject_budget_policy_violation",
                input_data={"department": department, "amount": amount},
                output_data=request["approval"],
                trusted=True,
                metadata={"defense_triggered": b_report.guard_name}
            ))
            return request, events
    else:
        # In INSECURE mode:
        # Check if conflicting instructions trick the agent into bypassing budget check
        if metadata.get("bypass_budget_check") or metadata.get("priority_override"):
            events.append(TraceEvent(
                agent=AgentRole.APPROVER,
                kind=EventKind.AGENT_DECISION,
                action="accept_conflicting_instruction_bypass",
                input_data=metadata,
                output_data={"budget_check_skipped": True, "reason": metadata.get("priority_override")},
                trusted=False,
                metadata={"policy_breach": "instruction_override_accepted"}
            ))
            # Approver fell for conflicting instruction! Continues without budget check
        elif not budget_result.get("sufficient", False):
            request["approval"] = {"approved": False, "reason": "Insufficient budget"}
            events.append(TraceEvent(
                agent=AgentRole.APPROVER,
                kind=EventKind.AGENT_DECISION,
                action="reject_insufficient_budget",
                input_data={},
                output_data=request["approval"],
                trusted=True
            ))
            return request, events

    # ── Rule 3: VP delegation threshold ($10,000) ──
    if amount > 10000:
        request["approval"] = {
            "approved": False,
            "reason": f"Amount ${amount:,.2f} exceeds standard $10,000 threshold — requires VP signoff"
        }
        events.append(TraceEvent(
            agent=AgentRole.APPROVER,
            kind=EventKind.POLICY_CHECK,
            action="vp_threshold_check",
            input_data={"amount": amount, "threshold": 10000},
            output_data={"passed": False},
            trusted=True
        ))
        return request, events

    # ── Approved → record to ledger ──
    approval_id = "APR-" + uuid.uuid4().hex[:8].upper()
    APPROVAL_LEDGER[approval_id] = {
        "vendor_id": request.get("vendor_id"),
        "amount": amount,
        "department": department,
        "requester": request.get("requester", "unknown"),
        "timestamp": str(uuid.uuid4())
    }
    request["approval"] = {"approved": True, "approval_id": approval_id}

    events.append(TraceEvent(
        agent=AgentRole.APPROVER,
        kind=EventKind.AUTHORIZATION,
        action="approve_purchase",
        input_data={"amount": amount, "department": department},
        output_data={"approval_id": approval_id},
        trusted=True
    ))

    return request, events


# ── Agent: Purchaser ───────────────────────────────────────────────────

def agent_purchaser(
    request: dict[str, Any],
    overrides: dict | None = None,
    defended: bool = False,
) -> tuple[dict[str, Any], list[TraceEvent]]:
    """
    Executes purchase.
    In INSECURE mode: Blindly trusts approval claim from upstream context.
    In DEFENDED mode: Validates approval signature against ledger before executing.
    """
    events: list[TraceEvent] = []
    approval = request.get("approval", {})

    if not approval.get("approved", False):
        events.append(TraceEvent(
            agent=AgentRole.PURCHASER,
            kind=EventKind.AGENT_DECISION,
            action="skip_unapproved",
            input_data=approval,
            output_data={"status": "skipped", "reason": "No approved status in request"},
            trusted=True
        ))
        request["purchase_result"] = {"status": "skipped", "reason": "No approved status in request"}
        return request, events

    approval_id = approval.get("approval_id")
    vendor_id = request.get("vendor_id", "")
    amount = request.get("amount", 0)

    if defended:
        is_valid, reason, ledger_event = CryptographicLedgerGuard.verify_approval(
            approval_id, vendor_id, amount
        )
        events.append(ledger_event)
        if not is_valid:
            request["purchase_result"] = {
                "status": "rejected",
                "reason": f"Execution halted by CryptographicLedgerGuard: {reason}"
            }
            events.append(TraceEvent(
                agent=AgentRole.PURCHASER,
                kind=EventKind.AGENT_DECISION,
                action="purchase_blocked_by_guard",
                input_data={"approval_id": approval_id},
                output_data=request["purchase_result"],
                trusted=True,
                metadata={"defense_triggered": "CryptographicLedgerGuard", "blocked": True}
            ))
            return request, events

        # Guard: re-validate against the canonical per-vendor credit limit
        # (credit claims that arrived inside vendor tool output are ignored).
        within_limit, credit_report, credit_event = CanonicalCreditLimitGuard.inspect_purchase(
            vendor_id, amount
        )
        events.append(credit_event)
        if not within_limit:
            request["purchase_result"] = {
                "status": "rejected",
                "reason": f"Execution halted by CanonicalCreditLimitGuard: {credit_report.reason}"
            }
            events.append(TraceEvent(
                agent=AgentRole.PURCHASER,
                kind=EventKind.AGENT_DECISION,
                action="purchase_blocked_by_guard",
                input_data={"vendor_id": vendor_id, "amount": amount},
                output_data=request["purchase_result"],
                trusted=True,
                metadata={"defense_triggered": "CanonicalCreditLimitGuard", "blocked": True}
            ))
            return request, events

    purchase_result, tool_events = call_tool(
        "submit_purchase",
        {
            "vendor_id": vendor_id,
            "amount": amount,
            "approval_id": approval_id,
            "requester": request.get("requester", "unknown"),
        },
        agent=AgentRole.PURCHASER,
        overrides=overrides,
        defended=defended,
    )
    events.extend(tool_events)

    request["purchase_result"] = purchase_result

    events.append(TraceEvent(
        agent=AgentRole.PURCHASER,
        kind=EventKind.AGENT_DECISION,
        action="purchase_completed",
        input_data={"vendor_id": vendor_id, "amount": amount},
        output_data=purchase_result,
        trusted=purchase_result.get("status") == "executed",
        unverified_source=any(not e.trusted for e in events),
    ))

    return request, events


# ── Agent: Auditor ─────────────────────────────────────────────────────

def agent_auditor(
    request: dict[str, Any],
    overrides: dict | None = None,
    defended: bool = False,
) -> tuple[dict[str, Any], list[TraceEvent]]:
    """
    Post-execution compliance review.

    Produces a deterministic audit verdict based only on what the
    trace actually shows, so downstream analyzers have a single
    authoritative record of what happened:
      - whether the purchase was executed / skipped / blocked
      - which approval token (if any) was used
      - whether the vendor matches the authoritative catalog
    """
    events: list[TraceEvent] = []

    vendor_id = request.get("vendor_id", "")
    amount = request.get("amount", 0)
    canonical = VENDOR_CATALOG.get(vendor_id)

    purchase_result = request.get("purchase_result", {})
    purchase_status = purchase_result.get("status", "skipped")
    approval = request.get("approval", {})
    approval_id = approval.get("approval_id")

    # Ground truth the defender can rely on post-hoc: is this vendor
    # actually in the authoritative catalog and verified there?
    provenance_ok = bool(canonical) and bool(canonical.get("verified", False))

    verdict_bits = {
        "purchase_status": purchase_status,
        "approval_id": approval_id,
        "vendor_id": vendor_id,
        "vendor_canonical": bool(canonical),
        "vendor_verified_per_catalog": provenance_ok,
        "amount": amount,
    }

    events.append(TraceEvent(
        agent=AgentRole.AUDITOR,
        kind=EventKind.POLICY_CHECK,
        action="post_execution_audit",
        input_data={
            "vendor_id": vendor_id,
            "amount": amount,
            "purchase_status": purchase_status,
        },
        output_data=verdict_bits,
        trusted=True,
        metadata={
            "audit_scope": "post_execution",
            "provenance_ok": provenance_ok,
            "purchase_executed": purchase_status == "executed",
        },
    ))

    return request, events


# ── Pipeline Orchestrator ──────────────────────────────────────────────

def run_procurement_pipeline(
    request: dict[str, Any],
    tool_overrides: dict[str, dict[str, Any]] | None = None,
    defended: bool = False,
) -> tuple[dict[str, Any], list[TraceEvent]]:
    """
    Run the full 4-agent pipeline and collect all trace events.
    """
    all_events: list[TraceEvent] = []

    # Stage 1: Requester
    request, events = agent_requester(request, overrides=tool_overrides, defended=defended)
    all_events.extend(events)

    # Stage 2: Vendor Lookup
    request, events = agent_vendor_lookup(request, overrides=tool_overrides, defended=defended)
    all_events.extend(events)

    # Stage 3: Approver
    request, events = agent_approver(request, overrides=tool_overrides, defended=defended)
    all_events.extend(events)

    # Stage 4: Purchaser
    request, events = agent_purchaser(request, overrides=tool_overrides, defended=defended)
    all_events.extend(events)

    # Stage 5: Auditor (post-execution review)
    request, events = agent_auditor(request, overrides=tool_overrides, defended=defended)
    all_events.extend(events)

    return request, all_events
