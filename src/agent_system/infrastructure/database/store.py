"""Transactional SQLite storage for tasks, events and shared configuration."""
import json
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, event, inspect, select, update
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError

from agent_system.application.tasks import transition_task
from agent_system.contracts.models import Event, Task
from agent_system.domain.dependencies import validate_graph
from agent_system.domain.errors import DomainError, RevisionConflict
from agent_system.domain.lifecycle import TransitionFacts
from agent_system.domain.types import TaskStatus
from agent_system.infrastructure.database.schema import configuration, events, tasks

SCHEMA_REVISION = "0001"


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
        for table in (tasks, events, configuration):
            columns = {column["name"] for column in inspect(connection).get_columns(table.name)}
            if not set(table.columns.keys()).issubset(columns):
                raise StorageError(f"required columns missing: {table.name}")
        if connection.exec_driver_sql("PRAGMA quick_check").scalar_one() != "ok":
            raise StorageError("SQLite integrity check failed")

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

    @staticmethod
    def _append_event(connection, event_record: Event):
        connection.execute(events.insert().values(event_id=str(event_record.event_id),
                           correlation_id=str(event_record.correlation_id), payload=event_record.model_dump_json()))

    def history(self, task_id: UUID) -> list[Event]:
        with self.engine.connect() as connection:
            payloads = connection.execute(select(events.c.payload).where(
                events.c.correlation_id == str(task_id)).order_by(events.c.sequence)).scalars().all()
        return [Event.model_validate_json(payload) for payload in payloads]

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
