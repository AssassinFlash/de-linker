"""Control this worktree's c332 instance. Faults stay on 127.0.0.1."""

from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import time
import urllib.request
from pathlib import Path

HOST = "127.0.0.1"
INSTANCE = "c332"
HOME = Path.home() / "de-linker-local" / INSTANCE
WP = "http://127.0.0.1:9187"
GENIE = "http://127.0.0.1:9189"
GENIE_PORT = 9189
CHECKOUT = Path(__file__).resolve().parents[4]
UV = "/opt/homebrew/bin/uv"
INDEX = Path.home() / "de-linker-data/index/builds/20261018T173840Z/index.sqlite"
PID = HOME / "run" / "genie.pid"
LOG = HOME / "logs" / "genie.log"
TURN_LOG = HOME / "genie" / "turns.sqlite"
ABILITY_FLAG = HOME / "fault-ability.txt"
MU = HOME / "wordpress/wp-content/mu-plugins/c332-fault-ability.php"

# Keys a fault run may set. `just serve` inherits the parent environment, so
# restore strips them before restarting the healthy service.
FAULT_ENV = (
    "GENIE_BASE_URL",
    "DEEPSEEK_BASE_URL",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "GENIE_INDEX",
    "GENIE_API_KEY",
)

MU_SOURCE = """<?php
/**
 * Local fault for campaign #332. The runner deletes this file.
 *
 * @package Linker
 */

declare( strict_types = 1 );

add_filter(
	'rest_pre_dispatch',
	static function ( $result, $server, $request ) {
		unset( $server );
		$flag = %s;
		if ( ! is_readable( $flag ) ) {
			return $result;
		}
		$mode = trim( (string) file_get_contents( $flag ) );
		// rest_pre_dispatch runs before the route match, so the ability
		// name is not a parameter yet. Priority 100 is after ACF, which
		// returns null at priority 10 and would drop this error.
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) $_SERVER['REQUEST_URI'] : '';
		if ( ! str_contains( $uri, 'linker/search-products' ) ) {
			return $result;
		}
		if ( '500' === $mode ) {
			return new WP_Error( 'c332_fault', 'injected ability 500', array( 'status' => 500 ) );
		}
		if ( 'timeout' === $mode ) {
			sleep( 25 );
			return new WP_Error( 'c332_fault', 'injected ability timeout', array( 'status' => 504 ) );
		}
		return $result;
	},
	100,
	3
);
"""


def _run(
    argv: list[str], env: dict[str, str] | None = None, timeout: float = 120
) -> str:
    result = subprocess.run(
        argv,
        cwd=CHECKOUT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(argv)} -> {result.returncode}\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
        )
    return result.stdout


def wp(*args: str, timeout: float = 60) -> str:
    return _run(["just", "wp", INSTANCE, *args], timeout=timeout)


def service_token() -> str:
    text = wp("config", "get", "LINKER_GENIE_SERVICE_TOKEN", "--type=constant")
    token = text.strip().splitlines()[-1].strip()
    if len(token) < 32:
        raise RuntimeError("service token did not come back from wp-config")
    return token


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for key in FAULT_ENV:
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


def _start_time(pid: int) -> str:
    result = subprocess.run(
        ["ps", "-o", "lstart=", "-p", str(pid)],
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C", "TZ": "UTC"},
        check=False,
    )
    return result.stdout.strip()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_genie(pid: int, sig: int) -> None:
    """Signal the genie session. A pid we do not own is left alone."""
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return
    except PermissionError:
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError):
            return


def stop_genie() -> None:
    if not PID.is_file():
        return
    lines = PID.read_text().splitlines()
    if not lines:
        PID.unlink(missing_ok=True)
        return
    try:
        pid = int(lines[0])
    except ValueError:
        PID.unlink(missing_ok=True)
        return
    if _alive(pid):
        _signal_genie(pid, signal.SIGTERM)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and _alive(pid):
            time.sleep(0.1)
        if _alive(pid):
            _signal_genie(pid, signal.SIGKILL)
            time.sleep(0.3)
    if _alive(pid) and health():
        raise RuntimeError(
            f"genie pid {pid} is still listening and could not be signaled"
        )
    PID.unlink(missing_ok=True)
    time.sleep(0.2)


