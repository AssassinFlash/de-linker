"""Disposable loopback-only ingress probe; never starts a business/model handler.

Run with the engine virtualenv on the VPS, only after operator coordination.
Uses the installed native Gate classes, a synthetic token, temporary ledgers,
random high ports and a separate nginx master. No production config is installed.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


class Sink:
    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        size = 0
        while True:
            message = await receive()
            size += len(message.get("body", b""))
            if not message.get("more_body", False):
                break
        body = json.dumps({"bytes": size}).encode()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": body})


def serve(kind: str, port: int) -> None:
    import uvicorn

    if kind == "engine":
        sys.path.insert(0, "/opt/linker-engine/current/src")
        from linker_engine.gate import Gate

        app = Gate(Sink(), limit=6 * 1024 * 1024)
    else:
        sys.path.insert(0, "/opt/linker-genie/current/src")
        from linker_genie.gate import Gate
        from linker_genie.schema import MAX_REQUEST_BYTES

        app = Gate(Sink(), limit=MAX_REQUEST_BYTES)
    uvicorn.run(app, host="127.0.0.1", port=port, lifespan="off", log_level="error")


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def ready(value: int) -> None:
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", value), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("isolated listener did not start")


def header_only(value: int, route: str, length: int, auth: bool) -> tuple[int, float]:
    with socket.create_connection(("127.0.0.1", value), timeout=3) as sock:
        header = (
            f"POST {route} HTTP/1.1\r\nHost: localhost\r\n"
            f"Content-Length: {length}\r\nConnection: close\r\n"
        )
        if auth:
            header += (
                "X-Linker-Service-Token: isolated-synthetic-token\r\n"
                + "X-Linker-Resource-Subject: "
                + "a" * 64
                + "\r\n"
            )
        began = time.monotonic()
        sock.sendall((header + "\r\n").encode())
        status = int(sock.recv(4096).split(b" ")[1])
        return status, round(time.monotonic() - began, 4)


def body_request(value: int, route: str, size: int, chunked: bool) -> tuple[int, int]:
    conn = http.client.HTTPConnection("127.0.0.1", value, timeout=15)
    headers = {
        "X-Linker-Service-Token": "isolated-synthetic-token",
        "X-Linker-Resource-Subject": "a" * 64,
    }
    body: Any = b"x" * size
    if chunked:
        body = (b"x" * min(65536, size - i) for i in range(0, size, 65536))
    try:
        conn.request("POST", route, body=body, headers=headers, encode_chunked=chunked)
    except BrokenPipeError:
        pass
    reply = conn.getresponse()
    data = reply.read()
    conn.close()
    return reply.status, json.loads(data).get("bytes", 0) if reply.status == 200 else 0


def main() -> None:
    candidate = Path(sys.argv[1]).read_text()
    processes: list[subprocess.Popen[bytes]] = []
    with tempfile.TemporaryDirectory(prefix="linker539-proxy-") as directory:
        base = Path(directory)
        engine, genie, proxy = port(), port(), port()
        assert len({engine, genie, proxy}) == 3
        env = {
            **os.environ,
            "GENIE_SERVICE_TOKEN": "isolated-synthetic-token",
            "LINKER_ENGINE_GATE_MODE": "enforce",
            "LINKER_ENGINE_CACHE": str(base / "cache"),
        }
        try:
            # Check the exact candidate with the existing certificate paths first.
            exact = base / "candidate.conf"
            exact.write_text(candidate)
            subprocess.run(
                ["/usr/sbin/nginx", "-t", "-q", "-c", str(exact)], check=True
            )
            for kind, value in [("engine", engine), ("genie", genie)]:
                processes.append(
                    subprocess.Popen(
                        [sys.executable, __file__, "serve", kind, str(value)],
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                )
                ready(value)
            # Preserve the candidate's actual proxy/body directives. Only isolate
            # listen/upstream/runtime paths and remove TLS for a loopback fixture.
            fixture = candidate.replace("user www-data;", "user root;")
            fixture = fixture.replace("listen 8443 ssl;", f"listen 127.0.0.1:{proxy};")
            fixture = fixture.replace("/run/linker-engine-tls", str(base))
            fixture = fixture.replace("127.0.0.1:8901", f"127.0.0.1:{engine}")
            fixture = fixture.replace("127.0.0.1:8902", f"127.0.0.1:{genie}")
            fixture = "\n".join(
                line for line in fixture.splitlines() if "ssl_" not in line
            )
            for sub in ["client", "proxy", "fastcgi", "uwsgi", "scgi"]:
                (base / sub).mkdir()
            config = base / "isolated.conf"
            config.write_text(fixture)
            processes.append(
                subprocess.Popen(
                    [
                        "/usr/sbin/nginx",
                        "-c",
                        str(config),
                        "-g",
                        "daemon off; master_process on;",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )
            ready(proxy)
            results: dict[str, Any] = {
                "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
                "ports": {"engine": engine, "genie": genie, "proxy": proxy},
                "candidate_syntax": "pass",
                "checks": [],
            }
            for kind, route, limit in [
                ("engine", "/design/residential", 6 * 1024 * 1024),
                ("genie", "/genie/turn", 30 * 1024 * 1024),
            ]:
                status, elapsed = header_only(proxy, route, 2 * 1024 * 1024, False)
                assert status == 401
                results["checks"].append(
                    {
                        "service": kind,
                        "case": "unauthorized headers only, zero body sent",
                        "status": status,
                        "seconds": elapsed,
                    }
                )
                status, _ = header_only(proxy, route, limit + 1, True)
                assert status == 413
                results["checks"].append(
                    {
                        "service": kind,
                        "case": "declared cap+1, zero body sent",
                        "status": status,
                    }
                )
                for size in [4 * 1024 * 1024 + 1, limit]:
                    status, seen = body_request(proxy, route, size, False)
                    assert (status, seen) == (200, size)
                    results["checks"].append(
                        {
                            "service": kind,
                            "case": "within public proxy cap",
                            "bytes": size,
                            "status": status,
                            "native_seen": seen,
                        }
                    )
                status, _ = body_request(proxy, route, limit + 1, True)
                assert status == 413
                results["checks"].append(
                    {"service": kind, "case": "chunked cap+1", "status": status}
                )
            # Check the unmodified actual native Genie cap independently of its
            # narrower existing WordPress/proxy raw-request envelope.
            sys.path.insert(0, "/opt/linker-genie/current/src")
            from linker_genie.schema import MAX_REQUEST_BYTES

            status, _ = body_request(genie, "/turn", MAX_REQUEST_BYTES + 1, True)
            assert status == 413
            results["checks"].append(
                {
                    "service": "genie",
                    "case": "direct native chunked cap+1",
                    "native_cap": MAX_REQUEST_BYTES,
                    "status": status,
                }
            )
            results["spool_files"] = sum(
                len(list((base / sub).rglob("*")))
                for sub in ["client", "proxy", "fastcgi", "uwsgi", "scgi"]
            )
            assert results["spool_files"] == 0
            print(json.dumps(results, indent=2))
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    print(json.dumps({"cleanup": "own processes stopped and temporary tree removed"}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve(sys.argv[2], int(sys.argv[3]))
    else:
        main()
