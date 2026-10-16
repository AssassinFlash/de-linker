<?php
$ids = array(17, 6909, 18, 6911, 4083, 6633, 3302, 6693, 3198, 6696, 3998, 6637, 3999, 6635, 2747, 6702, 13, 6913, 746, 6871, 749, 6923, 792, 6921, 826, 6869, 862, 6865, 874, 6919, 932, 6863, 1673, 6827, 2748, 6700, 558, 6897, 574, 6881, 623, 6873, 1755, 6917, 1674, 6825);
$out = array('posts' => array(), 'seo' => array(), 'legacy' => array());
foreach ($ids as $id) {
  $p = get_post($id);
  if (!$p) { continue; }
  $out['posts'][(string) $id] = array('post_title' => $p->post_title, 'post_content' => $p->post_content, 'post_status' => $p->post_status);
  $t = get_post_meta($id, '_seopress_titles_title', true);
  $d = get_post_meta($id, '_seopress_titles_desc', true);
  $row = array();
  if (metadata_exists('post', $id, '_seopress_titles_title')) { $row['title'] = (string) $t; }
  if (metadata_exists('post', $id, '_seopress_titles_desc')) { $row['desc'] = (string) $d; }
  if ($row) { $out['seo'][(string) $id] = $row; }
  $lc = get_post_meta($id, '_linker_de_content', true);
  if ($lc !== '') {
    $lrow = array('content' => (string) $lc);
    if (metadata_exists('post', $id, '_linker_de_title')) { $lrow['title'] = (string) get_post_meta($id, '_linker_de_title', true); }
    $out['legacy'][(string) $id] = $lrow;
  }
}
file_put_contents('/tmp/m2-dump.json', wp_json_encode($out));
echo "bytes=" . filesize('/tmp/m2-dump.json') . " posts=" . count($out['posts']) . " seo=" . count($out['seo']) . " legacy=" . count($out['legacy']) . "\n";
