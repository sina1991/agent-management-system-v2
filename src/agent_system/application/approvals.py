from datetime import datetime
from agent_system.contracts.models import Approval


def approval_valid(approval: Approval, *, action_digest: str, scope: str,
                   policy_version: str, now: datetime) -> bool:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include timezone")
    return (approval.decision == "approved" and approval.action_digest == action_digest
            and approval.scope == scope and approval.policy_version == policy_version
            and approval.decided_at is not None and approval.decided_at <= now < approval.expires_at)
