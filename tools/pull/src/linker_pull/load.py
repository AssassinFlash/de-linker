"""`linker-pull load <name> <snapshot>`: a snapshot into a local WordPress instance.

The instance is linker-local's (docs/specs/5-local-stack.md): found by name in
its Registry (`just up <name>` creates and registers it), with WordPress in
wordpress/ of its directory and the database linker_<name> that its
wp-config.php must name, with the live table prefix wp_.

Loading first refuses what it must not touch: an instance whose WordPress or
WooCommerce version differs from the snapshot's (the live site updates itself;
a database its newer version has migrated has no way back onto older code), a
dump that does not match its manifest, and, with live_code, an instance whose
plugins point into a checkout (the live code would replace them). Only then
does it replace every wp_ table with the snapshot's, rewrite the live address
to the local one (as written, JSON-escaped and URL-encoded; WP-CLI keeps
serialized values valid) and empty the object cache, which still holds the old
database's values (the local stack runs Redis).

The snapshot's files — plugins, themes, uploads, and with live_code the live
plugins and must-use plugins — are installed by linker-local's
snapshot.install, the one implementation of that rule. Without live_code the
plugins the instance had (ours from the checkout) plus every other plugin live
runs stay active, the third-party ones at the live version; with it the live
list stays, so the instance is a copy of the live site. Code Snippets stays
off either way: its table is data here. The instance must keep mail and
outgoing requests on this Mac (linker-local's isolation mu-plugin does).

With live_code, the address rewrite breaks the old i18n plugin's German
freshness gate: the stored German was fingerprinted over a body that held the
live address, and the rewritten body no longer matches, so the plugin serves
the English fallback (18 of the 316 German pages on 2026-10-10, the home
among them). `_refresh_german()` repairs exactly those posts — recomputing
every fingerprint THROUGH THE PLUGIN'S OWN CODE (wp eval-file in the
instance; the sha formula is never copied here) and only where undoing the
address rewrite on a copy of the content reproduces the stored fingerprint,
which proves the mismatch is the rewrite's doing and not German that was
already stale on live. This is transitional scaffolding around the old
plugin's rule, and it goes when #18 deletes the old plugins.

The users afterwards are the snapshot's: staff accounts keep their logins,
so a login link for one of them (`just login <name> --user <login>`) opens
wp-admin; the result lists those logins.

Then it applies the local licences (licenses.py: SEOPress PRO's key from the
owner's file, LiveCanvas's site apikey and SEOPress's status from live), so
wp-admin opens without activation banners, and writes snapshot.json beside the
instance: which snapshot it holds and when that was taken.

Finally it compares the instance with the snapshot's manifest (published
products, attachments, the files of the attachments, leftovers of the live
address) and reports what differs. With live_code and the old i18n plugin
installed it also spot-checks that German pages serve German (the language
a `--live-code` copy promises), so a freshness fallback cannot hide behind
`ok: true` again.
"""

from __future__ import annotations

import gzip
import http.client
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from linker_local import snapshot as local_snapshot
from linker_local import wordpress as local_wordpress
from linker_local.instance import Instance, check_name
from linker_local.instance import home as local_home
from linker_local.registry import Registry

from linker_pull import licenses, live, manifest
from linker_pull.anonymize import TABLE_PREFIX
from linker_pull.snapshot import DATABASE

Say = Callable[[str], None]

# Code Snippets' table travels as data; the plugin never runs locally (docs/specs/6-live-pull.md).
NEVER_ACTIVE = ("code-snippets",)
# WP-CLI with the live plugins loaded (`wp rewrite flush`) peaks at 171 MB
# (measured 2026-10-09) and dies at PHP's default 128M. 2048M is the live
# host's limit, which the local stack's php.ini copies (docs/specs/5-local-stack.md).
MEMORY_LIMIT = "2048M"
# Commands that only touch the database need neither plugins nor themes; the
# live plugins would otherwise run on every one of them.
SKIP = ("--skip-plugins", "--skip-themes")


class LoadError(RuntimeError):
    """The snapshot could not be loaded into the instance."""


