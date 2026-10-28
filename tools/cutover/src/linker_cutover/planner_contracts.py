"""Refuse a UI that cannot preserve retained or currently writable inputs."""

from __future__ import annotations

import json
import shlex
from collections.abc import Iterable
from pathlib import PurePosixPath

from .target import Target

_TOOLS = "wp-content/plugins/linker-tools"
_DECLARATIONS = ("project-input-contracts.json", "build/planner/source-manifest.json")

# Native server transport preserves its configured origin, TLS verification and
# private team identity. This is never exposed as a browser/public Gateway RPC.
_CHECK = r"""
if (!defined('WP_CLI') || !WP_CLI) { throw new RuntimeException('planner UI compatibility requires native operator'); }
$paths = json_decode(%s, true, 16, JSON_THROW_ON_ERROR);
$fail = static function () { throw new RuntimeException('planner UI input compatibility refused'); };
$contracts = static function ($value) use ($fail) {
    if (!is_array($value) || !array_is_list($value)) { $fail(); }
    foreach ($value as $item) {
        if (!is_string($item) || 1 !== preg_match('/\A[a-z][a-z0-9_]*\z/', $item)) { $fail(); }
    }
    if (count(array_unique($value)) !== count($value)) { $fail(); }
    return $value;
};
$capabilities = null;
foreach ($paths as $index => $path) {
    $declared = array();
    if (null !== $path && file_exists($path)) {
        if (is_link($path) || !is_file($path) || realpath($path) !== $path) { $fail(); }
        $value = json_decode(file_get_contents($path), true, 32, JSON_THROW_ON_ERROR);
        if (!is_array($value)) { $fail(); }
        if (0 === $index && (1 !== ($value['schema_version'] ?? null) || array_diff(array_keys($value), array('schema_version', 'project_input_contracts')))) { $fail(); }
        $declared = $contracts($value['project_input_contracts'] ?? array());
    }
    $capabilities = null === $capabilities ? $declared : array_intersect($capabilities, $declared);
}
if ('' !== (string) get_option('linker_planner_url', '')) {
    if (!class_exists(\Linker\Tools\Planner\Transport::class)) { $fail(); }
    $state = (new \Linker\Tools\Planner\Transport())->object(
        new \Linker\Tools\Planner\Principal('team', 'ui-release-compatibility'),
        'inputs/contracts', array('schema_version' => 1)
    );
    if (is_wp_error($state) || 1 !== ($state['schema_version'] ?? null)
        || !is_string($state['input_inventory_sha256'] ?? null)
        || 1 !== preg_match('/\A[a-f0-9]{64}\z/', $state['input_inventory_sha256'])
        || !is_int($state['retained_revision_count'] ?? null) || $state['retained_revision_count'] < 0
        || !is_int($state['retained_input_count'] ?? null) || $state['retained_input_count'] < 0) { $fail(); }
    $required = array_unique(array_merge(
        $contracts($state['required_input_contracts'] ?? null),
        $contracts($state['supported_input_contracts'] ?? null)
    ));
    if (array_diff($required, $capabilities ?? array())) { $fail(); }
}
"""


def check_script(target: Target, replacements: Iterable[tuple[str, str | None]]) -> str:
    """Check the exact incoming or rollback files in the final rename shell.

    Both the generated source declaration and the compiled planner declaration
    must support the floor; copying a new declaration over an old bundle cannot
    authorize that old UI. Absent declarations are empty, never an exemption.
    """
    changes = list(replacements)
    if not any(path == _TOOLS or path.startswith(_TOOLS + "/") for path, _ in changes):
        return ""
    paths: list[str | None] = []
    for declaration in _DECLARATIONS:
        relative = _TOOLS + "/" + declaration
        value: str | None = target.path_of(relative)
        for changed, candidate in changes:
            if relative == changed or relative.startswith(changed + "/"):
                tail = str(PurePosixPath(relative).relative_to(changed))
                value = (
                    str(PurePosixPath(candidate) / tail)
                    if candidate is not None and tail != "."
                    else candidate
                )
        paths.append(value)
    # JSON is encoded as one PHP string literal, then the complete program is
    # shell-quoted by shlex. Neither path nor credentials enter shell code.
    php = _CHECK % (
        "'" + json.dumps(paths).replace("\\", "\\\\").replace("'", "\\'") + "'"
    )
    return shlex.join([*target.wp_on_target(), "eval", php])
