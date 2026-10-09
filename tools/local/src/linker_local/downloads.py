"""Downloads kept in a cache, so a second instance or a reset does not fetch again."""

from __future__ import annotations

import hashlib
import os
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from linker_local.instance import SHARED

# Seconds a download may wait for data: the 600 that WP-CLI 2.12 gives its own
# `wp core download` (core-command, Core_Command::download()).
TIMEOUT = 600
# One cache for the whole Mac, shared by every data root.
CACHE = SHARED / ".cache"


class DownloadError(RuntimeError):
    """A download failed or its content is not the expected one."""


def fetch(url: str, cache: Path = CACHE, sha1: str | None = None) -> Path:
    """Return the cached copy of `url`, downloading it first when missing.

    With `sha1`, the file is checked on every call, cached or not, and a
    mismatch is an error: a release archive never changes, so a different hash
    means a damaged or substituted file.
    """
    target = cache / Path(urlsplit(url).path).name
    if not target.exists():
        cache.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".part")
        request = urllib.request.Request(url, headers={"User-Agent": "linker-local"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                with partial.open("wb") as handle:
                    shutil.copyfileobj(response, handle)
        except OSError as error:
            partial.unlink(missing_ok=True)
            raise DownloadError(f"{url}: {error}") from error
        os.replace(partial, target)
    if sha1 is not None:
        actual = _sha1(target)
        if actual != sha1:
            raise DownloadError(
                f"{target}: SHA-1 is {actual}, expected {sha1} (delete it to retry)"
            )
    return target


def _sha1(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha1").hexdigest()
