"""Install the current package snapshot into a Git Target with reversible staging."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import shutil
import tempfile
import subprocess
import tomllib
from urllib.parse import urlsplit
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


def _local_source() -> tuple[Path, Path, str]:
    package = Path(__file__).resolve().parents[1]
    project = package.parents[1]
    if not (package / "__init__.py").is_file():
        raise InstallError("cannot resolve packaged application source")
    with (project / "pyproject.toml").open("rb") as stream:
        version = tomllib.load(stream)["project"]["version"]
    return project, package, version

def _remote_source(url: str, destination: Path) -> tuple[Path, Path, str, str]:
    parsed=urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise InstallError("Source URL must be credential-free HTTPS Git URL")
    clone=destination/"source"
    try:
        subprocess.run(["git","clone","--depth","1",url,str(clone)],check=True,capture_output=True,text=True,timeout=120)
    except (OSError,subprocess.SubprocessError) as error:
        raise InstallError("Source repository clone failed") from error
    project=clone
    package=project/"src"/"agent_system"
    if not (package/"__init__.py").is_file() or not (project/"requirements.lock.txt").is_file():
        raise InstallError("Source repository layout or dependency lock is invalid")
    with (project/"pyproject.toml").open("rb") as stream:
        version=tomllib.load(stream)["project"]["version"]
    revision=subprocess.run(["git","-C",str(project),"rev-parse","HEAD"],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
    return project,package,version,revision


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
    if manifest.get("manifest_version") != 1 or not isinstance(manifest.get("release_version"), str):
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
    return {"installation_id": manifest["installation_id"], "version": manifest["release_version"],
            "status": "verified", "file_count": len(actual), "database": "verified"}


def install(target: Path, *, source_url: str | None = None) -> dict:
    target = Path(target).expanduser().resolve()
    if not target.is_dir():
        raise InstallError("Target directory must already exist")
    if not ((target / ".git").is_dir() or (target / ".git").is_file()):
        raise InstallError("Target must be a Git working tree")
    local_project, local_package, local_version = _local_source()
    source = local_package
    source_version = local_version
    source_revision = None
    remote_tmp = tempfile.TemporaryDirectory(prefix="ams-source-") if source_url else None
    if source_url:
        try:
            local_project, source, source_version, source_revision = _remote_source(source_url,Path(remote_tmp.name))
        except Exception:
            remote_tmp.cleanup()
            raise
    if source == target or source.is_relative_to(target):
        if remote_tmp: remote_tmp.cleanup()
        raise InstallError("source package cannot be installed into itself")
    root = target / SYSTEM_DIR
    manifest_path = _manifest(target)
    if manifest_path.exists():
        status = doctor(target)
        if remote_tmp: remote_tmp.cleanup()
        return {**status, "status": "existing"}
    if root.exists() and any(root.iterdir()):
        if remote_tmp: remote_tmp.cleanup()
        raise InstallError("reserved .agent-system directory is non-empty and has no valid manifest")
    root.mkdir(parents=True, exist_ok=True)
    app = root / "app"
    state = root / "state"
    config_dir = root / "config"
    profiles = root / "profiles"
    for directory in (app, state, config_dir, profiles):
        directory.mkdir(parents=True, exist_ok=True)
    release_name = source_version
    final_release = app / release_name
    if final_release.exists():
        if remote_tmp: remote_tmp.cleanup()
        raise InstallError("release path already exists without a valid manifest")
    staging = Path(tempfile.mkdtemp(prefix=f".{release_name}.staging-", dir=app))
    try:
        shutil.copytree(source, staging / "agent_system", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # Verify dependencies before publishing a manifest or claiming success.
        deps = {name: importlib.metadata.version(name) for name in ("pydantic", "SQLAlchemy", "alembic")}
        if source_url:
            venv=root/".venv"
            import venv as venv_module
            venv_module.EnvBuilder(with_pip=True).create(venv)
            python=venv/("Scripts/python.exe" if os.name=="nt" else "bin/python")
            try:
                subprocess.run([str(python),"-m","pip","install","--disable-pip-version-check","-c",str(local_project/"requirements.lock.txt"),"."],cwd=local_project,check=True,capture_output=True,text=True,timeout=600)
            except (OSError,subprocess.SubprocessError) as error:
                raise InstallError("Target dependency installation failed") from error
            metadata_code="import importlib.metadata,json; print(json.dumps({n:importlib.metadata.version(n) for n in ('pydantic','SQLAlchemy','alembic')}))"
            deps=json.loads(subprocess.run([str(python),"-c",metadata_code],check=True,capture_output=True,text=True,timeout=10).stdout)
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
                    "release_version": source_version, "source_url": source_url,
                    "source_revision": source_revision, "schema_version": "0003",
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
    finally:
        if remote_tmp: remote_tmp.cleanup()
