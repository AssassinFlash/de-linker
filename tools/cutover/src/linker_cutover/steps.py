"""The cutover steps of docs/specs/17-cutover.md, one function each.

Every step is separately re-runnable, which is what spec 17's heading asks for:
`maintenance`, `deploy`, `export_snippets`, `remove_legacy`, `migrations`,
`services`, `hygiene`, `verify`, `rollback`. None reads another's state; the
only thing they share is the `Target`, so an operator can interrupt the window,
look at the site, and run the failed step again.

Listing legacy tables and options goes through WP-CLI's own commands
(`wp db tables`, `wp option list`) and filters in Python rather than through
SQL with a hard-coded `wp_` prefix: the prefix is a site setting, and a rule
that assumes one would quietly match nothing on a site that changed it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from linker_cutover import atomic, plan
from linker_cutover import backup as backup_module
from linker_cutover import snapshot as snapshot_module
from linker_cutover.target import HOST_URL, CutoverError, Target, wp_prefix_for


@dataclass(frozen=True)
class Result:
    """What a step did, in the order it did it — the evidence a run leaves."""

    step: str
    actions: list[str]
    notes: list[str]
    publication: atomic.Receipt | None = None

    def describe(self) -> str:
        lines = [f"{self.step}: {action}" for action in self.actions]
        lines += [f"{self.step}: note: {note}" for note in self.notes]
        return "\n".join(lines)


def maintenance(target: Target, *, on: bool) -> Result:
    """Step 2 and the first half of step 7 of spec 17: the maintenance window.

    The window is the core `.maintenance` file itself. `wp maintenance-mode
    activate` exists on the host but writes a literal timestamp, and core's
    `wp_maintenance()` stops honouring a file whose timestamp is over ten
    minutes old — shorter than a deploy window, and it cannot be re-armed
    mid-run (measured on production 2026-10-14, and the command's status
    wording "not active" also contains "active", which the first version of
    this step read as its own success). The `time()` form re-evaluates on
    every request, so the window lasts exactly as long as the file exists,
    and the readback below is the proof, not the command's exit status.

    Turning it on when it is already on (or off when already off) is not a
    failure: the window is re-runnable step by step.
    """
    path = shlex.quote(target.path_of(".maintenance"))
    if on:
        target.shell(f"printf '%s\\n' '<?php $upgrading = time();' > {path}")
    else:
        target.shell(f"rm -f {path}")
    active = target.exists(".maintenance")
    if active != on:
        state = "still present" if active else "still absent"
        raise CutoverError(
            f"the maintenance file is {state} after {'writing' if on else 'removing'} it"
        )
    action = "wrote .maintenance" if on else "removed .maintenance"
    note = "maintenance page: active" if on else "maintenance page: off"
    return Result("maintenance", [action], [note])


def stage_plugin(repository: Path, slug: str, staging: Path) -> Path:
    """Build the tree that ships, for one plugin.

    The checkout's `vendor/` carries the development dependencies (`just`
    installs with them, docs/local-stack.md "与线上一致的部分"); production
    carries none. So the deploy does not rsync the checkout: it rsyncs into a
    staging tree with the plugin's own ignores and installs the runtime
    dependencies there. `build/` and `vendor/` ship; `node_modules/`, `tests/`
    and the tool configs do not.
    """
    source = Path(repository) / plan.REPO / slug
    if not (source / f"{slug}.php").is_file():
        raise CutoverError(f"{source} does not look like the {slug} plugin")
    destination = Path(staging) / slug
    stamp = Path(staging) / ".stage" / f"{slug}.sha256"
    fingerprint = _stage_fingerprint(source)
    if (
        stamp.is_file()
        and stamp.read_text(encoding="utf-8").strip() == fingerprint
        and (
            not (destination / "composer.json").is_file()
            or (destination / "vendor").is_dir()
        )
    ):
        # Nothing changed since the last build: the staged tree already is the
        # source with its runtime vendor (the Composer build was ~8 minutes of
        # every deploy, 2026-10-18). The fingerprint covers every source file,
        # dev files included: a test edit rebuilds, which is merely slower.
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    excludes: list[str] = []
    for pattern in plan.DEPLOY_EXCLUDES:
        excludes += ["--exclude", pattern]
    completed = subprocess.run(
        ["rsync", "-a", "--delete", *excludes, f"{source}/", f"{destination}/"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise CutoverError(f"staging {slug}: {completed.stderr.strip()}")
    if (destination / "composer.json").is_file():
        composer = shutil.which("composer")
        if composer is None:
            raise CutoverError("composer is not installed (README.md)")
        installed = subprocess.run(
            [
                composer,
                "install",
                "--no-dev",
                "--no-interaction",
                "--no-progress",
                "--optimize-autoloader",
                "--quiet",
            ],
            cwd=destination,
            check=False,
            capture_output=True,
            text=True,
        )
        if installed.returncode != 0:
            raise CutoverError(
                f"composer install --no-dev in {destination}: "
                + (installed.stderr or installed.stdout).strip()
            )
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(fingerprint + "\n", encoding="utf-8")
    return destination


def _stage_fingerprint(source: Path) -> str:
    """sha256 over every source file's path and content: the staging cache key."""
    digest = hashlib.sha256()
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        digest.update(path.relative_to(source).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def deployment_artifacts(repository: Path) -> list[atomic.Artifact]:
    """The single owned-path inventory used by publication and rollback."""
    mu = repository / plan.MU_PLUGINS_REPO
    plugins = sorted(mu.glob("*.php"))
    if not plugins:
        raise CutoverError(f"{mu} carries no must-use plugin")
    themes = repository / plan.THEMES_REPO
    theme_files = sorted(path for path in themes.rglob("*") if path.is_file())
    if not theme_files:
        raise CutoverError(f"{themes} carries no theme file")
    artifacts = [
        atomic.Artifact(path, f"{plan.MU_PLUGINS_DIR}/{path.name}")
        for path in plugins + sorted(mu.glob("*.pem"))
    ]
    artifacts += [
        atomic.Artifact(path, f"{plan.THEMES_DIR}/{path.relative_to(themes)}")
        for path in theme_files
    ]
    for slug in plan.NEW_PLUGINS:
        source = repository / plan.REPO / slug
        if not (source / f"{slug}.php").is_file():
            raise CutoverError(f"{source} does not look like the {slug} plugin")
        artifacts.append(atomic.Artifact(source, f"{plan.PLUGINS_DIR}/{slug}"))
    return artifacts


def deployment_id(repository: Path) -> str:
    """UTC time plus the source commit: review #299 decision 3."""
    git = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    if git.returncode:
        raise CutoverError("the deployment source must be a git checkout")
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-" + git.stdout.strip()


# The full backup is weekly (AGENTS.md §5, #305); nothing schedules it, so each
# deploy says when the newest one is older than this.
FULL_BACKUP_DAYS = 7


# The host revalidates compiled PHP every 2 s (opcache.revalidate_freq=2,
# opcache.validate_timestamps=1, read on the host 2026-10-18, #308): the
# deploy asks the site to reset its opcode cache straight after the switch
# and retries for longer than one revalidation period.
OPCACHE_RESET_ATTEMPTS = 15
OPCACHE_RESET_PAUSE = 0.2  # seconds; 15 × 0.2 s = 3 s > the 2 s period


def opcache_reset_script(target: Target) -> str:
    """The after-switch step: a one-time token on the host, posted to the site.

    The token is made, written and posted on the host; it is read by
    `mu-plugins/linker-deploy-reset.php` from the same private directory and
    deleted there. It travels in a header file, never on a command line other
    accounts on the shared host could list.
    """
    url = shlex.quote(target.base_url.rstrip("/") + "/")
    marker = atomic.AFTER_SWITCH_MARKER
    return f"""(
umask 077
dir="$HOME/.config/terravolt-builder"
mkdir -p "$dir"
token="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \\n')"
printf '%s\\n' "$token" > "$dir/opcache-reset.token"
printf 'X-Linker-Opcache-Reset: %s\\n' "$token" > "$dir/opcache-reset.header"
outcome=none
attempt=0
while [ "$attempt" -lt {OPCACHE_RESET_ATTEMPTS} ]; do
  attempt=$((attempt + 1))
  answer="$(curl -sS -o /dev/null -D - --max-time 5 -X POST -H @"$dir/opcache-reset.header" {url} 2>/dev/null | tr -d '\\r' | sed -n 's/^[Xx]-[Ll]inker-[Oo]pcache-[Rr]eset: *//p')"
  if [ -n "$answer" ]; then outcome="$answer"; break; fi
  sleep {OPCACHE_RESET_PAUSE}
done
rm -f "$dir/opcache-reset.token" "$dir/opcache-reset.header"
printf '{marker}opcache-reset=%s attempts=%s\\n' "$outcome" "$attempt"
)"""


def full_backup_reminder(home: Path, *, now: datetime | None = None) -> str | None:
    """A line for the deploy log when the weekly full backup is due, else None."""
    latest = backup_module.latest_complete(home)
    if latest is None:
        return "reminder: there is no complete full backup; run `just cutover backup`"
    taken = datetime.strptime(latest.name, "cutover-%Y%m%d-%H%M").replace(tzinfo=UTC)
    age = (now or datetime.now(UTC)) - taken
    if age.days < FULL_BACKUP_DAYS:
        return None
    return (
        f"reminder: the newest full backup ({latest.name}) is {age.days} days old; "
        "run `just cutover backup` (weekly)"
    )


def deploy(
    target: Target,
    *,
    repository: Path,
    staging: Path,
    deploy_id: str | None = None,
    on_switch: Callable[[], None] | None = None,
    snapshot_home: Path | None = None,
    now: datetime | None = None,
) -> Result:
    """Snapshot the database, build all trees, upload all artifacts, then switch the batch.

    The snapshot comes first and a failed one stops the deploy before anything
    is uploaded: the database is the part of the site a code deploy can change
    that the atomic switch does not keep (#305). Verification and private
    archiving follow in `finish_deploy`. Keeping that phase separate lets the
    first-cutover drill complete its data steps and leave maintenance mode
    before the same verification runs.
    """
    home = snapshot_home or backup_module.DATA_HOME
    # Each phase says what it is doing and how long it took: the deploy used to
    # say nothing until the end, so a slow phase looked like a hang (2026-10-18).
    print("deploy: database snapshot", flush=True)
    started = time.monotonic()
    taken = snapshot_module.take(target, home)
    print(f"deploy: snapshot done in {time.monotonic() - started:.1f}s", flush=True)
    reminder = full_backup_reminder(home, now=now)
    artifacts = deployment_artifacts(repository)
    # Finish every local Composer build before starting any remote upload.
    print("deploy: staging and Composer builds", flush=True)
    started = time.monotonic()
    prepared = [
        atomic.Artifact(
            stage_plugin(repository, item.source.name, staging), item.relative
        )
        if item.source.is_dir()
        else item
        for item in artifacts
    ]
    print(f"deploy: staging done in {time.monotonic() - started:.1f}s", flush=True)
    receipt = atomic.publish(
        target,
        prepared,
        deploy_id=deploy_id or deployment_id(repository),
        on_switch=on_switch,
        after_switch=opcache_reset_script(target),
    )
    assert receipt.switch_seconds is not None
    actions = [
        f"database snapshot {taken.path} ({taken.size} bytes, sha256 {taken.sha256[:16]}…, "
        f"{', '.join(snapshot_module.SKIPPED_TABLES)} left out); "
        f"restore with `just cutover restore-snapshot {taken.name}`"
    ]
    actions += [f"deployed {item.relative} by rename" for item in artifacts]
    actions += [
        f"deploy id: {receipt.deploy_id}",
        f"total switch duration: {receipt.switch_seconds:.3f} s",
    ]
    actions += [f"after switch: {line}" for line in receipt.after_switch]
    print("deploy: plugin activation and language packs", flush=True)
    started = time.monotonic()
    installed = {
        str(entry["name"])
        for entry in target.wp_json("plugin", "list", "--fields=name")
        if isinstance(entry, dict) and "name" in entry
    }
    missing = [slug for slug in plan.INSTALLED_PLUGINS if slug not in installed]
    present = [slug for slug in plan.INSTALLED_PLUGINS if slug in installed]
    if missing:
        target.wp("plugin", "install", *missing, "--activate")
        actions.append("wp plugin install " + " ".join(missing) + " --activate")
    if present:
        target.wp("plugin", "activate", *present)
        actions.append(
            "wp plugin activate " + " ".join(present) + " (already installed)"
        )

    target.wp("plugin", "activate", *plan.NEW_PLUGINS)
    actions.append("wp plugin activate " + " ".join(plan.NEW_PLUGINS))
    actions += deploy_language_packs(target)
    actions += configure_consent(target, repository=repository)
    # Templates and the WindPress volume are data, not files: without present a
    # deploy keeps the previous volume, and a page whose fragment changed (the
    # inquiry form on 2026-10-18) renders unstyled. Idempotent; present keeps its
    # own rollback copy. --allow-stale because a stylesheet change makes the
    # cache stale by definition and present would refuse after the switch; the
    # browser-side WindPress compile that follows is the step that clears it.
    print(f"deploy: activation done in {time.monotonic() - started:.1f}s", flush=True)
    print("deploy: present (templates and the WindPress volume)", flush=True)
    started = time.monotonic()
    target.wp("linker-commerce", "present", "--user=1", "--allow-stale")
    actions.append(
        "wp linker-commerce present --user=1 --allow-stale (now run the WindPress "
        "admin compile: npm tools/windpress-compile.mjs with an admin login)"
    )
    # The switch-time reset covers the rename itself; present and the plugin
    # activation run afterwards, and a request can still meet a tree the
    # workers compiled before them (one 500 in the 2026-10-18 probe window).
    # A second reset at the end leaves every worker compiling the final tree.
    print(f"deploy: present done in {time.monotonic() - started:.1f}s", flush=True)
    refresh = target.shell(opcache_reset_script(target))
    line = refresh.replace(atomic.AFTER_SWITCH_MARKER, "").strip().splitlines()[-1:]
    actions.append("after present: " + (" ".join(line) or "opcache-reset=unknown"))
    if reminder:
        # Last, so it is the line the log ends on and never shifts the others.
        actions.append(reminder)
    return Result("deploy", actions, [], receipt)


def deploy_language_packs(target: Target) -> list[str]:
    """The de_DE_formal packs of WordPress core and WooCommerce (plan.LANGUAGE_PACK_*).

    Idempotent: WP-CLI answers "already installed" with success, so the step is
    safe to re-run and a site that carries the packs is untouched. Without them
    the German pages render every WooCommerce and WordPress core string in
    English — see the incident note on plan.LANGUAGE_PACK_LOCALE.
    """
    actions: list[str] = []
    target.wp("core", "language", "install", plan.LANGUAGE_PACK_LOCALE)
    actions.append(f"wp core language install {plan.LANGUAGE_PACK_LOCALE}")
    for plugin in plan.LANGUAGE_PACK_PLUGINS:
        target.wp("language", "plugin", "install", plugin, plan.LANGUAGE_PACK_LOCALE)
        actions.append(
            f"wp language plugin install {plugin} {plan.LANGUAGE_PACK_LOCALE}"
        )
    return actions


def configure_consent(target: Target, *, repository: str | Path) -> list[str]:
    """Replay the native CMP settings after every deployment, then read them back.

    Idempotent: every deploy sends the same write-then-verify pair, and the
    migration writes only where the site still differs. The database snapshot
    taken before the switch is the backup for this path. A standalone
    ``201-consent.py --write`` is a different entry and refuses to run without
    ``--backup-dir``.
    """
    directory = Path(repository) / "tools" / "migrate"
    source = (directory / "201-consent.php").read_text().removeprefix("<?php")
    settings = json.loads((directory / "201-consent.json").read_text())
    for write in (True, False):
        payload = base64.b64encode(
            json.dumps(
                {
                    "plan": settings,
                    "write": write,
                    "production": target.rsync_remote is not None,
                }
            ).encode()
        ).decode()
        target.wp(
            "eval", source.replace("__LINKER_CONSENT_PAYLOAD__", payload), "--user=1"
        )
    return ["consent: native CMP settings replayed and verified"]


# Unauthenticated deploy reads carry no consent cookie, so analytics is denied.
# The product pages are the same pair ``verify`` already fetches.
CONSENT_PAGES = ("/", "/de/", *plan.VERIFY_PRODUCT_PATHS)
GOOGLE_TAG_HANDLE = "google_gtagjs"


def consent(target: Target) -> Result:
    """Check production's carrier and the actual HTML, without issuing consent."""
    actions: list[str] = []
    notes: list[str] = []
    for slug in ("cookie-law-info", "wp-consent-api", plan.SITE_KIT):
        entries = target.wp_json(
            "plugin", "list", f"--name={slug}", "--fields=name,status"
        )
        active = isinstance(entries, list) and any(
            isinstance(entry, dict) and entry.get("status") == "active"
            for entry in entries
        )
        actions.append(f"consent: {slug} active: {active}")
        if not active:
            notes.append(f"consent: {slug} must remain active")
    for option, field, expected in (("googlesitekit_consent_mode", "enabled", True),):
        raw = target.wp("option", "get", option, "--format=json", check=False)
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            value = {}
        if not isinstance(value, dict) or value.get(field) != expected:
            notes.append(f"consent: {option}.{field} differs from its contract")
    raw = target.wp(
        "option",
        "get",
        "googlesitekit_analytics-4_settings",
        "--format=json",
        check=False,
    )
    try:
        settings = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        settings = {}
    if (
        not isinstance(settings, dict)
        or not settings.get("measurementID")
        or not settings.get("useSnippet")
    ):
        notes.append("consent: Analytics must be connected with its snippet enabled")
    for path in CONSENT_PAGES:
        status, html = target.http(path, cache_buster=None)
        actions.append(f"consent: GET {path} -> {status}")
        if status != 200 or "ckyBannerTemplate" not in html:
            notes.append(f"consent: {path} does not include the CMP banner")
        tags = re.findall(r"<script\b[^>]*>", html, flags=re.I)
        google_tags = [tag for tag in tags if "googletagmanager.com/gtag/js" in tag]
        if not google_tags or any(
            'type="text/plain"' not in tag
            or 'data-cookieyes="cookieyes-analytics"' not in tag
            for tag in google_tags
        ):
            notes.append(
                f"consent: {path} must hold every Google tag behind statistics consent"
            )
        if f'id="{GOOGLE_TAG_HANDLE}-js"' not in html:
            notes.append(
                f"consent: {path} google_gtagjs handle is absent while analytics "
                "consent is denied. Fallback: while CookieYes is active, hold every "
                "googletagmanager.com/gtag/js tag by URL and log a linker-consent "
                "warning. This check still fails until the handle is present. "
                "Deactivating CookieYes leaves the tag unchanged because nothing "
                "could release it; that request logs the same warning and the "
                "carrier check above fails closed."
            )
        if "linker-consent-withdrawal" not in html:
            notes.append(f"consent: {path} is missing the withdrawal adapter")
    return Result("consent", actions, notes)


def verify_site(target: Target, *, cache_buster: str) -> Result:
    """The existing site and production Search Console checks, shared by callers."""
    result = verify(target, cache_buster=cache_buster)
    if target.rsync_remote is not None:
        ownership = search_console(target)
        privacy = consent(target)
        return Result(
            "verify",
            result.actions + ownership.actions + privacy.actions,
            result.notes + ownership.notes + privacy.notes,
        )
    return result


def finish_deploy(
    target: Target, receipt: atomic.Receipt, *, cache_buster: str
) -> Result:
    """Only a passing verify allows backups to leave the web root."""
    checked = verify_site(target, cache_buster=cache_buster)
    if checked.notes:
        return Result("deploy-verify", checked.actions, checked.notes)
    atomic.archive(target, receipt)
    return Result(
        "deploy-verify",
        checked.actions
        + [
            f"archived backups by rename: {receipt.backup_directory}",
            "retained only the most recent deploy backup set",
        ],
        [],
    )


def resume_deploy(target: Target, *, repository: Path, cache_buster: str) -> Result:
    """Verify/archive a pending batch after an interrupted reply or failed verify."""
    receipt = atomic.pending_receipt(
        target, [item.relative for item in deployment_artifacts(repository)]
    )
    checked = finish_deploy(target, receipt, cache_buster=cache_buster)
    return Result(
        "resume-deploy",
        [f"deploy id: {receipt.deploy_id}", *checked.actions],
        checked.notes,
    )


def rollback_deploy(target: Target, *, repository: Path) -> Result:
    """Restore a consistent manifest, then prove live identities, activation and HTTP."""
    relatives = [item.relative for item in deployment_artifacts(repository)]
    receipt = atomic.rollback(target, relatives)
    actions = [f"deploy id: {receipt.deploy_id}", *receipt.readbacks]
    listed = target.wp_json("plugin", "list", "--fields=name,status")
    statuses = {
        row["name"]: row.get("status", "missing")
        for row in listed
        if isinstance(row, dict) and "name" in row
    }
    notes: list[str] = []
    for slug in plan.NEW_PLUGINS:
        status = statuses.get(slug, "missing")
        actions.append(f"plugin {slug}: {status}")
        if status != "active":
            notes.append(f"plugin {slug} is {status} after rollback")
    checked = verify_site(target, cache_buster=receipt.deploy_id + "-rollback")
    return Result("rollback-deploy", actions + checked.actions, notes + checked.notes)


def ensure_plugins(target: Target, slugs: tuple[str, ...]) -> list[str]:
    """Install what is missing and activate what is there; one line per decision.

    Two things this must not do: install over an installed plugin (the local
    instances have one, and their isolation layer blocks wordpress.org on
    purpose), and stay silent about which of the two it did.
    """
    installed = {
        str(entry["name"])
        for entry in target.wp_json("plugin", "list", "--fields=name")
        if isinstance(entry, dict) and "name" in entry
    }
    actions: list[str] = []
    missing = [slug for slug in slugs if slug not in installed]
    present = [slug for slug in slugs if slug in installed]
    if missing:
        target.wp("plugin", "install", *missing, "--activate")
        actions.append("wp plugin install " + " ".join(missing) + " --activate")
    if present:
        target.wp("plugin", "activate", *present)
        actions.append(
            "wp plugin activate " + " ".join(present) + " (already installed)"
        )
    return actions


def export_snippets(target: Target, directory: Path) -> Result:
    """Step 3's precondition: every snippet row out of the database before the plugin goes.

    The rows land OUTSIDE the repository, beside the backup. They are the old
    tree's code, and the new tree carries no old code (AGENTS.md: what is
    carried is content and data, rulings, evidence, verified specifications);
    what the repository keeps is the confirmation that each row's work has an
    owner in the new tree, which `remove_legacy` reports.
    """
    directory.mkdir(parents=True, exist_ok=True)
    rows = _snippets_via_eval(target)
    active = [row for row in rows if str(row.get("active")) == "1"]
    (directory / "snippets.json").write_text(
        json.dumps(rows, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    for row in active:
        (directory / f"snippet-{row['id']}.php").write_text(
            str(row.get("code", "")), encoding="utf-8"
        )
    return Result(
        "snippets",
        [f"exported {len(rows)} rows ({len(active)} active) to {directory}"],
        ["code lands outside the repository; the repository records the confirmation"],
    )


def remove_legacy(target: Target, *, snippets: Path, acceptance: Path) -> Result:
    """Step 3's removal half: deactivate, delete, and clear what is left behind.

    The order is the point. Every legacy plugin is deactivated before any of
    them is deleted, so no plugin is left calling into code that is already
    gone; the snippets are exported before `code-snippets` itself is deleted.

    The must-use directory is cleaned with the same `*.bak-*` rule as the
    plugins directory, and what goes from there is archived under the day's
    acceptance record first (spec 17 §3): the old i18n loader and the
    recorder's own backups are, by the time this step runs, the only copies.
    """
    actions: list[str] = []
    notes: list[str] = []
    if not Path(snippets).is_file():
        raise CutoverError(
            f"{snippets} is missing — export the snippets before deleting the plugin"
        )
    installed = {
        str(entry["name"])
        for entry in target.wp_json("plugin", "list", "--fields=name")
        if isinstance(entry, dict) and "name" in entry
    }
    present = [slug for slug in plan.LEGACY_PLUGINS if slug in installed]
    notes += [
        f"{slug} was not installed"
        for slug in plan.LEGACY_PLUGINS
        if slug not in installed
    ]
    if present:
        target.wp("plugin", "deactivate", *present)
        actions.append("wp plugin deactivate " + " ".join(present))
        target.wp("plugin", "delete", *present)
        actions.append("wp plugin delete " + " ".join(present))

    for relative in plan.LEGACY_PLUGIN_PATHS:
        path = f"{plan.PLUGINS_DIR}/{relative}"
        if target.exists(path):
            target.shell(f"rm -rf {shlex.quote(target.path_of(path))}")
            actions.append(f"rm -rf {path}")

    archive = Path(acceptance) / plan.MU_ARCHIVE
    actions += _remove_globs(target, plan.PLUGINS_DIR)
    actions += _remove_globs(target, plan.MU_PLUGINS_DIR, archive=archive)

    for name in plan.LEGACY_MU_PLUGINS:
        relative = f"{plan.MU_PLUGINS_DIR}/{name}"
        if not target.exists(relative):
            continue
        _archive(target, relative, archive, actions)
        target.shell(f"rm -f {shlex.quote(target.path_of(relative))}")
        actions.append(f"rm -f {relative}")
    actions.append(
        "deployed in place, so no removal: " + ", ".join(plan.REPLACED_PLUGINS)
    )
    if not notes:
        notes.append("every legacy plugin was installed and is gone")
    return Result("plugins", actions, notes)


def _remove_globs(
    target: Target, relative: str, *, archive: Path | None = None
) -> list[str]:
    """Remove the leftover `*.bak-*` files of one root-relative directory.

    With `archive`, every match is copied there before it is removed. The mu
    directory needs that and the plugins directory does not: what the rule takes
    out of `wp-content/plugins` is a leftover of a plugin that is itself being
    deleted, while the files it takes out of `wp-content/mu-plugins` are the
    only remaining copy of the loader the old i18n plugin bootstrapped from.
    """
    actions: list[str] = []
    for pattern in plan.LEGACY_GLOBS:
        listing = target.shell(
            f"find {shlex.quote(target.path_of(relative))} -maxdepth 1 "
            f"-name {shlex.quote(pattern)} -print"
        )
        for name in listing.split():
            path = f"{relative}/{Path(name).name}"
            if archive is not None:
                _archive(target, path, archive, actions)
            target.shell(f"rm -rf {shlex.quote(name)}")
            actions.append(f"rm -rf {path}")
    return actions


def _archive(target: Target, relative: str, archive: Path, actions: list[str]) -> None:
    """Keep a copy of what the step is about to delete from the site."""
    target.copy_file_out(relative, archive / Path(relative).name)
    actions.append(f"archived {relative} to {archive}")


def migrations(
    repository: Path,
    target: Target,
    *,
    backup: Path,
    administrator: str,
    writes: bool,
) -> Result:
    """Step 4's data half: the migrations, run against the target's own WP-CLI.

    Without `writes` every migration prints its plan, which is what the local
    drill runs: the migrations rewrite products, facts and German objects, and a
    drill that wrote them would leave the instance unable to be the clean state
    a second drill needs (spec 17's precondition is a clean snapshot).
    """
    actions: list[str] = []
    notes: list[str] = []
    # The migration writes its backup OF the current values into this
    # directory, and it does not create it: the caller owns the path it hands
    # over (measured 2026-10-14 — 7-facts died with FileNotFoundError on a
    # `migrate/` nothing had made, before it wrote anything, which is why the
    # site kept its old values).
    backup_dir = Path(backup) / "migrate"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for migration in plan.MIGRATIONS:
        script = Path(repository) / "tools" / "migrate" / migration.script
        if not script.is_file():
            raise CutoverError(f"{script} is missing")
        command = ["python3", str(script), "--wp", wp_prefix_for(target)]
        if migration.needs_admin and administrator:
            command += ["--user", administrator]
        if migration.needs_backup_dir:
            command += ["--backup-dir", str(backup_dir)]
        # A plan path in the options is repository-relative. The cutover is not
        # run from the repository root, so the writer must get an absolute path.
        options = list(migration.options)
        if "--plan" in options:
            index = options.index("--plan") + 1
            options[index] = str((Path(repository) / options[index]).resolve())
        command += options
        command += list(migration.subcommand)
        if writes:
            command.append("--write")
        # The host is decided by the target, not by the flag: a drill against a
        # local instance must never get the production write-allowance, and the
        # migration's own guard compares the site's siteurl, not the machine.
        if migration.production_guard and target.base_url == HOST_URL:
            command.append("--production")
        print("data: " + " ".join(shlex.quote(part) for part in command))
        completed = subprocess.run(command, check=False)
        actions.append(
            f"{migration.script} {'--write' if writes else '(plan)'} exit {completed.returncode}"
        )
        if completed.returncode != 0:
            # Both exits of these scripts are defined: 0 is done (or the plan
            # found no drift), 1 is drift, a refusal or an unfinished write.
            # A window run of 2026-10-14 tolerated the 1s as notes and the
            # step read as green while nothing had been written.
            raise CutoverError(
                f"{migration.script} exited {completed.returncode} on {target.label}"
            )
    return Result("data", actions, notes)


def retire_stale_schema(target: Target, *, writes: bool) -> Result:
    """Step 4's schema half: the retained SEO plugin's own Product template goes.

    The plugin is retained and so is its schema library; only the entry that
    emits a Product node is retired, because this plugin now emits the product
    page's Product node and two of them — one saying the brand is this company,
    one saying the manufacturer's — is worse than either alone. Retired by
    making the row a draft, not by deleting it: the plugin's own query reads
    published rows, and a draft is a row an operator can put back by hand.
    """
    rows = _schema_rows(target)
    stale = [row for row in rows if row["product"]]
    actions = [
        f"{len(rows)} schema templates, {len(stale)} carrying a {plan.SCHEMA_RETIRED} node"
    ]
    for row in stale:
        actions.append(f"row {row['id']} ({row['title']}, {row['status']})")
    if not stale:
        return Result("schema", actions, ["nothing to retire"])

    if writes:
        ids = [str(row["id"]) for row in stale]
        # Draft, not delete: the type does not support the trash (WP-CLI
        # refuses without --force), and a draft row is one the plugin's own
        # query no longer applies and an operator can put back by hand.
        target.wp("post", "update", *ids, "--post_status=draft")
        actions.append("wp post update " + " ".join(ids) + " --post_status=draft")
    else:
        actions.append("dry run — nothing retired")
    return Result("schema", actions, [])


def _schema_rows(target: Target) -> list[dict[str, object]]:
    """The plugin's schema templates: id, title, status, and whether each is a Product node."""
    php = (
        "$out = array();"
        f"foreach ( get_posts( array( 'post_type' => '{plan.SCHEMA_POST_TYPE}', 'post_status' => 'any', "
        "'numberposts' => -1 ) ) as $row ) {"
        f"  $stored = (string) get_post_meta( $row->ID, '{plan.SCHEMA_TEMPLATE_META}', true );"
        f"  $out[] = array( 'id' => $row->ID, 'title' => $row->post_title, 'status' => $row->post_status, "
        f"  'product' => 1 === preg_match( '/\"@type\"\\s*:\\s*\"{plan.SCHEMA_RETIRED}\"/', $stored ) );"
        "}"
        "echo wp_json_encode( $out );"
    )
    parsed = json.loads(target.wp("eval", php))
    if not isinstance(parsed, list):
        raise CutoverError("the schema listing did not return a list")
    return [row for row in parsed if isinstance(row, dict)]


def hygiene(target: Target, *, backup: Path, writes: bool) -> Result:
    """Step 6: the host's housekeeping, and the two things only a person can do.

    The legacy tables are dropped only after the backup holds them, and the
    names are part of the step's output: the rule is a prefix, and a prefix is
    only safe when somebody looked at what it matched.
    """
    actions: list[str] = []
    notes: list[str] = list(plan.MANUAL)

    revisions = target.wp(
        "post", "list", "--post_type=revision", "--format=ids"
    ).split()
    if revisions:
        if writes:
            # `--force` is the difference between deleting and failing: a
            # revision does not support the trash, and plain `wp post delete`
            # refuses every one of them (measured 2026-10-14 on the first
            # 2156-revision site — a fresh drill instance has none, which is
            # why the drill never saw it).
            target.wp("post", "delete", *revisions, "--force")
        actions.append(
            f"revisions: {'deleted' if writes else 'would delete'} {len(revisions)}"
        )
    else:
        notes.append("revisions: none")

    # The object cache is the one hygiene item whose mechanism differs by
    # target, and the difference is real. A site with the drop-in already in
    # place is served by it — every local instance is, because the stack copies
    # Redis Object Cache's `object-cache.php` itself rather than activating the
    # plugin: its activation hook runs FLUSHDB on the database every instance
    # on this Mac shares (docs/local-stack.md), which a rehearsal must not do
    # to its neighbours. A site without the drop-in gets the plugin.
    if target.exists(plan.OBJECT_CACHE_DROPIN):
        actions.append(f"object cache: {plan.OBJECT_CACHE_DROPIN} is in place")
    else:
        actions += ensure_plugins(target, (plan.OBJECT_CACHE_PLUGIN,))

    for label, args in plan.HYGIENE:
        if writes:
            target.wp(*args)
        actions.append(f"{label}: wp {' '.join(args)}")

    prefix = table_prefix(target)
    tables = [name for name in table_names(target) if is_legacy_table(name, prefix)]
    if tables:
        if writes:
            for name in tables:
                target.wp("db", "query", f"DROP TABLE {_identifier(name)}")
        actions.append(
            f"tables: {'dropped' if writes else 'would drop'} {', '.join(tables)}"
        )
    else:
        notes.append("tables: no legacy tables")

    options = [name for name in option_names(target) if _is_legacy_option(name)]
    if options:
        if writes:
            target.wp("option", "delete", *options)
        actions.append(
            f"options: {'deleted' if writes else 'would delete'} {len(options)} names"
        )
        (Path(backup) / "legacy-options.json").write_text(
            json.dumps(sorted(options), indent=1) + "\n", encoding="utf-8"
        )
    else:
        notes.append("options: no legacy option names")

    hooks = [hook for hook in cron_hooks(target) if _is_legacy_cron_hook(hook)]
    if hooks:
        if writes:
            target.wp("cron", "event", "delete", *hooks)
        actions.append(
            f"cron: {'deleted' if writes else 'would delete'} {', '.join(hooks)}"
        )
    else:
        notes.append("cron: no legacy hooks")

    rows, total = autoload_report(target, Path(backup) / "autoload.json")
    actions.append(
        f"autoload: {rows} options, {total} bytes written to the backup for review"
    )
    return Result("hygiene", actions, notes)


def _rsync(source: Path, destination: str) -> None:
    """One rsync leg of a publish: a directory (or file) onto the VPS."""
    source_arg = f"{source}/" if source.is_dir() else str(source)
    completed = subprocess.run(
        [
            "rsync",
            "-az",
            "--delete",
            # The local virtualenv is this Mac's build (hundreds of MB, arm64
            # binaries); the release builds its own on the host. Caches never
            # travel either.
            "--exclude=.venv",
            "--exclude=__pycache__",
            "--exclude=.pytest_cache",
            "--exclude=.mypy_cache",
            "--exclude=.ruff_cache",
            "-e",
            "ssh -o BatchMode=yes",
            source_arg,
            f"{plan.SERVICES_SSH}:{destination}",
        ],
        check=False,
    )
    if completed.returncode != 0:
        raise CutoverError(
            f"rsync {source} -> {plan.SERVICES_SSH}:{destination} failed"
        )


def services(*, repository: Path, addresses: dict[str, str], run: bool) -> Result:
    """Step 5: publish the two services to the VPS and write their addresses into the site.

    The release script is the genie's `ops/release.sh` for both services: its
    root is its parameter, so one implementation owns the release rule (version
    directory, `current` symlink, rollback) for two services. It copies from a
    directory on the machine it runs on, so a publish stages over ssh first
    (the tree and the script into `plan.SERVICES_STAGING`) and runs there.
    After both publishes it runs `ops/activate.sh` there (venvs, the quality
    worker's unit, daemon-reload, restarts, every unit up), so a services
    deploy is this one step; the environments, the tokens and the engine's
    data files — state/feed.json and state/compatibility.json, refreshed
    nightly by linker-engine-feed-sync.timer — stay host setup. The site's
    feed now carries the compatibility contract, so a contract change reaches
    the engine through that timer, not through a hand copy. The timer runs the
    stable copy /opt/linker-engine/ops/sync-feed.py, which this step does not
    install: copy services/engine/ops/sync-feed.py there once when it changes.
    Without `run` it reports the command lines instead.
    """
    actions: list[str] = []
    notes: list[str] = []
    ssh = ("ssh", "-o", "BatchMode=yes", plan.SERVICES_SSH)
    staging_root = plan.SERVICES_STAGING
    if run:
        # macOS ships rsync 2.6.9, which cannot create the destination's
        # parents; the staging root exists only after the first publish.
        made = subprocess.run(
            [*ssh, f"mkdir -p {staging_root}/engine {staging_root}/genie"],
            check=False,
        )
        if made.returncode != 0:
            raise CutoverError(
                f"could not create {staging_root} on {plan.SERVICES_SSH}"
            )
    for service, root, directory in plan.SERVICES:
        staging = f"{staging_root}/{service}"
        if run:
            _rsync(repository / directory, f"{staging}/")
            _rsync(repository / plan.RELEASE_SCRIPT, f"{staging_root}/release.sh")
            publish = (
                f"GENIE_RELEASE_ROOT={shlex.quote(root)} "
                f"bash {staging_root}/release.sh publish {staging}"
            )
            completed = subprocess.run([*ssh, publish], check=False)
            if completed.returncode != 0:
                raise CutoverError(f"publishing {service} failed")
            actions.append(f"published {service} -> {root} (staged at {staging})")
        else:
            actions.append(
                "would publish "
                f"{service}: rsync {directory} -> {plan.SERVICES_SSH}:{staging}, then "
                f"GENIE_RELEASE_ROOT={root} bash {staging_root}/release.sh publish {staging}"
            )
    activate = f"bash {staging_root}/activate.sh"
    if run:
        _rsync(repository / plan.ACTIVATE_SCRIPT, f"{staging_root}/activate.sh")
        completed = subprocess.run([*ssh, activate], check=False)
        if completed.returncode == plan.ACTIVATE_NO_TOKEN:
            actions.append("activated engine and genie; quality worker installed")
            notes.append(
                "linker-genie-judge is not started: set GENIE_JUDGE_TOKEN in "
                "/etc/linker-genie.env and LINKER_GENIE_JUDGE_TOKEN in wp-config.php, "
                "then run this step again"
            )
        elif completed.returncode != 0:
            raise CutoverError(
                "activating the services failed (journalctl -u <unit> on the VPS)"
            )
        else:
            actions.append("activated engine, genie and the quality worker")
    else:
        actions.append(
            f"would activate: rsync {plan.ACTIVATE_SCRIPT} -> "
            f"{plan.SERVICES_SSH}:{staging_root}/activate.sh, then {activate} "
            "(uv sync, judge unit, daemon-reload, restart engine/genie/judge)"
        )
    for _service, option, variable in plan.SERVICE_OPTIONS:
        value = addresses.get(variable, "")
        if value:
            actions.append(f"{option} <- {variable} ({value})")
        else:
            notes.append(f"{option}: {variable} is not set — the window writes it")
    actions.append(f"repository: {repository}")
    return Result("services", actions, notes)


def verify(target: Target, *, cache_buster: str) -> Result:
    """Step 7's read-only subset: the entry points of both languages answer.

    The product pages carry an assertion the status cannot make: exactly one
    `Product` node in the page's JSON-LD. Two of them — one from this tree, one
    from the schema template the switch retires — is the failure the retirement
    exists to prevent, and both cases answer 200 (#81, GAP-7).
    """
    actions: list[str] = []
    notes: list[str] = []
    for path in plan.VERIFY_PATHS:
        status, body = target.http(path, cache_buster=cache_buster)
        german = path.startswith("/de/")
        language = 'lang="de' in body
        actions.append(
            f"GET {path} -> {status}" + (f" lang=de {language}" if german else "")
        )
        if status != 200:
            notes.append(f"{path} answered {status}")
        if german and not language:
            notes.append(f"{path} is not German")
        if path not in plan.VERIFY_PRODUCT_PATHS:
            continue
        products, unreadable = product_nodes(body)
        actions.append(
            f"GET {path} -> {products} {plan.VERIFY_PRODUCT_TYPE} node(s) in ld+json"
        )
        if products != 1:
            notes.append(
                f"{path} carries {products} {plan.VERIFY_PRODUCT_TYPE} nodes, "
                "expected exactly 1"
            )
        if unreadable:
            notes.append(
                f"{path}: {unreadable} JSON-LD block(s) did not parse — the count "
                "above is not the whole page"
            )
    for path, expected in plan.VERIFY_REDIRECTS:
        status, _ = target.http(path, cache_buster=cache_buster)
        actions.append(f"GET {path} -> {status} (expected {expected})")
        if status != expected:
            notes.append(f"{path} answered {status}, expected {expected}")
    return Result("verify", actions, notes)


def search_console(target: Target) -> Result:
    """The site is still a verified Search Console property (#145).

    Site Kit holds the verification: a virtual file `/google<token>.html`
    whose token is a user option of the administrator who connected it. A
    rollback to an older backup, a plugin cleanup or a Site Kit reset takes it
    away while every page still answers 200, and Search Console unverifies the
    owner a grace period later. The file is read without a cache-buster —
    Site Kit serves the exact path only, and that is what Google requests.
    Production only: a local instance is never connected to Google.
    """
    actions: list[str] = []

    def failed(note: str) -> Result:
        return Result(plan.SEARCH_CONSOLE_STEP, actions, [note])

    active = any(
        entry.get("status") == "active"
        for entry in target.wp_json(
            "plugin", "list", f"--name={plan.SITE_KIT}", "--fields=name,status"
        )
    )
    actions.append(f"{plan.SITE_KIT} active: {active}")
    if not active:
        return failed(
            f"{plan.SITE_KIT} is not active — Search Console loses its verification"
        )
    raw = target.wp(
        "option",
        "get",
        plan.SITE_KIT_SEARCH_CONSOLE_OPTION,
        "--format=json",
        check=False,
    )
    try:
        settings = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return failed(
            f"{plan.SITE_KIT_SEARCH_CONSOLE_OPTION} did not parse: {raw[:200]!r}"
        )
    if not isinstance(settings, dict):
        settings = {}
    owner = settings.get("ownerID")
    actions.append(
        f"Search Console property: {settings.get('propertyID')} (owner user {owner})"
    )
    if settings.get("propertyID") != plan.SEARCH_CONSOLE_PROPERTY or not owner:
        return failed(f"Site Kit is not connected to {plan.SEARCH_CONSOLE_PROPERTY}")
    token = target.wp(
        "user",
        "meta",
        "get",
        str(owner),
        table_prefix(target) + plan.SITE_KIT_VERIFICATION_FILE_META,
        check=False,
    ).strip()
    if not token:
        return failed(f"user {owner} holds no Site Kit verification file token")
    path = f"/google{token}.html"
    status, body = target.http(path, cache_buster=None)
    actions.append(f"GET {path} -> {status}")
    if status != 200 or f"google{token}.html" not in body:
        return failed(f"{path} does not serve the verification token")
    return Result(plan.SEARCH_CONSOLE_STEP, actions, [])


# The blocks a page declares as JSON-LD. WordPress writes the `type` attribute
# quoted and in either style, and not always first, so neither is assumed here.
_LD_JSON = re.compile(
    r"<script[^>]*type=[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


def product_nodes(html: str) -> tuple[int, int]:
    """(`Product` nodes, JSON-LD blocks that did not parse) in a page.

    Blocks, not nodes, would be the easy count and the wrong one: a single
    `@graph` holds two contradictory Product nodes as readily as two blocks do.
    What could not be read is returned rather than skipped — a block this
    cannot parse is a check that did not run, and a silent zero would read as
    "the page has none".
    """
    products = 0
    unreadable = 0
    for block in _LD_JSON.findall(html):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            unreadable += 1
            continue
        products += _product_count(parsed)
    return products, unreadable


def _product_count(node: object) -> int:
    """How many schema.org Product nodes one parsed JSON-LD value holds."""
    if isinstance(node, list):
        return sum(_product_count(item) for item in node)
    if not isinstance(node, dict):
        return 0
    count = 0
    types = node.get("@type")
    if types == plan.VERIFY_PRODUCT_TYPE or (
        isinstance(types, list) and plan.VERIFY_PRODUCT_TYPE in types
    ):
        count += 1
    graph = node.get("@graph")
    if isinstance(graph, list):
        count += sum(_product_count(item) for item in graph)
    return count


def rollback(target: Target, *, backup: Path) -> Result:
    """Step 8: the backup goes back, and the step checks what came back.

    The database import is what reactivates the old plugins — the activation
    list lives in the database — so the check that matters is not that the list
    changed but that the switch is undone: every plugin the switch removes is
    installed again. A rollback that leaves the site without them is the one
    outcome the window cannot afford to discover later.
    """
    backup_module.restore(target, Path(backup))
    listed = target.wp("plugin", "list", "--fields=name,status")
    installed = {
        line.split("\t")[0] for line in listed.splitlines()[1:] if line.strip()
    }
    missing = [slug for slug in plan.LEGACY_PLUGINS if slug not in installed]
    notes = [f"{slug} is not installed after the rollback" for slug in missing]
    return Result(
        "rollback",
        [
            f"restored {backup}",
            f"plugins listed: {len(installed)}",
            f"plugins the switch removes, back: {len(plan.LEGACY_PLUGINS) - len(missing)}/{len(plan.LEGACY_PLUGINS)}",
        ],
        notes,
    )


def autoload_report(target: Target, destination: Path) -> tuple[int, int]:
    """Write the autoloaded options, largest first, and return (count, bytes).

    Spec 17 §6 asks for the volume to be reviewed; WP-CLI's `option list` has no
    size field, so the size is the length of each value as the site stores it.
    Writing the list out is what makes the review possible after the window.
    """
    rows = target.wp_json("option", "list", "--autoload=on")
    sized = [
        (str(row.get("option_name", "")), len(str(row.get("option_value", ""))))
        for row in rows
        if isinstance(row, dict)
    ]
    sized.sort(key=lambda item: item[1], reverse=True)
    total = sum(size for _, size in sized)
    destination.write_text(
        json.dumps(
            {
                "total_bytes": total,
                "options": [
                    {"option_name": name, "bytes": size} for name, size in sized
                ],
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(sized), total


def table_names(target: Target) -> list[str]:
    """Every table with the site's own prefix, from WP-CLI's own listing."""
    listed = target.wp("db", "tables", "--all-tables-with-prefix", "--format=csv")
    return [name.strip() for name in listed.split(",") if name.strip()]


def table_prefix(target: Target) -> str:
    """The site's table prefix, from WP-CLI (`wp db prefix`)."""
    prefix = target.wp("db", "prefix").strip()
    if not prefix:
        raise CutoverError("wp db prefix returned nothing")
    return prefix


def option_names(target: Target) -> list[str]:
    """Every option name, from WP-CLI's own listing."""
    listed = target.wp(
        "option", "list", "--fields=option_name", "--format=csv"
    ).splitlines()
    return [line.strip() for line in listed[1:] if line.strip()]


def cron_hooks(target: Target) -> list[str]:
    """Every hook on the WP-Cron schedule, once each, in schedule order."""
    listed = target.wp("cron", "event", "list", "--fields=hook", "--format=csv")
    hooks: list[str] = []
    for line in listed.splitlines()[1:]:
        hook = line.strip()
        if hook and hook not in hooks:
            hooks.append(hook)
    return hooks


def is_legacy_table(name: str, prefix: str) -> bool:
    """Whether a table belongs to the old tree, given the site's own table prefix.

    The stored prefixes are prefix-relative (`linker_`, not `wp_linker_`), so a
    site that changed its table prefix is still matched — and a live table that
    merely contains the word is not.
    """
    return any(
        name.startswith(f"{prefix}{legacy}") for legacy in plan.LEGACY_TABLE_PREFIXES
    ) or name == (f"{prefix}{plan.SNIPPETS.suffix}")


def _is_legacy_option(name: str) -> bool:
    return name.startswith(plan.LEGACY_OPTION_PREFIXES)


def _is_legacy_cron_hook(hook: str) -> bool:
    return hook.startswith(plan.LEGACY_CRON_PREFIXES)


def _snippets_via_eval(target: Target) -> list[dict[str, object]]:
    """Read the snippet rows with WP-CLI's own PHP, whatever the table prefix is."""
    php = (
        "$rows = $GLOBALS['wpdb']->get_results("
        "\"SELECT id, name, active, scope, code FROM \" . $GLOBALS['wpdb']->prefix "
        '. "snippets ORDER BY id", ARRAY_A); echo wp_json_encode($rows);'
    )
    parsed = json.loads(target.wp("eval", php))
    if not isinstance(parsed, list):
        raise CutoverError("the snippets export did not return a list")
    return [row for row in parsed if isinstance(row, dict)]


def _identifier(name: str) -> str:
    """A table name safe to put in SQL: ours, but never interpolated unchecked."""
    if not name.replace("_", "").isalnum():
        raise CutoverError(f"{name!r} is not a table name")
    return f"`{name}`"


def _file_count(directory: Path) -> int:
    return sum(1 for path in directory.rglob("*") if path.is_file())
