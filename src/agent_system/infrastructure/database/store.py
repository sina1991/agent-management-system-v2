"""Transactional SQLite storage for tasks, events and shared configuration."""
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, event, inspect, select, update
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError

from agent_system.application.tasks import transition_task
from agent_system.contracts.models import Approval, Event, Execution, Handoff, Result, Task
from agent_system.domain.dependencies import validate_graph
from agent_system.domain.errors import DomainError, RevisionConflict
from agent_system.domain.lifecycle import TransitionFacts
from agent_system.domain.types import TaskStatus
from agent_system.infrastructure.database.schema import approvals, configuration, context, events, executions, handoffs, results, tasks

SCHEMA_REVISION = "0003"


class StorageError(DomainError):
    code = "STORAGE_INVALID"


class Store:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.engine = create_engine(URL.create("sqlite", database=str(self.path)))
        @event.listens_for(self.engine, "connect")
        def sqlite_options(connection, _):
            # Disable sqlite legacy transaction control so DDL participates in rollback.
            connection.isolation_level = None
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
        @event.listens_for(self.engine, "begin")
        def explicit_begin(connection):
            connection.exec_driver_sql("BEGIN")

    def close(self):
        self.engine.dispose()

    def initialize(self):
        """Explicitly initialize a clean DB; never auto-upgrade an existing schema."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.engine.begin() as connection:
            tables = set(inspect(connection).get_table_names())
            if tables:
                self._verify_connection(connection)
                return
            config = Config()
            config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            self._verify_connection(connection)

    @staticmethod
    def _verify_connection(connection):
        if MigrationContext.configure(connection).get_current_revision() != SCHEMA_REVISION:
            raise StorageError("unknown or incompatible schema revision")
        required = {"tasks", "events", "configuration", "alembic_version"}
        if not required.issubset(inspect(connection).get_table_names()):
            raise StorageError("required tables missing")
        for table in (tasks, events, configuration, executions, results, approvals, handoffs, context):
            columns = {column["name"] for column in inspect(connection).get_columns(table.name)}
            if not set(table.columns.keys()).issubset(columns):
                raise StorageError(f"required columns missing: {table.name}")
        if connection.exec_driver_sql("PRAGMA quick_check").scalar_one() != "ok":
            raise StorageError("SQLite integrity check failed")

    def upgrade(self):
        """Explicitly migrate with a SQLite-consistent backup and restore on failure."""
        if not self.path.is_file():
            raise StorageError("database missing")
        self.close()
        backup = self.path.with_name(self.path.name + ".pre-upgrade-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".bak")
        if backup.exists(): raise StorageError("timestamped backup already exists")
        try:
            with sqlite3.connect(self.path) as source, sqlite3.connect(backup) as destination:
                source.backup(destination)
            self.engine = create_engine(URL.create("sqlite", database=str(self.path)))
            @event.listens_for(self.engine, "connect")
            def sqlite_options(connection, _):
                connection.isolation_level = None
                cursor = connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.close()
            @event.listens_for(self.engine, "begin")
            def explicit_begin(connection): connection.exec_driver_sql("BEGIN")
            with self.engine.begin() as connection:
                config = Config()
                config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                self._verify_connection(connection)
        except Exception:
            self.close()
            if backup.exists():
                restore = self.path.with_name(self.path.name + ".restore.tmp")
                with sqlite3.connect(backup) as source, sqlite3.connect(restore) as destination:
                    source.backup(destination)
                restore.replace(self.path)
            self.engine = create_engine(URL.create("sqlite", database=str(self.path)))
            raise
        return str(backup)

    def verify(self):
        if not self.path.is_file():
            raise StorageError("database missing")
        with self.engine.connect() as connection:
            self._verify_connection(connection)

    def create_task(self, task: Task) -> Event:
        if task.status != TaskStatus.CREATED or task.revision != 0:
            raise StorageError("new task must start at CREATED, revision 0")
        task = Task.model_validate_json(task.model_dump_json())
        created = Event(event_type="task.created", correlation_id=task.task_id,
                        payload={"task_id": str(task.task_id), "revision": 0})
        try:
            with self.engine.begin() as connection:
                graph = {item.task_id: item.dependency_ids for item in
                         (Task.model_validate_json(p) for p in connection.execute(select(tasks.c.payload)).scalars())}
                graph[task.task_id] = task.dependency_ids
                validate_graph(graph)
                connection.execute(tasks.insert().values(task_id=str(task.task_id), revision=0,
                                                         payload=task.model_dump_json()))
                self._append_event(connection, created)
        except IntegrityError as error:
            raise StorageError("duplicate task or event") from error
        return created

    def assign_agent(self, task_id: UUID, agent_id: UUID, *, expected_revision: int) -> Task:
        """Bind a selected Agent to a READY Task with optimistic concurrency."""
        with self.engine.begin() as connection:
            payload = connection.execute(select(tasks.c.payload).where(tasks.c.task_id == str(task_id))).scalar_one_or_none()
            if payload is None:
                raise KeyError(task_id)
            task = Task.model_validate_json(payload)
            if task.status != TaskStatus.READY or task.revision != expected_revision:
                raise RevisionConflict("task is not READY at the expected revision")
            updated = Task.model_validate({**task.model_dump(), "assigned_agent": agent_id,
                                           "revision": task.revision + 1})
            changed = Event(event_type="task.agent_assigned", correlation_id=task.task_id,
                            payload={"task_id": str(task.task_id), "agent_id": str(agent_id),
                                     "revision": updated.revision})
            result = connection.execute(update(tasks).where(tasks.c.task_id == str(task_id),
                                        tasks.c.revision == expected_revision).values(
                                            revision=updated.revision, payload=updated.model_dump_json()))
            if result.rowcount != 1:
                raise RevisionConflict("task revision changed")
            self._append_event(connection, changed)
        return updated

    def get_task(self, task_id: UUID) -> Task:
        with self.engine.connect() as connection:
            row = connection.execute(select(tasks.c.payload).where(tasks.c.task_id == str(task_id))).scalar_one_or_none()
        if row is None:
            raise KeyError(task_id)
        return Task.model_validate_json(row)

    def transition(self, task_id: UUID, target: TaskStatus, facts: TransitionFacts, *, expected_revision: int) -> Task:
        with self.engine.begin() as connection:
            payload = connection.execute(select(tasks.c.payload).where(tasks.c.task_id == str(task_id))).scalar_one_or_none()
            if payload is None:
                raise KeyError(task_id)
            task = Task.model_validate_json(payload)
            # Dependency readiness is read from persisted state, never trusted from callers.
            statuses = {item.task_id: item.status for item in
                        (Task.model_validate_json(p) for p in connection.execute(select(tasks.c.payload)).scalars())}
            from dataclasses import replace
            from agent_system.domain.dependencies import dependencies_complete
            facts = replace(facts, dependencies_completed=dependencies_complete(task.dependency_ids, statuses))
            updated, changed = transition_task(task, target, facts, expected_revision=expected_revision)
            result = connection.execute(update(tasks).where(tasks.c.task_id == str(task_id),
                                       tasks.c.revision == expected_revision).values(
                                           revision=updated.revision, payload=updated.model_dump_json()))
            if result.rowcount != 1:
                raise RevisionConflict("task revision changed")
            self._append_event(connection, changed)
        return updated

    def create_execution(self, execution: Execution) -> Event:
        with self.engine.begin() as connection:
            row = connection.execute(select(tasks.c.payload).where(tasks.c.task_id == str(execution.task_id))).scalar_one_or_none()
            if row is None: raise KeyError(execution.task_id)
            task = Task.model_validate_json(row)
            if task.status != TaskStatus.ASSIGNED or task.assigned_agent != execution.agent_id:
                raise StorageError("Execution Agent does not match assigned Task")
            connection.execute(executions.insert().values(execution_id=str(execution.execution_id),
                task_id=str(execution.task_id), attempt=execution.attempt, status=execution.status,
                lease_expires_at=execution.lease_expires_at.isoformat(), payload=execution.model_dump_json(),
                idempotency_key=execution.idempotency_key))
            record = Event(event_type="execution.started", correlation_id=execution.task_id,
                payload={"execution_id":str(execution.execution_id),"attempt":execution.attempt})
            self._append_event(connection, record)
        return record

    def finish_execution(self, execution_id: UUID, result: Result, *, status: str) -> Event:
        if status not in {"succeeded", "failed", "cancelled", "unknown"} or result.execution_id != execution_id or result.status != status:
            raise StorageError("Execution and Result status mismatch")
        with self.engine.begin() as connection:
            row = connection.execute(select(executions).where(executions.c.execution_id == str(execution_id))).mappings().first()
            if row is None: raise KeyError(execution_id)
            execution = Execution.model_validate_json(row["payload"])
            if execution.status != "running": raise StorageError("Execution is already terminal")
            terminal_execution = execution.model_copy(update={"status": status})
            connection.execute(update(executions).where(executions.c.execution_id == str(execution_id),
                executions.c.status == "running").values(status=status, payload=terminal_execution.model_dump_json()))
            connection.execute(results.insert().values(result_id=str(result.result_id),
                execution_id=str(result.execution_id), status=result.status, payload=result.model_dump_json()))
            record = Event(event_type="execution.finished", correlation_id=execution.task_id,
                payload={"execution_id":str(execution_id),"status":status,"result_id":str(result.result_id)})
            self._append_event(connection, record)
        return record

    def get_execution(self, execution_id: UUID) -> Execution:
        with self.engine.connect() as connection:
            row = connection.execute(select(executions.c.payload, executions.c.status).where(executions.c.execution_id == str(execution_id))).first()
        if row is None: raise KeyError(execution_id)
        return Execution.model_validate_json(row.payload).model_copy(update={"status": row.status})

    def get_result(self, execution_id: UUID) -> Result:
        with self.engine.connect() as connection:
            row = connection.execute(select(results.c.payload).where(results.c.execution_id == str(execution_id))).scalar_one_or_none()
        if row is None: raise KeyError(execution_id)
        return Result.model_validate_json(row)

    def latest_execution_id(self, task_id: UUID) -> UUID:
        with self.engine.connect() as connection:
            value = connection.execute(select(executions.c.execution_id).where(
                executions.c.task_id == str(task_id)).order_by(executions.c.attempt.desc()).limit(1)).scalar_one_or_none()
        if value is None: raise KeyError(task_id)
        return UUID(value)

    def execution_attempts(self, task_id: UUID) -> int:
        with self.engine.connect() as connection:
            return connection.execute(select(executions.c.attempt).where(executions.c.task_id == str(task_id)).order_by(executions.c.attempt.desc()).limit(1)).scalar_one_or_none() or 0

    def recover_expired_executions(self, *, now: datetime | None = None) -> list[UUID]:
        now = now or datetime.now(timezone.utc)
        recovered = []
        with self.engine.connect() as connection:
            rows = connection.execute(select(executions).where(executions.c.status == "running")).mappings().all()
        for row in rows:
            execution = Execution.model_validate_json(row["payload"])
            if execution.lease_expires_at > now: continue
            unknown = Result(execution_id=execution.execution_id, status="unknown", error_code="EXECUTION_LOST")
            with self.engine.begin() as connection:
                current = connection.execute(select(executions.c.payload).where(
                    executions.c.execution_id == str(execution.execution_id), executions.c.status == "running")).scalar_one_or_none()
                if current is None: continue
                current_execution = Execution.model_validate_json(current)
                if current_execution.lease_expires_at > now: continue
                task_payload = connection.execute(select(tasks.c.payload).where(tasks.c.task_id == str(execution.task_id))).scalar_one_or_none()
                if task_payload is None: raise StorageError("orphan Execution references missing Task")
                task = Task.model_validate_json(task_payload)
                connection.execute(update(executions).where(executions.c.execution_id == str(execution.execution_id),
                    executions.c.status == "running").values(status="unknown"))
                connection.execute(results.insert().values(result_id=str(unknown.result_id),
                    execution_id=str(unknown.execution_id), status=unknown.status, payload=unknown.model_dump_json()))
                if task.status == TaskStatus.RUNNING:
                    updated, changed = transition_task(task, TaskStatus.FAILED,
                        TransitionFacts(result_recorded=True, execution_stopped=True, reason="orchestrator recovery: lease expired"),
                        expected_revision=task.revision)
                    connection.execute(update(tasks).where(tasks.c.task_id == str(task.task_id),
                        tasks.c.revision == task.revision).values(revision=updated.revision, payload=updated.model_dump_json()))
                    self._append_event(connection, changed)
                event_record = Event(event_type="execution.recovered_unknown", correlation_id=execution.task_id,
                    payload={"execution_id":str(execution.execution_id),"result_id":str(unknown.result_id)})
                self._append_event(connection, event_record)
                recovered.append(execution.execution_id)
        return recovered

    @staticmethod
    def _append_event(connection, event_record: Event):
        connection.execute(events.insert().values(event_id=str(event_record.event_id),
                           correlation_id=str(event_record.correlation_id), payload=event_record.model_dump_json()))

    def history(self, task_id: UUID) -> list[Event]:
        with self.engine.connect() as connection:
            payloads = connection.execute(select(events.c.payload).where(
                events.c.correlation_id == str(task_id)).order_by(events.c.sequence)).scalars().all()
        return [Event.model_validate_json(payload) for payload in payloads]

    def save_approval(self, approval: Approval) -> Approval:
        with self.engine.begin() as connection:
            connection.execute(approvals.insert().values(approval_id=str(approval.approval_id),
                action_digest=approval.action_digest, decision=approval.decision, payload=approval.model_dump_json()))
        return approval

    def get_approval(self, approval_id: UUID) -> Approval:
        with self.engine.connect() as connection:
            payload=connection.execute(select(approvals.c.payload).where(approvals.c.approval_id==str(approval_id))).scalar_one_or_none()
        if payload is None: raise KeyError(approval_id)
        return Approval.model_validate_json(payload)

    def decide_approval(self, approval_id: UUID, *, decision: str, actor: str, now: datetime) -> Approval:
        if decision not in {"approved", "rejected"} or not actor.strip(): raise StorageError("invalid approval decision")
        with self.engine.begin() as connection:
            payload=connection.execute(select(approvals.c.payload).where(approvals.c.approval_id==str(approval_id))).scalar_one_or_none()
            if payload is None: raise KeyError(approval_id)
            approval=Approval.model_validate_json(payload)
            if approval.decision != "pending" or now >= approval.expires_at: raise StorageError("approval is decided or expired")
            updated=approval.model_copy(update={"decision":decision,"decided_by":actor,"decided_at":now})
            # Revalidate the immutable replacement before writing.
            updated=Approval.model_validate_json(updated.model_dump_json())
            connection.execute(approvals.update().where(approvals.c.approval_id==str(approval_id), approvals.c.decision=="pending").values(decision=decision,payload=updated.model_dump_json()))
        return updated

    def save_handoff(self, handoff: Handoff) -> Handoff:
        with self.engine.begin() as connection:
            task=connection.execute(select(tasks.c.payload).where(tasks.c.task_id==str(handoff.task_id))).scalar_one_or_none()
            execution=connection.execute(select(executions.c.task_id).where(executions.c.execution_id==str(handoff.execution_id))).scalar_one_or_none()
            if task is None or execution != str(handoff.task_id): raise StorageError("Handoff references unrelated Task or Execution")
            connection.execute(handoffs.insert().values(handoff_id=str(handoff.handoff_id),task_id=str(handoff.task_id),execution_id=str(handoff.execution_id),payload_digest=handoff.payload_digest,payload=handoff.model_dump_json()))
        return handoff

    def get_handoff(self, handoff_id: UUID) -> Handoff:
        with self.engine.connect() as connection:
            payload=connection.execute(select(handoffs.c.payload).where(handoffs.c.handoff_id==str(handoff_id))).scalar_one_or_none()
        if payload is None: raise KeyError(handoff_id)
        return Handoff.model_validate_json(payload)

    def set_context(self, key: str, value, *, expected_revision: int | None = None) -> int:
        if not key.strip(): raise ValueError("context key required")
        payload=json.dumps(value,ensure_ascii=False,allow_nan=False)
        with self.engine.begin() as connection:
            row=connection.execute(select(context.c.revision).where(context.c.key==key)).scalar_one_or_none()
            if row is None:
                if expected_revision not in (None,0): raise RevisionConflict("context revision changed")
                revision=1
                connection.execute(context.insert().values(key=key,revision=revision,payload=payload))
            else:
                if expected_revision != row: raise RevisionConflict("context revision changed")
                revision=row+1
                connection.execute(context.update().where(context.c.key==key,context.c.revision==row).values(revision=revision,payload=payload))
        return revision

    def get_context(self, key: str) -> tuple[object,int]:
        with self.engine.connect() as connection:
            row=connection.execute(select(context.c.payload,context.c.revision).where(context.c.key==key)).first()
        if row is None: raise KeyError(key)
        return json.loads(row.payload),row.revision

    def set_config(self, key: str, value):
        if not key.strip():
            raise ValueError("configuration key is required")
        payload = json.dumps(value, allow_nan=False)
        with self.engine.begin() as connection:
            found = connection.execute(select(configuration.c.key).where(configuration.c.key == key)).first()
            if found:
                connection.execute(configuration.update().where(configuration.c.key == key).values(payload=payload))
            else:
                connection.execute(configuration.insert().values(key=key, payload=payload))

    def get_config(self, key: str):
        with self.engine.connect() as connection:
            payload = connection.execute(select(configuration.c.payload).where(configuration.c.key == key)).scalar_one_or_none()
        if payload is None:
            raise KeyError(key)
        return json.loads(payload)
