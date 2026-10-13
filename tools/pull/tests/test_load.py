"""Loading a snapshot into a real local WordPress: MySQL, PHP, WP-CLI, WordPress 7.1.3.

A "live" WordPress is installed under https://de-linker.com with the address in
the forms the live tables hold it (plain, JSON-escaped, URL-encoded, inside a
serialized option), dumped with mysqldump, given MariaDB's first line, and
pseudonymized into a snapshot with a licensed plugin, a theme and live plugins.
That snapshot is loaded into a second WordPress laid out as linker-local lays
out its instances. CI has none of these tools and skips the module; anywhere
else a missing tool fails it.
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from linker_local.instance import Instance, database_of

from linker_pull import load, manifest, sqldump
from linker_pull.anonymize import Anonymizer, accounts_from_dump

WORDPRESS = "7.1.3"
PORT = 8199  # only part of the address written into the database; nothing listens
SOURCE_DB = "linker_t6_pytest_source"
NAME = "t6_pytest"
SOCKET_QUERY = "SELECT @@socket"


def register(home: Path, name: str, port: int) -> None:
    """Write the instance into linker-local's registry, as `just up` would."""
    (home / "instances.toml").write_text(
        f"# test registry\n\n[{name}]\nport = {port}\nengine_port = {port - 1}\n"
        f"genie_port = {port - 2}\n"
    )


