"""The launchd definition must survive release rotation and be the one loaded.

The 2026-11-11 instance repair found `com.linker.knowledge-publication` naming
`knowledge-worker/releases/<pruned>/.venv/bin/python`: every 900-second wakeup
exited 78 (EX_CONFIG) before the worker started, so no knowledge generation was
prepared or acknowledged. The renderer wrote whatever interpreter it was given,
the schedule named its runner inside the same release directory, and nothing read
back which definition launchctl had actually loaded.
"""

from __future__ import annotations

import importlib.util
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

OPS = Path(__file__).resolve().parents[1] / "ops"


def load() -> Any:
    spec = importlib.util.spec_from_file_location(
        "install_publication_worker", OPS / "install_publication_worker.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["install_publication_worker"] = module
    spec.loader.exec_module(module)
    return module


installer = load()

SETTINGS: dict[str, object] = {
    "interval_seconds": 900,
    "lease_seconds": 7200,
    "worker_id": "publication-618-mac",
    "loaded_url": "http://127.0.0.1:8902/knowledge/loaded",
    "host": "linker-services",
}


def source_at(root: Path) -> Path:
    (root / "ops").mkdir(parents=True)
    (root / "ops/install_publication_worker.py").write_text("")
    return root


def environment(tmp_path: Path) -> Path:
    path = tmp_path / "worker.env"
    path.write_text("LINKER_PUBLICATION_JOBS_URL=https://site.test/jobs\n")
    path.chmod(0o600)
    return path


def test_scheduled_interpreter_must_outlive_release_rotation(tmp_path: Path) -> None:
    reaped = tmp_path / "knowledge-worker/releases/1418dc26e14c/.venv/bin/python"
    reaped.parent.mkdir(parents=True)
    reaped.write_bytes(b"#!/bin/sh\n")
    with pytest.raises(ValueError, match="interpreter must outlive release rotation"):
        installer.rendered(
            environment(tmp_path), SETTINGS, reaped, source_at(tmp_path / "source")
        )
    stable = tmp_path / "knowledge-publication/venv/bin/python"
    assert installer.stable_interpreter(stable) == stable


def test_interpreter_symlink_is_kept_so_the_environment_keeps_its_packages(
    tmp_path: Path,
) -> None:
    # A virtual environment's bin/python is a symlink to the base interpreter.
    # Resolving it selects that base interpreter, which cannot import the
    # environment's own dependencies.
    base = tmp_path / "base/bin/python3.12"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"")
    dedicated = tmp_path / "knowledge-publication/venv/bin/python"
    dedicated.parent.mkdir(parents=True)
    dedicated.symlink_to(base)
    assert installer.stable_interpreter(dedicated) == dedicated
    escape = tmp_path / "linked/venv/bin/python"
    escape.parent.mkdir(parents=True)
    escape.symlink_to(
        tmp_path / "knowledge-worker/releases/1418dc26e14c/.venv/bin/python"
    )
    with pytest.raises(ValueError, match="interpreter must outlive release rotation"):
        installer.stable_interpreter(escape)


def test_scheduled_source_must_outlive_release_rotation(tmp_path: Path) -> None:
    # The interpreter alone is not enough: the runner script, the worker and the
    # working directory all come from the same release root.
    reaped = source_at(tmp_path / "knowledge-worker/releases/db0fddffa-main")
    with pytest.raises(ValueError, match="worker source must outlive release rotation"):
        installer.rendered(
            environment(tmp_path), SETTINGS, Path(sys.executable), reaped
        )
    stable = source_at(tmp_path / "knowledge-publication/source")
    assert installer.stable_source(stable) == stable


