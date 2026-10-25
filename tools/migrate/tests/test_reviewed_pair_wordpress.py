"""Native paired content/baseline transaction tests, opt-in on an owned local site.

Only newly created private fixture pages are written, then deleted. Existing
pages and production are never changed. An unavailable model client throws if
called; all intended baseline adoption uses the native reviewed-copy API.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

WP = os.environ.get("LINKER_REVIEWED_PAIR_TEST_WP", "")
pytestmark = pytest.mark.skipif(not WP, reason="Requires owned local WordPress")
spec = importlib.util.spec_from_file_location(
    "reviewed_pair", Path(__file__).parents[1] / "reviewed_page_pair.py"
)
assert spec and spec.loader
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)


def php(source: str) -> dict[str, Any]:
    result = subprocess.run(
        [*shlex.split(WP), "eval", "eval(stream_get_contents(STDIN));"],
        input=source,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    line = next(
        line for line in result.stdout.splitlines() if line.startswith("@@fixture@@")
    )
    answer: dict[str, Any] = json.loads(line.removeprefix("@@fixture@@"))
    return answer


@pytest.fixture
def pages() -> Any:
    site = php(
        "echo '@@fixture@@'.wp_json_encode(['home'=>home_url(),'root'=>ABSPATH]);"
    )
    assert urlsplit(site["home"]).hostname in {"localhost", "127.0.0.1"}
    assert Path(site["root"]).resolve().is_relative_to(Path.home() / "de-linker-local")
    created = php(r"""
$ids=[];
foreach(['en','de'] as $lang){
    $id=wp_insert_post(wp_slash(['post_type'=>'page','post_status'=>'private',
        'post_title'=>'Reviewed pair fixture '.$lang,
        'post_content'=>'<p>Original '.$lang.'. \\u003c \\s+</p>']),true,false);
    if(is_wp_error($id))throw new RuntimeException('Fixture insert failed');
    pll_set_post_language($id,$lang);$ids[]=$id;
}
pll_save_post_translations(['en'=>$ids[0],'de'=>$ids[1]]);
update_post_meta($ids[0],'_linker_i18n_status','structure_mismatch');
update_post_meta($ids[0],'_linker_i18n_note',wp_slash('Preserve \\ original note.'));
update_post_meta($ids[1],'_linker_i18n_source_hash','original-hash');
update_post_meta($ids[1],'_linker_i18n_units','{}');
echo '@@fixture@@'.wp_json_encode(['ids'=>$ids]);
""")
    ids = created["ids"]
    try:
        yield ids
    finally:
        result = php(
            "$ids="
            + json.dumps(ids)
            + ";foreach($ids as $id){wp_delete_post($id,true);}"
            "echo '@@fixture@@'.wp_json_encode(['left'=>array_values(array_filter($ids,'get_post'))]);"
        )
        assert result["left"] == []


@pytest.mark.parametrize(
    "case",
    [
        "normal_restore",
        "source_drift",
        "metadata_drift",
        "after_adoption_failure",
        "second_update_failure",
        "silent_units_rejection",
        "silent_units_add_rejection",
        "silent_status_rejection",
        "silent_hash_rejection",
        "silent_note_delete_rejection",
        "metadata_race",
        "metadata_insert_after_lock",
        "metadata_duplicate_after_lock",
    ],
)
def test_native_pair_and_baseline_commit_together(pages: list[int], case: str) -> None:
    if case == "metadata_insert_after_lock":
        php(
            f"delete_post_meta({pages[0]},'_linker_i18n_note');"
            "echo '@@fixture@@'.wp_json_encode(['ready'=>true]);"
        )
    if case == "silent_units_add_rejection":
        php(
            f"delete_post_meta({pages[1]},'_linker_i18n_units');"
            "echo '@@fixture@@'.wp_json_encode(['ready'=>true]);"
        )
    before = pair.read(WP, *pages)
    changes = [
        {
            "id": i,
            "before": before["pages"][str(i)],
            "after": f"<p>Reviewed {lang}. \\u003c \\s+ Grüße.</p>",
        }
        for i, lang in zip(pages, ("en", "de"), strict=True)
    ]
    payload = {
        "mode": "adopt",
        "changes": changes,
        "metadata_before": before["metadata"],
    }
    if case == "source_drift":
        changes[0]["before"] += "Unreviewed concurrent edit."
    if case == "metadata_drift":
        php(
            f"update_post_meta({pages[0]},'_linker_i18n_note','Concurrent external note.');"
            "echo '@@fixture@@'.wp_json_encode(['changed'=>true]);"
        )
    source = base64.b64encode(pair.render(payload).encode()).decode()
    config = base64.b64encode(
        json.dumps({"case": case, "ids": pages}).encode()
    ).decode()
    runner = r"""
