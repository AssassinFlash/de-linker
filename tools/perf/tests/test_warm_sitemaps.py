"""A retired draft shortcut must warm the uncached draft in the same language."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest


@pytest.mark.parametrize("german_target", ["/de/loesungsentwurf/", "/cart/"])
def test_retired_draft_destination(
    german_target: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    main = runpy.run_path(str(Path(__file__).parents[1] / "warm-sitemaps.py"))["main"]
    site = "https://linker.test"
    report = tmp_path / "warm.json"

    def get(url: str, *, xml: bool = False) -> tuple[dict[str, str | int], bytes]:
        route = urlsplit(url).path
        target = {"/solution-draft/": "/cart/", "/de/solution-draft/": german_target}
        result: dict[str, str | int] = {
            "status": 200,
            "url": site + target.get(route, route),
            "cache": "hit" if route == "/products/" else "",
            "server_policy": "no-cache",
            "browser_policy": "no-cache, private",
        }
        body = f"<urlset><url><loc>{site}/products/</loc></url></urlset>" if xml else ""
        return result, body.encode()

    monkeypatch.setitem(main.__globals__, "get", get)
    monkeypatch.setattr(sys, "argv", ["warm", "--site", site, "--output", str(report)])
    if german_target == "/cart/":
        with pytest.raises(SystemExit):
            main()
    else:
        main()
    failed = json.loads(report.read_text())["failed"]
    assert failed == (
        [site + "/de/solution-draft/"] if german_target == "/cart/" else []
    )
