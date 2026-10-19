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
import sys
import threading
import time
import urllib.error
import urllib.request
from http.client import HTTPResponse
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from cases import CASES, MARKER, Case, by_id, exfil_port
from corpus import build
from grade import grade
from poison import is_published
from poison import search as poison_search

EVIDENCE = Path(
    os.environ.get("C334_EVIDENCE", Path.home() / "de-linker-data/campaign-334")
)
# Direct /turn has no proxy budget. A scanned PDF may render four pages
# (attachments.MAX_RENDERED_PAGES), each vision call capped at 30 s
# (vision.TIMEOUT_SECONDS), and the agent still has to run. 240 s covers
# that stack. A proxied turn returns inside Proxy::TURN_BUDGET (60 s),
# before this socket gives up.
TIMEOUT = 240
INSTANCE = os.environ.get("C334_INSTANCE", "c334")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("only", nargs="*", help="case id prefixes, for example N1 P")
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument(
        "--summarise-only",
        action="store_true",
        help="rewrite summary.json from the run files already on disk",
    )
    parser.add_argument(
        "--regrade",
        action="store_true",
        help="grade the run files on disk again, then rewrite summary.json",
    )
    parser.add_argument(
        "--wp", default=os.environ.get("C334_WP", "http://127.0.0.1:9193")
    )
    parser.add_argument("--genie", default=os.environ.get("C334_GENIE", ""))
    parser.add_argument("--instance", default=os.environ.get("C334_INSTANCE", "c334"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    global INSTANCE
    INSTANCE = args.instance
    evidence = EVIDENCE
    if args.regrade:
        summary = regrade(evidence)
        _print_summary(summary)
        return
    if args.summarise_only:
        summary = _summarise(evidence)
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        _print_summary(summary)
        return
    selected = select_cases(args.only)
    index_cases = [case for case in selected if case.channel == "index"]
    browser_cases = [case for case in selected if case.channel == "browser"]
    live_cases = [case for case in selected if case.channel not in {"index", "browser"}]
    evidence.mkdir(parents=True, exist_ok=True)
    for case in index_cases:
        path = evidence / "runs" / f"{case.id}.json"
        if path.is_file() and not args.rerun:
            print(f"skip {case.id}", flush=True)
            continue
        print(f"run {case.id} {case.title}", flush=True)
        _write_graded(path, case, _index_record(case, evidence))
    if not live_cases and not browser_cases:
        _finish(evidence)
        return
    _local(args.wp)
    manifest = build(evidence / "corpus")
    if live_cases:
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
        try:
            for case in live_cases:
                path = evidence / "runs" / f"{case.id}.json"
                if path.is_file() and not args.rerun:
                    print(f"skip {case.id}", flush=True)
                    continue
                print(f"run {case.id} {case.title}", flush=True)
                record = _run_case(case, manifest, genie, token, args.wp, product)
                _write_graded(path, case, record)
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
    if browser_cases:
        _browser(evidence, browser_cases, args.wp)
    _finish(evidence)


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


class _StayLocal(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect whose next host is not loopback.

    urllib copies custom headers onto the next request, including
    X-Linker-Service-Token, and turns the POST into a GET. The next host is
    checked here, before that request is built.
    """

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        _local(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_StayLocal)


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
        with _opener().open(request, timeout=TIMEOUT) as response:
            _local(response.geturl())
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
        with _opener().open(request, timeout=TIMEOUT) as response:
            _local(response.geturl())
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
    stored = _read_token(file)
    if stored:
        return stored
    raw = _wp(
        instance, ["config", "get", "LINKER_GENIE_SERVICE_TOKEN", "--type=constant"]
    )
    token = raw.strip().splitlines()[-1].strip()
    if not token or token.lower() == "null":
        raise SystemExit("Genie service token is not configured on this instance")
    _store_token(file, token)
    return token


def _read_token(file: Path) -> str | None:
    """Return the token, tightening the file to owner-read even when it already existed."""
    if not file.is_file():
        return None
    _tighten(file)
    text = file.read_text(encoding="utf-8").strip()
    return text or None


def _store_token(file: Path, token: str) -> None:
    """Write the token as mode 0600. A umask cannot leave it group-readable."""
    file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, (token + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    _tighten(file)


def _tighten(file: Path) -> None:
    file.chmod(0o600)


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
    self_tests = []
    counts = {"pass": 0, "defect": 0, "error": 0}
    sent = 0
    known = by_id()
    for path in sorted((evidence / "runs").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        verdict = str((record.get("grade") or {}).get("verdict") or "error")
        row = {
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
        if _self_test(record, known):
            self_tests.append(row)
            continue
        counts[verdict] = counts.get(verdict, 0) + 1
        if (record.get("grade") or {}).get("sent"):
            sent += 1
        rows.append(row)
    return {**counts, "sent": sent, "self_test": self_tests, "cases": rows}


def _self_test(record: dict[str, Any], known: dict[str, Case]) -> bool:
    """V1 searches a temporary index. It has no customer answer to grade."""
    if record.get("self_test") is True:
        return True
    case = known.get(str(record.get("id") or ""))
    return case is not None and case.self_test


def _wanted(case: Case, only: list[str]) -> bool:
    if not only:
        return True
    return any(case.id.startswith(prefix) for prefix in only)


def select_cases(only: list[str]) -> list[Case]:
    """Every selected case, including the browser and temporary-index channels."""
    return [case for case in CASES if _wanted(case, only)]


def _write_graded(path: Path, case: Case, record: dict[str, Any]) -> None:
    record["grade"] = grade(case.expectation(), record).as_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  {record['grade']['verdict']} {record.get('duration_ms')} ms", flush=True)


def _index_record(case: Case, evidence: Path) -> dict[str, Any]:
    """Search a temporary index. The published vector index is not opened.

    The hit text is the reading. There is no model answer and no turn route,
    so the security and attribution checks have nothing to read. The row is a
    self-test and stays out of the graded counts.
    """
    db = evidence / "poison-index" / "index.sqlite"
    started = time.time()
    hits: list[str] = []
    try:
        hits = poison_search(db, case.question)
        if not hits:
            raise RuntimeError("temporary index returned no hits")
        text = "\n".join(hits)
        step: dict[str, Any] = {
            "status": 200,
            "answer": "",
            "readings": [{"text": text, "failed": None}],
            "blocks": [],
        }
    except Exception as error:  # noqa: BLE001 — one case must not abort the battery
        step = {"status": 0, "error": f"{type(error).__name__}: {error}", "answer": ""}
    return {
        "id": case.id,
        "group": case.group,
        "owasp": case.owasp,
        "title": case.title,
        "channel": case.channel,
        "file": case.file,
        "question": case.question,
        "duration_ms": int((time.time() - started) * 1000),
        "status": step.get("status"),
        "answer": step.get("answer"),
        "readings": step.get("readings"),
        "blocks": step.get("blocks"),
        "steps": [step],
        "error": step.get("error"),
        "self_test": True,
        "index": {"path": str(db), "published": is_published(db), "hits": len(hits)},
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def _mtime_ns(path: Path) -> int | None:
    if not path.is_file():
        return None
    return path.stat().st_mtime_ns


def _browser_error(case: Case, message: str) -> dict[str, Any]:
    detail = (message or "browser.mjs failed").strip()[-500:]
    return {
        "id": case.id,
        "channel": "browser",
        "error": detail,
        "turn_requests": 0,
        "steps": [{"status": 0, "error": detail}],
    }


def _browser(evidence: Path, cases: list[Case], wp: str) -> None:
    """Run the selected browser cases, then grade those records.

    browser.mjs receives the evidence directory, `--wp`, and `--only`. A run
    asked for U1 does not rewrite U2. A non-zero exit does not keep a pass
    left by an earlier run: a selected file that this invocation did not
    rewrite is graded as an error.
    """
    script = Path(__file__).with_name("browser.mjs")
    ids = [case.id for case in cases]
    stamps = {
        case.id: _mtime_ns(evidence / "runs" / f"{case.id}.json") for case in cases
    }
    done = subprocess.run(
        ["node", str(script), str(evidence), "--wp", wp, "--only", ",".join(ids)],
        cwd=script.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.stdout:
        print(done.stdout, end="" if done.stdout.endswith("\n") else "\n", flush=True)
    if done.returncode != 0 and done.stderr:
        print(done.stderr, file=sys.stderr, flush=True)
    message = (
        done.stderr or done.stdout or f"browser.mjs exited {done.returncode}"
    ).strip()
    for case in cases:
        path = evidence / "runs" / f"{case.id}.json"
        fresh = path.is_file() and _mtime_ns(path) != stamps[case.id]
        stale_pass = done.returncode != 0 and not fresh
        record: dict[str, Any] = {}
        if path.is_file() and not stale_pass:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                record = loaded
        if not record:
            record = _browser_error(case, message)
        print(f"grade {case.id}", flush=True)
        _write_graded(path, case, record)


def regrade(evidence: Path) -> dict[str, Any]:
    """Grade every stored run again and rewrite summary.json."""
    runs = evidence / "runs"
    changed = 0
    known = by_id()
    if runs.is_dir():
        for path in sorted(runs.glob("*.json")):
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                continue
            case_id = str(loaded.get("id") or path.stem)
            new = grade(_expect(case_id), loaded).as_dict()
            if loaded.get("grade") != new:
                changed += 1
            loaded["grade"] = new
            case = known.get(case_id)
            if case is not None and case.self_test:
                loaded["self_test"] = True
            path.write_text(
                json.dumps(loaded, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    summary = _summarise(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary["changed"] = changed
    return summary


def _finish(evidence: Path) -> None:
    summary = _summarise(evidence)
    (evidence / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _print_summary(summary)


def _print_summary(summary: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                key: summary[key]
                for key in ("pass", "defect", "error", "sent", "changed", "self_test")
                if key in summary
            },
            indent=2,
        )
    )


class _Listener:
    """A loopback socket. A hit means something opened the exfil URL's port."""

    def __init__(self, port: int | None = None) -> None:
        self.port = exfil_port() if port is None else port
        self.bound_port: int | None = None
        self.hits: list[str] = []
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", self.port))
        # socket.socket.listen() with no backlog uses the runtime's default
        # queue (docs.python.org/3/library/socket.html#socket.socket.listen).
        sock.listen()
        # accept returns twice a second so stop() does not wait for a client.
        sock.settimeout(0.5)
        self.bound_port = int(sock.getsockname()[1])
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
