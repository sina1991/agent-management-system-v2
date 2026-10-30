import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from agent_system.application.workflow import run_task
from agent_system.contracts.models import Agent, Task
from agent_system.domain.types import TaskStatus
from agent_system.infrastructure.database.store import Store
from agent_system.infrastructure.registry import AgentRegistry, RegistryError

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name)/"target"/"system.db")
        self.store.initialize()
        self.agent = Agent(name="echo", role="worker", description="deterministic echo",
                           capabilities=("task.execute",), runtime="python-worker",
                           provider="text.echo", version="1", kind="internal")
        AgentRegistry(self.store).register(self.agent)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def task(self, expected):
        task = Task(title="echo", description="echo input", input={"value":"hello"},
                    expected_output="same value", acceptance_criteria=("output equals expected",),
                    verification_spec={"verifier":"json_equals", "parameters":{"expected":expected}})
        self.store.create_task(task)
        return task

    def test_success_completes_and_records_trace(self):
        task = self.task({"value":"hello"})
        result = run_task(self.store, task.task_id)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(result["verified"])
        self.assertEqual(self.store.get_task(task.task_id).assigned_agent, self.agent.agent_id)
        self.assertEqual(self.store.get_task(task.task_id).revision, 7)
        self.assertGreaterEqual(len(self.store.history(task.task_id)), 8)

    def test_failed_verification_does_not_mark_task_complete(self):
        task = self.task({"value":"different"})
        result = run_task(self.store, task.task_id)
        self.assertEqual(result["status"], "CHANGES_REQUESTED")
        self.assertFalse(result["verified"])

    def test_no_agent_and_duplicate_name_fail_closed(self):
        task = self.task({"value":"hello"})
        registry = AgentRegistry(self.store)
        with self.assertRaises(RegistryError):
            registry.register(self.agent)
        second = Agent(name="math", role="worker", description="sum",
                       capabilities=("math.sum",), runtime="python-worker",
                       provider="math.sum", version="1", kind="internal")
        registry.register(second)
        # The task capability has no matching sum Agent after disabling echo.
        records = self.store.get_config(registry.KEY)
        records[0]["status"] = "disabled"
        self.store.set_config(registry.KEY, records)
        with self.assertRaises(RegistryError):
            run_task(self.store, task.task_id)
        self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.CREATED)
