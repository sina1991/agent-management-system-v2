import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import text
from agent_system.contracts.models import Task
from agent_system.domain.errors import DependencyError, GuardRejected, RevisionConflict
from agent_system.domain.lifecycle import TransitionFacts as F
from agent_system.domain.types import TaskStatus as S
from agent_system.infrastructure.database.store import Store, StorageError


def make_task(**changes):
    return Task(**(dict(title="Audit", description="Read", expected_output="Report",
                       acceptance_criteria=["Reviewed"], verification_spec={"verifier": "manual"}) | changes))

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/"state"/"system.db"
        self.store = Store(self.path)
        self.store.initialize()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_restart_reinitialize_preserves_tasks_events_and_configuration(self):
        task = make_task()
        self.store.create_task(task)
        self.store.set_config("context", {"project": "test"})
        self.store.close()
        self.store = Store(self.path)
        self.store.initialize()
        self.store.verify()
        self.assertEqual(self.store.get_task(task.task_id), task)
        self.assertEqual(len(self.store.history(task.task_id)), 1)
        self.assertEqual(self.store.get_config("context"), {"project": "test"})

    def test_event_write_failure_rolls_back_task_change(self):
        task = make_task()
        self.store.create_task(task)
        with patch.object(self.store, "_append_event", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                self.store.transition(task.task_id, S.PLANNED, F(plan_recorded=True), expected_revision=0)
        self.assertEqual(self.store.get_task(task.task_id).status, S.CREATED)
        self.assertEqual(len(self.store.history(task.task_id)), 1)

    def test_stale_writer_cannot_overwrite_or_append_event(self):
        task = make_task()
        self.store.create_task(task)
        other = Store(self.path)
        try:
            stale = other.get_task(task.task_id)
            self.store.transition(task.task_id, S.PLANNED, F(plan_recorded=True), expected_revision=0)
            with self.assertRaises(RevisionConflict):
                other.transition(task.task_id, S.CANCELLED, F(), expected_revision=stale.revision)
        finally:
            other.close()
        self.assertEqual(len(self.store.history(task.task_id)), 2)

    def test_persisted_dependencies_override_caller_claim(self):
        parent = make_task()
        self.store.create_task(parent)
        child = make_task(dependency_ids=[parent.task_id])
        self.store.create_task(child)
        self.store.transition(child.task_id, S.PLANNED, F(plan_recorded=True), expected_revision=0)
        with self.assertRaises(GuardRejected):
            self.store.transition(child.task_id, S.READY, F(plan_recorded=True, dependencies_completed=True,
                                                          policy_allowed=True), expected_revision=1)
        with self.assertRaises(DependencyError):
            self.store.create_task(make_task(dependency_ids=[uuid4()]))

    def test_separate_targets_do_not_share_state(self):
        task = make_task()
        self.store.create_task(task)
        other = Store(Path(self.tmp.name)/"other"/"system.db")
        try:
            other.initialize()
            with self.assertRaises(KeyError):
                other.get_task(task.task_id)
        finally:
            other.close()

    def test_unknown_schema_not_silently_upgraded(self):
        with self.store.engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='9999'"))
        with self.assertRaises(StorageError):
            self.store.initialize()
        with self.assertRaises(StorageError):
            self.store.verify()

    def test_failed_initialization_can_be_retried(self):
        fresh = Store(Path(self.tmp.name)/"fresh.db")
        try:
            with patch.object(fresh, "_verify_connection", side_effect=StorageError("failed")):
                with self.assertRaises(StorageError):
                    fresh.initialize()
            fresh.initialize()
            fresh.verify()
        finally:
            fresh.close()

    def test_cli_create_show_and_history_persisted(self):
        import contextlib
        import io
        import json
        from agent_system.interfaces.cli import main
        task = make_task()
        payload = Path(self.tmp.name)/"task.json"
        payload.write_text(task.model_dump_json())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["task", "create", str(self.path), str(payload)]), 0)
        for command in ("show", "history"):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["task", command, str(self.path), str(task.task_id)]), 0)
            data = json.loads(output.getvalue())
            self.assertTrue(data)
        missing = Path(self.tmp.name)/"missing.db"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["db", "verify", str(missing)]), 2)
        self.assertFalse(missing.exists())

class InstallerTests(unittest.TestCase):
    def setUp(self):
        import os
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)/"target"
        self.target.mkdir()
        (self.target/".git").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_then_doctor_and_existing_install_preserves_state(self):
        import json
        import contextlib
        import io
        from agent_system.infrastructure.installer import doctor, install
        result = install(self.target)
        self.assertEqual(result["status"], "verified")
        self.assertGreater(result["file_count"], 10)
        app = self.target/".agent-system"/"app"/"0.2.0.dev0"
        self.assertTrue((app/"agent_system"/"infrastructure"/"database"/"migrations"/"versions"/"0001_initial.py").is_file())
        self.assertEqual(doctor(self.target)["database"], "verified")
        store = Store(self.target/".agent-system"/"state"/"system.db")
        task = make_task()
        store.create_task(task)
        store.close()
        second = install(self.target)
        self.assertEqual(second["status"], "existing")
        self.assertEqual(second["installation_id"], result["installation_id"])
        store = Store(self.target/".agent-system"/"state"/"system.db")
        self.assertEqual(store.get_task(task.task_id), task)
        store.close()

    def test_target_requirements_and_preexisting_content_are_protected(self):
        from agent_system.infrastructure.installer import InstallError, install
        with self.assertRaises(InstallError):
            install(self.target/"missing")
        other = Path(self.tmp.name)/"not-git"
        other.mkdir()
        with self.assertRaises(InstallError):
            install(other)
        reserved = self.target/".agent-system"
        reserved.mkdir()
        marker = reserved/"keep.txt"
        marker.write_text("user data")
        with self.assertRaises(InstallError):
            install(self.target)
        self.assertEqual(marker.read_text(), "user data")

    def test_doctor_detects_release_tampering_and_missing_db(self):
        from agent_system.infrastructure.installer import InstallError, doctor, install
        install(self.target)
        release = self.target/".agent-system"/"app"/"0.2.0.dev0"/"agent_system"/"__init__.py"
        release.write_text(release.read_text()+"# changed\n")
        with self.assertRaises(InstallError):
            doctor(self.target)
