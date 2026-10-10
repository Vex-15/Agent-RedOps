"""
Remediation Recommender

Maps policy violations to concrete, code-level defenses.
Each defense identifies *where* in the codebase to add a guard,
*what* the guard does, and *why* it breaks the attack path.
"""

from __future__ import annotations
from core.types import (
    PolicyViolation, Defense, ViolationCategory,
)


# ── Defense catalog ────────────────────────────────────────────────────
# Keyed by ViolationCategory.  Each entry is a factory function
# that takes a PolicyViolation and returns a Defense.

def _defense_trust_boundary(v: PolicyViolation) -> Defense:
    return Defense(
        name="Tool Output Validation Layer",
        description=(
            "Add a validation middleware between tool responses and agent "
            "consumption.  Before any agent acts on a tool_result, the "
            "middleware cross-references the result against an authoritative "
            "data source (e.g., the VENDOR_CATALOG dict for vendor lookups)."
        ),
        code_location="agents/pipeline.py — agent_vendor_lookup()",
        fix_description=(
            "After calling vendor_lookup, compare the returned 'verified' "
            "field against VENDOR_CATALOG[vendor_id]['verified'].  If they "
            "disagree, flag the result as untrusted and refuse to forward "
            "it to the approver.\n\n"
            "```python\n"
            "# In agent_vendor_lookup, after tool call:\n"
            "from agents.tools import VENDOR_CATALOG\n"
            "real = VENDOR_CATALOG.get(vendor_id, {})\n"
            "if real and vendor_info.get('verified') != real.get('verified'):\n"
            "    vendor_info['verified'] = real['verified']  # use ground truth\n"
            "    vendor_info['_tamper_detected'] = True\n"
            "```"
        ),
        category=ViolationCategory.TRUST_BOUNDARY,
    )


def _defense_auth_bypass(v: PolicyViolation) -> Defense:
    return Defense(
        name="Approval Ledger Validation",
        description=(
            "The submit_purchase tool must validate the approval_id "
            "against the APPROVAL_LEDGER before executing.  This moves "
            "authorization enforcement from the agent (untrusted) to the "
            "tool (trusted application code)."
        ),
        code_location="agents/tools.py — tool_submit_purchase()",
        fix_description=(
            "Replace tool_submit_purchase with tool_submit_purchase_defended, "
            "which checks APPROVAL_LEDGER[approval_id] exists and matches "
            "the vendor_id and amount.\n\n"
            "```python\n"
            "# In TOOL_REGISTRY:\n"
            "TOOL_REGISTRY = {\n"
            "    ...\n"
            "    'submit_purchase': tool_submit_purchase_defended,  # ← swap\n"
            "}\n"
            "```"
        ),
        category=ViolationCategory.AUTH_BYPASS,
    )


def _defense_deceptive_output(v: PolicyViolation) -> Defense:
    return Defense(
        name="Tool Response Integrity Check",
        description=(
            "Hash or sign tool responses at the source.  Before "
            "consuming a tool result, verify its integrity.  For the "
            "simulated environment, this means cross-checking returned "
            "data against the canonical data store."
        ),
        code_location="agents/tools.py — call_tool()",
        fix_description=(
            "Add a post-call validation step in call_tool() that compares "
            "the result against known ground truth.  If the tool is "
            "vendor_lookup, compare against VENDOR_CATALOG.  If the tool "
            "is check_budget, compare against the hardcoded budget dict.\n\n"
            "```python\n"
            "# In call_tool(), after getting result:\n"
            "if tool_name == 'vendor_lookup':\n"
            "    real = VENDOR_CATALOG.get(args['vendor_id'], {})\n"
            "    if real and result.get('verified') != real.get('verified'):\n"
            "        result['_integrity_failed'] = True\n"
            "        events.append(TraceEvent(\n"
            "            kind=EventKind.ERROR,\n"
            "            action='integrity_check_failed',\n"
            "        ))\n"
            "```"
        ),
        category=ViolationCategory.DECEPTIVE_TOOL_OUTPUT,
    )