def instance(name: str, port: int | None, home: Path | None = None) -> Instance:
    """The instance called `name`, as linker-local's registry states it.

    `--port` overrides the address written into the database, for an instance
    served somewhere other than its registered port.
    """
    check_name(name)
    found = Registry(home or local_home()).get(name)
    if found is None:
        raise LoadError(
            f"no instance {name} in the registry: `just up {name}` creates it"
        )
    if port is not None and port != found.port:
        found = replace(found, port=port)
    if not (found.docroot / "wp-config.php").is_file():
        raise LoadError(
            f"{found.docroot} has no wp-config.php: not a WordPress instance"
        )
    return found


class WpCli:
    """WP-CLI on the instance, with the PHP in $PHP (the justfile's PHP 8.3)."""

    def __init__(self, target: Instance) -> None:
        php = shutil.which(os.environ.get("PHP", "php"))
        wp = shutil.which("wp")
        if php is None or wp is None:
            raise LoadError("PHP ($PHP) and WP-CLI (`wp`) are needed")
        self.prefix = [
            php,
            "-d",
            f"memory_limit={MEMORY_LIMIT}",
            wp,
            f"--path={target.docroot}",
        ]

    def run(self, *args: str, stdin: Iterator[bytes] | None = None) -> str:
        """A command; its standard output without the trailing newline.

        `stdin` is streamed in; the output goes to temporary files meanwhile, so
        a command that writes while it reads cannot block on a full pipe.
        """
        environment = {**os.environ, "WP_CLI_DISABLE_AUTO_CHECK_UPDATE": "1"}
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            with subprocess.Popen(
                [*self.prefix, *args],
                stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                env=environment,
            ) as process:
                if stdin is not None:
                    assert process.stdin is not None
                    try:
                        for chunk in stdin:
                            process.stdin.write(chunk)
                    except BrokenPipeError:
                        pass  # the command stopped reading; its status says why
            out.seek(0)
            err.seek(0)
            output = out.read().decode(errors="replace")
            error = err.read().decode(errors="replace")
        if process.returncode != 0:
            raise LoadError(f"wp {' '.join(args)}: {(error or output).strip()}")
        return output.rstrip("\n")

    def query(self, sql: str) -> list[str]:
        """Rows of a read-only query, one tab-separated line each."""
        output = self.run("db", "query", sql, "--skip-column-names", *SKIP)
        return output.splitlines() if output else []


