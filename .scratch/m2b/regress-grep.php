<?php
// Post-apply regression: the six old names and the old addresses must be
// absent from every published rendered surface (content + seo metas), with
// the whitelist documented in the report (revisions, drafts, seopress_404).
$names = array('Linker Advisor','Linker Planner','Linker Site Detail','Linker Berater','Linker Planer','Linker Standortdetails');
$urls = array('/linker-advisor/','/linker-planner/','/linker-planer/','/linker-berater/');
$all = array_merge($names, $urls);
$posts = get_posts(array(
  'post_type' => array('page','post','lc_partial','lc_dynamic_template'),
  'post_status' => 'publish', 'numberposts' => -1, 'fields' => 'ids', 'lang' => '',
));
$hits = 0;
foreach ($posts as $id) {
  $p = get_post($id);
  $content = $p->post_content;
  $title = get_post_meta($id, '_seopress_titles_title', true);
  $desc = get_post_meta($id, '_seopress_titles_desc', true);
  $found = array();
  foreach ($all as $t) {
    $n = substr_count($content, $t) + substr_count($title, $t) + substr_count($desc, $t);
    if ($n) { $found[] = "$t x$n"; }
  }
  if ($found) {
    $hits++;
    echo "HIT #$id {$p->post_type} " . json_encode($p->post_title) . ": " . implode(', ', $found) . "\n";
  }
}
echo "published surfaces scanned: " . count($posts) . ", hits: $hits\n";
// The German sources' legacy metas.
$metas = array();
$rows = get_posts(array('post_type' => array('page','post'), 'post_status' => 'any', 'numberposts' => -1, 'fields' => 'ids'));
foreach ($rows as $id) {
  $c = get_post_meta($id, '_linker_de_content', true);
  if ($c === '' || $c === null) continue;
  foreach ($all as $t) { $n = substr_count((string)$c, $t); if ($n) { $metas[] = "#$id $t x$n"; } }
  $tmeta = get_post_meta($id, '_linker_de_title', true);
  foreach ($all as $t) { if (strpos((string)$tmeta, $t) !== false) { $metas[] = "#$id title $t"; } }
}
echo "legacy source metas: " . (empty($metas) ? 'clean' : implode('; ', $metas)) . "\n";
// The media alts.
$alt_rows = $GLOBALS['wpdb']->get_results("SELECT post_id, meta_value FROM {$GLOBALS['wpdb']->postmeta} WHERE meta_key = '_wp_attachment_image_alt' AND (meta_value LIKE '%Linker Advisor%' OR meta_value LIKE '%Linker Planner%' OR meta_value LIKE '%Linker Site Detail%' OR meta_value LIKE '%Linker Berater%' OR meta_value LIKE '%Linker Planer%' OR meta_value LIKE '%Linker Standortdetails%')");
echo "media alts: " . (empty($alt_rows) ? 'clean' : count($alt_rows) . ' stale') . "\n";
// Drafts (reported separately as the known non-whitelist residue).
$draft_hits = 0;
foreach (get_posts(array('post_type' => array('page','post','lc_partial','lc_dynamic_template'), 'post_status' => 'draft', 'numberposts' => -1, 'fields' => 'ids')) as $id) {
  $c = get_post($id)->post_content;
  $found = array();
  foreach ($all as $t) { $n = substr_count($c, $t); if ($n) { $found[] = "$t x$n"; } }
  if ($found) { $draft_hits++; }
}
echo "draft surfaces with old tokens: $draft_hits\n";
