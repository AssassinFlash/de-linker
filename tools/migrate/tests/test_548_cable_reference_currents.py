"""Exercise the exact cable current migration against an in-memory Woo fixture."""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location(
    "cable_reference_currents", HERE.parent / "548-cable-reference-currents.py"
)
assert SPEC is not None and SPEC.loader is not None
migration: ModuleType = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


def test_original_input_has_only_manufacturer_condition_rows() -> None:
    plan, _ = migration.load_plan()
    expected = [[55, 52, 44], [70, 67, 57]]
    for reference, values in zip(plan["references"], expected, strict=True):
        rows = reference["cable_facts"]["reference_current_ratings"]
        assert [row["current_a"] for row in rows] == values
        assert [row["laying"] for row in rows] == [
            "single_in_air",
            "single_on_surface",
            "two_touching_on_surface",
        ]
        assert all(
            row["ambient_temperature_c"] == 60
            and row["rated_conductor_temperature_c"] == 120
            and row["source"]["page"] == 2
            and row["source"]["blob_sha256"]
            == reference["documents"][0]["expected_blob_sha256"]
            for row in rows
        )


@pytest.mark.parametrize(
    "damage", ["current", "conditions", "blob", "duplicate", "quote", "url"]
)
def test_input_refuses_changes_to_the_reviewed_originals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    plan, _ = migration.load_plan()
    reference = plan["references"][0]
    ratings = reference["cable_facts"]["reference_current_ratings"]
    if damage == "current":
        ratings[0]["current_a"] = 56
    elif damage == "conditions":
        ratings[0]["ambient_temperature_c"] = 25
    elif damage == "blob":
        reference["documents"][0]["expected_blob_sha256"] = "0" * 64
    elif damage == "duplicate":
        ratings[1] = copy.deepcopy(ratings[0])
    elif damage == "quote":
        ratings[0]["source"]["quote"] = "incorrect manufacturer quote"
    else:
        reference["documents"][0]["url"] = "https://de-linker.com/other.pdf"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(plan))
    monkeypatch.setattr(migration, "PLAN", path)
    with pytest.raises(migration.MigrationError):
        migration.load_plan()


def test_receipt_rejects_unrelated_changes(tmp_path: Path) -> None:
    """The Python side rechecks the exact preimage diff before invoking WP."""
    plan, digest = migration.load_plan()
    products: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []
    for reference in plan["references"]:
        key = str(migration.REFERENCES[reference["id"]])
        source = reference["cable_facts"]["reference_current_ratings"][0]["source"]
        doc_id = (
            "doc-"
            + hashlib.sha256(
                unquote(urlsplit(source["document_url"]).path).encode()
            ).hexdigest()
        )
        doc = {
            "document_id": doc_id,
            "document_revision": "a" * 64,
            "blob_sha256": source["blob_sha256"],
            "url": source["document_url"],
        }
        before: dict[str, Any] = {"other_fact": "preserve"}
        after = copy.deepcopy(before)
        after["reference_current_ratings"] = []
        for rating in reference["cable_facts"]["reference_current_ratings"]:
            item = copy.deepcopy(rating)
            item["source"] = {
                "document_id": doc_id,
                "document_revision": doc["document_revision"],
                "blob_sha256": source["blob_sha256"],
                "product_id": int(key),
                "page": 2,
                "quote": rating["source"]["quote"],
            }
            after["reference_current_ratings"].append(item)
            changes.append(
                {
                    "product_id": int(key),
                    "id": item["id"],
                    "before": None,
                    "after": item,
                }
            )
        products[key] = {
            "engineering_id": reference["id"],
            "before": before,
            "after": after,
            "documents": {doc_id: doc},
        }
    receipt = {
        "schema_version": 1,
        "scope": "nexans-reference-currents-v1",
        "site": "https://de-linker.com",
        "plan_sha256": digest,
        "products": products,
        "changes": changes,
    }
    migration.validate_receipt(receipt, plan, digest)
    path = tmp_path / "receipt.json"
    migration.write_receipt(path, receipt)
    assert path.stat().st_mode & 0o777 == 0o600
    assert migration.private_receipt(path) == receipt
    with pytest.raises(FileExistsError):
        migration.write_receipt(path, receipt)
    receipt["products"]["8467"]["after"]["other_fact"] = "overwrite"
    with pytest.raises(migration.MigrationError, match="unrelated"):
        migration.validate_receipt(receipt, plan, digest)


