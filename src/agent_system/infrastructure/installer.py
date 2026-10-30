"""Install the current package snapshot into a Git Target with reversible staging."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_system import __version__
from agent_system.infrastructure.database.store import Store

SYSTEM_DIR = ".agent-system"


class InstallError(RuntimeError):
    code = "INSTALL_FAILED"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_package() -> Path:
    source = Path(__file__).resolve().parents[1]
    if not (source / "__init__.py").is_file():
        raise InstallError("cannot resolve packaged application source")
    return source


def _release_files(release: Path) -> dict[str, str]:
    package = release / "agent_system"
    if not package.is_dir():
        raise InstallError("installed application package missing")
    return {p.relative_to(release).as_posix(): _sha256(p)
            for p in sorted(package.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def _manifest(target: Path) -> Path:
    return target / SYSTEM_DIR / "manifest.json"


def doctor(target: Path) -> dict:
    target = Path(target).expanduser().resolve()
    root = target / SYSTEM_DIR
    manifest_path = _manifest(target)
    if not root.is_dir() or not manifest_path.is_file():
        raise InstallError("V2 installation manifest missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InstallError("installation manifest unreadable") from error
    if manifest.get("manifest_version") != 1 or manifest.get("release_version") != __version__:
        raise InstallError("unsupported installation manifest or release")
    release = root / "app" / manifest.get("release_path", "")
    expected = manifest.get("files")
    if not isinstance(expected, dict) or not expected:
        raise InstallError("installation inventory missing")
    actual = _release_files(release)
    if actual != expected:
        raise InstallError("release files differ from installation inventory")
    database = root / "state" / "system.db"
    store = Store(database)
    try:
        store.verify()
    finally:
        store.close()
    return {"installation_id": manifest["installation_id"], "version": __version__,
            "status": "verified", "file_count": len(actual), "database": "verified"}


def install(target: Path) -> dict:
    target = Path(target).expanduser().resolve()
    if not target.is_dir():
        raise InstallError("Target directory must already exist")
    if not ((target / ".git").is_dir() or (target / ".git").is_file()):
        raise InstallError("Target must be a Git working tree")
    source = _source_package()
    if source == target or source.is_relative_to(target):
        raise InstallError("source package cannot be installed into itself")
    root = target / SYSTEM_DIR
    manifest_path = _manifest(target)
    if manifest_path.exists():
        status = doctor(target)
        return {**status, "status": "existing"}
    if root.exists() and any(root.iterdir()):
        raise InstallError("reserved .agent-system directory is non-empty and has no valid manifest")
    root.mkdir(parents=True, exist_ok=True)
    app = root / "app"
    state = root / "state"
    config_dir = root / "config"
    profiles = root / "profiles"
    for directory in (app, state, config_dir, profiles):
        directory.mkdir(parents=True, exist_ok=True)
    release_name = __version__
    final_release = app / release_name
    if final_release.exists():
        raise InstallError("release path already exists without a valid manifest")
    staging = Path(tempfile.mkdtemp(prefix=f".{release_name}.staging-", dir=app))
    try:
        shutil.copytree(source, staging / "agent_system", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # Verify dependencies before publishing a manifest or claiming success.
        deps = {name: importlib.metadata.version(name) for name in ("pydantic", "SQLAlchemy", "alembic")}
        inventory = _release_files(staging)
        os.replace(staging, final_release)
        db_path = state / "system.db"
        store = Store(db_path)
        try:
            store.initialize()
            store.verify()
        finally:
            store.close()
        config = config_dir / "system.json"
        if not config.exists():
            config.write_text(json.dumps({"schema_version": 1}, indent=2) + "\n", encoding="utf-8")
        manifest = {"manifest_version": 1, "installation_id": str(uuid4()),
                    "release_version": __version__, "schema_version": "0002",
                    "release_path": release_name, "files": inventory,
                    "dependencies": deps, "installation_status": "verified",
                    "installed_at": datetime.now(timezone.utc).isoformat()}
        temporary_manifest = root / ".manifest.json.tmp"
        temporary_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary_manifest, manifest_path)
        return doctor(target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        # Keep a completed release and DB for safe repair; no manifest means doctor reports incomplete.
        raise
