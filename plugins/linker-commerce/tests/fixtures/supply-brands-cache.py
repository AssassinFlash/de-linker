#!/usr/bin/env python3
"""Replay navigation cache races with native WP/Woo functions, without booting WP.

Example:
  python3 tests/fixtures/supply-brands-cache.py --wordpress-root /path/to/wordpress \
    --php /opt/homebrew/opt/php@8.3/bin/php
Use --source-revision <git SHA> to prove the same fixture fails an earlier source.
No database, HTTP, model, instance mutation or generated file is involved.
"""

import argparse
import base64
from pathlib import Path
import subprocess


def native_function(source: str, name: str) -> str:
    """Extract these native functions verbatim; their braces are balanced."""
    start = source.index(f"function {name}(")
    position = source.index("{", start) + 1
    depth = 1
    while depth:
        depth += (source[position] == "{") - (source[position] == "}")
        position += 1
    return source[start:position]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wordpress-root", required=True, type=Path)
    parser.add_argument("--php", default="php")
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    plugin = Path(__file__).resolve().parents[2]
    repository = plugin.parents[1]
    core = (args.wordpress_root / "wp-includes/taxonomy.php").read_text()
    woo = (
        args.wordpress_root
        / "wp-content/plugins/woocommerce/includes/wc-term-functions.php"
    ).read_text()
    php = r'''<?php
$runtime_options = [];
$persisted_options = [];
$runtime_visibility = ['exclude-from-catalog' => 101, 'outofstock' => 102];
$persisted_visibility = $runtime_visibility;
$products = [];
$refreshes = 0;
function taxonomy_exists($taxonomy) { return true; }
function is_taxonomy_hierarchical($taxonomy) { return true; }
function get_current_blog_id() { return 1; }
function absint($value) { return abs((int) $value); }
function wp_parse_args($args, $defaults) { return array_merge($defaults, $args); }
function wp_list_pluck($rows, $field, $index) {
    $result = [];
    foreach ($rows as $row) { $result[$row->$index] = $row->$field; }
    return $result;
}
function get_option($key, $default = false) {
    global $runtime_options;
    return $runtime_options[$key] ?? $default;
}
function shortcode_atts($defaults, $atts, $name = '') { return array_merge($defaults, $atts); }
function sanitize_title($value) { return trim($value); }
function esc_html($value) { return htmlspecialchars($value, ENT_QUOTES); }
function wp_cache_supports($feature) { return true; }
function wp_cache_flush_runtime() {
    global $runtime_options, $persisted_options, $runtime_visibility, $persisted_visibility, $refreshes;
    $runtime_options = $persisted_options;
    $runtime_visibility = $persisted_visibility;
    ++$refreshes;
    return true;
}
function has_filter($name) { return true; }
function apply_filters($name, $id) { return $id; }
function get_post_type($id) { return 'product'; }
function get_post_status($id) { return 'publish'; }
function get_post_meta($id, $key, $single = true) { return ''; }
function wp_upload_dir() { throw new LogicException('Navigation must not resolve a PDF.'); }
function get_posts($args) {
    global $products, $runtime_visibility;
    $roots = ['home-storage' => 100, 'commercial-storage' => 200];
    $categories = [];
    foreach ($args['tax_query'][0]['terms'] as $slug) {
        if (isset($roots[$slug])) {
            $root = $roots[$slug];
            $categories[] = $root;
            $categories = array_merge($categories, get_term_children($root, 'product_cat'));
        }
    }
    $hidden = $args['tax_query'][1]['terms'] ?? [];
    if (($args['tax_query'][1]['field'] ?? '') === 'name') {
        $hidden = array_map(fn($name) => $runtime_visibility[$name], $hidden);
    }
    $ids = [];
    foreach ($products as $id => $product) {
        if (in_array($product['category'], $categories, true)
            && !array_intersect($product['visibility'] ?? [], $hidden)) { $ids[] = $id; }
    }
    return $ids;
}
function get_terms($args) {
    global $products, $runtime_visibility;
    if ($args['taxonomy'] === 'product_visibility') {
        $rows = [];
        foreach ($runtime_visibility as $name => $id) {
            $rows[] = (object) ['name' => $name, 'term_taxonomy_id' => $id];
        }
        return $rows;
    }
    return array_map(fn($id) => $products[$id]['brand'], $args['object_ids']);
}
'''
    for source, name in (
        (core, "get_term_children"),
        (core, "_get_term_hierarchy"),
        (woo, "wc_get_product_visibility_term_ids"),
    ):
        php += native_function(source, name) + "\n"
    for relative in (
        "Products/Publication.php",
        "Products/EngineeringReference.php",
        "Presentation/SupplyBrands.php",
    ):
        if args.source_revision:
            source = subprocess.check_output(
                ["git", "show", f"{args.source_revision}:plugins/linker-commerce/includes/{relative}"],
                cwd=repository,
                text=True,
            )
        else:
            source = (plugin / "includes" / relative).read_text()
        encoded = base64.b64encode(source.removeprefix("<?php").encode()).decode()
        php += f'eval(base64_decode("{encoded}"));\n'
    php += r'''
$reader = new Linker\Commerce\Presentation\SupplyBrands();
$atts = ['categories' => 'home-storage', 'prefix' => 'Home batteries from '];
$products = [11 => ['category' => 101, 'brand' => 'Moved']];
$runtime_options = ['product_cat_children' => [100 => [101]], 'woocommerce_hide_out_of_stock_items' => 'no'];
$persisted_options = ['product_cat_children' => [200 => [101]], 'woocommerce_hide_out_of_stock_items' => 'no'];
get_term_children(100, 'product_cat');
$category = $reader->render($atts);
$products = [11 => ['category' => 100, 'brand' => 'GoodWe', 'visibility' => [102]]];
$runtime_options = ['product_cat_children' => [], 'woocommerce_hide_out_of_stock_items' => 'no'];
$persisted_options = ['product_cat_children' => [], 'woocommerce_hide_out_of_stock_items' => 'yes'];
get_option('woocommerce_hide_out_of_stock_items');
$stock = $reader->render($atts);
$primed = wc_get_product_visibility_term_ids();
$persisted_visibility['exclude-from-catalog'] = 201;
$products = [11 => ['category' => 100, 'brand' => 'Hidden', 'visibility' => [201]]];
$persisted_options['woocommerce_hide_out_of_stock_items'] = 'no';
$visibility = $reader->render($atts);
$checks = [
    'native_category_reparenting' => $category === '',
    'native_cached_stock_option' => $stock === '',
    'recreated_visibility_term_excluded' => $visibility === '',
    'native_woo_helper_remains_static' => $primed['exclude-from-catalog'] === 101
        && wc_get_product_visibility_term_ids()['exclude-from-catalog'] === 101,
    'one_fresh_batch_per_read' => $refreshes === 3,
];
echo json_encode(['checks' => $checks, 'actual' => compact('category', 'stock', 'visibility', 'refreshes')]), "\n";
exit(in_array(false, $checks, true) ? 1 : 0);
'''
    result = subprocess.run([args.php], input=php, text=True, capture_output=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
