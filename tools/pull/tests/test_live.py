"""The production host is only ever read: what this tool may run there."""

from __future__ import annotations

import gzip
import os
import subprocess
from pathlib import Path

import pytest

from linker_pull import live


@pytest.mark.parametrize(
    "command",
    [
        ("option", "update", "blogname", "x"),
        ("db", "export", "-"),
        ("db", "import", "dump.sql"),
        ("db", "query", "DELETE FROM wp_options"),
        ("plugin", "activate", "x"),
        ("search-replace", "a", "b"),
        ("eval", "echo 1;"),
        ("core",),
    ],
)
def test_wp_cli_runs_only_read_only_commands(command: tuple[str, ...]) -> None:
    # Refused before anything reaches ssh.
    with pytest.raises(live.LiveError, match="not one of the read-only commands"):
        live.wp(*command)


def test_every_remote_wp_cli_command_skips_loading_plugins_and_themes() -> None:
    for args in (
        ("core", "version"),
        ("config", "get", "DB_NAME"),
        ("plugin", "list", "--fields=name,status,version,file"),
        ("theme", "list", "--fields=name,status,version"),
        ("user", "list", "--fields=ID,user_login,user_email,roles"),
    ):
        command = live.wp_command(args)

        assert "--skip-plugins" in command and "--skip-themes" in command, command


@pytest.mark.parametrize(
    "args",
    [
        ("plugin", "list", "--fields=name,status,version,file"),
        ("theme", "list", "--fields=name,status,version"),
    ],
)
def test_extension_lists_never_refresh_the_update_transients(
    args: tuple[str, ...],
) -> None:
    # `plugin list`/`theme list` without --skip-update-check delete the
    # update_plugins/update_themes site transients on the host and ask
    # WordPress to rebuild them (CommandWithUpgrade::_list(), wp-cli 2.12.0).
    assert "--skip-update-check" in live.wp_command(args)


@pytest.mark.parametrize(
    "args", [("core", "version"), ("user", "list", "--fields=ID,user_login")]
)
def test_no_other_command_carries_the_list_only_flag(args: tuple[str, ...]) -> None:
    # The flag is documented on plugin/theme list alone (Plugin_Command.php:1431,
    # Theme_Command.php:880); on other commands it is an unknown parameter.
    assert "--skip-update-check" not in live.wp_command(args)


def test_rsync_copies_from_the_host_into_a_local_directory(tmp_path: Path) -> None:
    command = live.rsync_command(
        "wp-content/uploads/",
        tmp_path / "uploads",
        filters=("--exclude=*",),
        link_dest=[tmp_path / "previous"],
    )

    assert command[-2:] == [
        f"hostinger-de-linker:{live.WP_ROOT}/wp-content/uploads/",
        str(tmp_path / "uploads"),
    ]
    assert "--exclude=*" in command
    assert f"--link-dest={tmp_path / 'previous'}" in command
    assert command[command.index("-e") + 1] == "ssh -o BatchMode=yes"


@pytest.mark.parametrize("source", ["/etc/", "wp-content/../../", "../x"])
def test_rsync_stays_inside_the_wordpress_root(source: str, tmp_path: Path) -> None:
    with pytest.raises(live.LiveError, match="not a path inside"):
        live.rsync_command(source, tmp_path)


