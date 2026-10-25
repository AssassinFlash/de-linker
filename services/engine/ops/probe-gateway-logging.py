"""Real disposable TLS/syslog probe; no live listener/config/model/mail writes.

Run with the installed engine virtualenv after operator coordination. Only the
native Gate classes run; their downstream is a byte-count sink. Certificates,
SQLite slots, syslog socket and nginx master belong to this temporary fixture.
"""

from __future__ import annotations

import hashlib
import http.client
import importlib
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

TOKEN = "synthetic-gateway-HEADERCANARY"
SUBJECT = "a" * 64
CANARIES = ("QUERYCANARY", "BODYCANARY", "HEADERCANARY", "PATHCANARY")


class Sink:
    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        size = 0
        while True:
            message = await receive()
            size += len(message.get("body", b""))
            if not message.get("more_body", False):
                break
        headers = dict(scope.get("headers", []))
        body = json.dumps(
            {
                "bytes": size,
                "request_id": headers.get(b"x-linker-request-id", b"").decode(),
            }
        ).encode()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": body})


def serve(kind: str, value: int) -> None:
    import uvicorn

    if kind == "engine":
        sys.path.insert(0, "/opt/linker-engine/current/src")
        app = importlib.import_module("linker_engine.gate").Gate(
            Sink(), limit=6 * 1024 * 1024
        )
    else:
        sys.path.insert(0, "/opt/linker-genie/current/src")
        app = importlib.import_module("linker_genie.gate").Gate(
            Sink(), limit=30 * 1024 * 1024
        )
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=value,
        lifespan="off",
        log_level="error",
        access_log=False,
    )


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


def request(
    value: int,
    context: ssl.SSLContext,
    route: str,
    *,
    auth: bool = True,
    oversized: int = 0,
    method: str = "POST",
) -> dict[str, Any]:
    conn = http.client.HTTPSConnection("127.0.0.1", value, timeout=5, context=context)
    conn.connect()
    assert isinstance(conn.sock, ssl.SSLSocket)
    tls = conn.sock.version()
    body = b"synthetic-BODYCANARY" if not oversized else b""
    headers = {
        "Authorization": "Bearer synthetic-HEADERCANARY",
        "User-Agent": "synthetic-HEADERCANARY",
        "X-Linker-Request-ID": "untrusted-HEADERCANARY",
        "X-Linker-Resource-Subject": SUBJECT,
        "Content-Length": str(oversized or len(body)),
    }
    if auth:
        headers["X-Linker-Service-Token"] = TOKEN
    conn.request(method, route + "?private=QUERYCANARY", body=body, headers=headers)
    response = conn.getresponse()
    data = response.read()
    result: dict[str, Any] = {
        "status": response.status,
        "request_id": response.getheader("X-Linker-Request-ID", ""),
        "tls": tls,
    }
    if response.status == 200:
        result["native"] = json.loads(data)
    conn.close()
    return result


