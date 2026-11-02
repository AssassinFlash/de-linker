"""Exercise the actual receipt-backed migration on an isolated PHP fixture."""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]


def test_native_receipt_partial_resume_and_revision_guard() -> None:
    php = shutil.which("php")
    if not php:
        pytest.skip("PHP is required")
    products = {}
    for pid, de, model, sku in [
        (4103, 6632, "57.3", "DLK-SAJ-CB2573HV5"),
        (4104, 6631, "71.6", "DLK-SAJ-CB2716HV5"),
        (4105, 6630, "85.9", "DLK-SAJ-CB2859HV5"),
        (4106, 6629, "100.3", "DLK-SAJ-CB21003HV5"),
    ]:
        en = f"SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-{model}-HV5)"
        german = f"SAJ CB2 57.3-100.3-HV5 Kurzanleitung zur Installation, Englisch (gilt für den CB2-{model}-HV5)"

        def raw(title: str) -> str:
            return json.dumps(
                {
                    "keep": [1, 2],
                    "downloads": [
                        {},
                        {},
                        {},
                        {
                            "download_file": 6337,
                            "download_title": title,
                            "download_role": "manual",
                            "download_language": "EN",
                        },
                    ],
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )

        products[pid] = {
            "de": de,
            "sku": sku,
            "meta": {
                "_tv_legacy_acf_json": raw(en),
                "_linker_de_acf_json": raw(german),
                "_linker_de_source_acf_json": raw(en),
            },
        }
    source = (HERE / "548-cb2-guide-titles.php").read_bytes()
    harness = r"""<?php
namespace Linker\Commerce\Products\Publication {
 final class DocumentFiles {
  public static function resolve($url) { return ['url'=>$url,'blob_sha256'=>$GLOBALS['bad_pdf']?str_repeat('0',64):$GLOBALS['sha']]; }
  public static function id($url) { return $GLOBALS['doc']; }
 }
}
namespace Linker\Commerce\Products {
 final class Materials { public static function localized_document_title($title,$german=null) { $m=unserialize($GLOBALS['option_raw']);return $german?($m[$title]??$title):$title; } }
 final class Publication {
  public static function manifest() {
   $products=[];
   foreach($GLOBALS['fx'] as $id=>$p) $products[]=['product_id'=>(int)$id,'documents'=>[$GLOBALS['doc']],'product_revision'=>hash('sha256',json_encode($p['meta'])),'ready'=>['knowledge'=>true],'sku'=>$p['sku']];
   $title=json_decode($GLOBALS['fx'][4103]['meta']['_tv_legacy_acf_json'],true)['downloads'][3]['download_title'];
   $m=unserialize($GLOBALS['option_raw']);
   $docs=[['document_id'=>$GLOBALS['doc'],'blob_sha256'=>$GLOBALS['sha'],'product_ids'=>[4103,4104,4105,4106],'type'=>'manual','role'=>'manual','title'=>$title,'title_de'=>$m[$title]??'','document_revision'=>hash('sha256',$title)]];
   return ['products'=>$products,'documents'=>$docs,'compatibility_revision'=>'compat','model_identity_revision'=>'models','source_revision'=>hash('sha256',json_encode($GLOBALS['fx']))];
  }
 }
}
namespace {
 define('ABSPATH','/fixture/'); define('ARRAY_A','ARRAY_A');
 $GLOBALS['fx']=json_decode(base64_decode('FIXTURE'),true,512,JSON_THROW_ON_ERROR);
 $GLOBALS['sha']='a70cb4c39824185fb9f570a59f4966c54ec94a33c870d00c7ccd756393321dac';
 $GLOBALS['doc']='doc-74c741e3ff765006ebff2c089f627bf1ff20b13c12b991ec9047f100e3ec87fd';
 $GLOBALS['option_raw']=serialize(['keep'=>'other']); $GLOBALS['bad_pdf']=false; $GLOBALS['bound']=false; $GLOBALS['query_failed']=false; $GLOBALS['fail_id']=0;
 $source=base64_decode('SOURCE');
 class DB {
  public string $options='wp_options'; public string $postmeta='wp_postmeta'; public string $last_error='';
  function prepare($sql,...$args){return [$sql,$args];} function get_var($q){return '1';} function esc_like($s){return $s;}
  function get_row($q,$mode){return ['option_id'=>'42','option_value'=>$GLOBALS['option_raw']];}
  function get_results($q,$mode){$this->last_error=$GLOBALS['query_failed']?'error':'';return $GLOBALS['bound']?[['meta_id'=>1]]:[];}
  function query($q){[$to,$id,$name,$from]=$q[1];if($id!==42||$name!=='linker_de_document_titles'||$GLOBALS['option_raw']!==$from)return 0;$GLOBALS['option_raw']=$to;return 1;}
 }
 $GLOBALS['wpdb']=new DB();
 function home_url(){return 'https://de-linker.com';} function untrailingslashit($s){return rtrim($s,'/');}
 function maybe_unserialize($s){return unserialize($s);} function maybe_serialize($v){return serialize($v);}
 function wp_json_encode($v,$flags=0){return json_encode($v,$flags);} function wp_cache_delete($a,$b){} function wc_delete_product_transients($id){} function wp_slash($v){return $v;}
 function get_post_status($id){return 'publish';}
 function pll_get_post_language($id){return isset($GLOBALS['fx'][$id])?'en':'de';}
 function pll_get_post($id,$lang){foreach($GLOBALS['fx'] as $en=>$p)if((int)$en===$id||$p['de']===$id)return $lang==='en'?(int)$en:$p['de'];return null;}
 function get_post_meta($id,$key,$single=false){$p=$GLOBALS['fx'][$id];if($key==='_sku')return $p['sku'];if($key==='_linker_documents_managed')return ''; $v=$p['meta'][$key];return $single?$v:[$v];}
 function update_post_meta($id,$key,$to,$from){if($GLOBALS['fail_id']===$id||$GLOBALS['fx'][$id]['meta'][$key]!==$from)return false;$GLOBALS['fx'][$id]['meta'][$key]=$to;return true;}
 function call_migration($action,$receipt=null){global $source;$p=base64_encode(json_encode(['action'=>$action,'target'=>'production','receipt'=>$receipt],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));$s=str_replace("'548-cb2-guide-titles-payload'","'".$p."'",$source);ob_start();try{eval(substr($s,5));$o=ob_get_clean();$m='@@548-cb2-guide-titles@@';$i=strpos($o,$m);if($i===false)throw new \RuntimeException('missing marker');return json_decode(substr($o,$i+strlen($m)),true,512,JSON_THROW_ON_ERROR);}catch(\Throwable $e){ob_end_clean();return ['error'=>$e->getMessage()];}}
 function must($v,$s){if(!$v)throw new \RuntimeException($s);}
 $initial=$GLOBALS['fx'];$initial_option=$GLOBALS['option_raw'];
 $receipt=call_migration('preview');must(($receipt['scope']??'')==='cb2-guide-titles-v1','preview');must($GLOBALS['fx']===$initial&&$GLOBALS['option_raw']===$initial_option,'preview wrote');
 $tampered=$receipt;$tampered['products'][4103]['_tv_legacy_acf_json']['after']=str_replace('"keep":[1,2]','"keep":[1,3]',$tampered['products'][4103]['_tv_legacy_acf_json']['after']);must(isset(call_migration('apply',$tampered)['error']),'tampered receipt accepted');must($GLOBALS['fx']===$initial,'tampered receipt wrote');
 $GLOBALS['bound']=true;must(isset(call_migration('apply',$receipt)['error']),'new binding accepted');must($GLOBALS['fx']===$initial,'binding wrote');$GLOBALS['bound']=false;
 $GLOBALS['query_failed']=true;must(isset(call_migration('preview')['error']),'query error accepted');$GLOBALS['query_failed']=false;
 $GLOBALS['fail_id']=4104;$r=call_migration('apply',$receipt);must(isset($r['error']),'partial failure hidden');$r=call_migration('inspect',$receipt);must(($r['states']['4103:_tv_legacy_acf_json']??'')==='after'&&($r['states']['4104:_tv_legacy_acf_json']??'')==='before','partial state');must(isset(call_migration('verify',$receipt)['error']),'partial verify passed');
 $old=$GLOBALS['fx'][4106]['meta']['_linker_de_acf_json'];$GLOBALS['fx'][4106]['meta']['_linker_de_acf_json']=str_replace('"keep":[1,2]','"keep":[1,3]',$old);$snap=$GLOBALS['fx'];must(isset(call_migration('apply',$receipt)['error'])&&$GLOBALS['fx']===$snap,'conflict overwritten');$GLOBALS['fx'][4106]['meta']['_linker_de_acf_json']=$old;
 $GLOBALS['fail_id']=0;$r=call_migration('apply',$receipt);must(!isset($r['error']),'resume failed');must(!isset(call_migration('verify',$receipt)['error']),'verify failed');
 $GLOBALS['bound']=true;must(isset(call_migration('rollback',$receipt)['error']),'bound rollback accepted');$GLOBALS['bound']=false;
 $r=call_migration('rollback',$receipt);must(!isset($r['error'])&&$GLOBALS['fx']===$initial&&$GLOBALS['option_raw']===$initial_option,'rollback failed');
 $GLOBALS['bad_pdf']=true;must(isset(call_migration('preview')['error']),'wrong original accepted');echo "OK\n";
}
""".replace(
        "FIXTURE", base64.b64encode(json.dumps(products).encode()).decode()
    ).replace("SOURCE", base64.b64encode(source).decode())
    result = subprocess.run(
        [php], input=harness, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "OK"