def test_the_dump_hands_the_password_only_to_mysqldump_s_environment(
    tmp_path: Path,
) -> None:
    """dump_script() run against stand-ins for WP-CLI and mysqldump."""
    root = tmp_path / "public_html"
    root.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # The stand-in answers `config get <name>` with the last argument, whatever
    # flags precede it, as the real WP-CLI would.
    (bin_dir / "wp").write_text(
        "#!/bin/sh\n"
        'name=""; for arg in "$@"; do case "$arg" in --*) ;; *) name="$arg" ;; esac; done\n'
        'case "$name" in\n'
        "  DB_PASSWORD) echo 's3cr3t pass' ;;\n"
        "  DB_HOST) echo 127.0.0.1 ;;\n"
        "  DB_USER) echo u1 ;;\n"
        "  DB_NAME) echo db1 ;;\n"
        "esac\n"
    )
    (bin_dir / "mysqldump").write_text(
        '#!/bin/sh\nfor arg in "$@"; do echo "arg $arg"; done\necho "env $MYSQL_PWD"\necho "cwd $PWD"\n'
    )
    for tool in ("wp", "mysqldump"):
        (bin_dir / tool).chmod(0o755)

    result = subprocess.run(
        ["bash", "-c", live.dump_script(root=str(root), wp_cli=str(bin_dir / "wp"))],
        capture_output=True,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        check=True,
    )

    lines = gzip.decompress(result.stdout).decode().splitlines()
    arguments = [line.removeprefix("arg ") for line in lines if line.startswith("arg ")]
    assert arguments == [
        "--single-transaction",
        "--quick",
        "--skip-dump-date",
        "--order-by-primary",
        "--default-character-set=utf8mb4",
        "--host=127.0.0.1",
        "--user=u1",
        "db1",
    ]
    assert "env s3cr3t pass" in lines
    assert f"cwd {root}" in lines


def test_the_dumps_wp_config_get_runs_without_loading_the_sites_plugins(
    tmp_path: Path,
) -> None:
    """A stand-in WP-CLI that fails on --skip-plugins/--skip-themes proves the
    dump script passes them: the live plugins never initialize under a read."""
    root = tmp_path / "public_html"
    root.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "wp").write_text(
        "#!/bin/sh\n"
        'for arg in "$@"; do case "$arg" in --skip-plugins|--skip-themes) exit 0 ;; esac; done\n'
        "exit 1  # no flags: the old plugins would load\n"
    )
    (bin_dir / "mysqldump").write_text("#!/bin/sh\n")
    for tool in ("wp", "mysqldump"):
        (bin_dir / tool).chmod(0o755)

    result = subprocess.run(
        ["bash", "-c", live.dump_script(root=str(root), wp_cli=str(bin_dir / "wp"))],
        capture_output=True,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_the_page_addresses_of_a_sitemap() -> None:
    xml = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        b' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
        b"<url><loc>https://de-linker.com/de/</loc></url>"
        b"<url><loc> https://de-linker.com/de/produkt/gw10k-et/ </loc>"
        b"<image:image><image:loc>https://de-linker.com/wp-content/uploads/2026/07/a.webp</image:loc></image:image>"
        b"</url>"
        b"</urlset>"
    )
    index = (
        b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<sitemap><loc>https://de-linker.com/page-sitemap1.xml</loc></sitemap>"
        b"</sitemapindex>"
    )

    assert live.sitemap_urls(xml) == [
        "https://de-linker.com/de/",
        "https://de-linker.com/de/produkt/gw10k-et/",
    ]
    assert live.sitemap_urls(index) == []


@pytest.mark.parametrize(
    "args",
    [
        ("option", "get", "admin_email"),
        ("option", "get", "seopress_pro_license_key"),
        ("option", "get", "lc_apikey", "--format=json"),
        ("option", "get"),
    ],
)
def test_option_get_reads_only_the_licence_state_a_local_instance_reuses(
    args: tuple[str, ...],
) -> None:
    # Everything else of wp_options reaches this Mac through the
    # pseudonymized dump (licenses.py, #252); the key is the owner's file's.
    with pytest.raises(live.LiveError, match="outside LIVE_OPTIONS"):
        live.wp_command(args)


def test_the_licence_options_are_read_without_loading_plugins() -> None:
    for name in sorted(live.LIVE_OPTIONS):
        command = live.wp_command(("option", "get", name))

        assert command.endswith(f"option get {name}")
        assert "--skip-plugins" in command and "--skip-themes" in command
