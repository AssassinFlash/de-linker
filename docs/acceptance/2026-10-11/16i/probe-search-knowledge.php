<?php
/**
 * Probe: the search-knowledge ability against the imported #10 index.
 *
 *   just wp <instance> eval-file "$PWD/docs/acceptance/2026-10-11/16i/probe-search-knowledge.php"
 *
 * Absolute, because WP-CLI resolves a relative eval-file path against the
 * instance's WordPress root, not against the directory the command runs in.
 *
 * Runs the ability's own execute() (`Linker\Commerce\Abilities\SearchKnowledge`)
 * for three bake-off golden questions and prints the hits plus the gold page's
 * position in the ability's own ranking. The three questions are the ones the
 * ticket names: their ids, languages and questions are copied from
 * `services/genie/index/eval/golden.jsonl`; each gold page is its evidence's
 * (doc_sha256, page). Nothing here writes.
 *
 * @package Linker\Commerce
 */

// No declare(strict_types=1): `wp eval-file` evals the file, where the
// declaration cannot be the first statement of the script (fatal).

$questions = array(
	array(
		'id'     => '00506d0f0c-en',
		'lang'   => 'en',
		'query'  => 'Is the chint:DTSU666 meter listed as compatible with the CHS2-29.9K-T4-X?',
		'gold'   => array( '92b45188a10eac6d72eefc0345165b3c6ade83316555ddd6fdcf6c46cd67a262', 27 ),
	),
	array(
		'id'     => '0065e3e240-en',
		'lang'   => 'en',
		'query'  => 'What is the rated or maximum current of the GW261.2-BAT-LCD-G10?',
		'gold'   => array( '027415a66a00234f03d1268e180129fa016e601aaf1ecb7cda643a24aecb7d38', 2 ),
	),
	array(
		'id'     => '00cc9d826a-en',
		'lang'   => 'en',
		'query'  => 'What is the maximum AC output current of the GW125/261-ESA-LCN-G10?',
		'gold'   => array( 'c95aef48b1ea4fbd0ae8729c104774ce2b5ee7137809fc8fe20642be2780bbfe', 2 ),
	),
);

$index = new \Linker\Commerce\Abilities\KnowledgeIndex( $GLOBALS['wpdb'] );

foreach ( $questions as $question ) {
	$ability = new \Linker\Commerce\Abilities\SearchKnowledge();
	$result  = $ability->execute( array( 'query' => $question['query'], 'lang' => $question['lang'] ) );
	$hits    = $result['hits'];
	printf( "%s  %s\n", $question['id'], $question['query'] );
	printf( "  hits: %d\n", count( $hits ) );
	foreach ( array_slice( $hits, 0, 8 ) as $position => $hit ) {
		printf(
			"  %2d  %-24s p.%-4d %s | %s\n",
			$position + 1,
			$hit['chunk_id'],
			$hit['page'],
			mb_substr( (string) $hit['title'], 0, 46 ),
			mb_substr( preg_replace( '/\s+/', ' ', (string) $hit['text'] ), 0, 70 )
		);
	}
	// Where the gold page ranks in the ability's own candidate ranking (CANDIDATES deep).
	$rowids = $index->keyword_ranking( $question['query'], array() );
	$chunks = $index->table( 'chunks' );
	$gold   = null;
	foreach ( $rowids as $position => $rowid ) {
		$row = $GLOBALS['wpdb']->get_row(
			$GLOBALS['wpdb']->prepare( "SELECT doc_sha256, page FROM `{$chunks}` WHERE rowid = %d", $rowid ),
			ARRAY_A
		);
		if ( ! is_array( $row ) ) {
			continue;
		}
		if ( $row['doc_sha256'] === $question['gold'][0] && (int) $row['page'] === $question['gold'][1] ) {
			$gold = $position + 1;
			break;
		}
	}
	printf(
		"  gold page %s p.%d in the keyword ranking: %s (of %d candidates)\n\n",
		substr( $question['gold'][0], 0, 12 ),
		$question['gold'][1],
		null === $gold ? 'beyond the candidate depth' : (string) $gold,
		count( $rowids )
	);
}
