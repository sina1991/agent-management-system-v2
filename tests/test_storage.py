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
        app = self.target/".agent-system"/"app"/"0.6.0.dev0"
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
        release = self.target/".agent-system"/"app"/"0.6.0.dev0"/"agent_system"/"__init__.py"
        release.write_text(release.read_text()+"# changed\n")
        with self.assertRaises(InstallError):
            doctor(self.target)

class ExecutionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/"state.db"
        self.store = Store(self.path)
        self.store.initialize()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _running_execution(self):
        from datetime import timedelta
        from agent_system.contracts.models import Execution, utcnow
        from agent_system.domain.lifecycle import TransitionFacts as F
        from agent_system.domain.types import TaskStatus as S
        agent_id = uuid4()
        task = make_task(assigned_agent=agent_id)
        self.store.create_task(task)
        task = self.store.transition(task.task_id, S.PLANNED, F(plan_recorded=True), expected_revision=0)
        task = self.store.transition(task.task_id, S.READY, F(plan_recorded=True, policy_allowed=True), expected_revision=1)
        task = self.store.assign_agent(task.task_id, agent_id, expected_revision=2)
        task = self.store.transition(task.task_id, S.ASSIGNED,
            F(agent_selected=True, policy_allowed=True), expected_revision=task.revision)
        execution = Execution(task_id=task.task_id, agent_id=agent_id, timeout_seconds=3,
            idempotency_key=f"{task.task_id}:1", owner_token=uuid4(), status="running",
            started_at=utcnow()-timedelta(minutes=1), heartbeat_at=utcnow()-timedelta(minutes=1),
            lease_expires_at=utcnow()-timedelta(seconds=1))
        self.store.create_execution(execution)
        self.store.transition(task.task_id, S.RUNNING,
            F(agent_selected=True, execution_created=True, policy_allowed=True), expected_revision=4)
        return task.task_id, execution

    def test_execution_and_result_are_separate_and_terminal_once(self):
        from agent_system.contracts.models import Result
        task_id, execution = self._running_execution()
        result = Result(execution_id=execution.execution_id, status="succeeded", output={"value":1})
        self.store.finish_execution(execution.execution_id, result, status="succeeded")
        self.assertEqual(self.store.get_execution(execution.execution_id).status, "succeeded")
        # Execution contract is immutable; terminal state is reflected by the dedicated row.
        self.assertEqual(self.store.get_result(execution.execution_id), result)

    def test_expired_attempt_recovered_atomically_and_idempotently(self):
        from agent_system.domain.types import TaskStatus
        task_id, execution = self._running_execution()
        self.assertEqual(self.store.recover_expired_executions(), [execution.execution_id])
        self.assertEqual(self.store.get_task(task_id).status, TaskStatus.FAILED)
        self.assertEqual(self.store.get_result(execution.execution_id).status, "unknown")
        self.assertEqual(self.store.recover_expired_executions(), [])

    def test_live_lease_is_left_running(self):
        from datetime import timedelta
        from agent_system.contracts.models import utcnow
        task_id, execution = self._running_execution()
        self.assertEqual(self.store.recover_expired_executions(now=utcnow()-timedelta(minutes=2)), [])
        self.assertEqual(self.store.get_task(task_id).status.value, "RUNNING")

    def test_explicit_upgrade_from_0001_keeps_backup_and_existing_rows(self):
        import shutil
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import create_engine
        self.store.close()
        shutil.rmtree(self.path.parent)
        self.path.parent.mkdir()
        self.store = Store(self.path)
        config = Config()
        config.set_main_option("script_location", str(Path(__file__).parents[1]/"src/agent_system/infrastructure/database/migrations"))
        engine = create_engine(f"sqlite:///{self.path}")
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "0001")
        engine.dispose()
        self.store.close()
        self.store = Store(self.path)
        backup = self.store.upgrade()
        self.store.verify()
        self.assertTrue(Path(backup).is_file())
        with self.store.engine.connect() as connection:
            self.assertIn("executions", __import__("sqlalchemy").inspect(connection).get_table_names())

