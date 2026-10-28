"""Native PHP contract guard; only WordPress and the private status read are isolated."""

import os
import shutil
from pathlib import Path


def planner_wp(state_file: Path | None = None) -> list[str]:
    """Run the actual supplied PHP; no state file means an unconfigured planner."""
    php = shutil.which(os.environ.get("PHP", "php"))
    if php is None:
        raise RuntimeError("native PHP is required for the UI compatibility guard")
    prelude = r"""
namespace Linker\Tools\Planner {
class Principal { public function __construct(public string $kind, public string $subject) {} }
class Transport { public function object($actor,$path,$body) { if ($actor->kind!=='team'||$path!=='inputs/contracts'||$body!==['schema_version'=>1]||getenv('PLANNER_FIXTURE_STATE')==='') throw new \RuntimeException('wrong private contract'); return json_decode(file_get_contents(getenv('PLANNER_FIXTURE_STATE')),true); } }
}
namespace {
define('WP_CLI',true);
function get_option($key,$default='') { return $key==='linker_planner_url'&&getenv('PLANNER_FIXTURE_STATE')!==''?'https://private.invalid/planning':$default; }
function is_wp_error($value) { return false; }
if ($argc!==3||$argv[1]!=='eval') throw new \RuntimeException('fixture requires the native eval command');
eval($argv[2]);
}
"""
    return [
        "env",
        "PLANNER_FIXTURE_STATE=" + (str(state_file) if state_file is not None else ""),
        php,
        "-r",
        prelude,
    ]
