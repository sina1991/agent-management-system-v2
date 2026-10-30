"""Versioned wire contracts. Unknown fields and naive timestamps are rejected."""
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import (BaseModel, ConfigDict, Field, JsonValue, StringConstraints,
                      field_validator, model_validator)

from agent_system.domain.types import Permission, TaskStatus

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True,
                              allow_inf_nan=False)
    schema_version: Literal["1.0"] = "1.0"

    @field_validator("*", mode="after")
    @classmethod
    def normalize_time(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timestamp must include timezone")
            return value.astimezone(timezone.utc)
        return value

class Agent(Contract):
    agent_id: UUID = Field(default_factory=uuid4)
    name: Text
    role: Text
    description: Text
    capabilities: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = ()
    runtime: Text
    provider: Text
    permissions: frozenset[Permission] = frozenset()
    version: Text
    availability: Literal["available", "busy", "offline"] = "available"
    status: Literal["active", "disabled"] = "active"
    kind: Literal["internal", "external", "human_assisted"]

class VerificationSpec(Contract):
    verifier: Text
    parameters: dict[str, JsonValue] = Field(default_factory=dict)

class Task(Contract):
    task_id: UUID = Field(default_factory=uuid4)
    title: Text
    description: Text
    input: dict[str, JsonValue] = Field(default_factory=dict)
    expected_output: Text
    assigned_agent: UUID | None = None
    priority: Annotated[int, Field(strict=True, ge=0, le=100)] = 50
    dependency_ids: tuple[UUID, ...] = ()
    constraints: tuple[Text, ...] = ()
    acceptance_criteria: tuple[Text, ...] = Field(min_length=1)
    verification_spec: VerificationSpec
    status: TaskStatus = TaskStatus.CREATED
    revision: NonnegativeInt = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def valid_task(self) -> Self:
        if self.task_id in self.dependency_ids:
            raise ValueError("task cannot depend on itself")
        if len(set(self.dependency_ids)) != len(self.dependency_ids):
            raise ValueError("duplicate dependencies")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at precedes created_at")
        if self.status in {TaskStatus.ASSIGNED, TaskStatus.RUNNING} and self.assigned_agent is None:
            raise ValueError("assigned/running task requires assigned_agent")
        return self

class Execution(Contract):
    execution_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    agent_id: UUID
    attempt: PositiveInt = 1
    timeout_seconds: PositiveInt
    idempotency_key: Text
    owner_token: UUID
    status: Literal["pending", "running", "succeeded", "failed", "cancelled", "unknown"] = "pending"
    started_at: datetime | None = None
    heartbeat_at: datetime | None = None
    lease_expires_at: datetime | None = None

    @model_validator(mode="after")
    def valid_lease(self) -> Self:
        if (self.heartbeat_at is None) != (self.lease_expires_at is None):
            raise ValueError("heartbeat and lease must be supplied together")
        if self.heartbeat_at and self.lease_expires_at <= self.heartbeat_at:
            raise ValueError("lease must expire after heartbeat")
        if self.started_at and self.heartbeat_at and self.heartbeat_at < self.started_at:
            raise ValueError("heartbeat precedes execution start")
        if self.status == "running" and (self.started_at is None or self.heartbeat_at is None):
            raise ValueError("running execution requires start and lease")
        return self

class Artifact(Contract):
    artifact_id: UUID = Field(default_factory=uuid4)
    execution_id: UUID
    relative_path: Text
    size_bytes: NonnegativeInt
    checksum: Digest

    @field_validator("relative_path")
    @classmethod
    def safe_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value or "\x00" in value or str(path) == ".":
            raise ValueError("artifact path must be a safe relative POSIX path")
        return str(path)

class Result(Contract):
    result_id: UUID = Field(default_factory=uuid4)
    execution_id: UUID
    status: Literal["succeeded", "failed", "cancelled", "unknown"]
    output: JsonValue = None
    artifacts: tuple[Artifact, ...] = ()
    error_code: Text | None = None
    retryable: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def valid_result(self) -> Self:
        if any(a.execution_id != self.execution_id for a in self.artifacts):
            raise ValueError("artifact belongs to another execution")
        if len({a.artifact_id for a in self.artifacts}) != len(self.artifacts):
            raise ValueError("duplicate artifact IDs")
        if len({a.relative_path for a in self.artifacts}) != len(self.artifacts):
            raise ValueError("duplicate artifact paths")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("failed result requires error_code")
        if self.status == "succeeded" and self.error_code is not None:
            raise ValueError("successful result cannot include error_code")
        if self.retryable and self.status != "failed":
            raise ValueError("only explicit failures may be retryable")
        return self

class Event(Contract):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Text
    occurred_at: datetime = Field(default_factory=utcnow)
    correlation_id: UUID
    causation_id: UUID | None = None
    payload: dict[str, JsonValue] = Field(default_factory=dict)

class Message(Contract):
    message_id: UUID = Field(default_factory=uuid4)
    sender_id: UUID
    recipient_id: UUID
    correlation_id: UUID
    sent_at: datetime = Field(default_factory=utcnow)
    payload: dict[str, JsonValue] = Field(default_factory=dict)

class Approval(Contract):
    approval_id: UUID = Field(default_factory=uuid4)
    action_digest: Digest
    scope: Text
    expires_at: datetime
    policy_version: Text
    decision: Literal["pending", "approved", "rejected"] = "pending"
    decided_by: Text | None = None
    decided_at: datetime | None = None

    @model_validator(mode="after")
    def valid_decision(self) -> Self:
        if self.decision == "pending":
            if self.decided_by is not None or self.decided_at is not None:
                raise ValueError("pending approval cannot include decision metadata")
        elif self.decided_by is None or self.decided_at is None:
            raise ValueError("decision requires actor and time")
        if self.decided_at and self.decided_at >= self.expires_at:
            raise ValueError("decision must precede expiry")
        return self

CONTRACTS = {c.__name__: c for c in (Agent, Task, Message, Execution, Result, Event, Approval, Artifact)}
