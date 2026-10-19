"""Test process for #405. Not a route the service ships.

The integration test starts this file. It is the real Genie app plus one read
route on the same PageReader, so WordPress's `wp_remote_post` and the next
read share one cache.
"""

from __future__ import annotations

import socket
from typing import Any

import uvicorn
from pydantic import BaseModel, ConfigDict

from linker_genie.app import app, page_reader
from linker_genie.schema import PageContext, PageType


class ProbeRead(BaseModel):
    """One read-page: the type and path the shell would send on a turn."""

    model_config = ConfigDict(extra="forbid")

    type: PageType
    url: str
    post_id: int | None = None


@app.post("/__page_cache_test/read")
def read_for_test(body: ProbeRead) -> dict[str, Any]:
    """The next read-page, through the process that received the invalidation."""
    return page_reader().read(
        PageContext(type=body.type, url=body.url, post_id=body.post_id),
        "what does this page say",
        False,
    )


def main() -> None:
    """Listen on a free loopback port and print `READY <port>` once."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()
    print(f"READY {port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
