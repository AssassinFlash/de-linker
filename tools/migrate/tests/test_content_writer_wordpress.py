"""Exercise the real content writer with native WordPress/MySQL fault injection.

Opt in with LINKER_CONTENT_WRITER_TEST_WP pointing to a dedicated local instance.
Only two newly-created private fixture pages are edited/deleted. The process
kills its own test connection, never a server or another process's connection.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

WP = os.environ.get("LINKER_CONTENT_WRITER_TEST_WP", "")
EVIDENCE = os.environ.get("LINKER_CONTENT_WRITER_TEST_EVIDENCE", "")
pytestmark = pytest.mark.skipif(
    not WP, reason="Requires a dedicated local WordPress instance"
)
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "content_writer", HERE.parent / "repair-legal-script.py"
)
assert spec and spec.loader
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


def php(source: str) -> dict[str, Any]:
    result = subprocess.run(
        [*shlex.split(WP), "eval", source], capture_output=True, text=True, check=False
    )
    if result.returncode and EVIDENCE:
        directory = Path(EVIDENCE)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        name = datetime.now(UTC).strftime("wpcli-driver-failure-%Y%m%dT%H%M%S%fZ.json")
        (directory / name).write_text(
            json.dumps(
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                indent=2,
            )
            + "\n"
        )
    assert result.returncode == 0, result.stderr
    lines = [
        line.removeprefix("@@writer-fixture@@")
        for line in result.stdout.splitlines()
        if line.startswith("@@writer-fixture@@")
    ]
    assert len(lines) == 1, result.stdout
    answer: dict[str, Any] = json.loads(lines[0])
    return answer


def output(expression: str) -> str:
    return "echo '@@writer-fixture@@'.wp_json_encode(" + expression + ");"


@pytest.fixture
def pages() -> Any:
    site = php(output("['home'=>home_url(),'root'=>ABSPATH,'db'=>DB_NAME]"))
    assert urlsplit(site["home"]).hostname in {"127.0.0.1", "localhost"}, site
    assert (
        Path(site["root"]).resolve().is_relative_to(Path.home() / "de-linker-local")
    ), site
    assert site["db"].startswith("linker_"), site
    ids = php(
        "$ids=[];foreach(['A','B'] as $label){"
        "$id=wp_insert_post(wp_slash(['post_type'=>'page','post_status'=>'private',"
        "'post_title'=>'Content writer fault fixture '.$label,"
        "'post_content'=>'<p>Original '.$label.'. \\u003c</p>']),true,false);"
        "if(is_wp_error($id))throw new RuntimeException('Fixture insert failed');"
        "$ids[]=$id;}" + output("['ids'=>$ids]")
    )["ids"]
    try:
        yield ids
    finally:
        # These IDs belong exclusively to the disposable fixture just created.
        deleted = php(
            "$ids="
            + json.dumps(ids)
            + ";foreach($ids as $id){wp_delete_post($id,true);}"
            + output("['left'=>array_values(array_filter($ids,'get_post'))]")
        )
        assert deleted["left"] == []


@pytest.mark.parametrize(
    "case",
    [
        "normal",
        "source_drift",
        "second_update_failure",
        "disconnect_first_update",
        "disconnect_start",
        "disconnect_commit_before",
        "commit_ack_unknown",
        "replace_connection",
    ],
)
def test_transaction_connection_and_commit_boundaries(
    pages: list[int], case: str
) -> None:
    snapshot = writer.invoke(WP, {"operation": "read", "ids": pages})
    changes = [
        {
            "id": page,
            "before": snapshot["rows"][str(page)]["content"],
            "after": f"<p>Changed {page}. \\u003c</p>",
        }
        for page in pages
    ]
    if case == "source_drift":
        changes[0]["before"] += "Unrelated concurrent edit"
    payload = base64.b64encode(
        json.dumps({"operation": "save", "changes": changes}).encode()
    ).decode()
    source = (
        writer.PHP.read_text()
        .removeprefix("<?php")
        .replace("__LEGAL_SCRIPT_PAYLOAD__", payload)
    )
    encoded_source = base64.b64encode(source.encode()).decode()
    config = base64.b64encode(
        json.dumps({"case": case, "ids": pages}).encode()
    ).decode()
    runner = r"""
