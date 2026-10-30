"""Synchronous MVP Task path for explicitly registered, trusted internal workers."""
from datetime import timedelta
from hashlib import sha256
import json
from uuid import uuid4

from agent_system.contracts.models import Agent, Execution, Result, utcnow
from agent_system.domain.lifecycle import TransitionFacts as Facts
from agent_system.domain.types import Permission, TaskStatus as S
from agent_system.infrastructure.database.store import Store
from agent_system.infrastructure.registry import AgentRegistry
from agent_system.runtime.workers import WorkerRegistry


class WorkflowError(RuntimeError):
    code = "WORKFLOW_FAILED"


def run_task(store: Store, task_id, *, timeout_seconds: int = 30) -> dict:
    task = store.get_task(task_id)
    if task.status != S.CREATED:
        raise WorkflowError(f"task must be CREATED; found {task.status}")
    agent = AgentRegistry(store).select("task.execute")
    worker = WorkerRegistry().get(agent.provider)
    task = store.transition(task.task_id, S.PLANNED, Facts(plan_recorded=True), expected_revision=task.revision)
    task = store.transition(task.task_id, S.READY, Facts(plan_recorded=True, policy_allowed=True), expected_revision=task.revision)
    task = store.assign_agent(task.task_id, agent.agent_id, expected_revision=task.revision)
    task = store.transition(task.task_id, S.ASSIGNED, Facts(agent_selected=True, policy_allowed=True), expected_revision=task.revision)
    now = utcnow()
    execution = Execution(task_id=task.task_id, agent_id=agent.agent_id,
                          timeout_seconds=timeout_seconds, idempotency_key=f"{task.task_id}:1",
                          owner_token=uuid4(), status="running", started_at=now,
                          heartbeat_at=now, lease_expires_at=now + timedelta(seconds=timeout_seconds))
    store.set_config(f"execution:{execution.execution_id}", json.loads(execution.model_dump_json()))
    task = store.transition(task.task_id, S.RUNNING,
        Facts(agent_selected=True, execution_created=True, policy_allowed=True), expected_revision=task.revision)
    try:
        output = worker(task.input)
        verified = task.verification_spec.verifier == "json_equals" and output == task.verification_spec.parameters.get("expected")
        result = Result(execution_id=execution.execution_id, status="succeeded", output=output)
    except Exception as error:
        # Do not expose exception text from Worker code in the public result.
        output, verified = None, False
        result = Result(execution_id=execution.execution_id, status="failed",
                        error_code="WORKER_FAILED", retryable=False)
    store.set_config(f"result:{execution.execution_id}", json.loads(result.model_dump_json()))
    store.set_config(f"execution:{execution.execution_id}", {**json.loads(execution.model_dump_json()),
                     "status": "succeeded" if result.status == "succeeded" else "failed"})
    reason = "" if verified else "worker result did not pass the declared verifier"
    task = store.transition(task.task_id, S.REVIEW if result.status == "succeeded" else S.FAILED,
        Facts(result_recorded=True, execution_stopped=True, reason=reason), expected_revision=task.revision)
    if task.status == S.REVIEW and verified:
        task = store.transition(task.task_id, S.COMPLETED,
            Facts(result_recorded=True, verification_passed=True, policy_allowed=True), expected_revision=task.revision)
    elif task.status == S.REVIEW:
        task = store.transition(task.task_id, S.CHANGES_REQUESTED,
            Facts(reason=reason), expected_revision=task.revision)
    return {"task_id": str(task.task_id), "status": task.status.value,
            "execution_id": str(execution.execution_id), "result": result.model_dump(mode="json"),
            "verified": verified}
