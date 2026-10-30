"""Initial deny-first permission policy; it never executes operations."""
from collections.abc import Set
from agent_system.domain.types import Decision, Permission


def evaluate_permissions(required: Set[Permission], granted: Set[Permission], *,
                         in_scope: bool, enforceable: bool, sensitive: bool,
                         approval_valid: bool = False) -> Decision:
    if not in_scope or not enforceable or not required.issubset(granted):
        return Decision.DENY
    if sensitive and not approval_valid:
        return Decision.APPROVAL_REQUIRED
    return Decision.ALLOW
