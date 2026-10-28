"""An installed release must be complete, unchanged and owned by this instance."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from linker_local.engine_release import engine_project, require_input_compatibility
from linker_local.instance import Instance
from linker_local.processes import ProcessError


def selected(tmp_path: Path) -> tuple[Instance, Path, Path, Path]:
    instance = Instance("owned", 1, 2, 3, tmp_path / "instances")
    checkout = tmp_path / "checkout/engine"
    python = checkout / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    release = instance.dir / "planner/runtime-releases/frozen"
    files = {}
    for name in (
        "pyproject.toml",
        "uv.lock",
        "src/linker_engine/__init__.py",
        "src/linker_engine/application.py",
        "src/linker_engine/planning/worker_host.py",
        "schemas/feed.schema.json",
    ):
        path = release / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (release / ".venv").symlink_to(checkout / ".venv", target_is_directory=True)
    selection = instance.dir / "planner/engine-release.json"
    selection.write_text(
        json.dumps({"schema_version": 1, "directory": str(release), "files": files})
    )
    return instance, checkout, release, selection


def test_uninstalled_uses_checkout_and_installed_preserves_exact_selection(
    tmp_path: Path,
) -> None:
    instance, checkout, release, selection = selected(tmp_path)
    original = selection.read_bytes()
    assert engine_project(instance, checkout) == release
    assert selection.read_bytes() == original
    selection.unlink()
    assert engine_project(instance, checkout) == checkout
    # Use the current guard against a retained history even for an old binary
    # with no capability declaration. The head alone no longer needs the key.
    store = instance.dir / "planner/workspace"
    store.mkdir()
    values = [b'{"installation":{"pv_string_links":[]}}', b"{}"]
    hashes = [hashlib.sha256(body).hexdigest() for body in values]
    for sha, body in zip(hashes, values, strict=True):
        blob = store / "blobs" / sha[:2] / sha
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_bytes(body)
    with sqlite3.connect(store / "workspace.sqlite") as db:
        db.execute("CREATE TABLE projects(id TEXT,revision INTEGER)")
        db.execute(
            "CREATE TABLE revisions(project_id TEXT,number INTEGER,input_sha256 TEXT)"
        )
        db.execute("INSERT INTO projects VALUES (?,2)", ("a" * 32,))
        db.executemany(
            "INSERT INTO revisions VALUES (?,?,?)",
            [("a" * 32, i, sha) for i, sha in enumerate(hashes, 1)],
        )
    current_guard = Path(__file__).resolve().parents[3] / "services/engine"
    with pytest.raises(ProcessError, match="retained project inputs"):
        require_input_compatibility(current_guard, store, [])
    require_input_compatibility(
        current_guard, store, ["installation_pv_string_links_v1"]
    )


@pytest.mark.parametrize(
    "change", ["altered", "missing", "extra", "symlink", "environment", "schema"]
)
def test_changed_or_incomplete_release_is_never_replaced_by_checkout(
    tmp_path: Path, change: str
) -> None:
    instance, checkout, release, _ = selected(tmp_path)
    source = release / "src/linker_engine/application.py"
    if change == "altered":
        source.write_text("changed")
    elif change == "missing":
        source.unlink()
    elif change == "extra":
        (release / "src/linker_engine/unbound.py").write_text("extra")
    elif change == "symlink":
        original = source.read_bytes()
        source.unlink()
        foreign = tmp_path / "foreign.py"
        foreign.write_bytes(original)
        source.symlink_to(foreign)
    elif change == "schema":
        (release / "schemas/feed.schema.json").write_text("changed validation")
    else:
        (release / ".venv").unlink()
        foreign_environment = tmp_path / "foreign-environment"
        foreign_python = foreign_environment / "bin/python"
        foreign_python.parent.mkdir(parents=True)
        foreign_python.touch()
        (release / ".venv").symlink_to(foreign_environment, target_is_directory=True)
    with pytest.raises(ProcessError, match="could not be verified"):
        engine_project(instance, checkout)


@pytest.mark.parametrize(
    "change", ["foreign", "parent", "bad_hash", "missing_entry", "malformed"]
)
def test_selection_cannot_escape_or_relax_the_source_binding(
    tmp_path: Path, change: str
) -> None:
    instance, checkout, release, selection = selected(tmp_path)
    value = json.loads(selection.read_bytes())
    if change == "foreign":
        value["directory"] = str(tmp_path / "foreign")
    elif change == "parent":
        value["files"]["../outside.py"] = "a" * 64
    elif change == "bad_hash":
        value["files"]["uv.lock"] = "wrong"
    elif change == "missing_entry":
        del value["files"]["src/linker_engine/application.py"]
    else:
        value = {"schema_version": True, "directory": str(release), "files": []}
    selection.write_text(json.dumps(value))
    original = selection.read_bytes()
    with pytest.raises(ProcessError, match="could not be verified"):
        engine_project(instance, checkout)
    assert selection.read_bytes() == original
