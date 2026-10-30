import unittest
from dataclasses import replace
from uuid import uuid4
from agent_system.application.tasks import transition_task
from agent_system.contracts.models import Task
from agent_system.domain.dependencies import dependencies_complete, validate_graph
from agent_system.domain.errors import (DependencyError, GuardRejected,
                                        InvalidTransition, RevisionConflict)
from agent_system.domain.lifecycle import TransitionFacts as F, check_transition
from agent_system.domain.types import TaskStatus as S

class LifecycleTests(unittest.TestCase):
    def test_complete_lifecycle_increments_revision_and_emits_event(self):
        task = Task(title="Audit", description="Read", expected_output="Report",
                    acceptance_criteria=["Reviewed"], assigned_agent=uuid4(),
                    verification_spec={"verifier": "manual"})
        facts = F(plan_recorded=True, dependencies_completed=True, policy_allowed=True,
                  agent_selected=True, execution_created=True, execution_stopped=True,
                  result_recorded=True, verification_passed=True)
        for target in (S.PLANNED, S.READY, S.ASSIGNED, S.RUNNING, S.REVIEW, S.COMPLETED):
            previous = task
            task, event = transition_task(task, target, facts, expected_revision=task.revision)
            self.assertEqual(task.revision, previous.revision + 1)
            self.assertEqual(event.payload["from"], previous.status)
            self.assertEqual(event.payload["to"], target)
            self.assertEqual(event.correlation_id, task.task_id)
            self.assertEqual(event.occurred_at, task.updated_at)
            self.assertNotEqual(previous.status, target)

    def test_cannot_skip_review_or_reopen_terminal_task(self):
        for source, target in ((S.CREATED, S.RUNNING), (S.RUNNING, S.COMPLETED),
                               (S.COMPLETED, S.READY), (S.CANCELLED, S.PLANNED)):
            with self.subTest(source=source, target=target), self.assertRaises(InvalidTransition):
                check_transition(source, target, F(), revision=0, expected_revision=0)

    def test_success_claim_is_insufficient_to_complete(self):
        facts = F(result_recorded=True, dependencies_completed=True, policy_allowed=True)
        with self.assertRaises(GuardRejected):
            check_transition(S.REVIEW, S.COMPLETED, facts, revision=0, expected_revision=0)

    def test_stale_revision_rejected(self):
        with self.assertRaises(RevisionConflict):
            check_transition(S.CREATED, S.PLANNED, F(plan_recorded=True), revision=2, expected_revision=1)

    def test_running_cancellation_requires_confirmed_stop(self):
        with self.assertRaises(GuardRejected):
            check_transition(S.RUNNING, S.CANCELLED, F(), revision=0, expected_revision=0)
        check_transition(S.RUNNING, S.CANCELLED, F(execution_stopped=True), revision=0, expected_revision=0)

    def test_retry_requires_budget(self):
        with self.assertRaises(GuardRejected):
            check_transition(S.FAILED, S.PLANNED, F(plan_recorded=True), revision=0, expected_revision=0)
        check_transition(S.FAILED, S.PLANNED, F(plan_recorded=True, retry_available=True), revision=0, expected_revision=0)

    def test_approval_requires_checkpoint_and_recorded_return(self):
        facts = F(reason="publish", execution_stopped=True, approval_return_status=S.REVIEW)
        with self.assertRaises(GuardRejected):
            check_transition(S.RUNNING, S.WAITING_FOR_APPROVAL, facts, revision=0, expected_revision=0)
        check_transition(S.RUNNING, S.WAITING_FOR_APPROVAL, replace(facts, checkpoint_reached=True), revision=0, expected_revision=0)
        resume = F(result_recorded=True, policy_allowed=True, approval_granted=True, approval_return_status=S.READY)
        with self.assertRaises(GuardRejected):
            check_transition(S.WAITING_FOR_APPROVAL, S.REVIEW, resume, revision=0, expected_revision=0)

    def test_dependency_graph_rejects_unknown_cycles_and_duplicates(self):
        a, b, c = uuid4(), uuid4(), uuid4()
        validate_graph({a: (), b: (a,), c: (a, b)})
        for graph in ({a: (b,)}, {a: (b,), b: (a,)}, {a: (a,)}, {a: (), b: (a, a)}):
            with self.subTest(graph=graph), self.assertRaises(DependencyError):
                validate_graph(graph)
        self.assertFalse(dependencies_complete([a], {a: S.FAILED}))
        self.assertTrue(dependencies_complete([a], {a: S.COMPLETED}))
        with self.assertRaises(DependencyError):
            dependencies_complete([b], {a: S.COMPLETED})
