"""Preview or apply the paired LiveCanvas home comparison mount through WP-CLI."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import reviewed_page_pair


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="WP-CLI prefix")
    parser.add_argument("--en", required=True, type=int)
    parser.add_argument("--de", required=True, type=int)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--remove", action="store_true")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "marketing_controls", Path(__file__).with_name("marketing-controls.py")
    )
    assert spec and spec.loader
    controls = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controls)

    ids = (args.en, args.de)
    snapshot = reviewed_page_pair.read(args.wp, *ids)
    before = tuple(snapshot["pages"][str(post)] for post in ids)
    installed = controls.plan_pair("home_project_comparison", *before)
    if args.remove:
        mount = '[linker_planner mode="home"]\n'
        after = tuple(page.replace(mount, "", 1) for page in installed)
    else:
        after = installed
    if before == after:
        print(f"{snapshot['home']} {ids}: already in the requested state")
        return
    if not (args.apply or args.remove):
        print(f"{snapshot['home']} {ids}: add one comparison mount on each homepage")
        return
    reviewed_page_pair.invoke(
        args.wp,
        {
            "mode": "adopt",
            "changes": [
                {"id": post, "before": old, "after": new}
                for post, old, new in zip(ids, before, after, strict=True)
            ],
            "metadata_before": snapshot["metadata"],
        },
    )
    result = reviewed_page_pair.read(args.wp, *ids)
    if tuple(result["pages"][str(post)] for post in ids) != after:
        raise RuntimeError("The bilingual comparison placement did not read back.")
    print(f"{snapshot['home']} {ids}: paired comparison placement verified")


if __name__ == "__main__":
    main()