def tools_missing() -> list[str]:
    missing = []
    php = shutil.which(os.environ.get("PHP", "php"))
    version = (
        subprocess.run(
            [php, "-r", "echo PHP_MAJOR_VERSION, '.', PHP_MINOR_VERSION;"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        if php
        else ""
    )
    # The production host's PHP; WP-CLI 2.12 prints deprecations on newer ones.
    if version != "8.3":
        missing.append("PHP 8.3 in $PHP (`just test` sets it)")
    if shutil.which("wp") is None:
        missing.append("WP-CLI")
    if shutil.which("mysql") is None or shutil.which("mysqldump") is None:
        missing.append("mysql and mysqldump")
    elif subprocess.run(
        ["mysql", "--user=root", "-e", "SELECT 1"], capture_output=True, check=False
    ).returncode:
        missing.append("a MySQL server that `mysql -u root` reaches")
    return missing


if os.environ.get("CI") and tools_missing():
    pytest.skip("CI has no local WordPress stack", allow_module_level=True)


def mysql(sql: str) -> str:
    return subprocess.run(
        ["mysql", "--user=root", "--batch", "--skip-column-names", "-e", sql],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def wp(docroot: Path, *args: str) -> str:
    php = shutil.which(os.environ.get("PHP", "php"))
    wp_cli = shutil.which("wp")
    assert php and wp_cli, tools_missing()
    result = subprocess.run(
        [php, "-d", "memory_limit=1G", wp_cli, f"--path={docroot}", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"wp {' '.join(args)}: {result.stderr}"
    return result.stdout.strip()


def install(docroot: Path, database: str, url: str, core: Path) -> None:
    shutil.copytree(core, docroot)
    mysql(f"DROP DATABASE IF EXISTS `{database}`; CREATE DATABASE `{database}`")
    wp(
        docroot,
        "config",
        "create",
        f"--dbname={database}",
        "--dbuser=root",
        "--dbpass=",
        f"--dbhost=localhost:{mysql(SOCKET_QUERY)}",
        "--skip-check",
    )
    wp(
        docroot,
        "core",
        "install",
        f"--url={url}",
        "--title=t6",
        "--admin_user=owner",
        "--admin_password=unused-local-password",
        "--admin_email=owner@mail.example",
        "--skip-email",
    )


@pytest.fixture(scope="module")
def core(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """WordPress 7.1.3 without its default themes and plugins (WP-CLI caches the download)."""
    missing = tools_missing()
    assert not missing, f"missing: {', '.join(missing)} (docs/specs/6-live-pull.md)"
    directory = tmp_path_factory.mktemp("core") / "wordpress"
    wp(directory, "core", "download", f"--version={WORDPRESS}", "--skip-content")
    return directory


@pytest.fixture(scope="module")
def snapshot_dir(
    core: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Path]:
    work = tmp_path_factory.mktemp("live")
    docroot = work / "wordpress"
    install(docroot, SOURCE_DB, "https://de-linker.com", core)
    wp(
        docroot,
        "option",
        "add",
        "dlk_links",
        "--format=json",
        json.dumps(
            {
                "shop": "https://de-linker.com/products/",
                "json": '{"u":"https:\\/\\/de-linker.com\\/de\\/"}',
            }
        ),
    )
    wp(
        docroot,
        "post",
        "create",
        "--post_type=page",
        "--post_status=publish",
        "--post_title=Kontakt",
        '--post_content=<a href="https://de-linker.com/de/kontakt/">Kontakt</a> '
        '{"url":"https:\\/\\/de-linker.com\\/de\\/"} share?u=https%3A%2F%2Fde-linker.com%2Fde%2F',
    )
    for title in ("GW10K-ET", "GW8K-ET"):
        wp(
            docroot,
            "post",
            "create",
            "--post_type=product",
            "--post_status=publish",
            f"--post_title={title}",
        )
    attachment = wp(
        docroot,
        "post",
        "create",
        "--post_type=attachment",
        "--post_status=inherit",
        "--post_title=logo",
        "--post_mime_type=image/webp",
        "--porcelain",
    )
    wp(
        docroot,
        "post",
        "meta",
        "add",
        attachment,
        "_wp_attached_file",
        "2026/07/logo.webp",
    )
    wp(
        docroot,
        "user",
        "create",
        "jana",
        "jdoe@kunde.example",
        "--role=subscriber",
        "--user_pass=unused-local-password",
    )
    wp(
        docroot,
        "option",
        "update",
        "active_plugins",
        "--format=json",
        json.dumps(
            [
                "fake-licensed/fake-licensed.php",
                "code-snippets/code-snippets.php",
                "old-custom/old-custom.php",
            ]
        ),
    )
    dumped = subprocess.run(
        [
            "mysqldump",
            "--user=root",
            "--single-transaction",
            "--skip-dump-date",
            # The local server runs with GTIDs; the live MariaDB writes no GTID statements.
            "--set-gtid-purged=OFF",
            SOURCE_DB,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    mysql(f"DROP DATABASE `{SOURCE_DB}`")
    # The live dump's first line, which MySQL's client has to take as it is.
    lines = [
        "/*M!999999\\- enable the sandbox mode */ \n",
        *dumped.splitlines(keepends=True),
    ]

    snapshot = work / "snapshot"
    snapshot.mkdir()
    anonymizer = Anonymizer(accounts_from_dump(iter(lines)))
    stats = manifest.DatabaseStats()
    with gzip.open(snapshot / "db.sql.gz", "wt", encoding="utf-8") as out:
        for line in sqldump.write(
            stats.observe(anonymizer.process(sqldump.read(iter(lines))))
        ):
            out.write(line)
    files = {
        "uploads/2026/07/logo.webp": "image",
        "plugins/fake-licensed/fake-licensed.php": "<?php\n/**\n * Plugin Name: Fake licensed\n */\n",
        "themes/fake-theme/style.css": "/*\nTheme Name: Fake\n*/\n",
        "live/plugins/code-snippets/code-snippets.php": "<?php\n/**\n * Plugin Name: Code Snippets\n */\n",
        "live/plugins/old-custom/old-custom.php": "<?php\n/**\n * Plugin Name: Old custom\n */\n",
        "live/mu-plugins/old-loader.php": "<?php\n",
    }
    for relative, content in files.items():
        (snapshot / relative).parent.mkdir(parents=True, exist_ok=True)
        (snapshot / relative).write_text(content)
    (snapshot / "site").mkdir()
    # The live plugin list, as the snapshot's site/plugins.json holds it; this
    # "live" site runs no WooCommerce, and neither does the instance below.
    (snapshot / "site" / "plugins.json").write_text("[]\n")
    manifest.write(
        snapshot,
        {
            "format": manifest.FORMAT,
            "source": {"wordpress": WORDPRESS},
            "database": {"tables": stats.tables(), "posts": dict(stats.posts)},
            "files": manifest.file_entries(snapshot),
        },
    )
    yield snapshot


@pytest.fixture
def instance(core: Path, tmp_path: Path) -> Iterator[Instance]:
    home = tmp_path / "local"
    target = home / NAME / "wordpress"
    install(target, database_of(NAME), f"http://127.0.0.1:{PORT}", core)
    register(home, NAME, PORT)
    yield load.instance(NAME, None, home)
    mysql(f"DROP DATABASE IF EXISTS `{database_of(NAME)}`")


def test_the_snapshot_lands_with_every_form_of_the_live_address_rewritten(
    snapshot_dir: Path, instance: Instance
) -> None:
    said: list[str] = []
    # Uploads are merged in, as linker-local installs them: a local file stays.
    local_upload = instance.wp_content / "uploads" / "local-only.txt"
    local_upload.parent.mkdir(parents=True, exist_ok=True)
    local_upload.write_text("made here")

    result = load.load(instance, snapshot_dir, live_code=False, say=said.append)

    url = instance.url
    assert result == {
        "home": url,
        "published_products": {"snapshot": 2, "instance": 2},
        "attachments": {"snapshot": 1, "instance": 1},
        "attachment_files_missing": 0,
        "live_address_left": {
            "https://de-linker.com": 0,
            "https:\\/\\/de-linker.com": 0,
            "https%3A%2F%2Fde-linker.com": 0,
        },
        "staff_logins": ["owner"],  # the "live" administrator, for `just login --user`
        "ok": True,
    }
    docroot = instance.docroot
    assert wp(docroot, "option", "get", "siteurl") == url
    assert json.loads(wp(docroot, "option", "get", "dlk_links", "--format=json")) == {
        "shop": f"{url}/products/",
        "json": '{"u":"' + url.replace("/", "\\/") + '\\/de\\/"}',
    }
    page = wp(
        docroot,
        "post",
        "list",
        "--post_type=page",
        "--title=Kontakt",
        "--field=post_content",
    )
    assert f'href="{url}/de/kontakt/"' in page
    assert '"url":"' + url.replace("/", "\\/") + '\\/de\\/"' in page
    assert "share?u=http%3A%2F%2F127.0.0.1%3A8199%2Fde%2F" in page
    assert "de-linker.com" not in page
    assert wp(
        docroot, "user", "list", "--role=subscriber", "--field=user_email"
    ).startswith("customer-")
    assert (instance.wp_content / "uploads/2026/07/logo.webp").read_text() == "image"
    assert local_upload.read_text() == "made here"
    assert (instance.wp_content / "themes/fake-theme/style.css").is_file()
    assert json.loads(
        wp(docroot, "option", "get", "active_plugins", "--format=json")
    ) == ["fake-licensed/fake-licensed.php"]
    assert not (instance.wp_content / "plugins/old-custom").exists()
    # The snapshot replaced every password. admin.txt must not still offer the
    # one provision() wrote, and it must name a login that is still on the instance.
    note = instance.admin_file.read_text()
    assert "unused-local-password" not in note
    assert "owner" in note
    assert "just login" in note
    assert instance.admin_file.stat().st_mode & 0o777 == 0o600


def test_with_the_live_code_the_live_plugins_run_but_code_snippets(
    snapshot_dir: Path, instance: Instance
) -> None:
    result = load.load(instance, snapshot_dir, live_code=True, say=lambda message: None)

    assert result["ok"] is True
    active = json.loads(
        wp(instance.docroot, "option", "get", "active_plugins", "--format=json")
    )
    assert active == ["fake-licensed/fake-licensed.php", "old-custom/old-custom.php"]
    assert (instance.wp_content / "plugins/code-snippets/code-snippets.php").is_file()
    assert (instance.wp_content / "mu-plugins/old-loader.php").is_file()


def test_the_live_code_does_not_replace_plugins_linked_from_a_checkout(
    snapshot_dir: Path, instance: Instance, tmp_path: Path
) -> None:
    checkout = tmp_path / "checkout" / "linker-i18n"
    checkout.mkdir(parents=True)
    (instance.wp_content / "plugins" / "linker-i18n").symlink_to(
        checkout, target_is_directory=True
    )

    with pytest.raises(load.LoadError, match="runs plugins from a checkout"):
        load.load(instance, snapshot_dir, live_code=True, say=lambda message: None)


def test_an_instance_whose_wp_config_names_another_database_is_refused(
    snapshot_dir: Path, tmp_path: Path
) -> None:
    home = tmp_path / "local"
    docroot = home / "other" / "wordpress"
    docroot.mkdir(parents=True)
    (docroot / "wp-config.php").write_text(
        "<?php\ndefine( 'DB_NAME', 'linker_somebody_else' );\n"
        "if ( ! defined( 'ABSPATH' ) ) {\n\tdefine( 'ABSPATH', __DIR__ . '/' );\n}\n"
        "require_once ABSPATH . 'wp-settings.php';\n"
    )
    register(home, "other", PORT)

    with pytest.raises(
        load.LoadError, match="names database linker_somebody_else, not linker_other"
    ):
        load.load(
            load.instance("other", None, home),
            snapshot_dir,
            live_code=False,
            say=lambda message: None,
        )


def test_a_loaded_snapshot_rewrites_admin_txt_off_the_old_password(
    tmp_path: Path,
) -> None:
    """The note is the file a session reads; it must not keep a password the snapshot voided."""
    path = tmp_path / "t109" / "admin.txt"
    path.parent.mkdir()
    path.write_text(
        "url: http://127.0.0.1:8969/wp-admin/\nuser: local-admin\npassword: old-secret\n"
    )

    load.write_admin_note(
        path,
        "t109",
        "http://127.0.0.1:8969",
        ["857558227@qq.com"],
    )

    text = path.read_text()
    assert "old-secret" not in text
    assert "local-admin is not on this instance" in text
    assert "`857558227@qq.com`" in text
    assert "just login t109 --user=<login>" in text
    assert path.stat().st_mode & 0o777 == 0o600


def test_an_unregistered_name_is_refused(tmp_path: Path) -> None:
    with pytest.raises(load.LoadError, match="no instance nope"):
        load.instance("nope", None, tmp_path / "local")


def test_a_name_that_cannot_name_an_instance_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not an instance name"):
        load.instance("../elsewhere", None, tmp_path / "local")


def copied(snapshot: Path, tmp_path: Path) -> Path:
    """A writable copy of the snapshot, for tests that change it."""
    twin = tmp_path / "snapshot"
    shutil.copytree(snapshot, twin)
    return twin


def test_an_instance_of_another_wordpress_version_is_refused_before_anything(
    snapshot_dir: Path, instance: Instance, tmp_path: Path
) -> None:
    """The version guard fires before the database is replaced: the instance's
    own content survives the refusal."""
    twin = copied(snapshot_dir, tmp_path)
    data = manifest.read(twin)
    data["source"]["wordpress"] = "6.0.0"
    manifest.write(twin, data)
    wp(instance.docroot, "post", "create", "--post_title=survives", "--porcelain")

    with pytest.raises(load.LoadError, match="different versions.*WordPress"):
        load.load(instance, twin, live_code=False, say=lambda message: None)

    assert (
        "survives"
        in wp(instance.docroot, "post", "list", "--field=post_title").splitlines()
    )


def test_an_instance_without_the_snapshots_woocommerce_is_refused(
    snapshot_dir: Path, instance: Instance, tmp_path: Path
) -> None:
    """The live site runs WooCommerce; an instance that does not is not its copy."""
    twin = copied(snapshot_dir, tmp_path)
    (twin / "site" / "plugins.json").write_text(
        '[{"name": "woocommerce", "status": "active", "version": "11.2.0"}]\n'
    )

    with pytest.raises(load.LoadError, match="WooCommerce.*not installed"):
        load.load(instance, twin, live_code=False, say=lambda message: None)


def test_a_dump_that_does_not_match_its_manifest_is_refused(
    snapshot_dir: Path, instance: Instance, tmp_path: Path
) -> None:
    twin = copied(snapshot_dir, tmp_path)
    with gzip.open(twin / "db.sql.gz", "at", encoding="utf-8") as dump:
        dump.write("-- appended after the manifest was written\n")

    with pytest.raises(load.LoadError, match="does not match the sha256"):
        load.load(instance, twin, live_code=False, say=lambda message: None)


def test_an_unreadable_dump_is_refused(
    snapshot_dir: Path, instance: Instance, tmp_path: Path
) -> None:
    twin = copied(snapshot_dir, tmp_path)
    (twin / "db.sql.gz").write_bytes(b"not gzip at all")

    with pytest.raises(load.LoadError, match="not a readable dump"):
        load.load(instance, twin, live_code=False, say=lambda message: None)


def test_the_language_rule_tells_a_german_page_from_an_english_fallback() -> None:
    german = (
        '<html lang="de-DE"><body><h1>Wert verbinden. Für Sie da.</h1>'
        "<p>Wir liefern Speicher für Installateure und EPCs. Der Wechselrichter "
        "wird mit dem Akku geliefert und ist nicht Teil des Pakets. Die Batterie "
        "wird auf dem Dach montiert und mit dem Wechselrichter verbunden."
        "</p></body></html>"
    )
    fallback = (
        '<html lang="de-DE"><body><h1>Linking Value. Serving You.</h1>'
        "<p>We deliver storage for installers and EPCs. The inverter is shipped "
        "with the battery and is not part of the package. The battery will be "
        "mounted on your roof and connected with the inverter for your site."
        "</p></body></html>"
    )
    english_route = german.replace('lang="de-DE"', 'lang="en-GB"')

    assert load._reads_german(german)
    assert not load._reads_german(fallback)  # the route stays de; the words are not
    assert not load._reads_german(english_route)


def test_a_live_code_copy_without_any_german_page_to_check_is_refused(
    snapshot_dir: Path, instance: Instance, tmp_path: Path
) -> None:
    """The old i18n plugin installed but nothing holding German is not a copy
    of the live site; verify refuses instead of reporting ok."""
    twin = copied(snapshot_dir, tmp_path)
    stub = twin / "live" / "plugins" / "linker-i18n"
    stub.mkdir(parents=True)
    (stub / "linker-i18n.php").write_text(
        "<?php\n/**\n * Plugin Name: linker-i18n\n */\n"
    )

    with pytest.raises(load.LoadError, match="no page holds German"):
        load.load(instance, twin, live_code=True, say=lambda message: None)
