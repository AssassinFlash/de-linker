import hashlib
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from linker_local.downloads import DownloadError, fetch

ARCHIVE = b"release archive"


class Origin:
    """A local HTTP server with one file, counting the requests for it."""

    def __init__(self) -> None:
        self.requests = 0
        origin = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                origin.requests += 1
                if self.path != "/release.zip":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(ARCHIVE)))
                self.end_headers()
                self.wfile.write(ARCHIVE)

            def log_message(self, format: str, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"


@pytest.fixture
def origin(monkeypatch: pytest.MonkeyPatch) -> Iterator[Origin]:
    for variable in (
        "HTTP_PROXY",
        "http_proxy",
        "HTTPS_PROXY",
        "https_proxy",
        "ALL_PROXY",
    ):
        monkeypatch.delenv(variable, raising=False)
    served = Origin()
    thread = threading.Thread(target=served.server.serve_forever)
    thread.start()
    yield served
    served.server.shutdown()
    thread.join()
    served.server.server_close()


def test_downloads_once_and_then_serves_the_cached_copy(
    tmp_path: Path, origin: Origin
) -> None:
    sha1 = hashlib.sha1(ARCHIVE).hexdigest()

    first = fetch(f"{origin.url}/release.zip", tmp_path, sha1=sha1)
    second = fetch(f"{origin.url}/release.zip", tmp_path, sha1=sha1)

    assert first == second == tmp_path / "release.zip"
    assert first.read_bytes() == ARCHIVE
    assert origin.requests == 1


def test_a_file_with_another_hash_is_refused_every_time(
    tmp_path: Path, origin: Origin
) -> None:
    for _ in range(2):
        with pytest.raises(DownloadError, match="SHA-1"):
            fetch(f"{origin.url}/release.zip", tmp_path, sha1="0" * 40)


def test_a_failed_download_leaves_nothing_in_the_cache(
    tmp_path: Path, origin: Origin
) -> None:
    with pytest.raises(DownloadError, match="404"):
        fetch(f"{origin.url}/missing.zip", tmp_path)

    assert list(tmp_path.iterdir()) == []