global $wpdb;
$cfg=json_decode(base64_decode('__CONFIG__'),true);$injected=false;$blocked=false;
$session_before=$wpdb->get_var('SELECT @@session.transaction_isolation');
$fault=static function($query)use($cfg,&$injected){
    global $wpdb;
    if($cfg['case']==='after_adoption_failure' && $query==='COMMIT'){
        if(get_post_meta($cfg['ids'][0],'_linker_i18n_status',true)!=='synced')
            throw new RuntimeException('Fault ran before adoption');
        $injected=true;throw new RuntimeException('Injected failure after adoption');
    }
    if($cfg['case']==='second_update_failure'
        && preg_match('/^UPDATE\s+`?'.preg_quote($wpdb->posts,'/').'`?\s/i',$query)
        && preg_match('/\bWHERE\s+`?ID`?\s*=\s*'.$cfg['ids'][1].'\b/i',$query)){
        $injected=true;throw new RuntimeException('Injected second page failure');
    }
    return $query;
};
$deny=static function($check,$id,$key)use($cfg,&$injected){
    $targets=[
        'silent_units_rejection'=>['update_post_metadata','_linker_i18n_units'],
        'silent_units_add_rejection'=>['add_post_metadata','_linker_i18n_units'],
        'silent_status_rejection'=>['update_post_metadata','_linker_i18n_status'],
        'silent_hash_rejection'=>['update_post_metadata','_linker_i18n_source_hash'],
        'silent_note_delete_rejection'=>['delete_post_metadata','_linker_i18n_note']
    ];
    if(isset($targets[$cfg['case']]) && $targets[$cfg['case']]===[current_filter(),$key]){
        $injected=true;return false;
    }
    return $check;
};
$race=static function($id)use($cfg,&$injected,&$blocked){
    if($id!==$cfg['ids'][0] || $injected
        || !in_array($cfg['case'],['metadata_race','metadata_insert_after_lock','metadata_duplicate_after_lock'],true))return;
    global $wpdb;
    // This connection writes only this test's new private fixture page.
    $host=$wpdb->parse_db_host(DB_HOST);$other=mysqli_init();
    mysqli_real_connect($other,$host[0],DB_USER,DB_PASSWORD,DB_NAME,$host[1]?:3306,$host[2]);
    mysqli_query($other,'SET SESSION innodb_lock_wait_timeout=1');
    $query=$cfg['case']==='metadata_race'
        ?$wpdb->prepare('UPDATE %i SET meta_value=%s WHERE post_id=%d AND meta_key=%s',
            $wpdb->postmeta,'Concurrent external note.',$id,'_linker_i18n_note')
        :$wpdb->prepare('INSERT INTO %i (post_id,meta_key,meta_value) VALUES (%d,%s,%s)',
            $wpdb->postmeta,$id,$cfg['case']==='metadata_duplicate_after_lock'?'_linker_i18n_status':'_linker_i18n_note','Concurrent external note.');
    try{
        mysqli_query($other,$query);
        if(mysqli_affected_rows($other)!==1)throw new RuntimeException('Race changed no row');
        $injected=true;
    }catch(mysqli_sql_exception $error){
        if($error->getCode()!==1205)throw $error;
        $blocked=true;$injected=true;
    }finally{mysqli_close($other);}
};
$race_priority=in_array($cfg['case'],['metadata_insert_after_lock','metadata_duplicate_after_lock'],true)?-PHP_INT_MAX+1:PHP_INT_MIN;
add_filter('query',$fault,PHP_INT_MAX-2);
add_filter('update_post_metadata',$deny,10,3);
add_filter('add_post_metadata',$deny,10,3);
add_filter('delete_post_metadata',$deny,10,3);
add_action('pre_post_update',$race,$race_priority);
ob_start();$error='';
try{
eval(base64_decode('__SOURCE__'));
}catch(Throwable $e){$error=$e->getMessage();}
$writer_output=ob_get_clean();remove_filter('query',$fault,PHP_INT_MAX-2);
remove_filter('update_post_metadata',$deny,10);
remove_filter('add_post_metadata',$deny,10);
remove_filter('delete_post_metadata',$deny,10);
remove_action('pre_post_update',$race,$race_priority);
echo '@@fixture@@'.wp_json_encode(['error'=>$error,'injected'=>$injected,'blocked'=>$blocked,
    'writer_output'=>$writer_output,'session_before'=>$session_before,
    'session_after'=>$wpdb->get_var('SELECT @@session.transaction_isolation')]);
""".replace("__CONFIG__", config).replace("__SOURCE__", source)
    result = php(runner)
    observed = pair.read(WP, *pages)
    assert result["session_before"] == result["session_after"]
    success = case in {
        "normal_restore",
        "metadata_insert_after_lock",
        "metadata_duplicate_after_lock",
    } or (case == "metadata_race" and result["blocked"])
    if success:
        assert result["error"] == ""
        assert observed["pages"] == {str(c["id"]): c["after"] for c in changes}
        assert observed["current"] is True
        receipt = json.loads(
            next(
                line.removeprefix("@@reviewed-pair@@")
                for line in result["writer_output"].splitlines()
                if line.startswith("@@reviewed-pair@@")
            )
        )
        assert observed["metadata"] == receipt["expected_metadata"]
        if case in {
            "metadata_race",
            "metadata_insert_after_lock",
            "metadata_duplicate_after_lock",
        }:
            assert result["blocked"] is True
            assert result["injected"] is True
        pair.invoke(
            WP,
            {
                "mode": "restore",
                "changes": [
                    {"id": c["id"], "before": c["after"], "after": c["before"]}
                    for c in changes
                ],
                "metadata_before": observed["metadata"],
                "metadata_restore": before["metadata"],
            },
        )
        restored = pair.read(WP, *pages)
        assert restored == before
    else:
        assert result["error"]
        expected = json.loads(json.dumps(before))
        if case in {"metadata_race", "metadata_drift"}:
            expected["metadata"][str(pages[0])]["_linker_i18n_note"] = [
                "Concurrent external note."
            ]
        assert observed == expected
        if case.startswith("silent_") or case in {
            "after_adoption_failure",
            "second_update_failure",
            "silent_units_rejection",
            "metadata_race",
        }:
            assert result["injected"] is True