def start_genie(extra: dict[str, str] | None = None) -> None:
    token = service_token()
    env = clean_env(extra)
    env["GENIE_WP_URL"] = WP
    env["GENIE_LOG"] = str(TURN_LOG)
    env["GENIE_SERVICE_TOKEN"] = token
    env.setdefault("GENIE_INDEX", str(INDEX))
    argv = [
        UV,
        "run",
        "--locked",
        "--project",
        str(CHECKOUT / "services" / "genie"),
        "uvicorn",
        "linker_genie.app:app",
        "--host",
        HOST,
        "--port",
        str(GENIE_PORT),
    ]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    pid = os.posix_spawn(
        argv[0],
        argv,
        env,
        file_actions=[
            (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
            (
                os.POSIX_SPAWN_OPEN,
                1,
                str(LOG),
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o644,
            ),
            (os.POSIX_SPAWN_DUP2, 1, 2),
        ],
        setsid=True,
    )
    PID.write_text(f"{pid}\n{_start_time(pid)}\n{' '.join(argv)}\n")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if health():
            return
        time.sleep(0.2)
    raise RuntimeError(f"genie did not listen; tail of {LOG}:\n{_tail(LOG)}")


def restart_genie(extra: dict[str, str] | None = None) -> None:
    stop_genie()
    start_genie(extra)


def health() -> bool:
    try:
        with urllib.request.urlopen(f"{GENIE}/health", timeout=2) as reply:
            return int(reply.status) == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def restore() -> None:
    """Put Genie, the ability flag, the service URL and Redis back."""
    ABILITY_FLAG.unlink(missing_ok=True)
    MU.unlink(missing_ok=True)
    stop_genie()
    _run(["just", "serve", INSTANCE], env=clean_env(), timeout=180)
    ensure_redis()
    wp("option", "update", "linker_genie_url", GENIE)
    wp("cache", "flush")


def set_genie_url(url: str) -> None:
    wp("option", "update", "linker_genie_url", url)
    wp("cache", "flush")


def install_ability_fault() -> None:
    MU.parent.mkdir(parents=True, exist_ok=True)
    quoted = "'" + str(ABILITY_FLAG).replace("'", "\\'") + "'"
    MU.write_text(MU_SOURCE % quoted)


def set_ability_mode(mode: str) -> None:
    install_ability_fault()
    ABILITY_FLAG.write_text(mode)


def clear_ability_mode() -> None:
    ABILITY_FLAG.unlink(missing_ok=True)


def seed_upload_limit(units: int = 20) -> str:
    """Set the guest upload window to `units` for the loopback addresses."""
    php = f"""
global $wpdb;
$bucket = str_pad((string) intdiv(time(), HOUR_IN_SECONDS), 10, '0', STR_PAD_LEFT);
$names = array();
foreach (array('127.0.0.1', '::1', '') as $who) {{
    $row = 'linker_tools_limit_genie_upload.' . substr(md5($who), 0, 12) . '.' . $bucket;
    $wpdb->query($wpdb->prepare(
        "INSERT INTO {{$wpdb->options}} (option_name, option_value, autoload) VALUES (%s, %s, 'off')
         ON DUPLICATE KEY UPDATE option_value = %s",
        $row, '{units}', '{units}'
    ));
    $names[] = $row;
}}
echo implode(' ', $names);
"""
    return wp("eval", php).strip().splitlines()[-1]


def clear_upload_limit() -> None:
    wp(
        "db",
        "query",
        "DELETE FROM wp_options WHERE option_name LIKE 'linker_tools_limit_genie_upload.%'",
    )


def redis_bin() -> list[str]:
    return ["brew", "services"]


def ensure_redis() -> None:
    probe = subprocess.run(
        ["redis-cli", "ping"], capture_output=True, text=True, check=False
    )
    if probe.stdout.strip() == "PONG":
        return
    subprocess.run([*redis_bin(), "start", "redis"], check=False)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        probe = subprocess.run(
            ["redis-cli", "ping"], capture_output=True, text=True, check=False
        )
        if probe.stdout.strip() == "PONG":
            return
        time.sleep(0.3)
    raise RuntimeError("redis did not come back")


def redis_stop() -> None:
    subprocess.run([*redis_bin(), "stop", "redis"], check=True)


def redis_restart() -> None:
    subprocess.run([*redis_bin(), "restart", "redis"], check=True)
    ensure_redis()


def max_turn_id() -> int:
    """The newest turn id, or 0 when the log is missing. Read-only."""
    if not TURN_LOG.is_file():
        return 0
    connection = sqlite3.connect(f"file:{TURN_LOG}?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT COALESCE(MAX(id), 0) FROM turns").fetchone()
    except sqlite3.Error:
        return 0
    finally:
        connection.close()
    if row is None:
        return 0
    return int(row[0])


def latest_turn(question: str, after_id: int = 0) -> dict[str, object]:
    """The newest turn log row for `question` with id greater than `after_id`."""
    if not TURN_LOG.is_file():
        return {}
    connection = sqlite3.connect(f"file:{TURN_LOG}?mode=ro", uri=True)
    try:
        row = connection.execute(
            """
            SELECT id, provider, model, fallback, failures, grounded, understanding
            FROM turns WHERE question = ? AND id > ? ORDER BY id DESC LIMIT 1
            """,
            (question, after_id),
        ).fetchone()
    except sqlite3.Error:
        return {}
    finally:
        connection.close()
    if row is None:
        return {}
    return {
        "log_id": row[0],
        "provider": row[1],
        "model": row[2],
        "log_fallback": row[3],
        "log_failures": row[4],
        "log_grounded": row[5],
        "understanding": row[6],
    }


def _tail(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(errors="replace")[-2000:]
