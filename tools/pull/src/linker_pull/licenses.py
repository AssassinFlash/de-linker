"""The licences a loaded instance runs with, applied after every load (#252).

A snapshot carries no licence (anonymize drops `lc_apikey` and every
`*licen[cs]e*` option), so every reload used to bring back LiveCanvas's
"Please activate your product" banner and SEOPress PRO's "Activate your
license" link. This module puts the live site's activation state back into
the local database, read from two places and never printed:

- SEOPress PRO: the key is the owner's, in ~/.config/terravolt-builder/seopress.env
  (SEOPRESS_LICENSE_KEY; the same key live runs, checked 2026-10-17). The
  status and the expiry are what live holds: SEOPress PRO calls its store on
  every admin page while the status is valid and no expiry is stored
  (seopress_migrate_license_expiry, wp-seopress-pro 10.2.1 inc/admin/cron.php),
  and the local isolation blocks that call.
- LiveCanvas: its banner keys on the site option `lc_apikey`
  (livecanvas-plugin-index.php, the admin_notices hook), an apikey its
  updater issues per site from the licence code. The local instance reuses
  live's site apikey, read from live: issuing one would register every local
  address with LiveCanvas's updater, and the local isolation blocks every
  call that apikey could make anyway (#252 decided this between the two ways
  the ticket named).

Values travel from ssh's or the file's bytes into `wp option update`'s
standard input, so they reach no argument list, log or result.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Protocol

from linker_pull import live

# Where the owner keeps the licence files (600, outside the repository);
# LINKER_LICENSE_DIR points elsewhere, for the tests.
DEFAULT_DIRECTORY = Path.home() / ".config" / "terravolt-builder"
SEOPRESS_FILE = "seopress.env"
SEOPRESS_VARIABLE = "SEOPRESS_LICENSE_KEY"
# The live options the local instance copies, as LIVE_OPTIONS in live.py allows them.
LIVECANVAS_APIKEY = "lc_apikey"
SEOPRESS_STATUS = "seopress_pro_license_status"
SEOPRESS_EXPIRY = "seopress_pro_license_expiry"


class Wp(Protocol):
    def run(self, *args: str, stdin: Iterator[bytes] | None = None) -> str: ...


ReadLive = Callable[[str], str]


def directory() -> Path:
    return Path(os.environ.get("LINKER_LICENSE_DIR") or DEFAULT_DIRECTORY)


def env_value(path: Path, name: str) -> str | None:
    """`name`'s value in a KEY=value file; None when the file or the line is missing."""
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        return None
    for line in lines:
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip().strip("'\"") or None
    return None


def apply(wp: Wp, read_live: ReadLive | None = None) -> dict[str, str]:
    """Write the licences into the instance; per product, "applied" or why not.

    `read_live` reads one LIVE_OPTIONS option from live (live.option unless given).
    """
    read = read_live or live.option
    report: dict[str, str] = {}

    key = env_value(directory() / SEOPRESS_FILE, SEOPRESS_VARIABLE)
    if key is None:
        report["seopress-pro"] = (
            f"not applied: no {SEOPRESS_VARIABLE} in {directory() / SEOPRESS_FILE}"
        )
    else:
        try:
            status = read(SEOPRESS_STATUS)
            expiry = read(SEOPRESS_EXPIRY)
        except live.LiveError as error:
            report["seopress-pro"] = f"not applied: {error}"
        else:
            _update(wp, "seopress_pro_license_key", key)
            _update(wp, SEOPRESS_STATUS, status)
            if expiry:
                _update(wp, SEOPRESS_EXPIRY, expiry)
            report["seopress-pro"] = (
                "applied" if status == "valid" else f"applied, live status {status!r}"
            )

    try:
        apikey = read(LIVECANVAS_APIKEY)
    except live.LiveError as error:
        report["livecanvas"] = f"not applied: {error}"
    else:
        if apikey:
            _update(wp, LIVECANVAS_APIKEY, apikey)
            report["livecanvas"] = "applied"
        else:
            report["livecanvas"] = "not applied: live has no lc_apikey"
    return report


def _update(wp: Wp, name: str, value: str) -> None:
    # Without a value argument `wp option update` reads it from standard input.
    # The plugins stay unloaded, so SEOPress's sanitize callback, which deletes
    # the status whenever the key changes (seopress_sanitize_license), stays out.
    wp.run(
        "option",
        "update",
        name,
        "--skip-plugins",
        "--skip-themes",
        stdin=iter([value.encode()]),
    )