def load(
    target: Instance, snapshot: Path, live_code: bool, say: Say
) -> dict[str, object]:
    data = manifest.read(snapshot)
    wp = WpCli(target)
    database = wp.run("config", "get", "DB_NAME")
    if database != target.database:
        raise LoadError(
            f"{target.docroot}/wp-config.php names database {database}, not {target.database}"
        )
    # The dump's tables are wp_ tables; WordPress must read those.
    prefix = wp.run("config", "get", "table_prefix")
    if prefix != TABLE_PREFIX:
        raise LoadError(
            f"{target.docroot}/wp-config.php has table prefix {prefix}, not {TABLE_PREFIX}"
        )
    _require_versions(target, data, snapshot)
    _require_dump(snapshot, data)
    plugins_dir = target.wp_content / "plugins"
    linked = sorted(path.name for path in plugins_dir.glob("*") if path.is_symlink())
    if live_code and linked:
        raise LoadError(
            f"{target.name} runs plugins from a checkout ({', '.join(linked)}); "
            "the live code would replace them, so a copy of the live site needs an instance without"
        )
    before = _active_plugins(wp)

    say(f"database: importing {snapshot / DATABASE} into {target.database}")
    wp.run("db", "clean", "--yes", *SKIP)
    wp.run("db", "import", "-", *SKIP, stdin=_dump(snapshot / DATABASE))
    for old, new in replacements(live.URL, target.url):
        count = wp.run(
            "search-replace",
            old,
            new,
            "--all-tables-with-prefix",
            "--format=count",
            *SKIP,
        )
        say(f"search-replace {old} -> {new}: {count} replacements")
    # The tables changed under WordPress: what a persistent object cache holds is stale.
    wp.run("cache", "flush", *SKIP)

    say("files: uploads, plugins, themes" + (", live plugins" if live_code else ""))
    local_snapshot.install(target, snapshot, live_code=live_code)

    live_active = _active_plugins(wp)
    if live_code:
        wanted = live_active
    else:
        # Ours stay the checkout's (before); every other plugin live runs —
        # the licensed ones and the third-party ones snapshot.install brought
        # at the live version — runs here too (#252).
        wanted = before + [
            entry
            for entry in live_active
            if not entry.split("/")[0].startswith(local_snapshot.OURS)
        ]
    active = [
        entry
        for entry in dict.fromkeys(wanted)
        if (plugins_dir / entry).is_file() and entry.split("/")[0] not in NEVER_ACTIVE
    ]
    wp.run(
        "option", "update", "active_plugins", json.dumps(active), "--format=json", *SKIP
    )
    say(f"active plugins: {', '.join(entry.split('/')[0] for entry in active)}")
    german = _refresh_german(target, say) if live_code else None
    wp.run("rewrite", "flush")
    _bind_publication(wp, say, active)
    # The dump replaced every user_pass with an irreversible placeholder
    # (anonymize.local_password). The password provision() wrote into admin.txt
    # no longer opens anything, and the file is the only place a session looks
    # for one. Rewrite it here, where the replacement happens, so the next
    # session reads the logins that still work instead of a password that does not.
    staff = [
        login
        for login in wp.run(
            "user",
            "list",
            "--role__in=administrator,shop_manager",
            "--field=user_login",
            *SKIP,
        ).splitlines()
        if login
    ]
    write_admin_note(target.admin_file, target.name, target.url, staff)
    keys = licenses.apply(wp)
    for product, outcome in keys.items():
        say(f"licence {product}: {outcome}")
    write_snapshot_note(target, snapshot, data)
    result = verify(wp, target, data["database"]["posts"], german)
    result["licences"] = keys
    result["snapshot"] = snapshot_note(snapshot, data)
    # A licence left out brings the activation banners back (#252): not ok.
    result["ok"] = bool(result["ok"]) and all(
        outcome.startswith("applied") for outcome in keys.values()
    )
    return result


def snapshot_note(snapshot: Path, data: dict[str, Any]) -> dict[str, str]:
    """Which snapshot an instance holds and when it was taken (manifest `created`, UTC)."""
    return {"name": snapshot.name, "taken": str(data["created"])}


