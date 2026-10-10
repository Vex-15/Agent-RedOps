"""
RedOps Domain Types

Every agent action, tool call, and decision produces a TraceEvent.
A chain of TraceEvents from a malicious input to a policy violation
constitutes an AttackPath. Defenses are code-level guards that break
the attack path at a specific link.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


# ── Enums ──────────────────────────────────────────────────────────────

class AgentRole(str, Enum):
    REQUESTER = "requester"        # initiates purchase requests
    VENDOR_LOOKUP = "vendor_lookup" # resolves vendor details via tool
    APPROVER = "approver"          # decides whether to approve
    PURCHASER = "purchaser"        # executes the purchase


class EventKind(str, Enum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_DECISION = "agent_decision"
    POLICY_CHECK = "policy_check"
    AUTHORIZATION = "authorization"
    ERROR = "error"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ViolationCategory(str, Enum):
    TRUST_BOUNDARY = "trust_boundary"        # agent trusted unverified data
    AUTH_BYPASS = "authorization_bypass"       # purchase without valid approval
    CONFLICTING_INSTRUCTIONS = "conflicting_instructions"
    DECEPTIVE_TOOL_OUTPUT = "deceptive_tool_output"
    MISSING_VALIDATION = "missing_validation"
    SOCIAL_ENGINEERING = "social_engineering"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DefenseVerdict(str, Enum):
    BLOCKED = "blocked"     # defense stopped the attack
    BYPASSED = "bypassed"   # attack still succeeded
    ERROR = "error"


# ── Value Objects ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class TraceEvent:
    """Single atomic event in an agent execution trace."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    agent: AgentRole = AgentRole.REQUESTER
    kind: EventKind = EventKind.AGENT_DECISION
    action: str = ""
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    trusted: bool = True  # was this data from a trusted source?


@dataclass
class PolicyViolation:
    """A specific business-rule violation found in a trace."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: ViolationCategory = ViolationCategory.MISSING_VALIDATION
    severity: Severity = Severity.MEDIUM
    title: str = ""
    description: str = ""
    evidence_event_ids: list[str] = field(default_factory=list)
    root_cause: str = ""


@dataclass
class AttackPath:
    """
    Ordered chain of TraceEvents from the malicious input
    to the policy violation it caused.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    events: list[TraceEvent] = field(default_factory=list)
    violation: PolicyViolation | None = None
    entry_point: str = ""       # which input was malicious
    impact: str = ""            # what happened as a result

    @property
    def length(self) -> int:
        return len(self.events)


@dataclass
class Defense:
    """A code-level guard that breaks an attack path."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    code_location: str = ""         # e.g. "agents/vendor_agent.py:47"
    fix_description: str = ""       # human-readable fix
    category: ViolationCategory = ViolationCategory.MISSING_VALIDATION


@dataclass
class DefenseResult:
    """Result of re-running a scenario with a defense enabled."""
    defense: Defense = field(default_factory=Defense)
    verdict: DefenseVerdict = DefenseVerdict.ERROR
    trace_before: list[TraceEvent] = field(default_factory=list)
    trace_after: list[TraceEvent] = field(default_factory=list)
    violation_before: PolicyViolation | None = None
    violation_after: PolicyViolation | None = None
    explanation: str = ""


@dataclass
class PipelineResult:
    """Full output of a single scenario run through the pipeline."""
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    scenario_name: str = ""
    status: RunStatus = RunStatus.PENDING
    trace: list[TraceEvent] = field(default_factory=list)
    violations: list[PolicyViolation] = field(default_factory=list)
    attack_paths: list[AttackPath] = field(default_factory=list)
    defenses: list[DefenseResult] = field(default_factory=list)
    latency_ms: int = 0
    started_at: str = ""
    finished_at: str = ""
