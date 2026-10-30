"""Pure transition guards. Trusted services supply facts; this is not a runtime."""
from dataclasses import dataclass
from types import MappingProxyType

from agent_system.domain.errors import GuardRejected, InvalidTransition, RevisionConflict
from agent_system.domain.types import TaskStatus as S

TRANSITIONS = MappingProxyType({
    S.CREATED: frozenset({S.PLANNED, S.CANCELLED}),
    S.PLANNED: frozenset({S.READY, S.BLOCKED, S.CANCELLED}),
    S.READY: frozenset({S.ASSIGNED, S.BLOCKED, S.WAITING_FOR_APPROVAL, S.CANCELLED}),
    S.ASSIGNED: frozenset({S.RUNNING, S.READY, S.WAITING_FOR_APPROVAL, S.CANCELLED}),
    S.RUNNING: frozenset({S.REVIEW, S.FAILED, S.BLOCKED, S.WAITING_FOR_APPROVAL, S.CANCELLED}),
    S.REVIEW: frozenset({S.COMPLETED, S.CHANGES_REQUESTED, S.FAILED, S.WAITING_FOR_APPROVAL, S.CANCELLED}),
    S.CHANGES_REQUESTED: frozenset({S.PLANNED, S.CANCELLED}),
    S.BLOCKED: frozenset({S.PLANNED, S.READY, S.CANCELLED}),
    S.WAITING_FOR_APPROVAL: frozenset({S.PLANNED, S.READY, S.REVIEW, S.BLOCKED, S.CANCELLED}),
    S.FAILED: frozenset({S.PLANNED, S.CANCELLED}),
    S.COMPLETED: frozenset(),
    S.CANCELLED: frozenset(),
})

@dataclass(frozen=True)
class TransitionFacts:
    plan_recorded: bool = False
    dependencies_completed: bool = False
    policy_allowed: bool = False
    agent_selected: bool = False
    execution_created: bool = False
    execution_stopped: bool = False
    result_recorded: bool = False
    verification_passed: bool = False
    retry_available: bool = False
    reason: str = ""
    approval_granted: bool = False
    approval_return_status: S | None = None
    checkpoint_reached: bool = False


def check_transition(current: S, target: S, facts: TransitionFacts,
                     *, revision: int, expected_revision: int) -> None:
    if revision != expected_revision:
        raise RevisionConflict("task revision changed")
    if target not in TRANSITIONS[current]:
        raise InvalidTransition(f"{current} -> {target} is not allowed")
    def require(condition: bool, message: str):
        if not condition:
            raise GuardRejected(message)
    if target == S.CANCELLED:
        if current in {S.RUNNING, S.WAITING_FOR_APPROVAL}:
            require(facts.execution_stopped, "execution must be confirmed stopped")
        return
    if target in {S.BLOCKED, S.FAILED, S.CHANGES_REQUESTED, S.WAITING_FOR_APPROVAL}:
        require(bool(facts.reason.strip()), "a reason is required")
    if current == S.RUNNING:
        require(facts.execution_stopped, "execution must be stopped before leaving RUNNING")
    if current == S.FAILED and target == S.PLANNED:
        require(facts.retry_available, "retry budget unavailable")
    if target == S.PLANNED:
        require(facts.plan_recorded, "plan must be recorded")
    if target in {S.READY, S.ASSIGNED, S.RUNNING, S.COMPLETED}:
        require(facts.policy_allowed, "policy must allow action")
        require(facts.dependencies_completed, "dependencies must be complete")
    if target == S.READY:
        require(facts.plan_recorded, "plan must be recorded")
    if target == S.ASSIGNED:
        require(facts.agent_selected, "agent must be selected")
    if target == S.RUNNING:
        require(facts.agent_selected and facts.execution_created, "execution and agent required")
    if target == S.REVIEW:
        require(facts.result_recorded, "result must be recorded")
    if target == S.COMPLETED:
        require(facts.result_recorded and facts.verification_passed, "verified result required")
    if target == S.WAITING_FOR_APPROVAL:
        require(facts.approval_return_status in {S.PLANNED, S.READY, S.REVIEW}, "valid approval return status required")
        if current == S.RUNNING:
            require(facts.checkpoint_reached, "approval requires a checkpoint")
    if current == S.WAITING_FOR_APPROVAL and target in {S.PLANNED, S.READY, S.REVIEW}:
        require(facts.approval_granted and facts.policy_allowed, "valid approval and policy required")
        require(target == facts.approval_return_status, "approval return target mismatch")
