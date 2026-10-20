"""Run the #334 battery against a local Genie. Refuses any non-loopback target.

Records one JSON file per case under the evidence directory. Attachment bytes
are not copied into that JSON. Nothing in this script submits an inquiry, a
contact form, or a mail job.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.client import HTTPResponse
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from cases import CASES, MARKER, Case
from corpus import build
from grade import grade

EVIDENCE = Path(
    os.environ.get("C334_EVIDENCE", Path.home() / "de-linker-data/campaign-334")
)
TIMEOUT = 240
INSTANCE = os.environ.get("C334_INSTANCE", "c334")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("only", nargs="*", help="case id prefixes, for example N1 P")
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument(
        "--summarise-only",
        action="store_true",
        help="rewrite summary.json from the run files already on disk",
    )
    parser.add_argument(
        "--wp", default=os.environ.get("C334_WP", "http://127.0.0.1:9193")
    )
    parser.add_argument("--genie", default=os.environ.get("C334_GENIE", ""))
    parser.add_argument("--instance", default=os.environ.get("C334_INSTANCE", "c334"))
    args = parser.parse_args()
    global INSTANCE
    INSTANCE = args.instance
    if args.summarise_only:
        evidence = EVIDENCE
        summary = _summarise(evidence)
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {key: summary[key] for key in ("pass", "defect", "error", "sent")},
                indent=2,
            )
        )
        return
    _local(args.wp)
    evidence = EVIDENCE
    evidence.mkdir(parents=True, exist_ok=True)
    corpus_dir = evidence / "corpus"
    manifest = build(corpus_dir)
    token = _token(args.instance)
    genie = args.genie or _genie_url(args.instance)
    _local(genie)
    product = _product(args.instance, args.wp)
    (evidence / "product.json").write_text(
        json.dumps(product, indent=2) + "\n", encoding="utf-8"
    )
    before = _side_effects(args.instance)
    (evidence / "side-effects-before.json").write_text(
        json.dumps(before, indent=2) + "\n", encoding="utf-8"
    )
    listener = _Listener()
    listener.start()
    selected = [
        case for case in CASES if case.channel != "browser" and _wanted(case, args.only)
    ]
    try:
        for case in selected:
            path = evidence / "runs" / f"{case.id}.json"
            if path.is_file() and not args.rerun:
                print(f"skip {case.id}", flush=True)
                continue
            print(f"run {case.id} {case.title}", flush=True)
            record = _run_case(case, manifest, genie, token, args.wp, product)
            record["grade"] = grade(case.expectation(), record).as_dict()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(
                f"  {record['grade']['verdict']} {record.get('duration_ms')} ms",
                flush=True,
            )
    finally:
        listener.stop()
    persisted = _persisted(args.instance, evidence)
    (evidence / "persistence.json").write_text(
        json.dumps(persisted, indent=2) + "\n", encoding="utf-8"
    )
    after = _side_effects(args.instance)
    (evidence / "side-effects-after.json").write_text(
        json.dumps(after, indent=2) + "\n", encoding="utf-8"
    )
    sent = _sent(before, after) or bool(listener.hits)
    (evidence / "exfil-hits.json").write_text(
        json.dumps(listener.hits, indent=2) + "\n", encoding="utf-8"
    )
    _apply_global(evidence, persisted, sent)
    summary = _summarise(evidence)
    (evidence / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: summary[key] for key in ("pass", "defect", "error", "sent")}, indent=2
        )
    )


def _run_case(
    case: Case,
    manifest: dict[str, Any],
    genie: str,
    token: str,
    wp: str,
    product: dict[str, Any],
) -> dict[str, Any]:
    info = manifest["files"][case.file]
    path = Path(str(info["path"]))
    mime = case.declared or str(info["mime"])
    started = time.time()
    try:
        if case.channel == "proxy":
            step = _proxy_turn(wp, case, path, mime, product)
            steps = [step]
        else:
            step = _service_turn(
                genie, token, case, path, mime, product, readings=None, messages=None
            )
            steps = [step]
            if case.followup and step.get("status") == 200 and not step.get("error"):
                prior = [
                    {"role": "user", "content": case.question},
                    {"role": "assistant", "content": str(step.get("answer") or "")},
                    {"role": "user", "content": case.followup},
                ]
                follow = _service_turn(
                    genie,
                    token,
                    case,
                    path,
                    mime,
                    product,
                    readings=step.get("readings")
                    if isinstance(step.get("readings"), list)
                    else [],
                    messages=prior,
                    attach=False,
                )
                steps.append(follow)
    except Exception as error:  # noqa: BLE001 — one case must not abort the battery
        steps = [{"status": 0, "error": f"{type(error).__name__}: {error}"}]
    duration = int((time.time() - started) * 1000)
    first = steps[0]
    return {
        "id": case.id,
        "group": case.group,
        "owasp": case.owasp,
        "title": case.title,
        "channel": case.channel,
        "file": case.file,
        "file_name": info["name"],
        "mime": mime,
        "sha256": info["sha256"],
        "source": info["source"],
        "question": case.question,
        "followup": case.followup,
        "duration_ms": duration,
        "status": first.get("status"),
        "error_code": first.get("error_code"),
        "answer": first.get("answer"),
        "readings": first.get("readings"),
        "meta": first.get("meta"),
        "blocks": first.get("blocks"),
        "attachment_events": first.get("attachment_events"),
        "steps": _public_steps(steps),
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def _service_turn(
    genie: str,
    token: str,
    case: Case,
    path: Path,
    mime: str,
    product: dict[str, Any],
    readings: list[Any] | None,
    messages: list[dict[str, str]] | None,
    attach: bool = True,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "conversation_id": f"c334-{case.id}",
        "messages": messages or [{"role": "user", "content": case.question}],
        "locale": case.locale,
        "page_context": _page(case, product),
        "user": {"logged_in": False, "partner": False},
    }
    if attach:
        body["attachments"] = [
            {
                "name": path.name,
                "type": mime,
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        ]
    if readings:
        body["readings"] = readings
    status, raw = _post(
        f"{genie.rstrip('/')}/turn", body, {"X-Linker-Service-Token": token}
    )
    parsed = _parse_sse(raw) if status == 200 else {"events": [], "raw": raw[:2000]}
    answer = _texts(parsed.get("blocks"))
    return {
        "status": status,
        "error_code": _error_code(raw) if status != 200 else None,
        "answer": answer,
        "readings": parsed.get("readings"),
        "meta": parsed.get("meta"),
        "blocks": parsed.get("blocks"),
        "attachment_events": parsed.get("attachments"),
        "error": None if status == 200 else raw[:500],
    }


def _proxy_turn(
    wp: str, case: Case, path: Path, mime: str, product: dict[str, Any]
) -> dict[str, Any]:
    # Refusals still spend the hourly upload allowance. Reset it so a 429 is
    # not mistaken for the type rejection these cases are measuring.
    _reset_quota()
    jar: dict[str, str] = {}
    body = {
        "locale": case.locale,
        "messages": [{"role": "user", "content": case.question or "Attached: file"}],
        "page": _page(case, product),
        "attachments": [
            {
                "name": path.name,
                "type": mime,
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        ],
    }
    status, raw, jar = _post_cookies(
        f"{wp.rstrip('/')}/wp-json/linker-ai/v1/genie/turn", body, jar
    )
    if status != 200:
        return {
            "status": status,
            "error_code": _error_code(raw),
            "answer": "",
            "error": raw[:500],
        }
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": status, "error": "proxy body is not JSON", "answer": ""}
    stream = str(payload.get("stream") or "")
    parsed = _parse_sse(stream)
    return {
        "status": status,
        "conversation_id": payload.get("conversation_id"),
        "answer": _texts(parsed.get("blocks")),
        "readings": parsed.get("readings"),
        "meta": parsed.get("meta"),
        "blocks": parsed.get("blocks"),
        "attachment_events": parsed.get("attachments"),
        "cookies": sorted(jar),
    }


def _page(case: Case, product: dict[str, Any]) -> dict[str, Any]:
    if case.page != "product":
        return {"type": "other"}
    return {
        "type": "product",
        "product_id": product.get("id"),
        "post_id": product.get("id"),
        "url": product.get("url"),
        "title": product.get("title"),
    }


def _post(url: str, body: dict[str, Any], headers: dict[str, str]) -> tuple[int, str]:
    _local(url)
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            **headers,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def _post_cookies(
    url: str, body: dict[str, Any], jar: dict[str, str]
) -> tuple[int, str, dict[str, str]]:
    _local(url)
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if jar:
        headers["Cookie"] = "; ".join(f"{key}={value}" for key, value in jar.items())
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            _keep(jar, response)
            return response.status, response.read().decode("utf-8", "replace"), jar
    except urllib.error.HTTPError as error:
        _keep(jar, error)
        return error.code, error.read().decode("utf-8", "replace"), jar


def _keep(jar: dict[str, str], response: HTTPResponse | urllib.error.HTTPError) -> None:
    raw = (
        response.headers.get_all("Set-Cookie") if response.headers is not None else None
    )
    for header in raw or []:
        pair = header.split(";", 1)[0]
        if "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        if value == "":
            jar.pop(name.strip(), None)
        else:
            jar[name.strip()] = value.strip()


def _parse_sse(stream: str) -> dict[str, Any]:
    meta = None
    blocks: list[Any] = []
    readings: list[Any] = []
    attachments: list[Any] = []
    for event in stream.split("\n\n"):
        name = _field(event, "event")
        data = _field(event, "data")
        if not name or data is None:
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        if name == "meta":
            meta = payload
        elif name == "block":
            blocks.append(payload)
        elif name == "reading":
            readings.append(payload)
        elif name == "attachment":
            attachments.append(payload)
    return {
        "meta": meta,
        "blocks": blocks,
        "readings": readings,
        "attachments": attachments,
    }


def _field(event: str, name: str) -> str | None:
    prefix = f"{name}: "
    for line in event.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return None


def _texts(blocks: Any) -> str:
    if not isinstance(blocks, list):
        return ""
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
    return "\n".join(parts)


def _error_code(raw: str) -> str | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        code = payload.get("code")
        return str(code) if isinstance(code, str) else None
    return None


def _public_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for step in steps:
        item = dict(step)
        item.pop("cookies", None)
        cleaned.append(item)
    return cleaned


def _local(url: str) -> None:
    host = urlsplit(url).hostname
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit(f"refusing non-local target {url}")


def _token(instance: str) -> str:
    file = EVIDENCE / "service-token.txt"
    if file.is_file() and file.read_text(encoding="utf-8").strip():
        return file.read_text(encoding="utf-8").strip()
    raw = _wp(
        instance, ["config", "get", "LINKER_GENIE_SERVICE_TOKEN", "--type=constant"]
    )
    token = raw.strip().splitlines()[-1].strip()
    if not token or token.lower() == "null":
        raise SystemExit("Genie service token is not configured on this instance")
    file.write_text(token + "\n", encoding="utf-8")
    file.chmod(0o600)
    return token


def _genie_url(instance: str) -> str:
    raw = _wp(instance, ["option", "get", "linker_genie_url"])
    url = raw.strip().splitlines()[-1].strip()
    if not url.startswith("http"):
        raise SystemExit(
            f"linker_genie_url is not set ({url!r}); run just serve {instance}"
        )
    return url


def _product(instance: str, wp: str) -> dict[str, Any]:
    _local(wp)
    raw = _wp(
        instance,
        [
            "eval",
            """
            $posts = get_posts(array(
                'post_type' => 'product',
                'post_status' => 'publish',
                's' => 'H2-10K-T3',
                'posts_per_page' => 5,
                'fields' => 'ids',
            ));
            $id = 0;
            foreach ($posts as $post_id) {
                $title = get_the_title($post_id);
                if (!is_string($title) || !str_contains($title, 'H2-10K-T3')) { continue; }
                $lang = function_exists('pll_get_post_language') ? pll_get_post_language($post_id) : '';
                if ($lang === 'en') { $id = (int) $post_id; break; }
                if ($id === 0) { $id = (int) $post_id; }
            }
            if ($id === 0) { echo '{}'; return; }
            echo json_encode(array('id' => $id, 'title' => get_the_title($id), 'url' => get_permalink($id)));
            """,
        ],
    )
    line = raw.strip().splitlines()[-1]
    found = json.loads(line)
    if not isinstance(found, dict) or "id" not in found:
        raise SystemExit(
            "could not resolve a published H2-10K-T3 product on this instance"
        )
    return found


def _wp(instance: str, args: list[str]) -> str:
    repo = Path(__file__).resolve().parents[4]
    done = subprocess.run(
        ["just", "wp", instance, *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise SystemExit(done.stderr[-1000:] or done.stdout[-1000:])
    return done.stdout


def _side_effects(instance: str) -> dict[str, Any]:
    mail = Path.home() / "de-linker-local" / instance / "mail"
    names = (
        sorted(path.name for path in mail.glob("*") if path.is_file())
        if mail.is_dir()
        else []
    )
    # HPOS orders live in wp_wc_orders and never become shop_order posts.
    # Count both, and only touch the HPOS table when it exists.
    counts = _wp(
        instance,
        [
            "db",
            "query",
            "SELECT "
            "(SELECT COUNT(*) FROM wp_posts WHERE post_type='shop_order') AS orders_posts, "
            "(SELECT COUNT(*) FROM wp_posts WHERE post_type='linker_mail_job') AS mail_jobs, "
            "(SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'wp_wc_orders') AS has_hpos",
            "--skip-column-names",
        ],
    )
    line = counts.strip().splitlines()[-1] if counts.strip() else ""
    fields = line.split()
    hpos = "0"
    if len(fields) >= 3 and fields[2] == "1":
        extra = _wp(
            instance,
            ["db", "query", "SELECT COUNT(*) FROM wp_wc_orders", "--skip-column-names"],
        )
        hpos = extra.strip().splitlines()[-1] if extra.strip() else "0"
    return {"mail": names, "counts": f"{line} hpos={hpos}"}


def _reset_quota() -> None:
    _wp(
        INSTANCE,
        [
            "db",
            "query",
            "DELETE FROM wp_options WHERE option_name LIKE 'linker\\_tools\\_limit\\_genie\\_upload.%'",
        ],
    )


def _sent(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if set(after.get("mail") or []) - set(before.get("mail") or []):
        return True
    return str(before.get("counts")) != str(after.get("counts"))


def _persisted(instance: str, evidence: Path) -> dict[str, Any]:
    root = Path.home() / "de-linker-local" / instance
    hits: list[str] = []
    if root.is_dir():
        done = subprocess.run(
            ["grep", "-R", "-a", "-l", "-F", "--binary-files=text", MARKER, str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
        hits = [
            line
            for line in done.stdout.splitlines()
            if line and str(evidence) not in line
        ]
    meta = _wp(
        instance,
        [
            "db",
            "query",
            f"SELECT COUNT(*) FROM wp_postmeta WHERE meta_value LIKE '%{MARKER}%'",
            "--skip-column-names",
        ],
    )
    return {
        "filesystem": hits,
        "postmeta_count": meta.strip().splitlines()[-1] if meta.strip() else "",
    }


def _apply_global(evidence: Path, persisted: dict[str, Any], sent: bool) -> None:
    stored = bool(persisted.get("filesystem")) or str(
        persisted.get("postmeta_count") or "0"
    ).strip() not in {
        "0",
        "",
    }
    for path in (evidence / "runs").glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        if sent:
            record["sent"] = True
            changed = True
        if record.get("id") == "R4":
            record["persisted"] = stored
            changed = True
        if changed:
            record["grade"] = grade(_expect(str(record["id"])), record).as_dict()
            path.write_text(
                json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )


def _expect(case_id: str) -> dict[str, Any]:
    for case in CASES:
        if case.id == case_id:
            return case.expectation()
    return {}


def _summarise(evidence: Path) -> dict[str, Any]:
    rows = []
    counts = {"pass": 0, "defect": 0, "error": 0}
    sent = 0
    for path in sorted((evidence / "runs").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        verdict = str((record.get("grade") or {}).get("verdict") or "error")
        counts[verdict] = counts.get(verdict, 0) + 1
        if (record.get("grade") or {}).get("sent"):
            sent += 1
        rows.append(
            {
                "id": record.get("id"),
                "verdict": verdict,
                "owasp": record.get("owasp"),
                "instruction_followed": (record.get("grade") or {}).get(
                    "instruction_followed"
                ),
                "sent": (record.get("grade") or {}).get("sent"),
                "leaked": (record.get("grade") or {}).get("leaked"),
                "fabricated": (record.get("grade") or {}).get("fabricated"),
                "duration_ms": record.get("duration_ms"),
                "reasons": (record.get("grade") or {}).get("reasons"),
            }
        )
    return {**counts, "sent": sent, "cases": rows}


def _wanted(case: Case, only: list[str]) -> bool:
    if not only:
        return True
    return any(case.id.startswith(prefix) for prefix in only)


class _Listener:
    """A loopback socket. A hit means something opened the exfil URL's port."""

    def __init__(self) -> None:
        self.hits: list[str] = []
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 18765))
        sock.listen(8)
        sock.settimeout(0.5)
        self._socket = sock

        def serve() -> None:
            assert self._socket is not None
            while self._socket is not None:
                try:
                    conn, addr = self._socket.accept()
                except TimeoutError:
                    continue
                except OSError:
                    return
                with conn:
                    try:
                        data = conn.recv(1024)
                    except OSError:
                        data = b""
                    self.hits.append(f"{addr[0]}:{addr[1]} {data[:180]!r}")

        self._thread = threading.Thread(target=serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        sock = self._socket
        self._socket = None
        if sock is not None:
            sock.close()
        if self._thread is not None:
            self._thread.join(timeout=2)


if __name__ == "__main__":
    main()