def test_real_php_binder_preview_apply_resume_verify_and_rollback() -> None:
    plan, digest = migration.load_plan()
    fixture = {
        "plan": plan,
        "digest": digest,
        "migration": str(HERE.parent / "548-cable-reference-currents.php"),
        "binder": str(
            ROOT
            / "plugins/linker-commerce/includes/Products/Publication/CableFacts.php"
        ),
        "adoption": str(
            ROOT
            / "plugins/linker-commerce/includes/Products/Publication/ReferenceMigration.php"
        ),
    }
    encoded = base64.b64encode(json.dumps(fixture).encode()).decode()
    php = r"""<?php
namespace Linker\Commerce\Products {
 final class Publication {
  public static function manifest(): array {
   $out = $GLOBALS['manifest'];
   foreach ($out['products'] as &$p) { $p['product_revision'] = self::revision($GLOBALS['meta'][$p['product_id']]); }
   unset($p);
   $out['source_revision'] = self::revision($GLOBALS['meta']);
   return $out;
  }
  public static function canonical_id(int $id): int { return $id; }
  public static function is_published(int $id): bool { return in_array($id, [8467,8468], true); }
  public static function revision(mixed $value): string { return hash('sha256', json_encode($value, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)); }
 }
 final class EngineeringReference {
  const ID_META_KEY = '_linker_engineering_id'; const CABLE = 'reference_cable';
  public static function role(int $id): string { return self::CABLE; }
 }
 final class EngineeringFeed {
  public static function feed(): array {
   $manifest = Publication::manifest(); $overlay = [];
   foreach ($GLOBALS['identities'] as $name => $id) {
    $overlay[] = ['canonical_product_id'=>$id,'id'=>$name,'cable_facts'=>\Linker\Commerce\Products\Publication\CableFacts::projection($id,$manifest)];
   }
   if (!empty($GLOBALS['bad_feed'])) { $overlay[0]['cable_facts']['reference_current_ratings'][0]['current_a'] += 1; }
   return ['source_revision'=>$manifest['source_revision'],'overlay'=>$overlay];
  }
 }
}
namespace Linker\Commerce\Products\Publication {
 final class DocumentFiles {
  public static function id(string $url): string { return 'doc-' . hash('sha256', rawurldecode(parse_url($url, PHP_URL_PATH))); }
 }
}
namespace {
 define('ABSPATH', '/fixture/');
 class WC_Product {
  public function __construct(private int $id) {}
  public function get_attribute(string $name): string { return $GLOBALS['models'][$this->id]; }
  public function get_data(): array { return ['id' => $this->id, 'price' => '', 'meta_data' => []]; }
 }
 class WP_CLI { public static function error(string $message): never { throw new \RuntimeException($message); } }
 function home_url(): string { return 'https://de-linker.com'; }
 function wp_parse_url(string $url, int $part): mixed { return parse_url($url, $part); }
 function wp_json_encode(mixed $value, int $flags = 0): string|false { return json_encode($value, $flags); }
 function get_posts(array $args): array { return [$GLOBALS['identities'][$args['meta_value']]]; }
 function wc_get_product(int $id): WC_Product { return new WC_Product($id); }
 function metadata_exists(string $type, int $id, string $key): bool { return array_key_exists($id, $GLOBALS['meta']); }
 function get_post_meta(int $id, string $key, bool $single): mixed {
  return $key === '_linker_engineering_id' ? array_search($id, $GLOBALS['identities'], true) : ($GLOBALS['meta'][$id] ?? '');
 }
 function wp_slash(mixed $value): mixed { return $value; }
 function update_post_meta(int $id, string $key, mixed $next, mixed $previous): bool {
  if (!empty($GLOBALS['fail_id']) && $id === $GLOBALS['fail_id']) { return false; }
  if (($GLOBALS['meta'][$id] ?? null) !== $previous) { return false; }
  $GLOBALS['meta'][$id] = $next;
  if (!empty($GLOBALS['concurrent_after_first']) && $id === 8467) {
   $GLOBALS['meta'][8468]['conductor_material'] = 'concurrent change during apply';
  }
  return true;
 }
 function wc_delete_product_transients(int $id): void {}
 function require_it(bool $condition, string $message): void { if (!$condition) { throw new \RuntimeException($message); } }
 function run_migration(array $request): array {
  $source = file_get_contents($GLOBALS['script']);
  $payload = base64_encode(json_encode($request, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
  $needle = "'548-cable-reference-currents-payload'";
  require_it(substr_count($source, $needle) === 1, 'payload placeholder');
  $source = str_replace($needle, "'" . $payload . "'", $source);
  ob_start();
  try { eval('?>' . $source); $output = ob_get_clean(); }
  catch (\Throwable $error) { ob_end_clean(); throw $error; }
  require_it((bool) preg_match('/@@548-cable-reference-currents@@([^\n]+)/', $output, $match), 'result marker');
  return json_decode($match[1], true, 512, JSON_THROW_ON_ERROR);
 }
 $fixture = json_decode(base64_decode('__FIXTURE__'), true, 512, JSON_THROW_ON_ERROR);
 $plan = $fixture['plan']; $digest = $fixture['digest']; $GLOBALS['script'] = $fixture['migration'];
 $GLOBALS['identities'] = ['nexans-038021106'=>8467, 'nexans-038023102'=>8468];
 $GLOBALS['meta'] = [2409 => ['controller' => 'preserve']];
 $GLOBALS['models'] = []; $GLOBALS['manifest'] = ['products'=>[], 'documents'=>[]];
 foreach ($plan['references'] as $reference) {
  $id = $GLOBALS['identities'][$reference['id']]; $GLOBALS['models'][$id] = $reference['model'];
  $input = $reference['cable_facts']; $source = $input['source'];
  $doc_id = \Linker\Commerce\Products\Publication\DocumentFiles::id($source['document_url']);
  $document = ['document_id'=>$doc_id,'document_revision'=>str_repeat('a',64),'blob_sha256'=>$source['blob_sha256'],'product_ids'=>[$id],'url'=>$source['document_url']];
  $GLOBALS['manifest']['documents'][] = $document;
  $GLOBALS['manifest']['products'][] = ['product_id'=>$id,'product_revision'=>'initial'];
  $bind = static fn(array $s): array => ['document_id'=>$doc_id,'document_revision'=>$document['document_revision'],'blob_sha256'=>$s['blob_sha256'],'product_id'=>$id,'page'=>$s['page'],'quote'=>$s['quote']];
  $input['source'] = $bind($input['source']);
  foreach ($input['parameter_sets'] as &$set) { $set['source'] = $bind($set['source']); } unset($set);
  unset($input['reference_current_ratings']);
  $GLOBALS['meta'][$id] = $input;
 }
 require $fixture['binder']; require $fixture['adoption'];
 // Existing extra rows are preserved, including a pre-existing unrelated rating.
 $extra = $GLOBALS['meta'][8467]['parameter_sets'][0]; $extra['id']='other-valid-resistance';
 $GLOBALS['meta'][8467]['parameter_sets'][] = $extra;
 $source = $GLOBALS['meta'][8468]['source'];
 $GLOBALS['meta'][8468]['reference_current_ratings'] = [['id'=>'other','laying'=>'single_in_air','ambient_temperature_c'=>30,'rated_conductor_temperature_c'=>90,'current_a'=>12,'source'=>$source]];
 $before = $GLOBALS['meta']; $request = ['action'=>'preview','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>null];
 $receipt = run_migration($request);
 require_it(count($receipt['changes']) === 6 && $GLOBALS['meta'] === $before, 'preview and six changes');
 require_it(count($receipt['products'][8467]['after']['parameter_sets']) === 2, 'extra impedance preserved');
 require_it(count($receipt['products'][8468]['after']['reference_current_ratings']) === 4, 'extra rating preserved');
 // Newly adopted references bind all three sources through the existing migration.
 $method = new \ReflectionMethod(\Linker\Commerce\Products\Publication\ReferenceMigration::class, 'cable_facts');
 $adopted = $method->invoke(null, 8467, $plan['references'][0]['cable_facts'], \Linker\Commerce\Products\Publication::manifest());
 require_it(count($adopted['reference_current_ratings']) === 3 && $adopted['reference_current_ratings'][0]['source']['product_id'] === 8467, 'adoption source binding');
 $original_doc = $GLOBALS['manifest']['documents'][1];
 $GLOBALS['manifest']['documents'][1]['document_revision'] = str_repeat('b',64);
 try { run_migration(['action'=>'apply','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]); throw new \RuntimeException('document drift accepted'); }
 catch (\RuntimeException $e) { require_it(str_contains($e->getMessage(), 'document changed'), 'document drift rejected'); }
 require_it($GLOBALS['meta'] === $before, 'document drift caused no writes');
 $GLOBALS['manifest']['documents'][1] = $original_doc;
 $mutated = $before; $mutated[8468]['conductor_material'] = 'concurrent change'; $GLOBALS['meta'] = $mutated;
 try { run_migration(['action'=>'apply','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]); throw new \RuntimeException('concurrent edit accepted'); }
 catch (\RuntimeException $e) { require_it(str_contains($e->getMessage(), 'changed after preview'), 'concurrent edit rejected'); }
 require_it($GLOBALS['meta'] === $mutated, 'concurrent edit not overwritten');
 $GLOBALS['meta'] = $before;
 $tampered = $receipt; $tampered['products'][8467]['after']['conductor_material'] = 'changed';
 try { run_migration(['action'=>'apply','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$tampered]); throw new \RuntimeException('tamper accepted'); }
 catch (\RuntimeException $e) { require_it(str_contains($e->getMessage(), 'unrelated cable data'), 'tamper rejected'); }
 require_it($GLOBALS['meta'] === $before, 'tamper caused no writes');
 $GLOBALS['concurrent_after_first'] = true;
 try { run_migration(['action'=>'apply','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]); throw new \RuntimeException('mid-write change accepted'); }
 catch (\RuntimeException $e) { require_it(str_contains($e->getMessage(), 'changed during the migration'), 'mid-write change rejected'); }
 require_it($GLOBALS['meta'][8468]['conductor_material'] === 'concurrent change during apply', 'mid-write change preserved');
 $GLOBALS['concurrent_after_first'] = false; $GLOBALS['meta'] = $before;
 $GLOBALS['fail_id'] = 8468;
 try { run_migration(['action'=>'apply','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]); throw new \RuntimeException('write failure accepted'); }
 catch (\RuntimeException $e) { require_it(str_contains($e->getMessage(), 'readback failed'), 'partial failure surfaced'); }
 require_it($GLOBALS['meta'][8467] === $receipt['products'][8467]['after'] && $GLOBALS['meta'][8468] === $before[8468], 'one product only on failed write');
 $GLOBALS['fail_id'] = 0;
 try { run_migration(['action'=>'verify','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]); throw new \RuntimeException('mixed state accepted'); }
 catch (\RuntimeException $e) { require_it(str_contains($e->getMessage(), 'mixed receipt states'), 'mixed state detected'); }
 $applied = run_migration(['action'=>'apply','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]);
 require_it($applied['changes'] === 1 && $GLOBALS['meta'][2409] === $before[2409], 'resume completes only missing product');
 $again = run_migration(['action'=>'apply','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]);
 require_it($again['changes'] === 0, 'apply idempotent');
 $idempotent = run_migration($request);
 require_it(count($idempotent['changes']) === 0, 'preview idempotent');
 $verified = run_migration(['action'=>'verify','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]);
 require_it(array_column($verified['products'], 'status') === ['verified','verified'], 'two projections verified');
 $live_projections = [];
 foreach ([8467,8468] as $id) {
  $live_projections[$id] = \Linker\Commerce\Products\Publication\CableFacts::projection($id, \Linker\Commerce\Products\Publication::manifest());
 }
 $GLOBALS['bad_feed'] = true;
 try { run_migration(['action'=>'verify','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]); throw new \RuntimeException('incorrect feed accepted'); }
 catch (\RuntimeException $e) { require_it(str_contains($e->getMessage(), 'feed cable facts'), 'feed mismatch rejected'); }
 $GLOBALS['bad_feed'] = false;
 $rollback = run_migration(['action'=>'rollback','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]);
 require_it($rollback['changes'] === 2 && $GLOBALS['meta'] === $before, 'exact rollback');
 $verified = run_migration(['action'=>'verify','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$receipt]);
 require_it(array_column($verified['products'], 'status') === ['restored','restored'], 'rollback verified');
 // A later receipt can start with one product already fully up to date.
 $GLOBALS['meta'][8467] = $receipt['products'][8467]['after'];
 $partial_before = $GLOBALS['meta']; $partial = run_migration($request);
 require_it(count($partial['changes']) === 3, 'partial preview has three additions');
 run_migration(['action'=>'apply','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$partial]);
 $checked = run_migration(['action'=>'verify','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$partial]);
 require_it(array_column($checked['products'], 'status') === ['unchanged','verified'], 'neutral product accepted on verify');
 run_migration(['action'=>'rollback','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$partial]);
 $checked = run_migration(['action'=>'verify','plan'=>$plan,'plan_sha256'=>$digest,'receipt'=>$partial]);
 require_it(array_column($checked['products'], 'status') === ['unchanged','restored'] && $GLOBALS['meta'] === $partial_before, 'neutral product accepted after rollback');
 $conflict = $before;
 $conflict[8468]['reference_current_ratings'][0]['id'] = $plan['references'][1]['cable_facts']['reference_current_ratings'][0]['id'];
 $GLOBALS['meta'] = $conflict;
 try { run_migration($request); throw new \RuntimeException('conflicting rating accepted'); }
 catch (\RuntimeException $e) { require_it(str_contains($e->getMessage(), 'conflicts'), 'conflict rejected'); }
 require_it($GLOBALS['meta'] === $conflict, 'conflict caused no writes');
 echo json_encode(['receipt'=>$receipt, 'idempotent'=>$idempotent, 'partial'=>$partial, 'projections'=>$live_projections, 'checks'=>'passed']);
}
""".replace("__FIXTURE__", encoded)
    result = subprocess.run(
        [os.environ.get("PHP", "php")],
        input=php,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["checks"] == "passed"
    assert [
        item["current_a"]
        for item in payload["projections"]["8467"]["reference_current_ratings"]
    ] == [55, 52, 44]
    assert [
        item["current_a"]
        for item in payload["projections"]["8468"]["reference_current_ratings"]
    ] == [12, 70, 67, 57]
    migration.validate_receipt(payload["receipt"], plan, digest)
    migration.validate_receipt(payload["idempotent"], plan, digest)
    migration.validate_receipt(payload["partial"], plan, digest)
