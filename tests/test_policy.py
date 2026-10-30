import unittest
from datetime import timedelta
from agent_system.application.approvals import approval_valid
from agent_system.contracts.models import Approval, utcnow
from agent_system.domain.policy import evaluate_permissions
from agent_system.domain.types import Decision as D, Permission as P
from pydantic import ValidationError

class PolicyTests(unittest.TestCase):
    def test_deny_takes_precedence_over_approval(self):
        for granted, in_scope, enforceable in (({P.READ}, True, True),
                                               ({P.WRITE}, False, True),
                                               ({P.WRITE}, True, False)):
            self.assertEqual(evaluate_permissions({P.WRITE}, granted, in_scope=in_scope,
                             enforceable=enforceable, sensitive=True, approval_valid=True), D.DENY)
        self.assertEqual(evaluate_permissions({P.READ}, {P.READ}, in_scope=True,
                         enforceable=True, sensitive=False), D.ALLOW)
        self.assertEqual(evaluate_permissions({P.WRITE}, {P.WRITE}, in_scope=True,
                         enforceable=True, sensitive=True), D.APPROVAL_REQUIRED)

    def test_approval_matches_exact_action_scope_policy_and_time(self):
        now = utcnow()
        approval = Approval(action_digest="a" * 64, scope="target-1", policy_version="1",
                            expires_at=now + timedelta(minutes=5), decision="approved",
                            decided_by="owner", decided_at=now)
        args = dict(action_digest="a" * 64, scope="target-1", policy_version="1", now=now)
        self.assertTrue(approval_valid(approval, **args))
        for changes in ({"action_digest": "b" * 64}, {"scope": "target-2"},
                        {"policy_version": "2"}, {"now": approval.expires_at},
                        {"now": now - timedelta(seconds=1)}):
            self.assertFalse(approval_valid(approval, **(args | changes)))
        with self.assertRaises(ValidationError):
            Approval(action_digest="a" * 64, scope="target-1", policy_version="1",
                     expires_at=now, decision="approved")