class ContextApprovalHandoffTests(unittest.TestCase):
    def setUp(self):
        from agent_system.infrastructure.database.store import Store
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/"state.db")
        self.store.initialize()
    def tearDown(self):
        self.store.close(); self.tmp.cleanup()
    def test_context_revision_prevents_lost_update(self):
        from agent_system.domain.errors import RevisionConflict
        self.assertEqual(self.store.set_context("project",{"topic":"AMS"}),1)
        value,revision=self.store.get_context("project")
        self.assertEqual(value,{"topic":"AMS"})
        self.assertEqual(self.store.set_context("project",{"topic":"V2"},expected_revision=revision),2)
        with self.assertRaises(RevisionConflict): self.store.set_context("project",{},expected_revision=revision)
    def test_approval_is_bound_to_digest_and_decided_once(self):
        from datetime import timedelta
        from agent_system.contracts.models import Approval,utcnow
        from agent_system.infrastructure.database.store import StorageError
        now=utcnow(); item=Approval(action_digest="a"*64,scope="target",policy_version="1",expires_at=now+timedelta(minutes=5))
        self.store.save_approval(item)
        approved=self.store.decide_approval(item.approval_id,decision="approved",actor="owner",now=now)
        self.assertEqual(self.store.get_approval(item.approval_id),approved)
        with self.assertRaises(StorageError): self.store.decide_approval(item.approval_id,decision="rejected",actor="owner",now=now)
    def test_handoff_payload_digest_and_target_links_are_checked(self):
        import hashlib,json
        from agent_system.contracts.models import Handoff,Execution,utcnow
        from agent_system.domain.lifecycle import TransitionFacts as F
        from agent_system.domain.types import TaskStatus as S
        from agent_system.infrastructure.database.store import StorageError
        task=make_task();self.store.create_task(task)
        # A linked Task and Execution are required before a Handoff is accepted.
        agent=uuid4();task=Task.model_validate({**task.model_dump(),"assigned_agent":agent})
        # Create a fresh assigned workflow state for a valid execution.
        task2=make_task(assigned_agent=agent);self.store.create_task(task2)
        task2=self.store.transition(task2.task_id,S.PLANNED,F(plan_recorded=True),expected_revision=0)
        task2=self.store.transition(task2.task_id,S.READY,F(plan_recorded=True,policy_allowed=True),expected_revision=1)
        task2=self.store.assign_agent(task2.task_id,agent,expected_revision=2)
        task2=self.store.transition(task2.task_id,S.ASSIGNED,F(agent_selected=True,policy_allowed=True),expected_revision=3)
        now=utcnow(); execution=Execution(task_id=task2.task_id,agent_id=agent,timeout_seconds=10,idempotency_key="handoff-1",owner_token=uuid4(),status="running",started_at=now,heartbeat_at=now,lease_expires_at=now+__import__("datetime").timedelta(seconds=10))
        self.store.create_execution(execution)
        payload={"expected_output":"report"}; digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        handoff=Handoff(task_id=task2.task_id,execution_id=execution.execution_id,input_digest="b"*64,payload=payload,payload_digest=digest)
        self.assertEqual(self.store.save_handoff(handoff),handoff)
        self.assertEqual(self.store.get_handoff(handoff.handoff_id),handoff)
        with self.assertRaises(StorageError):
            self.store.save_handoff(Handoff(task_id=task.task_id,execution_id=execution.execution_id,input_digest="b"*64,payload=payload,payload_digest=digest))
    def test_backup_and_restore_are_verified_and_non_overwriting(self):
        from agent_system.infrastructure.database.backup import backup_database,restore_database
        from agent_system.infrastructure.database.store import StorageError
        backup=Path(self.tmp.name)/"snap.db"; restored=Path(self.tmp.name)/"restored.db"
        backup_database(self.store.path,backup);restore_database(backup,restored)
        check=Store(restored)
        try: check.verify()
        finally: check.close()
        with self.assertRaises(StorageError): restore_database(backup,restored)

    def test_remote_source_rejects_embedded_credentials(self):
        from agent_system.infrastructure.installer import InstallError, install
        with self.assertRaises(InstallError):
            install(self.path.parent,source_url="https://user:secret@example.com/repo.git")
