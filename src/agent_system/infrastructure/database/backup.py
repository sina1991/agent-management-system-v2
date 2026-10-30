"""Consistent, non-destructive SQLite backup and restore helpers."""
import sqlite3
from pathlib import Path
from uuid import uuid4
from agent_system.infrastructure.database.store import Store, StorageError

def backup_database(source: Path, destination: Path) -> Path:
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file() or destination.exists(): raise StorageError("source must exist and backup destination must be new")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary=destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        with sqlite3.connect(source) as src, sqlite3.connect(temporary) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok": raise StorageError("backup integrity check failed")
        check=Store(temporary)
        try: check.verify()
        finally: check.close()
        temporary.replace(destination)
        return destination
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

def restore_database(backup: Path, destination: Path) -> Path:
    backup, destination = Path(backup).resolve(), Path(destination).resolve()
    if not backup.is_file() or destination.exists(): raise StorageError("backup must exist and restore destination must be new")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary=destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        with sqlite3.connect(backup) as src, sqlite3.connect(temporary) as dst:
            src.backup(dst)
        check=Store(temporary)
        try: check.verify()
        finally: check.close()
        temporary.replace(destination)
        return destination
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