def test_definition_names_the_stable_source_and_imports_it(tmp_path: Path) -> None:
    stable = source_at(tmp_path / "knowledge-publication/source")
    content = installer.rendered(
        environment(tmp_path), SETTINGS, Path(sys.executable), stable
    )
    definition = plistlib.loads(content)
    arguments = definition["ProgramArguments"]
    assert arguments[1:3] == ["-B", str(stable / "ops/install_publication_worker.py")]
    assert definition["WorkingDirectory"] == str(stable)
    # The dedicated environment is not an editable release install, so the
    # worker's own package has to be named explicitly.
    assert definition["EnvironmentVariables"]["PYTHONPATH"] == str(stable / "src")
    # Nothing the definition names may sit under a release root.
    named = [*arguments, definition["WorkingDirectory"]]
    named += list(definition["EnvironmentVariables"].values())
    assert not [value for value in named if "/releases/" in value]
    assert "--host" in arguments and "linker-services" in arguments


def test_installer_refuses_an_interpreter_that_cannot_run_the_worker(
    tmp_path: Path,
) -> None:
    broken = tmp_path / "broken-python"
    broken.write_text("#!/bin/sh\necho 'No module named docling' >&2\nexit 1\n")
    broken.chmod(0o755)
    with pytest.raises(RuntimeError, match="cannot run the publication worker"):
        installer.verify_interpreter(broken, source_at(tmp_path / "source"))
    source = source_at(tmp_path / "working")
    (source / "ops/publication_worker.py").write_text(
        "import sys\nprint('--loaded-url')\nsys.exit(0)\n"
    )
    installer.verify_interpreter(Path(sys.executable), source)


def test_installer_refuses_a_label_that_owns_the_retained_definition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    target = home / "Library/LaunchAgents" / (installer.LABEL + ".plist")
    target.parent.mkdir(parents=True)
    prior = plistlib.dumps({"ProgramArguments": ["previous"]})
    target.write_bytes(prior)
    retained = target.with_suffix(".previous.plist")
    monkeypatch.setattr(installer.Path, "home", lambda: home)
    stable = source_at(tmp_path / "knowledge-publication/source")
    # Bootstrap succeeds, yet the label keeps the retained .previous file
    # loaded; the edited plist would never be consulted.
    state = {"loaded": False}

    def launchctl(
        arguments: list[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        if arguments[1] == "bootstrap":
            assert retained.exists()
            state["loaded"] = True
            return subprocess.CompletedProcess(arguments, 0, "", "")
        if not state["loaded"]:
            return subprocess.CompletedProcess(
                arguments, 113, "", f'Could not find service "{installer.LABEL}"'
            )
        return subprocess.CompletedProcess(
            arguments, 0, f"path = {retained}\narguments = {{\nprevious\n}}\n", ""
        )

    monkeypatch.setattr(installer.subprocess, "run", launchctl)
    content = installer.rendered(
        environment(tmp_path), SETTINGS, Path(sys.executable), stable
    )
    with pytest.raises(RuntimeError, match="owns_a_different_definition"):
        installer.install_definition(content)
    # The failed install restores the inspectable original rather than leaving
    # the new definition on disk for a later bootstrap to pick up.
    assert target.read_bytes() == prior


def test_installer_confirms_the_written_definition_is_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    target = home / "Library/LaunchAgents" / (installer.LABEL + ".plist")
    target.parent.mkdir(parents=True)
    monkeypatch.setattr(installer.Path, "home", lambda: home)
    stable = source_at(tmp_path / "knowledge-publication/source")
    content = installer.rendered(
        environment(tmp_path), SETTINGS, Path(sys.executable), stable
    )
    arguments = plistlib.loads(content)["ProgramArguments"]
    rendered_arguments = "\n".join(
        f"\t\t{index} = {value}" for index, value in enumerate(arguments, start=1)
    )

    def launchctl(call: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if call[1] == "print":
            return subprocess.CompletedProcess(
                call,
                0,
                f"\tpath = {target}\n\targuments = {{\n{rendered_arguments}\n\t}}\n",
                "",
            )
        return subprocess.CompletedProcess(call, 0, "", "")

    monkeypatch.setattr(installer.subprocess, "run", launchctl)
    installer.install_definition(content)
    assert plistlib.loads(target.read_bytes())["ProgramArguments"] == arguments
