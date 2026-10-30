"""Isolated process entrypoint for fixed, built-in, side-effect-free workers."""
import json
import sys
from agent_system.runtime.workers import WorkerRegistry, WorkerError

MAX_INPUT_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 64 * 1024

def main() -> int:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return 2
    try:
        request = json.loads(raw)
        if set(request) != {"worker", "input"} or not isinstance(request["input"], dict):
            return 2
        output = WorkerRegistry().get(request["worker"])(request["input"])
        encoded = json.dumps({"ok": True, "output": output}, ensure_ascii=False, allow_nan=False).encode()
        if len(encoded) > MAX_OUTPUT_BYTES:
            return 2
        sys.stdout.buffer.write(encoded)
        return 0
    except (ValueError, TypeError, WorkerError):
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
