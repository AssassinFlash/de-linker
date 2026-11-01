"""Exercise the real PHP migration against an in-memory Woo/manifest fixture."""

from __future__ import annotations

import base64
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

HERE = Path(__file__).resolve().parents[1]


def migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "hs3_titles", HERE / "548-hs3-titles.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(module: ModuleType) -> dict:
    products = {}
    old_titles = []
    for pid, (de, kw, sku) in module.PRODUCTS.items():
        rows = [
            {
                "url": "https://de-linker.com/wp-content/uploads/other.pdf",
                "title": "Keep me",
                "type": "manual",
                "lang": "en",
                "custom": {"keep": [1, 2]},
            }
        ]
        for doc in module.DOCUMENTS:
            title = module.old_title(doc, kw)
            old_titles.append(title)
            rows.append(
                {
                    "url": doc["url"],
                    "title": title,
                    "type": doc["type"],
                    "lang": doc["lang"],
                    "role": doc["role"],
                    "extra": {"keep": True},
                }
            )
        products[pid] = {"de": de, "sku": sku, "rows": rows}
    return {"products": products, "docs": module.DOCUMENTS, "old_titles": old_titles}


def test_expected_rows_preserve_every_unrelated_field_and_reject_drift() -> None:
    m = migration()
    before = fixture(m)["products"]["1185"]["rows"]
    after = m.expected_rows(before, 12)
    assert before[0] == after[0]
    assert [{k: v for k, v in row.items() if k != "title"} for row in before] == [
        {k: v for k, v in row.items() if k != "title"} for row in after
    ]
    assert before[1]["title"] != after[1]["title"]
    assert before[2]["title"] != after[2]["title"]
    before[1]["role"] = "not-the-reviewed-role"
    with pytest.raises(ValueError, match="role differs"):
        m.expected_rows(before, 12)
    before[1]["role"] = "certificate"
    before.append(before[1].copy())
    with pytest.raises(ValueError, match="exactly one row"):
        m.expected_rows(before, 12)


