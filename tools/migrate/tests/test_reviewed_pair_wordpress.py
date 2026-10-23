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
    ],
)
def test_native_pair_and_baseline_commit_together(pages: list[int], case: str) -> None:
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
        payload["metadata_before"] = json.loads(json.dumps(before["metadata"]))
        payload["metadata_before"][str(pages[0])]["_linker_i18n_note"] = [
            "Stale backup"
        ]
    source = base64.b64encode(pair.render(payload).encode()).decode()
    config = base64.b64encode(
        json.dumps({"case": case, "ids": pages}).encode()
    ).decode()
    runner = r"""
$cfg=json_decode(base64_decode('__CONFIG__'),true);$injected=false;
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
add_filter('query',$fault,PHP_INT_MAX-2);
ob_start();$error='';
try{
eval(base64_decode('__SOURCE__'));
}catch(Throwable $e){$error=$e->getMessage();}
$writer_output=ob_get_clean();remove_filter('query',$fault,PHP_INT_MAX-2);
echo '@@fixture@@'.wp_json_encode(['error'=>$error,'injected'=>$injected]);
""".replace("__CONFIG__", config).replace("__SOURCE__", source)
    result = php(runner)
    observed = pair.read(WP, *pages)
    if case == "normal_restore":
        assert result["error"] == ""
        assert observed["pages"] == {str(c["id"]): c["after"] for c in changes}
        assert observed["current"] is True
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
        assert observed == before
        if case in {"after_adoption_failure", "second_update_failure"}:
            assert result["injected"] is True
