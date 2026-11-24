<?php
/**
 * Apply the approved German search summaries to their native SEOPress fields.
 *
 * Usage: wp eval-file tools/migrate/bilingual-search-metadata.php [apply]
 *
 * @package Linker
 */

declare( strict_types = 1 );

$metadata = array(
	'loesungskonfigurator' => array(
		'page',
		'Planen Sie Ihr PV- und Speichersystem. Vergleichen Sie passende Geräte für Ihr Projekt, prüfen Sie Herstellerquellen und erstellen Sie eine Stückliste.',
	),
	'blog' => array(
		'page',
		'Lesen Sie Praxisbeiträge zur Auslegung von PV- und Speichersystemen: vom Lastprofil und der Geräteauswahl bis zur Inbetriebnahme und Übergabe.',
	),
	'gewerbespeicher-lastspitzenkappung-notstrom-skalierbarkeit' => array(
		'post',
		'Planen Sie Gewerbespeicher für Lastspitzen und Notstrom. Prüfen Sie Lastprofile, priorisieren Sie Verbraucher und vergleichen Sie mögliche Ausbaustufen.',
		'Gewerbespeicher für Lastspitzen und Notstrom | Linker',
	),
);
$write = in_array( 'apply', $args, true );
foreach ( $metadata as $slug => $fields ) {
	$posts = get_posts( array( 'post_type' => $fields[0], 'name' => $slug, 'lang' => 'de', 'posts_per_page' => 1, 'post_status' => 'publish', 'suppress_filters' => false ) );
	$post_id = $posts[0]->ID ?? 0;
	if ( ! $post_id || 'de' !== pll_get_post_language( $post_id ) ) {
		WP_CLI::error( 'Missing German page: ' . $slug );
	}
	$values = array( '_seopress_titles_desc' => $fields[1] );
	if ( isset( $fields[2] ) ) {
		$values['_seopress_titles_title'] = $fields[2];
	}
	foreach ( $values as $meta_key => $value ) {
		if ( $value === get_post_meta( $post_id, $meta_key, true ) ) {
			continue;
		}
		if ( $write ) {
			update_post_meta( $post_id, $meta_key, $value );
		}
		WP_CLI::log( ( $write ? 'Updated ' : 'Would update ' ) . $slug . ' ' . $meta_key );
	}
}
