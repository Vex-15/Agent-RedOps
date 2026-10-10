"""
Simulated Procurement Tools

These are the "tools" the agents call.  In a real system these would hit
vendor APIs, ERP databases, etc.  Here they are pure-Python stubs that
return deterministic data — *unless* a scenario has injected a deceptive
override via the tool_overrides dict.

The key design point: tools are *untrusted* I/O boundaries.  The agents
must never blindly trust what a tool returns.
"""

from __future__ import annotations
from core.types import TraceEvent, EventKind, AgentRole
from typing import Any


# ── Honest tool implementations ───────────────────────────────────────

VENDOR_CATALOG: dict[str, dict[str, Any]] = {
    "acme_supplies": {
        "name": "Acme Office Supplies",
        "verified": True,
        "max_credit": 5000,
        "categories": ["office", "furniture"],
    },
    "shady_imports": {
        "name": "Shady Imports LLC",
        "verified": False,
        "max_credit": 500,
        "categories": ["electronics"],
    },
    "globex_corp": {
        "name": "Globex Corporation",
        "verified": True,
        "max_credit": 25000,
        "categories": ["office", "IT", "furniture"],
    },
}

APPROVAL_LEDGER: dict[str, dict[str, Any]] = {
    # approval_id → details.  Starts empty; populated by the approver agent.
}


def tool_vendor_lookup(vendor_id: str) -> dict[str, Any]:
    """Look up vendor details from the catalog."""
    if vendor_id in VENDOR_CATALOG:
        return {"found": True, **VENDOR_CATALOG[vendor_id]}
    return {"found": False, "error": f"Vendor '{vendor_id}' not in catalog"}


def tool_check_budget(department: str, amount: float) -> dict[str, Any]:
    """Check whether a department has budget for the requested amount."""
    # Simulated budgets
    budgets = {
        "engineering": 50000,
        "marketing": 20000,
        "operations": 35000,
        "hr": 10000,
    }
    available = budgets.get(department, 0)
    return {
        "department": department,
        "requested": amount,
        "available": available,
        "sufficient": available >= amount,
    }


def tool_submit_purchase(
    vendor_id: str,
    amount: float,
    approval_id: str | None,
    requester: str,
) -> dict[str, Any]:
    """
    Execute a purchase.  This is the critical trust boundary:
    the tool itself must validate the approval_id against the ledger.
    """
    # ── This is the INSECURE version (no validation) ──
    # A defended version adds the check shown in the defense module.
    return {
        "status": "executed",
        "vendor_id": vendor_id,
        "amount": amount,
        "approval_id": approval_id,
        "requester": requester,
        "transaction_id": "TXN-" + vendor_id[:4].upper() + "-001",
    }


def tool_submit_purchase_defended(
    vendor_id: str,
    amount: float,
    approval_id: str | None,
    requester: str,
) -> dict[str, Any]:
    """
    DEFENDED version of submit_purchase.
    Validates approval_id against the authoritative ledger
    before executing.
    """
    if not approval_id or approval_id not in APPROVAL_LEDGER:
        return {
            "status": "rejected",
            "reason": "Invalid or missing approval_id — not found in approval ledger",
            "vendor_id": vendor_id,
            "amount": amount,
        }

    record = APPROVAL_LEDGER[approval_id]
    if record.get("vendor_id") != vendor_id:
        return {
            "status": "rejected",
            "reason": f"Approval {approval_id} is for vendor '{record.get('vendor_id')}', not '{vendor_id}'",
        }
    if record.get("amount") < amount:
        return {
            "status": "rejected",
            "reason": f"Approval {approval_id} covers ${record.get('amount')}, but ${amount} was requested",
        }

    return {
        "status": "executed",
        "vendor_id": vendor_id,
        "amount": amount,
        "approval_id": approval_id,
        "requester": requester,
        "transaction_id": "TXN-" + vendor_id[:4].upper() + "-002",
    }


# ── Tool registry ────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, callable] = {
    "vendor_lookup": tool_vendor_lookup,
    "check_budget": tool_check_budget,
    "submit_purchase": tool_submit_purchase,
}

DEFENDED_TOOL_REGISTRY: dict[str, callable] = {
    "vendor_lookup": tool_vendor_lookup,
    "check_budget": tool_check_budget,
    "submit_purchase": tool_submit_purchase_defended,
}


def call_tool(
    tool_name: str,
    args: dict[str, Any],
    agent: AgentRole,
    overrides: dict[str, dict[str, Any]] | None = None,
    defended: bool = False,
) -> tuple[dict[str, Any], list[TraceEvent]]:
    """
    Call a tool by name, returning (result, trace_events).
    If `overrides` contains a key matching tool_name, the override
    value is returned instead — simulating a deceptive tool response.
    """
    events: list[TraceEvent] = []

    # Record the call
    events.append(TraceEvent(
        agent=agent,
        kind=EventKind.TOOL_CALL,
        action=tool_name,
        input_data=args,
        trusted=True,
    ))

    # Check for scenario-injected deceptive override
    if overrides and tool_name in overrides:
        result = overrides[tool_name]
        events.append(TraceEvent(
            agent=agent,
            kind=EventKind.TOOL_RESULT,
            action=tool_name,
            output_data=result,
            trusted=False,  # ← this came from an untrusted override
            metadata={"injected": True, "source": "scenario_override"},
        ))
        return result, events

    # Normal execution
    registry = DEFENDED_TOOL_REGISTRY if defended else TOOL_REGISTRY
    fn = registry.get(tool_name)
    if not fn:
        error = {"error": f"Unknown tool: {tool_name}"}
        events.append(TraceEvent(
            agent=agent,
            kind=EventKind.ERROR,
            action=tool_name,
            output_data=error,
        ))
        return error, events

    result = fn(**args)
    events.append(TraceEvent(
        agent=agent,
        kind=EventKind.TOOL_RESULT,
        action=tool_name,
        output_data=result,
        trusted=True,
    ))
    return result, events
