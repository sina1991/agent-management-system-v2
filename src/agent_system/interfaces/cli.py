"""CLI for implementation status and versioned wire contracts."""
import argparse
import json
import sys
from pathlib import Path
from pydantic import ValidationError
from agent_system import __version__
from agent_system.contracts.models import CONTRACTS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ams")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Report the software implementation stage")
    schema = commands.add_parser("schema", help="Print a contract JSON Schema")
    schema.add_argument("contract", choices=sorted(CONTRACTS))
    validate = commands.add_parser("validate", help="Validate a contract JSON file")
    validate.add_argument("contract", choices=sorted(CONTRACTS))
    validate.add_argument("file", type=Path)
    db = commands.add_parser("db", help="Initialize or verify explicit local storage")
    db.add_argument("action", choices=["init", "verify"])
    db.add_argument("path", type=Path)
    task = commands.add_parser("task", help="Create or read tasks in existing storage")
    task.add_argument("action", choices=["create", "show", "history"])
    task.add_argument("database", type=Path)
    task.add_argument("value", help="JSON file for create; UUID for show/history")
    args = parser.parse_args(argv)
    if args.command == "status":
        print(json.dumps({"version": __version__, "stage": "storage_foundation",
                          "operational": False,
                          "message": "Contracts and task persistence available; installer and runtime pending."}))
        return 0
    if args.command in {"db", "task"}:
        from uuid import UUID
        from agent_system.contracts.models import Task
        from agent_system.domain.errors import DomainError
        from agent_system.infrastructure.database.store import Store
        from sqlalchemy.exc import SQLAlchemyError
        path = args.path if args.command == "db" else args.database
        # Verification and reads must not create an empty database as a side effect.
        if not path.is_file() and not (args.command == "db" and args.action == "init"):
            print(json.dumps({"code": "DATABASE_MISSING"}), file=sys.stderr)
            return 2
        store = Store(path)
        try:
            if args.command == "db":
                store.initialize() if args.action == "init" else store.verify()
                print(json.dumps({"database": str(path), "verified": True}))
            else:
                store.verify()
                if args.action == "create":
                    record = Task.model_validate_json(Path(args.value).read_text(encoding="utf-8"))
                    store.create_task(record)
                    print(json.dumps({"task_id": str(record.task_id), "status": record.status.value}))
                elif args.action == "show":
                    print(store.get_task(UUID(args.value)).model_dump_json())
                else:
                    print(json.dumps([e.model_dump(mode="json") for e in store.history(UUID(args.value))]))
            return 0
        except (DomainError, ValueError, KeyError, OSError, SQLAlchemyError) as error:
            print(json.dumps({"code": getattr(error, "code", "STORAGE_OPERATION_FAILED")}), file=sys.stderr)
            return 2
        finally:
            store.close()
    if args.command == "schema":
        print(json.dumps(CONTRACTS[args.contract].model_json_schema(), indent=2))
        return 0
    if args.command == "validate":
        try:
            CONTRACTS[args.contract].model_validate_json(args.file.read_text(encoding="utf-8"))
        except ValidationError as error:
            # Never echo input values or exception context, which may contain secrets.
            print(json.dumps({"valid": False, "code": "CONTRACT_INVALID",
                              "errors": [{"location": list(e["loc"]), "type": e["type"]}
                                         for e in error.errors(include_input=False, include_context=False)]}), file=sys.stderr)
            return 2
        except (OSError, UnicodeError):
            print(json.dumps({"valid": False, "code": "INPUT_UNREADABLE"}), file=sys.stderr)
            return 2
        print(json.dumps({"valid": True, "contract": args.contract, "schema_version": "1.0"}))
        return 0
    return 2