def _defense_social_engineering(v: PolicyViolation) -> Defense:
    return Defense(
        name="Vendor Identity-by-ID Enforcement",
        description=(
            "Never use display names for identity decisions.  All "
            "vendor identity checks must use the canonical vendor_id, "
            "not the name field from tool output."
        ),
        code_location="agents/pipeline.py — agent_approver()",
        fix_description=(
            "In agent_approver, validate vendor identity by vendor_id "
            "against the VENDOR_CATALOG, ignoring the 'name' field from "
            "tool output entirely.\n\n"
            "```python\n"
            "# In agent_approver:\n"
            "real_vendor = VENDOR_CATALOG.get(request['vendor_id'])\n"
            "if not real_vendor or not real_vendor.get('verified'):\n"
            "    # Reject — don't trust vendor_info from tool\n"
            "    ...\n"
            "```"
        ),
        category=ViolationCategory.SOCIAL_ENGINEERING,
    )


def _defense_conflicting_instructions(v: PolicyViolation) -> Defense:
    return Defense(
        name="Instruction Precedence Guard",
        description=(
            "Enforce that system policy always outranks any instruction "
            "carried in request metadata or tool output. Fields like "
            "bypass_budget_check or priority_override must be treated as "
            "untrusted data to evaluate (and normally reject), never as "
            "commands to obey."
        ),
        code_location="agents/guards.py — InstructionPrecedenceGuard",
        fix_description=(
            "At every stage where an agent reads request metadata, check "
            "for override keys and refuse to let them disable a policy "
            "check. The guard already exists in the defended pipeline; "
            "this defense makes it mandatory for the insecure path too.\n\n"
            "```python\n"
            "# In agent_approver, before honoring any metadata:\n"
            "if metadata.get('bypass_budget_check') or metadata.get('priority_override'):\n"
            "    # Do NOT skip the budget check — log and enforce policy\n"
            "    ...\n"
            "```"
        ),
        category=ViolationCategory.CONFLICTING_INSTRUCTIONS,
    )


def _defense_credit_limit(v: PolicyViolation) -> Defense:
    return Defense(
        name="Per-Vendor Credit Limit Enforcement",
        description=(
            "Before executing a purchase, re-validate the amount against "
            "the canonical per-vendor credit limit held in the vendor "
            "registry — never against the max_credit value that arrived "
            "inside tool output."
        ),
        code_location="agents/pipeline.py — agent_purchaser()",
        fix_description=(
            "Look up VENDOR_CATALOG[vendor_id]['max_credit'] and reject "
            "the purchase if amount exceeds it, regardless of what any "
            "tool claimed.\n\n"
            "```python\n"
            "# In agent_purchaser, before submit_purchase:\n"
            "from agents.tools import VENDOR_CATALOG\n"
            "max_credit = VENDOR_CATALOG.get(vendor_id, {}).get('max_credit', 0)\n"
            "if amount > max_credit:\n"
            "    request['purchase_result'] = {\n"
            "        'status': 'rejected',\n"
            "        'reason': f'Exceeds canonical vendor credit limit ${max_credit}',\n"
            "    }\n"
            "    ...\n"
            "```"
        ),
        category=ViolationCategory.POLICY_EXCEED_LIMIT,
    )


DEFENSE_FACTORIES = {
    ViolationCategory.TRUST_BOUNDARY: _defense_trust_boundary,
    ViolationCategory.AUTH_BYPASS: _defense_auth_bypass,
    ViolationCategory.DECEPTIVE_TOOL_OUTPUT: _defense_deceptive_output,
    ViolationCategory.SOCIAL_ENGINEERING: _defense_social_engineering,
    ViolationCategory.MISSING_VALIDATION: _defense_trust_boundary,
    ViolationCategory.CONFLICTING_INSTRUCTIONS: _defense_conflicting_instructions,
    ViolationCategory.POLICY_EXCEED_LIMIT: _defense_credit_limit,
}


def recommend_defenses(violations: list[PolicyViolation]) -> list[Defense]:
    """
    Given a set of violations, return recommended defenses.
    Deduplicates by category to avoid redundant recommendations.
    """
    seen_categories: set[ViolationCategory] = set()
    defenses: list[Defense] = []

    for v in violations:
        if v.category not in seen_categories:
            factory = DEFENSE_FACTORIES.get(v.category)
            if factory:
                defenses.append(factory(v))
                seen_categories.add(v.category)

    return defenses
