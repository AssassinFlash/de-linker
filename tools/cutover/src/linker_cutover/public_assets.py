"""Public browser files have a different mode contract from private staging."""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Iterable
from pathlib import Path

from linker_cutover.target import CutoverError, Target

# The incident's actual previous publication used directories 0755 and JS/fonts
# 0644; preserving private staging's 0700/0600 made the same bytes return 404.
# Only browser formats in the deployed assets/build contract become readable.
# PHP loaders, arbitrary JSON/config, vendor and backup data retain their modes.
_BROWSER_SUFFIXES = (
    ".js",
    ".mjs",
    ".css",
    ".ttf",
    ".otf",
    ".eot",
    ".woff",
    ".woff2",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".avif",
    ".ico",
    ".wasm",
)
_PUBLIC_TREES = ("assets", "build")

# Executed on the candidate's host, not on the source/private staging. The same
# read-only check is also prepended to the final SSH before the rename trap.
_REMOTE = r"""
import hashlib,json,os,stat,sys
from pathlib import Path
plans=json.loads(sys.argv[1]);normalize=sys.argv[2]=='normalize'
suffixes=set(json.loads(sys.argv[3]));expected=sys.argv[4];nodes={}
def fail(path):raise RuntimeError('public_asset_readability_failed: '+str(path))
def unreadable(error):fail(error.filename)
def regular(path,directory):
 try:s=path.lstat()
 except OSError:fail(path)
 if stat.S_ISLNK(s.st_mode) or not (stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode)):fail(path)
def browser_file(path):
 regular(path,False);nodes[path]=0o644
for plan in plans:
 root=Path(plan['path'])
 if not plan['directory']:
  browser_file(root);continue
 regular(root,True);nodes[root]=0o755
 roots=[]
 for name in ('assets','build'):
  tree=root/name
  if tree.is_symlink():fail(tree)
  if not tree.exists():continue
  regular(tree,True);roots.append(tree)
 if plan['theme']:
  for path in root.iterdir():
   if path.suffix.lower() in suffixes:
    browser_file(path);nodes[root]=0o755
 for tree in roots:
  nodes[root]=0o755
  for parent,dirs,files in os.walk(tree,onerror=unreadable,followlinks=False):
   parent=Path(parent);regular(parent,True);nodes[parent]=0o755
   for name in dirs:
    regular(parent/name,True)
   for name in files:
    path=parent/name
    if path.is_symlink():fail(path)
    if path.suffix.lower() in suffixes:browser_file(path)
if normalize:
 # Files first, deepest directories next, candidate root last. No source,
 # live tree, neighbour, private backup or out-of-artifact parent is changed.
 for path,wanted in sorted(nodes.items(),key=lambda item:(item[1]==0o755,-len(item[0].parts))):
  regular(path,wanted==0o755);path.chmod(wanted)
for path,wanted in nodes.items():
 regular(path,wanted==0o755)
 if stat.S_IMODE(path.stat().st_mode)!=wanted:fail(path)
fingerprint=hashlib.sha256(json.dumps(sorted((str(path),wanted)for path,wanted in nodes.items())).encode()).hexdigest()
if normalize:print('LINKER_PUBLIC_ASSETS='+fingerprint)
elif fingerprint!=expected:fail('prepared public inventory changed')
"""


def _command(
    target: Target,
    artifacts: Iterable[tuple[str, bool]],
    *,
    normalize: bool,
    expected: str | None = None,
) -> str:
    plans: list[dict[str, str | bool]] = []
    for relative, directory in artifacts:
        path = Path(relative)
        parts = path.parts
        if len(parts) < 3 or parts[:2] not in (
            ("wp-content", "plugins"),
            ("wp-content", "themes"),
        ):
            continue
        theme = parts[1] == "themes"
        tree = directory and len(parts) == 3
        file = (
            not directory
            and path.suffix.lower() in _BROWSER_SUFFIXES
            and (theme or (len(parts) > 4 and parts[3] in _PUBLIC_TREES))
        )
        if tree or file:
            candidate = str(path.with_name(f".{path.name}.next"))
            plans.append(
                {
                    "path": target.path_of(candidate),
                    "directory": directory,
                    "theme": theme,
                }
            )
    if not plans:
        return ""
    if not normalize and (
        expected is None or re.fullmatch(r"[a-f0-9]{64}", expected) is None
    ):
        raise CutoverError("public asset preparation proof is missing")
    return shlex.join(
        [
            "python3",
            "-c",
            _REMOTE,
            json.dumps(plans),
            "normalize" if normalize else "check",
            json.dumps(_BROWSER_SUFFIXES),
            expected or "",
        ]
    )


def prepare(target: Target, artifacts: Iterable[tuple[str, bool]]) -> str | None:
    """Make only incoming public browser files readable and verify the result."""
    command = _command(target, artifacts, normalize=True)
    if command:
        output = target.shell(command)
        records = re.findall(
            r"^LINKER_PUBLIC_ASSETS=([a-f0-9]{64})$", output, re.MULTILINE
        )
        if len(records) != 1:
            raise CutoverError("public asset preparation proof is unreadable")
        return records[0]
    return None


def check_script(
    target: Target, artifacts: Iterable[tuple[str, bool]], expected: str | None
) -> str:
    """Reject a changed/unreadable candidate before any live rename in that SSH."""
    return _command(target, artifacts, normalize=False, expected=expected)
