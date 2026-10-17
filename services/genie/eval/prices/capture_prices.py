"""Capture what the product abilities answer each kind of account (#242).

    uv run python eval/prices/capture_prices.py g242 http://127.0.0.1:9108 \
        tests/fixtures/prices.json \
        --approved g242-approved --pending g242-pending --restricted g242-restricted

For each account state the script mints the shell's own customer token through
WP-CLI (`just wp <instance> eval --user=<login>`, UserContext::mint: the token the
proxy hands the service, valid UserContext::TTL seconds), calls the abilities over HTTP the way
the service does (abilities.AbilityClient), and writes their answers. The guest
calls without a token. The token itself is never printed or written.

What is asked, from the live snapshot of 2026-10-17:
- search-products for "H2-10K-T3" (SAJ H2-10K-T3, product 4107): a search's card;
- get-product 4107 in English and German: the price line in each language;
- get-product 1957 (GoodWe GW208.9-BAT-LCD-G10, quoted per project), in both languages.

Only the fields the price path reads are kept (product id, title, facts, commerce),
so the fixture stays small and holds no documents.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from linker_genie.abilities import AbilityClient

MINT = "echo (new Linker\\Tools\\Genie\\UserContext())->mint();"
CALLS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("search_h2_en", "linker/search-products", {"text": "H2-10K-T3", "lang": "en"}),
    ("product_4107_en", "linker/get-product", {"product_id": 4107, "lang": "en"}),
    ("product_4107_de", "linker/get-product", {"product_id": 4107, "lang": "de"}),
    ("product_1957_en", "linker/get-product", {"product_id": 1957, "lang": "en"}),
    ("product_1957_de", "linker/get-product", {"product_id": 1957, "lang": "de"}),
)
KEPT = ("product_id", "title", "facts", "commerce")


def mint(instance: str, login: str, root: Path) -> str:
    """A fresh customer token for `login`, from the instance's own UserContext."""
    done = subprocess.run(
        ["just", "wp", instance, "eval", f"--user={login}", MINT],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    token = done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""
    if token.count("|") != 2:
        sys.exit(f"no token for {login}: is it a user of {instance}?")
    return token


def trim(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    if "qualified" in payload:
        return {
            **payload,
            "qualified": [
                {key: item[key] for key in KEPT if key in item}
                for item in payload["qualified"]
            ],
        }
    return {key: payload[key] for key in KEPT if key in payload}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instance")
    parser.add_argument("site")
    parser.add_argument("out", type=Path)
    for state in ("approved", "pending", "restricted"):
        parser.add_argument(f"--{state}", required=True, metavar="LOGIN")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    client = AbilityClient(args.site)
    states: dict[str, dict[str, Any]] = {}
    for state in ("approved", "pending", "restricted", "guest"):
        login = getattr(args, state, None)
        token = mint(args.instance, login, root) if login else None
        states[state] = {
            key: trim(client.run(name, arguments, token))
            for key, name, arguments in CALLS
        }
    args.out.write_text(
        json.dumps(states, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