global $wpdb, $wp_filter;
$cfg=json_decode(base64_decode('__CONFIG__'),true);
$before_mode=(new mysqli_driver())->report_mode;
$before_retries=$wpdb->reconnect_retries;
$before_thread=mysqli_thread_id($wpdb->dbh);
$before_connection=$wpdb->dbh;
$query_filters=static fn()=>array_sum(array_map('count',$GLOBALS['wp_filter']['query']->callbacks??[]));
$injected=false;$kill_ack=false;
$fault=static function($sql)use($cfg,$wpdb,&$injected,&$kill_ack){
    $first=preg_match('/^UPDATE\s+`?'.preg_quote($wpdb->posts,'/').'`?\s/i',$sql)
        && preg_match('/\bWHERE\s+`?ID`?\s*=\s*'.$cfg['ids'][0].'\b/i',$sql);
    $second=preg_match('/^UPDATE\s+`?'.preg_quote($wpdb->posts,'/').'`?\s/i',$sql)
        && preg_match('/\bWHERE\s+`?ID`?\s*=\s*'.$cfg['ids'][1].'\b/i',$sql);
    if($cfg['case']==='second_update_failure' && $second){
        $injected=true;return 'UPDATE `missing_content_writer_fixture` SET x=1';
    }
    $kill=($cfg['case']==='disconnect_first_update' && $first)
        ||($cfg['case']==='disconnect_start' && $sql==='START TRANSACTION')
        ||(in_array($cfg['case'],['disconnect_commit_before','commit_ack_unknown'],true)&&$sql==='COMMIT');
    if(!$injected && $cfg['case']==='replace_connection' && $first){
        $injected=true;$wpdb->dbh=mysqli_init();return $sql;
    }
    if(!$injected && $kill){
        $injected=true;
        if($cfg['case']==='commit_ack_unknown')mysqli_commit($wpdb->dbh);
        // A second local connection kills only this runner's own connection.
        $host=$wpdb->parse_db_host(DB_HOST);
        $killer=mysqli_init();
        mysqli_real_connect($killer,$host[0],DB_USER,DB_PASSWORD,DB_NAME,$host[1]?:3306,$host[2]);
        // SQL KILL remains supported on MySQL 9; COM_PROCESS_KILL does not.
        $kill_ack=mysqli_query($killer,'KILL CONNECTION '.(int)mysqli_thread_id($wpdb->dbh));
        mysqli_close($killer);
    }
    return $sql;
};
add_filter('query',$fault,20);
$before_filters=$query_filters();
ob_start();$failure=null;
try{eval(base64_decode('__SOURCE__'));}
catch(Throwable $e){$failure=['type'=>get_class($e),'message'=>$e->getMessage(),'code'=>$e->getCode()];}
$writer_output=ob_get_clean();
$after_filters=$query_filters();
remove_filter('query',$fault,20);
try{$after_thread=mysqli_thread_id($wpdb->dbh);}catch(Throwable $e){$after_thread=null;}
// Undo only this fixture's deliberate handle replacement for WP shutdown.
// No transaction or data is repaired here; process close retains its native
// rollback behavior. Record the writer's untouched post-failure state first.
if($cfg['case']==='replace_connection')$wpdb->dbh=$before_connection;
echo '@@writer-fixture@@'.wp_json_encode(['failure'=>$failure,'writer_output'=>$writer_output,
    'injected'=>$injected,'kill_ack'=>$kill_ack,'before_mode'=>$before_mode,'after_mode'=>(new mysqli_driver())->report_mode,
    'before_retries'=>$before_retries,'after_retries'=>$wpdb->reconnect_retries,
    'before_filters'=>$before_filters,'after_filters'=>$after_filters,
    'before_thread'=>$before_thread,'after_thread'=>$after_thread]);
""".replace("__CONFIG__", config).replace("__SOURCE__", encoded_source)
    result = php(runner)
    readback = writer.invoke(WP, {"operation": "read", "ids": pages})
    actual = [readback["rows"][str(page)]["content"] for page in pages]
    expected = (
        [c["after"] for c in changes]
        if case in {"normal", "commit_ack_unknown"}
        else [snapshot["rows"][str(page)]["content"] for page in pages]
    )
    assert actual == expected
    assert result["after_mode"] == result["before_mode"]
    assert result["after_retries"] == result["before_retries"]
    assert result["after_filters"] == result["before_filters"]
    if case == "normal":
        assert result["failure"] is None
        assert json.loads(result["writer_output"].removeprefix("@@legal-script@@")) == {
            "saved": 2
        }
    else:
        assert result["failure"] is not None
        assert not result["writer_output"]
        if case != "source_drift":
            assert result["injected"] is True
        if case in {"disconnect_commit_before", "commit_ack_unknown"}:
            assert "Commit outcome is unknown" in result["failure"]["message"]
        if case.startswith("disconnect_") or case == "commit_ack_unknown":
            assert result["kill_ack"] is True
    if case != "replace_connection":
        assert result["after_thread"] in {None, 0, result["before_thread"]}
    if EVIDENCE:
        evidence = Path(EVIDENCE)
        evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
        (evidence / f"writer-{case}.json").write_text(
            json.dumps(
                {
                    "case": case,
                    "result": result,
                    "pages": pages,
                    "before_sha256": [
                        writer.digest(snapshot["rows"][str(p)]["content"])
                        for p in pages
                    ],
                    "readback_sha256": [writer.digest(c) for c in actual],
                    "boundary": "Dedicated local fixture; commit_ack_unknown commits then disconnects before the caller observes COMMIT; it proves indeterminate handling, not every network failure.",
                },
                indent=2,
            )
            + "\n"
        )
