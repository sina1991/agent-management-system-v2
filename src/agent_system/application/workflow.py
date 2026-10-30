"""Bounded Task execution with explicit retry for safe built-in workers."""
from datetime import timedelta
import json
import os
import subprocess
import sys
from uuid import uuid4

from agent_system.contracts.models import Execution, Result, utcnow
from agent_system.domain.lifecycle import TransitionFacts as Facts
from agent_system.domain.types import TaskStatus as S
from agent_system.infrastructure.database.store import Store
from agent_system.infrastructure.registry import AgentRegistry

MAX_ATTEMPTS = 3
MAX_TIMEOUT_SECONDS = 300
MAX_OUTPUT_BYTES = 64 * 1024

class WorkflowError(RuntimeError):
    code = "WORKFLOW_FAILED"


def _run_worker(provider: str, payload: dict, timeout: int):
    request = json.dumps({"worker": provider, "input": payload}, allow_nan=False)
    if len(request.encode()) > MAX_OUTPUT_BYTES:
        raise WorkflowError("worker input exceeds size limit")
    env = {key: value for key, value in os.environ.items()
           if key in {"PATH", "SYSTEMROOT", "WINDIR", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP"}}
    process = subprocess.run([sys.executable, "-I", "-m", "agent_system.runtime.worker_host"],
        input=request, text=True, capture_output=True, timeout=timeout, env=env, check=False)
    if process.returncode != 0 or len(process.stdout.encode()) > MAX_OUTPUT_BYTES:
        raise WorkflowError("worker process failed")
    try:
        response = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise WorkflowError("worker returned invalid data") from error
    if set(response) != {"ok", "output"} or response["ok"] is not True:
        raise WorkflowError("worker returned invalid result")
    return response["output"]


def retry_task(store: Store, task_id) -> dict:
    task = store.get_task(task_id)
    if task.status != S.FAILED:
        raise WorkflowError("only FAILED tasks can be retried")
    attempts = store.get_config(f"task:{task_id}:attempts")
    if attempts >= MAX_ATTEMPTS:
        raise WorkflowError("retry budget exhausted")
    last_id = store.get_config(f"task:{task_id}:latest_execution")
    last = store.get_config(f"result:{last_id}")
    if not last.get("retryable", False):
        raise WorkflowError("last failure is not classified as retryable")
    store.transition(task.task_id, S.PLANNED,
        Facts(plan_recorded=True, retry_available=True, reason="explicit retry requested"),
        expected_revision=task.revision)
    return run_task(store, task_id, timeout_seconds=store.get_config(f"task:{task_id}:timeout"))


def run_task(store: Store, task_id, *, timeout_seconds: int = 30) -> dict:
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise WorkflowError(f"timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds")
    task = store.get_task(task_id)
    if task.status not in {S.CREATED, S.PLANNED}:
        raise WorkflowError(f"task must be CREATED or PLANNED; found {task.status}")
    attempts = store.get_config(f"task:{task_id}:attempts") if task.status == S.PLANNED else 0
    if attempts >= MAX_ATTEMPTS:
        raise WorkflowError("retry budget exhausted")
    agent = AgentRegistry(store).select("task.execute")
    if task.status == S.CREATED:
        task = store.transition(task.task_id, S.PLANNED, Facts(plan_recorded=True), expected_revision=task.revision)
    task = store.transition(task.task_id, S.READY, Facts(plan_recorded=True, policy_allowed=True), expected_revision=task.revision)
    task = store.assign_agent(task.task_id, agent.agent_id, expected_revision=task.revision)
    task = store.transition(task.task_id, S.ASSIGNED, Facts(agent_selected=True, policy_allowed=True), expected_revision=task.revision)
    attempts += 1
    store.set_config(f"task:{task_id}:attempts", attempts)
    store.set_config(f"task:{task_id}:timeout", timeout_seconds)
    now = utcnow()
    execution = Execution(task_id=task.task_id, agent_id=agent.agent_id, attempt=attempts,
        timeout_seconds=timeout_seconds, idempotency_key=f"{task.task_id}:{attempts}",
        owner_token=uuid4(), status="running", started_at=now, heartbeat_at=now,
        lease_expires_at=now + timedelta(seconds=timeout_seconds))
    store.set_config(f"task:{task_id}:latest_execution", str(execution.execution_id))
    store.set_config(f"execution:{execution.execution_id}", json.loads(execution.model_dump_json()))
    task = store.transition(task.task_id, S.RUNNING,
        Facts(agent_selected=True, execution_created=True, policy_allowed=True), expected_revision=task.revision)
    try:
        output = _run_worker(agent.provider, task.input, timeout_seconds)
        verified = task.verification_spec.verifier == "json_equals" and output == task.verification_spec.parameters.get("expected")
        result = Result(execution_id=execution.execution_id, status="succeeded", output=output)
    except subprocess.TimeoutExpired:
        verified = False
        result = Result(execution_id=execution.execution_id, status="failed",
                        error_code="WORKER_TIMEOUT", retryable=True)
    except Exception:
        verified = False
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
            "execution_id": str(execution.execution_id), "attempt": attempts,
            "result": result.model_dump(mode="json"), "verified": verified}