def test_php_preview_interrupted_apply_conflict_verify_and_rollback() -> None:
    php = shutil.which("php")
    if not php:
        pytest.skip("PHP is required")
    m = migration()
    source = (HERE / "548-hs3-titles.php").read_bytes()
    data = json.dumps(fixture(m), ensure_ascii=False).encode()
    harness = r"""<?php
namespace Linker\Commerce\Products\Publication {
 final class DocumentFiles {
  public static function resolve(string $url): ?array { foreach($GLOBALS['fx']['docs'] as $d) if($d['url']===$url) return ['url'=>$GLOBALS['site'].substr($url,strlen('https://de-linker.com')),'blob_sha256'=>$GLOBALS['bad_file'] ? str_repeat('0',64) : $d['sha']]; return null; }
  public static function id(string $url): string { foreach($GLOBALS['fx']['docs'] as $d) if(parse_url($d['url'],PHP_URL_PATH)===parse_url($url,PHP_URL_PATH)) return $d['id']; return ''; }
 }
}
namespace Linker\Commerce\Products {
 final class Materials { public static function localized_document_title(string $title, ?bool $german=null): string { $map=unserialize($GLOBALS['option_raw']); return $german ? ($map[$title]??$title) : $title; } }
 final class Publication {
  public static function manifest(): array {
   $products=[]; $ids=array_map('intval',array_keys($GLOBALS['fx']['products']));
   foreach($GLOBALS['fx']['products'] as $id=>$p) $products[]=['product_id'=>(int)$id,'title'=>'product-'.$id,'locale_product_ids'=>['en'=>(int)$id,'de'=>$p['de']],'published_locale_ids'=>[(int)$id,$p['de']],'documents'=>array_column($GLOBALS['fx']['docs'],'id'),'product_revision'=>hash('sha256',json_encode($p['rows'])),'ready'=>['knowledge'=>true]];
   $docs=[];
   foreach($GLOBALS['fx']['docs'] as $d) { $title=''; foreach($GLOBALS['fx']['products']['1185']['rows'] as $row) if(($row['url']??'')===$d['url']) $title=$row['title']; $url=$GLOBALS['site'].substr($d['url'],strlen('https://de-linker.com')); $docs[]=['document_id'=>$d['id'],'blob_sha256'=>$d['sha'],'url'=>$url,'aliases'=>[$url],'product_ids'=>$ids,'title'=>$title,'type'=>$d['type'],'lang'=>$d['lang'],'role'=>$d['role'],'citation_aliases'=>[],'document_revision'=>hash('sha256',$title)]; }
   return ['products'=>$products,'documents'=>$docs,'source_revision'=>hash('sha256',json_encode($GLOBALS['fx']['products']))];
  }
 }
}
namespace {
 define('ABSPATH','/fixture/'); define('ARRAY_A','ARRAY_A');
 $GLOBALS['fx']=json_decode(base64_decode('FIXTURE'),true,512,JSON_THROW_ON_ERROR);
 $source=base64_decode('SOURCE');
 $GLOBALS['option_raw']=serialize(array_fill_keys($GLOBALS['fx']['old_titles'],'alt')+['keep'=>'other']);
 $GLOBALS['bad_file']=false; $GLOBALS['fail_on_id']=0; $GLOBALS['lock_fail']=false; $GLOBALS['extra_association']=false; $GLOBALS['site']='https://de-linker.com';
 class WP_CLI { public static function error($message) { throw new \RuntimeException($message); } }
 class FakeDB {
  public string $options='wp_options'; public string $postmeta='wp_postmeta';
  public function prepare($query,...$args) { return [$query,$args]; }
  public function get_var($q) { return $GLOBALS['lock_fail'] && str_contains($q[0],'GET_LOCK') ? '0' : '1'; }
  public function get_row($q,$mode) { return ['option_id'=>'42','option_value'=>$GLOBALS['option_raw']]; }
  public function esc_like($s) { return $s; }
  public function get_results($q,$mode) { $out=[]; foreach($GLOBALS['fx']['products'] as $id=>$p) $out[]=['post_id'=>(string)$id,'meta_id'=>(string)(100+(int)$id)]; if($GLOBALS['extra_association']) $out[]=['post_id'=>'3000','meta_id'=>'9999']; return $out; }
  public function query($q) { [$sql,$args]=$q; [$to,$id,$name,$from]=$args; if($id!==42 || $name!=='linker_de_document_titles' || $GLOBALS['option_raw']!==$from) return 0; $GLOBALS['option_raw']=$to; return 1; }
 }
 $GLOBALS['wpdb']=new FakeDB();
 function home_url() { return $GLOBALS['site']; }
 function untrailingslashit($s) { return rtrim($s,'/'); }
 function maybe_unserialize($v) { return unserialize($v); }
 function maybe_serialize($v) { return serialize($v); }
 function wp_json_encode($value,$flags=0) { return json_encode($value,$flags); }
 function wp_cache_delete($a,$b) { return true; }
 function wc_delete_product_transients($id) { return true; }
 function wp_slash($v) { return $v; }
 function get_post_status($id) { return 'publish'; }
 function pll_get_post_language($id) { return isset($GLOBALS['fx']['products'][$id]) ? 'en' : 'de'; }
 function pll_get_post($id,$language) { foreach($GLOBALS['fx']['products'] as $en=>$p) if((int)$en===$id || $p['de']===$id) return $language==='en' ? (int)$en : $p['de']; return null; }
 function get_post_meta($id,$key,$single=false) { $p=$GLOBALS['fx']['products'][$id]; if($key==='_sku') return $p['sku']; if($key==='_linker_documents_managed') return $single ? '1' : ['1']; if($key==='_linker_documents') return $single ? $p['rows'] : [$p['rows']]; return null; }
 function update_post_meta($id,$key,$to,$from) { if($GLOBALS['fail_on_id']===$id || $GLOBALS['fx']['products'][$id]['rows']!==$from) return false; $GLOBALS['fx']['products'][$id]['rows']=$to; return true; }
 function call_migration($action,$receipt=null,$target='production') {
  global $source;
  $payload=base64_encode(json_encode(['action'=>$action,'target'=>$target,'receipt'=>$receipt],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));
  $program=str_replace("'548-hs3-titles-payload'", "'".$payload."'", $source);
  ob_start(); try { eval(substr($program,5)); $output=ob_get_clean(); $pos=strpos($output,'@@548-hs3-titles@@'); if($pos===false) throw new \RuntimeException('missing marker'); return json_decode(substr($output,$pos+strlen('@@548-hs3-titles@@')),true,512,JSON_THROW_ON_ERROR); } catch(\Throwable $e) { ob_end_clean(); return ['error'=>$e->getMessage()]; }
 }
 function must($yes,$message) { if(!$yes) throw new \RuntimeException($message); }
 $initial=$GLOBALS['fx']['products']; $initial_option=$GLOBALS['option_raw'];
 $receipt=call_migration('preview'); must(($receipt['scope']??'')==='hs3-document-titles-v1','preview');
 must($GLOBALS['fx']['products']===$initial && $GLOBALS['option_raw']===$initial_option,'preview changed data');
 $tampered=$receipt; $tampered['products']['1185']['after'][0]['title']='unexpected change'; must(isset(call_migration('apply',$tampered)['error']),'unrelated receipt change accepted');
 must(isset(call_migration('preview',null,'local')['error']),'wrong target accepted');
 $GLOBALS['site']='http://127.0.0.1:9347'; must((call_migration('preview',null,'local')['site']??'')===$GLOBALS['site'],'local preview rejected'); $GLOBALS['site']='https://de-linker.com';
 $GLOBALS['fail_on_id']=1186; $failed=call_migration('apply',$receipt); must(str_contains($failed['error']??'','1186 CAS failed'),'partial failure was not surfaced');
 $inspection=call_migration('inspect',$receipt); must(($inspection['states']['1185']??'')==='after' && ($inspection['states']['1186']??'')==='before' && ($inspection['states']['german_titles']??'')==='after','partial state');
 must(isset(call_migration('verify',$receipt)['error']),'mixed state verified');
 $GLOBALS['fx']['products']['2199']['rows'][0]['title']='concurrent edit';
 $inspection=call_migration('inspect',$receipt); must(($inspection['states']['2199']??'')==='conflict','inspection hid conflict');
 $snap=$GLOBALS['fx']['products']; must(isset(call_migration('apply',$receipt)['error']) && $snap===$GLOBALS['fx']['products'],'conflict was overwritten');
 $GLOBALS['fx']['products']['2199']['rows'][0]['title']='Keep me'; $GLOBALS['fail_on_id']=0;
 $applied=call_migration('apply',$receipt); must(!isset($applied['error']) && count(array_unique($applied['states']))===1 && reset($applied['states'])==='after','resume apply');
 $verified=call_migration('verify',$receipt); must(!isset($verified['error']),'verify after apply');
 foreach($GLOBALS['fx']['products'] as $id=>$p) { must($p['rows'][0]===$initial[$id]['rows'][0],'unrelated row changed'); foreach([1,2] as $i) { $a=$p['rows'][$i]; $b=$initial[$id]['rows'][$i]; unset($a['title'],$b['title']); must($a===$b,'unrelated row fields changed'); } }
 $map=unserialize($GLOBALS['option_raw']); foreach(unserialize($initial_option) as $key=>$value) must(($map[$key]??null)===$value,'old title mapping changed'); foreach($GLOBALS['fx']['docs'] as $d) must(($map[$d['title']]??null)===$d['de'],'new German title missing');
 $applied_option=$GLOBALS['option_raw']; $map=unserialize($applied_option); $map['keep']='concurrent'; $GLOBALS['option_raw']=serialize($map);
 $inspection=call_migration('inspect',$receipt); must(($inspection['states']['german_titles']??'')==='conflict','option conflict hidden');
 $snap=$GLOBALS['fx']['products']; must(isset(call_migration('rollback',$receipt)['error']) && $snap===$GLOBALS['fx']['products'],'option conflict overwritten');
 $GLOBALS['option_raw']=$applied_option; $restored=call_migration('rollback',$receipt);
 must(!isset($restored['error']) && $GLOBALS['fx']['products']===$initial && $GLOBALS['option_raw']===$initial_option,'rollback');
 $GLOBALS['bad_file']=true; must(isset(call_migration('preview')['error']),'file mismatch accepted'); $GLOBALS['bad_file']=false;
 $GLOBALS['extra_association']=true; must(isset(call_migration('preview')['error']),'extra association accepted'); $GLOBALS['extra_association']=false;
 $GLOBALS['lock_fail']=true; must(isset(call_migration('preview')['error']),'unavailable lock accepted');
 echo "OK\n";
}
""".replace("FIXTURE", base64.b64encode(data).decode()).replace(
        "SOURCE", base64.b64encode(source).decode()
    )
    result = subprocess.run(
        [php], input=harness, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "OK", result.stdout
