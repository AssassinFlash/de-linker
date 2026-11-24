"""The one-time transition from a shared WindPress bundle to page styles."""

from __future__ import annotations

import shlex
from pathlib import Path

from .target import Target

WINDPRESS = "wp-content/uploads/windpress"
CACHE = WINDPRESS + "/cache"
HERO = WINDPRESS + "/data/hero-readability.css"
PATHS = (".htaccess", WINDPRESS + "/data/main.css", CACHE, HERO)
PAGE_STYLES = "includes/Presentation/WindPressPageStyles.php"
APPLICATION = "includes/Planner/Application.php"

# Load the staged PHP in a standalone interpreter. WordPress has already loaded
# the old Application in the WP-CLI process while the candidates are staged.
_EDGE_CHECK = r"""
require $argv[1];
$app = new \Linker\Tools\Planner\Application('');
$expected = trim(substr($app->cache_rules('RewriteEngine On'), strlen('RewriteEngine On')));
$text = str_replace("\r\n", "\n", file_get_contents($argv[2]));
preg_match('/^# BEGIN WordPress$\n(.*?)^# END WordPress$/ms', $text, $matches);
$block = $matches[1] ?? '';
$shortcut = strpos($block, 'RewriteCond %{REQUEST_FILENAME} !-f');
$before = false === $shortcut ? '' : substr($block, 0, $shortcut);
if ('' === $expected || !str_contains("\n" . $before, "\n" . $expected . "\n")
    || !preg_match('/^RewriteRule [^\n]+index\.php\?linker_public_document=\$1 \[END,NC,QSA\]$/m', $before)) {
    throw new RuntimeException('Install the planner cache bypass and keep the Woo PDF rewrite before the WordPress static-file shortcut.');
}
"""


def check_edge(target: Target, app: str) -> None:
    """Read back the active WordPress block using the candidate's own rules."""
    target.shell(
        shlex.join(["php", "-r", _EDGE_CHECK, app, target.path_of(".htaccess")])
    )


def check_snapshot(target: Target, directory: str, deploy_id: str) -> None:
    """Read the bound pre-release copy before either direction of the switch."""
    saved = Path(directory) / "files"

    def quote(name: str) -> str:
        return shlex.quote(str(saved / name))

    marker = shlex.quote(str(Path(directory) / "deploy-id"))
    hero = quote(HERO)
    tests = [
        f'[ "$(cat {marker})" = {shlex.quote(deploy_id)} ]',
        f"test -s {quote('.htaccess')}",
        f"test -s {quote(WINDPRESS + '/data/main.css')}",
        f"test -s {quote(CACHE + '/tailwind.css')}",
        f"{{ test -s {hero} && test ! -e {hero}.absent; }} || {{ test ! -e {hero} && test -f {hero}.absent; }}",
    ]
    target.shell(
        "set -eu\n(\n"
        + " &&\n".join(f"( {test} )" for test in tests)
        + f"\n) || {{ echo 'Incomplete P0-A rollback snapshot for {deploy_id}' >&2; exit 1; }}"
    )
