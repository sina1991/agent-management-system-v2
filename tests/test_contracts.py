import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from pydantic import ValidationError
from agent_system.contracts.models import (CONTRACTS, Agent, Approval, Artifact,
                                          Event, Execution, Result, Task, utcnow)
from agent_system.interfaces.cli import main


def task_data(**changes):
    return dict(title="تحلیل پروژه", description="Read source", expected_output="Report",
                acceptance_criteria=["No source modification"],
                verification_spec={"verifier": "manual_review"}, **changes)

class ContractTests(unittest.TestCase):
    def test_task_json_roundtrip_and_schema_version(self):
        task = Task(**task_data())
        self.assertEqual(Task.model_validate_json(task.model_dump_json()), task)
        for name, model in CONTRACTS.items():
            with self.subTest(name=name):
                schema = model.model_json_schema()
                self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        for changes in ({"schema_version": "2.0"}, {"unknown": "field"},
                        {"priority": True}, {"title": " "}, {"revision": -1}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                Task(**(task_data() | changes))

    def test_naive_dates_rejected_and_utc_normalized(self):
        with self.assertRaises(ValidationError):
            Task(**task_data(created_at=datetime(2026, 1, 1)))
        time = datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=3)))
        task = Task(**task_data(created_at=time, updated_at=time))
        self.assertEqual(task.created_at.utcoffset(), timedelta(0))
        with self.assertRaises(ValidationError):
            Task(**task_data(created_at=utcnow(), updated_at=time))

    def test_invalid_dependencies_and_assignment_rejected(self):
        identifier = uuid4()
        for changes in ({"task_id": identifier, "dependency_ids": [identifier]},
                        {"dependency_ids": [identifier, identifier]}, {"status": "RUNNING"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                Task(**task_data(**changes))

    def test_execution_lease_and_attempt(self):
        now = utcnow()
        data = dict(task_id=uuid4(), agent_id=uuid4(), timeout_seconds=30,
                    owner_token=uuid4(), idempotency_key="operation-1")
        for changes in ({"attempt": 0}, {"timeout_seconds": True},
                        {"status": "running"}, {"heartbeat_at": now},
                        {"heartbeat_at": now, "lease_expires_at": now}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                Execution(**(data | changes))
        execution = Execution(**data, status="running", started_at=now, heartbeat_at=now,
                              lease_expires_at=now + timedelta(seconds=30))
        self.assertEqual(execution.attempt, 1)

    def test_artifact_traversal_and_result_consistency(self):
        eid = uuid4()
        data = dict(execution_id=eid, checksum="a" * 64, size_bytes=10)
        for path in ("../secret", "/etc/passwd", "C:/secret", "x/../../secret", "x\\secret", "."):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                Artifact(**data, relative_path=path)
        artifact = Artifact(**data, relative_path="reports/result.json")
        Result(execution_id=eid, status="succeeded", artifacts=[artifact])
        for changes in ({"status": "failed"}, {"retryable": True},
                        {"error_code": "FAIL"}, {"artifacts": [artifact, artifact]},
                        {"execution_id": uuid4(), "artifacts": [artifact]}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                Result(**(dict(execution_id=eid, status="succeeded") | changes))

    def test_agent_permissions_are_closed_vocabulary(self):
        data = dict(name="reader", role="audit", description="Read source", runtime="internal",
                    provider="local", version="1", kind="internal")
        Agent(**data, permissions=["read"])
        with self.assertRaises(ValidationError):
            Agent(**data, permissions=["root"])

    def test_cli_validates_without_echoing_secret_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"task.json"
            path.write_text(json.dumps(task_data()))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["validate", "Task", str(path)]), 0)
            path.write_text(json.dumps(task_data() | {"priority": "SECRET_VALUE"}))
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(main(["validate", "Task", str(path)]), 2)
            self.assertNotIn("SECRET_VALUE", error.getvalue())
            self.assertEqual(json.loads(error.getvalue())["code"], "CONTRACT_INVALID")

    def test_cli_unreadable_and_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"task.json"
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["validate", "Task", str(path)]), 2)
                path.write_text("not JSON")
                self.assertEqual(main(["validate", "Task", str(path)]), 2)
