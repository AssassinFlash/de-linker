import os
import sys
from pathlib import Path

import pytest

from linker_local import wpcli
from linker_local.instance import Instance
from linker_local.wpcli import WpCli, WpCliError


@pytest.fixture
def fake_wp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A `wp` on PATH that, run by Python in place of PHP, prints a version."""
    script = tmp_path / "bin" / "wp"
    script.parent.mkdir()
    script.write_text("print('WP-CLI 2.12.0')\n")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{script.parent}:/usr/bin:/bin")
    return script


def test_runs_wp_cli_under_the_given_php_with_the_instance_ini(
    tmp_path: Path, fake_wp: Path
) -> None:
    instance = Instance("a", 8888, 8889, 8890, tmp_path)

    command = WpCli(Path("/php83"), instance).command("core", "version")

    assert command == [
        "/php83",
        "-c",
        str(instance.php_ini),
        str(fake_wp),
        f"--path={instance.docroot}",
        "core",
        "version",
    ]


def test_wp_cli_keeps_project_configuration_without_research_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "environ", {"APIFY_TOKEN_PRIMARY": "synthetic-research"})
    environment = wpcli.environment(
        {"LINKER_LOCAL_LOGIN": "local-admin", "APIFY_TOKEN_ALT": "synthetic-extra"}
    )
    assert not any(key.startswith("APIFY_") for key in environment)

    assert environment["WP_CLI_DISABLE_AUTO_CHECK_UPDATE"] == "1"
    assert environment["LINKER_LOCAL_LOGIN"] == "local-admin"


def test_accepts_wp_cli_2_12(fake_wp: Path) -> None:
    wpcli.require_version(Path(sys.executable))


def test_refuses_another_wp_cli_version(fake_wp: Path) -> None:
    fake_wp.write_text("print('WP-CLI 2.13.0')\n")

    with pytest.raises(WpCliError, match="2.12 is required"):
        wpcli.require_version(Path(sys.executable))