def main() -> None:
    candidate = Path(sys.argv[1]).read_text()
    # Parse the exact production-path candidate before isolating its listeners,
    # certificate/runtime paths and syslog destination. This does not activate it.
    subprocess.run(
        ["/usr/sbin/nginx", "-t", "-q", "-c", str(Path(sys.argv[1]).resolve())],
        check=True,
    )
    processes: list[subprocess.Popen[bytes]] = []
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="linker533-tlslog-") as directory:
        base = Path(directory)
        engine, genie, proxy = port(), port(), port()
        assert len({engine, genie, proxy}) == 3
        env = {
            **os.environ,
            "GENIE_SERVICE_TOKEN": TOKEN,
            "LINKER_ENGINE_GATE_MODE": "enforce",
            "LINKER_ENGINE_CACHE": str(base / "cache"),
        }
        # This socket replaces /dev/log only in the disposable fixture. No test
        # request enters the real journal, production upstream or ledger.
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as logs:
            logs.bind(str(base / "access.sock"))
            logs.settimeout(0.5)
            try:
                for kind, value in [("engine", engine), ("genie", genie)]:
                    process = subprocess.Popen(
                        [sys.executable, __file__, "serve", kind, str(value)],
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    processes.append(process)
                    ready(value)
                subprocess.run(
                    [
                        "openssl",
                        "req",
                        "-x509",
                        "-newkey",
                        "rsa:2048",
                        "-nodes",
                        "-keyout",
                        str(base / "key.pem"),
                        "-out",
                        str(base / "cert.pem"),
                        "-days",
                        "1",
                        "-subj",
                        "/CN=localhost",
                        "-addext",
                        "subjectAltName=DNS:localhost,IP:127.0.0.1",
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                fixture = candidate.replace("user www-data;", "user root;")
                fixture = fixture.replace(
                    "listen 8443 ssl;", f"listen 127.0.0.1:{proxy} ssl;"
                )
                fixture = fixture.replace("/run/linker-engine-tls", str(base))
                fixture = fixture.replace("127.0.0.1:8901", f"127.0.0.1:{engine}")
                fixture = fixture.replace("127.0.0.1:8902", f"127.0.0.1:{genie}")
                fixture = fixture.replace("unix:/dev/log,", f"unix:{base}/access.sock,")
                fixture = fixture.replace(
                    "/etc/linker-engine/engine.crt", str(base / "cert.pem")
                ).replace("/etc/linker-engine/engine.key", str(base / "key.pem"))
                for sub in ["client", "proxy", "fastcgi", "uwsgi", "scgi"]:
                    (base / sub).mkdir()
                config = base / "isolated.conf"
                config.write_text(fixture)
                subprocess.run(
                    ["/usr/sbin/nginx", "-t", "-q", "-c", str(config)], check=True
                )
                # Retain actual TLS/config failure diagnostics, without ever
                # replacing/reloading a live configuration.
                invalid = base / "invalid.conf"
                invalid.write_text(
                    fixture.replace(str(base / "cert.pem"), str(base / "missing.pem"))
                )
                failure = subprocess.run(
                    ["/usr/sbin/nginx", "-t", "-q", "-c", str(invalid)],
                    capture_output=True,
                )
                assert (
                    failure.returncode != 0
                    and b"cannot load certificate" in failure.stderr
                )
                with (base / "gateway-error.log").open("wb") as errors:
                    gateway = subprocess.Popen(
                        [
                            "/usr/sbin/nginx",
                            "-c",
                            str(config),
                            "-g",
                            "daemon off; master_process on;",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=errors,
                    )
                    processes.append(gateway)
                    ready(proxy)
                    context = ssl.create_default_context(cafile=str(base / "cert.pem"))
                    checks: list[dict[str, Any]] = []
                    for route, cap in [
                        ("/design/residential", 6 * 1024 * 1024),
                        ("/genie/turn", 30 * 1024 * 1024),
                    ]:
                        cases: list[tuple[dict[str, Any], int]] = [
                            ({}, 200),
                            ({"auth": False}, 401),
                            ({"oversized": cap + 1}, 413),
                        ]
                        for args, expected in cases:
                            result = request(proxy, context, route, **args)
                            assert result["status"] == expected, result
                            checks.append(result)
                    # Real native engine single-flight rejection, no work/model.
                    sys.path.insert(0, "/opt/linker-engine/current/src")
                    slots = importlib.import_module("linker_engine.slots").Slots(
                        base / "cache" / "private" / "slots.sqlite"
                    )
                    held = slots.acquire(SUBJECT)
                    assert held is not None
                    try:
                        result = request(proxy, context, "/design/residential")
                        assert result["status"] == 429
                        checks.append(result)
                    finally:
                        slots.release(held)
                    result = request(proxy, context, "/PATHCANARY", method="PATHCANARY")
                    assert result["status"] == 200
                    checks.append(result)
                    # A stopped synthetic upstream generates native 502 diagnostics.
                    processes[0].terminate()
                    processes[0].wait(timeout=5)
                    result = request(proxy, context, "/design/residential")
                    assert result["status"] == 502
                    checks.append(result)
                    messages: list[str] = []
                    while True:
                        try:
                            messages.append(logs.recv(65536).decode())
                        except TimeoutError:
                            break
                    records = [json.loads(line[line.index("{") :]) for line in messages]
                    assert len(records) == len(checks), (len(records), len(checks))
                    for record in records:
                        assert set(record) == {
                            "schema",
                            "route",
                            "method",
                            "status",
                            "duration_s",
                            "request_bytes",
                            "sent_bytes",
                            "request_id",
                        }
                        assert record["schema"] == "linker_tls_access_v1"
                        assert record["method"] in {
                            "GET",
                            "POST",
                            "HEAD",
                            "OPTIONS",
                            "OTHER",
                        }
                        assert re.fullmatch(r"[a-f0-9]{32}", record["request_id"])
                        assert record["duration_s"] >= 0 and record["sent_bytes"] >= 0
                    assert not any(c in "".join(messages) for c in CANARIES)
                    indexed = {r["request_id"]: r for r in records}
                    for check in checks:
                        assert indexed[check["request_id"]]["status"] == check["status"]
                        assert check["tls"] in {"TLSv1.2", "TLSv1.3"}
                        if "native" in check:
                            assert check["native"]["request_id"] == check["request_id"]
                    assert any(
                        r["method"] == "OTHER" and r["route"] == "other"
                        for r in records
                    )
                    # A missing native logging destination must not stop requests.
                    # This closes only the fixture's own Unix socket, not /dev/log.
                    logs.close()
                    (base / "access.sock").unlink()
                    log_unavailable = request(proxy, context, "/genie/turn")
                    assert log_unavailable["status"] == 200
                    # The old private error channel is deliberately not declared
                    # PII-free: oversized/connect failures retain raw diagnostic context.
                    error_text = (base / "gateway-error.log").read_text()
                    assert (
                        "too large body" in error_text and "QUERYCANARY" in error_text
                    )
                    assert "connect() failed" in error_text
                    print(
                        json.dumps(
                            {
                                "candidate_sha256": hashlib.sha256(
                                    candidate.encode()
                                ).hexdigest(),
                                "checks": checks,
                                "access_records": records,
                                "access_canary_absent": True,
                                "private_error_diagnostics_retained": True,
                                "invalid_tls_config_diagnostic_retained": True,
                                "real_tls_certificate_verified": True,
                                "missing_syslog_still_serves_200": True,
                            },
                            indent=2,
                        )
                    )
            finally:
                for process in reversed(processes):
                    if process.poll() is None:
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
