"""Validated immutable task transitions; persistence is added in the next stage."""
from datetime import datetime
from agent_system.contracts.models import Event, Task, utcnow
from agent_system.domain.lifecycle import TransitionFacts, check_transition
from agent_system.domain.types import TaskStatus


def transition_task(task: Task, target: TaskStatus, facts: TransitionFacts, *,
                    expected_revision: int, now: datetime | None = None) -> tuple[Task, Event]:
    check_transition(task.status, target, facts, revision=task.revision,
                     expected_revision=expected_revision)
    timestamp = now if now is not None else utcnow()
    updated = Task.model_validate({**task.model_dump(), "status": target,
                                  "revision": task.revision + 1, "updated_at": timestamp})
    if updated.updated_at < task.updated_at:
        raise ValueError("transition timestamp moved backwards")
    event = Event(event_type="task.status_changed", correlation_id=task.task_id,
                  occurred_at=updated.updated_at, payload={
                      "task_id": str(task.task_id), "from": task.status.value,
                      "to": target.value, "revision": updated.revision, "reason": facts.reason,
                  })
    return updated, event