def write_snapshot_note(target: Instance, snapshot: Path, data: dict[str, Any]) -> None:
    """Record the loaded snapshot beside the instance, where `just status` reads it.

    A session can then tell how far its local copy trails live (#252: the
    snapshot every instance held on 2026-10-17 was two days old, and nothing
    said so).
    """
    note = {
        **snapshot_note(snapshot, data),
        "loaded": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    target.snapshot_file.write_text(json.dumps(note, indent=2) + "\n")


def write_admin_note(path: Path, name: str, url: str, staff: list[str]) -> None:
    """Rewrite admin.txt for the accounts a loaded snapshot left.

    provision() writes `url`/`user`/`password` for local-admin. A loaded
    snapshot replaces that account's password with a placeholder no one knows,
    and may remove the account. The file then has to say which logins remain
    and that each one is opened with `just login`, not with the old password.
    """
    lines = [f"url: {url}/wp-admin/"]
    if local_wordpress.ADMIN_USER in staff:
        lines.append(f"user: {local_wordpress.ADMIN_USER}")
        lines.append(
            "password: none — the snapshot replaced this account's password "
            "with an irreversible placeholder, so the password provision() wrote "
            "here no longer matches. Sign in with "
            f"`just login {name} --user={local_wordpress.ADMIN_USER}`."
        )
        others = [login for login in staff if login != local_wordpress.ADMIN_USER]
    else:
        lines.append(
            "password: none — the snapshot replaced every account password with "
            "an irreversible placeholder, and local-admin is not on this instance. "
            "Sign in with `just login "
            f"{name} --user=<login>`."
        )
        others = staff
    if others:
        listed = ", ".join(f"`{login}`" for login in others)
        lines.append(
            "Also present: "
            + listed
            + ". Each password is the same irreversible placeholder. Sign one in with "
            + f"`just login {name} --user=<login>`."
        )
    elif not staff:
        lines.append("No administrator or shop manager remains on this instance.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600)
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)


def _refresh_german(target: Instance, say: Say) -> list[str] | None:
    """Repair the old i18n plugin's German freshness fingerprints the address
    rewrite broke, and return German page paths for verify() to spot-check.

    Transitional scaffolding around the old plugin's rule (docs/specs/6-live-pull.md,
    2026-10-10): it goes when #18 deletes the old plugins. The fingerprints are
    recomputed by the plugin's own Translator, through a wp eval-file driver run
    in the instance — the sha formula is never reimplemented here. A post is
    repaired only when the plugin's own content_sha() over an address-undone
    copy of the content equals the stored fingerprint: the mismatch is then the
    rewrite's doing, not German that was stale on live already (that stale
    state stays as it was, gate and all). None when the old i18n plugin is not
    installed (a snapshot's live/ always has it; a test harness's does not).
    """
    if not (target.wp_content / "plugins" / "linker-i18n").is_dir():
        return None
    live_forms = [old for old, _ in replacements(live.URL, target.url)]
    local_forms = [new for _, new in replacements(live.URL, target.url)]
    pairs = json.dumps(
        [list(pair) for pair in zip(local_forms, live_forms, strict=True)]
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".php", encoding="utf-8", delete=False
    ) as driver:
        driver.write(_GERMAN_DRIVER)
        driver_path = Path(driver.name)
    try:
        # No SKIP flags: the driver needs the plugins loaded — they are active
        # by now — and every fingerprint comes from the plugin's own classes.
        output = WpCli(target).run("eval-file", str(driver_path), pairs)
    finally:
        driver_path.unlink(missing_ok=True)
    report = json.loads(output or "{}")
    say(
        f"german: {report.get('repaired', 0)} pages' fingerprints recomputed"
        f" ({report.get('stale_left', 0)} stale before the load stay stale)"
    )
    return [str(path) for path in report.get("german_pages", [])]


# Runs inside the instance (`wp eval-file <file> <json-pairs>`); the positional
# arguments arrive as $args (EvalFile_Command.php). Every fingerprint is the
# plugin's own (Translator::content_sha, Document::key, Translator::mark_current)
# — this file only drives them, so the rule has one implementation.
_GERMAN_DRIVER = r"""<?php
$pairs = json_decode($args[0] ?? '[]', true);
$undo = function ($text) use ($pairs) {
    return str_replace(array_column($pairs, 0), array_column($pairs, 1), (string) $text);
};
if (!class_exists('Linker\\I18n\\Translator')) {
    wp_send_json(array('repaired' => 0, 'stale_left' => 0, 'german_pages' => array()));
}
global $wpdb;
$ids = $wpdb->get_col(
    "SELECT post_id FROM {$wpdb->postmeta}"
    . " WHERE meta_key = '_linker_de_content' AND meta_value <> ''"
);
// The front page first, so the spot-check covers the home a visitor lands on.
$front = (int) get_option('page_on_front');
usort($ids, function ($a, $b) use ($front) { return ($b == $front) - ($a == $front); });
$repaired = 0;
$stale = 0;
$german = array();
foreach ($ids as $id) {
    $post = get_post((int) $id);
    if (!$post) {
        continue;
    }
    $stored = (string) get_post_meta($id, 'Linker\\I18n\\Translator'::META_SOURCE_SHA, true);
    // The plugin's own formula over the post as it is now.
    if ($stored !== 'Linker\\I18n\\Translator'::content_sha($id, $post)) {
        // Prove the mismatch is the address rewrite alone: the same plugin
        // formula over a copy of the content with the rewrite undone.
        $undone = clone $post;
        $undone->post_content = $undo($post->post_content);
        $payload = get_post_type($id) === 'product'
            ? 'Linker\\I18n\\Product'::source_payload($id)
            : null;
        if ('Linker\\I18n\\Translator'::content_sha($id, $undone, $payload !== null ? $undo($payload) : null) !== $stored) {
            $stale++;
            continue;
        }
        'Linker\\I18n\\Translator'::mark_current($id);
        $repaired++;
    }
    // The excerpt has its own axis; the same proof, the same plugin key.
    $es = (string) get_post_meta($id, 'Linker\\I18n\\Translator'::META_EXCERPT_SHA, true);
    if ($es !== '' && $es !== sha1('Linker\\I18n\\Document'::key($post->post_excerpt))) {
        if (sha1('Linker\\I18n\\Document'::key($undo($post->post_excerpt))) === $es) {
            update_post_meta(
                $id,
                'Linker\\I18n\\Translator'::META_EXCERPT_SHA,
                sha1('Linker\\I18n\\Document'::key($post->post_excerpt))
            );
        }
    }
    if (count($german) < 3) {
        $path = (string) wp_parse_url(get_permalink($id), PHP_URL_PATH);
        $de = class_exists('Linker_I18n_Router') ? Linker_I18n_Router::to_de($path) : $path;
        if ($de !== '') {
            $german[] = $de;
        }
    }
}
wp_send_json(array('repaired' => $repaired, 'stale_left' => $stale, 'german_pages' => $german));
"""


def _require_versions(target: Instance, data: dict[str, Any], snapshot: Path) -> None:
    """Refuse the load before anything is destroyed when the instance's
    WordPress or WooCommerce is not the snapshot's version.

    The live site updates itself (WooCommerce 11.1.0 became 11.2.0 on
    2026-10-09); a database its newer version has migrated has no migration
    path back onto older code. #5's spec amendment, 2026-10-09.
    """
    wanted = {
        "WordPress": str(data["source"]["wordpress"]),
        "WooCommerce": _snapshot_woocommerce(snapshot),
    }
    installed = local_wordpress.versions(target)
    drift = [
        f"{name}: instance {installed.get(name) or 'not installed'}, "
        f"snapshot {version or 'not in the snapshot'}"
        for name, version in wanted.items()
        if installed.get(name) != version
    ]
    if drift:
        raise LoadError(
            "the instance and the snapshot hold different versions — "
            f"`just reset {target.name}` rebuilds the instance: " + "; ".join(drift)
        )


def _snapshot_woocommerce(snapshot: Path) -> str | None:
    """The live WooCommerce's version, as the snapshot's site/plugins.json states it."""
    plugins = json.loads((snapshot / "site" / "plugins.json").read_text())
    for plugin in plugins:
        if str(plugin.get("name")) == "woocommerce":
            version = plugin.get("version")
            return str(version) if version else None
    return None


def _require_dump(snapshot: Path, data: dict[str, Any]) -> None:
    """The dump must be readable gzip and match its manifest before it replaces a database."""
    path = snapshot / DATABASE
    expected = data["files"].get(DATABASE, {}).get("sha256")
    if expected is None:
        raise LoadError(f"the manifest of {snapshot} lists no {DATABASE}")
    try:
        with gzip.open(path, "rb") as dump:
            if not dump.read(1):
                raise OSError("the dump is empty")
    except OSError as broken:
        raise LoadError(f"{path} is not a readable dump: {broken}") from broken
    if manifest.sha256_file(path) != expected:
        raise LoadError(f"{path} does not match the sha256 in its manifest")


def replacements(live_url: str, local_url: str) -> list[tuple[str, str]]:
    """The live address in the forms the live tables hold it, each with its local twin.

    Counted in the 2026-10-09 dump: 36,748 plain, 10,940 JSON-escaped
    (https:\\/\\/de-linker.com), 578 URL-encoded (https%3A%2F%2Fde-linker.com);
    no http:// or www. form.
    """
    return [
        (live_url, local_url),
        (live_url.replace("/", "\\/"), local_url.replace("/", "\\/")),
        (quote(live_url, safe=""), quote(local_url, safe="")),
    ]


def verify(
    wp: WpCli,
    target: Instance,
    posts: dict[str, int],
    german_pages: list[str] | None = None,
) -> dict[str, object]:
    """What the loaded instance holds, next to what the snapshot says."""
    counts = {
        key: int(
            wp.query(
                f"SELECT COUNT(*) FROM {TABLE_PREFIX}posts"
                f" WHERE post_type = '{key.split('/')[0]}' AND post_status = '{key.split('/')[1]}'"
            )[0]
        )
        for key in ("product/publish", "attachment/inherit")
    }
    uploads = target.wp_content / "uploads"
    attached = wp.query(
        f"SELECT meta_value FROM {TABLE_PREFIX}postmeta WHERE meta_key = '_wp_attached_file'"
    )
    missing = [path for path in attached if not (uploads / path).is_file()]
    leftovers = {
        old: int(
            wp.run(
                "search-replace",
                old,
                "x",
                "--all-tables-with-prefix",
                "--dry-run",
                "--format=count",
                *SKIP,
            )
        )
        for old, _ in replacements(live.URL, target.url)
    }
    staff = wp.run(
        "user",
        "list",
        "--role__in=administrator,shop_manager",
        "--field=user_login",
        *SKIP,
    )
    result: dict[str, object] = {
        "home": wp.run("option", "get", "home", *SKIP),
        "published_products": {
            "snapshot": posts.get("product/publish", 0),
            "instance": counts["product/publish"],
        },
        "attachments": {
            "snapshot": posts.get("attachment/inherit", 0),
            "instance": counts["attachment/inherit"],
        },
        "attachment_files_missing": len(missing),
        "live_address_left": leftovers,
        "staff_logins": staff.splitlines(),
    }
    # With the old i18n plugin installed, a --live-code copy promises German
    # pages in German; the freshness fallback serves English without any
    # error, so the promise is checked, not assumed (the 2026-10-10 review
    # found 18 pages fallen back behind an ok:true). None skips: no plugin,
    # no promise (a test harness's live/ has no linker-i18n).
    german_ok: bool | None = None
    if german_pages is not None:
        if not german_pages:
            raise LoadError(
                "the old i18n plugin is installed but no page holds German to check"
            )
        checked = {}
        for path in german_pages[:3]:
            checked[path] = _page_is_german(target, path)
        result["german_pages"] = checked
        german_ok = all(checked.values())
    result["ok"] = (
        result["home"] == target.url
        and counts["product/publish"] == posts.get("product/publish", 0)
        and counts["attachment/inherit"] == posts.get("attachment/inherit", 0)
        and not missing
        and not any(leftovers.values())
        and german_ok is not False
    )
    return result


# Closed-class words: a German page is full of them and an English fallback
# has almost none (German words an English text can carry are rare, and the
# counts must agree by a margin, not merely differ). The marker sets are
# disjoint by spelling on purpose.
GERMAN_MARKERS = re.compile(
    r"(?<![\w-])(?:der|die|das|und|für|mit|nicht|ist|auf|eine|einen|dem|den|von|wird|werden|für)(?![\w-])",
    re.IGNORECASE,
)
ENGLISH_MARKERS = re.compile(
    r"(?<![\w-])(?:the|and|for|with|that|this|are|you|your|our|from|will)(?![\w-])",
    re.IGNORECASE,
)


def _page_is_german(target: Instance, path: str) -> bool:
    """Whether the instance serves `path` (a German route) as a German page:
    <html lang="de…"> and a body whose language reads German."""
    connection = http.client.HTTPConnection(
        target.url.partition("://")[2].partition(":")[0] or "127.0.0.1",
        target.port,
        timeout=120,
    )
    connection.request("GET", path)
    response = connection.getresponse()
    status = response.status
    html = response.read().decode("utf-8", "replace")
    connection.close()
    return status == 200 and _reads_german(html)


def _reads_german(html: str) -> bool:
    """A page that says it is German and whose visible text is: the freshness
    fallback keeps lang="de" on the route and serves the English body, which
    this catches (the words carry the language, the attribute does not)."""
    if not re.search(r"<html[^>]*\slang=\"de", html):
        return False
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    german = len(GERMAN_MARKERS.findall(text))
    english = len(ENGLISH_MARKERS.findall(text))
    return german >= 10 and german >= 3 * english


def _bind_publication(wp: WpCli, say: Say, active: list[str]) -> None:
    """Bind this copy's figure and cited-answer revisions after the address rewrite.

    `Publication::revision()` hashes the record including its citation URL, so
    the rewrite above changes the revision of every cited FAQ and figure while
    the bindings still name the live revisions. Bindings are additive — the
    previous entries stay, as on live — and without them a migration that
    guards on "this citation was reviewed" refuses on an otherwise correct
    copy (`A cited FAQ no longer has its reviewed document binding`).
    """
    if not any(entry.split("/")[0] == "linker-commerce" for entry in active):
        return
    say("publication: binding this copy's figure and FAQ revisions")
    wp.run("linker-commerce", "publication", "bind-figures")


def _active_plugins(wp: WpCli) -> list[str]:
    try:
        value = json.loads(
            wp.run("option", "get", "active_plugins", "--format=json", *SKIP)
        )
    except LoadError:
        return []
    # A gap in the option's integer keys (the live list has one: a plugin was
    # unset in place, leaving indices 0-7, 9, 10, 11) makes WP-CLI print an
    # object whose keys are the old indices; its values are still the list.
    if isinstance(value, dict):
        return [str(entry) for entry in value.values()]
    return [str(entry) for entry in value] if isinstance(value, list) else []


def _dump(path: Path) -> Iterator[bytes]:
    """The snapshot's SQL for MySQL 9.6: MariaDB's dump as it is, first line
    ("enable the sandbox mode") included (tests/test_load.py), less the one
    MariaDB-only clause the live tables hold (mysql_compatible)."""
    with gzip.open(path, "rb") as dump:
        yield from mysql_compatible(dump)


# MariaDB 11.7+'s vector index, as mysqldump writes it into a CREATE TABLE
# (live wp_genie_chunks: VECTOR KEY `embedding` (`embedding`) `DISTANCE`='cosine').
VECTOR_KEY = re.compile(rb"^\s*VECTOR KEY ")
# A VECTOR(n) column definition (live wp_genie_chunks: `embedding` vector(3072)).
VECTOR_COLUMN = re.compile(rb"^(\s*`[^`]+` )vector\((\d+)\)", re.IGNORECASE)
# A vector component is a float32 (MariaDB VECTOR and MySQL VECTOR alike).
FLOAT32_BYTES = 4


def mysql_compatible(lines: Iterator[bytes]) -> Iterator[bytes]:
    """The dump with MariaDB's vectors in a form local PHP and MySQL can read.

    Two things, measured 2026-10-17 on the first snapshot that held the
    knowledge index (live wp_genie_chunks, 33,172 rows):

    - MySQL 9.6 rejects MariaDB's vector index clause with error 1064, and the
      whole import with it. The clause goes; a clause that closed the key list
      takes the comma before it along. The table keeps its other keys,
      FULLTEXT among them.
    - MySQL takes a VECTOR(3072) column and the 0x… values, but PHP 8.3's
      mysqlnd cannot read the type: one `SELECT *` on the table leaves the
      connection "out of sync", and every later query of that request fails
      (`wp search-replace` then skipped every table after it and rewrote no
      address). The column becomes VARBINARY of the same bytes: MySQL has no
      vector distance function either, so locally the search takes the
      FULLTEXT path (docs/specs/10-knowledge-index.md) and the bytes stay
      as they are.
    """
    held: bytes | None = None
    for line in lines:
        if VECTOR_KEY.match(line):
            if held is not None and not line.rstrip().endswith(b","):
                stripped = held.rstrip()
                if stripped.endswith(b","):
                    held = stripped[:-1] + held[len(stripped) :]
            continue
        column = VECTOR_COLUMN.match(line)
        if column:
            size = int(column.group(2)) * FLOAT32_BYTES
            line = column.group(1) + b"varbinary(%d)" % size + line[column.end() :]
        if held is not None:
            yield held
        held = line
    if held is not None:
        yield held
