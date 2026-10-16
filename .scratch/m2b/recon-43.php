<?php
$pairs = array(
  array('5', 2748, 'c', '<h3>Planner Sizing &amp; Compatibility Lists</h3>'),
  array('6', 2748, 'c', 'aria-label="Planner sizing and compatibility lists"'),
  array('7', 2748, 'c', '<b>Planner Sizing and Compatibility Lists</b>'),
  array('8', 2748, 'c', '<h3 class="lk-sstage-h3">Planner Sizing and Compatibility Lists</h3>'),
  array('9', 2748, 'c', '<strong>Deliverable:</strong> Planner Sizing · Complete Parts List'),
  array('10', 6700, 'c', '<h3>Planer-Auslegung &amp; Kompatibilitätslisten</h3>'),
  array('11', 6700, 'c', 'aria-label="Planer-Auslegung und Kompatibilitätslisten"'),
  array('12', 6700, 'c', '<b>Planer-Auslegung und Kompatibilitätslisten</b>'),
  array('13', 6700, 'c', '<h3 class="lk-sstage-h3">Planer-Auslegung und Kompatibilitätslisten</h3>'),
  array('14', 6700, 'c', '<strong>Ergebnis:</strong> Auslegung im Planer · Vollständige Stückliste'),
  array('15', 826, 'c', 'Site Detail maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.'),
  array('16', 6871, 'c', 'Der Planer modelliert geeignete'),
  array('17', 6871, 'c', '<td>Speicherpakete, Planer-Werkzeuge und Partnerpreise</td>'),
  array('18', 6863, 'c', 'href="/de/produkte/" data-linker-assistant-open'),
  array('19', 932, 'c', 'href="/products/" data-linker-assistant-open'),
  array('20', 746, 'c', 'Design with Planner →'),
  array('21', 792, 'c', 'Model Project in Planner →'),
  array('22', 746, 'c', '<td>Storage packages, Planner tools, and Partner pricing</td>'),
  array('23', 1673, 'c', 'put to the Genie'),
  array('24', 1673, 'c', 'the Advisor button'),
  array('25', 1673, 'c', 'the Advisor zone'),
  array('26', 1673, 'c', 'Advisor button zone'),
  array('27', 6827, 'c', 'the Advisor button'),
  array('28', 6827, 'c', 'the Advisor zone'),
  array('29', 6827, 'c', 'Advisor button zone'),
  array('1', 13, 'c', '<li>Quoted per site, not from the cart</li>'),
  array('2', 6913, 'c', '<li>Angebot pro Standort, nicht aus dem Warenkorb</li>'),
  array('3', 1755, 'd', 'CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project, not from the cart.'),
  array('4', 6917, 'd', 'Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten statt über den Warenkorb.'),
  array('30', 746, 'c', 'cannot simply be placed into an online shopping cart.'),
  array('31', 6871, 'c', 'lassen sich nicht einfach in einen Online-Warenkorb legen.'),
  array('32', 1673, 'c', '(session, cart, and login cookies)'),
  array('33', 6827, 'c', '(Session-, Warenkorb- und Login-Cookies)'),
  array('34', 1674, 'c', 'apply automatically in the cart'),
  array('35', 6825, 'c', 'werden im Warenkorb automatisch'),
  array('36', 1673, 'c', 'When you ask the Advisor a question'),
  array('37', 1673, 'c', 'not sent with Advisor messages'),
  array('38', 1673, 'c', 'Advisor conversations belonging to a signed-in account'),
  array('39', 1673, 'c', "from the Advisor's history"),
  array('40', 6827, 'c', 'Wenn Sie dem Berater eine Frage stellen'),
  array('41', 6827, 'c', 'nicht mit Berater-Nachrichten übermittelt'),
  array('42', 6827, 'c', 'Berater-Konversationen, die zu einem angemeldeten Konto gehören'),
  array('43', 6827, 'c', 'aus dem Verlauf des Beraters löschen'),
);
$cache = array();
foreach ($pairs as $row) {
  list($n, $id, $field, $needle) = $row;
  if (!isset($cache[$id])) {
    $p = get_post($id);
    $cache[$id] = array(
      'c' => $p ? $p->post_content : null,
      'd' => get_post_meta($id, '_seopress_titles_desc', true),
      't' => get_post_meta($id, '_seopress_titles_title', true),
    );
  }
  $hay = $cache[$id][$field];
  if ($hay === null) { echo "#$n ID $id: POST MISSING\n"; continue; }
  $count = substr_count($hay, $needle);
  echo "#$n post $id [$field] count=$count\n";
}
// context dump for the risky ones
foreach (array(1673, 6827) as $id) {
  $c = $cache[$id]['c'];
  echo "\n=== #$id Advisor contexts ===\n";
  $off = 0;
  while (($pos = strpos($c, 'Advisor', $off)) !== false) {
    echo "  ..." . str_replace(array("\n", "\r"), array("\\n", ""), substr($c, max(0, $pos - 100), 220)) . "...\n";
    $off = $pos + 7;
  }
}
foreach (array(746, 6871) as $id) {
  $c = $cache[$id]['c'];
  echo "\n=== #$id cart/Warenkorb contexts ===\n";
  foreach (array('cart', 'Warenkorb') as $needle) {
    $off = 0;
    while (($pos = strpos($c, $needle, $off)) !== false) {
      echo "  [$needle] ..." . str_replace(array("\n", "\r"), array("\\n", ""), substr($c, max(0, $pos - 130), 300)) . "...\n";
      $off = $pos + strlen($needle);
    }
  }
}
foreach (array(1674, 6825, 1673, 6827) as $id) {
  $c = $cache[$id]['c'];
  echo "\n=== #$id cookie/terms context ===\n";
  foreach (array('apply automatically in the cart', 'werden im Warenkorb automatisch', 'login cookies', 'Login-Cookies') as $needle) {
    $pos = strpos($c, $needle);
    if ($pos !== false) echo "  [$needle] ..." . str_replace(array("\n", "\r"), array("\\n", ""), substr($c, max(0, $pos - 130), 300)) . "...\n";
  }
}
echo "\n=== slugs/twins ===\n";
foreach (array(1755, 6917, 1674, 6825) as $id) {
  $p = get_post($id);
  echo "#$id " . ($p ? $p->post_name . ' ' . $p->post_type . ' ' . $p->post_status : 'MISSING') . " title=" . json_encode($p ? $p->post_title : null) . "\n";
}
echo "twins: 1755 -> " . json_encode(pll_get_post_translations(1755)) . "\n";
echo "twins: 1674 -> " . json_encode(pll_get_post_translations(1674)) . "\n";
echo "\n=== seo desc values ===\n";
foreach (array(1755, 6917) as $id) { echo "#$id desc=" . json_encode($cache[$id]['d']) . "\n"; }
