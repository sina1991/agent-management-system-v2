"""Allowlisted, deterministic workers. These handlers are trusted in-process code."""
from agent_system.domain.errors import DomainError

class WorkerError(DomainError):
    code = "WORKER_INPUT_INVALID"

def _echo(payload):
    if set(payload) != {"value"}: raise WorkerError("text.echo expects exactly a value field")
    return {"value": payload["value"]}

def _sum(payload):
    values = payload.get("values")
    if set(payload) != {"values"} or not isinstance(values, list) or not values or any(type(v) not in (int, float) for v in values):
        raise WorkerError("math.sum expects a non-empty numeric values list")
    return {"value": sum(values)}

class WorkerRegistry:
    _workers = {"text.echo": _echo, "math.sum": _sum}
    def get(self, name):
        try: return self._workers[name]
        except KeyError as error: raise WorkerError("worker is not allowlisted") from error
