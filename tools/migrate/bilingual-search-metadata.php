<?php
/**
 * Apply the approved German search summaries to their native SEOPress fields.
 *
 * Usage: wp eval-file tools/migrate/bilingual-search-metadata.php [apply]
 *
 * @package Linker
 */

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

( static function ( array $arguments ): void {
	$metadata = array(
		'solution-configurator'                      => array(
			'page',
			'Planen Sie Ihr PV- und Speichersystem. Vergleichen Sie passende Geräte für Ihr Projekt, prüfen Sie Herstellerquellen und erstellen Sie eine Stückliste.',
		),
		'blog'                                       => array(
			'page',
			'Lesen Sie Praxisbeiträge zur Auslegung von PV- und Speichersystemen: vom Lastprofil und der Geräteauswahl bis zur Inbetriebnahme und Übergabe.',
		),
		'ci-storage-peak-shaving-backup-scalability' => array(
			'post',
			'Planen Sie Gewerbespeicher für Lastspitzen und Notstrom. Prüfen Sie Lastprofile, priorisieren Sie Verbraucher und vergleichen Sie mögliche Ausbaustufen.',
			'Gewerbespeicher für Lastspitzen und Notstrom | Linker',
		),
	);
	$write    = in_array( 'apply', $arguments, true );
	foreach ( $metadata as $slug => $fields ) {
		$posts   = get_posts(
			array(
				'post_type'        => $fields[0],
				'name'             => $slug,
				'lang'             => 'en',
				'posts_per_page'   => 1,
				'post_status'      => 'publish',
				'suppress_filters' => false,
			)
		);
		$post_id = isset( $posts[0] ) ? (int) pll_get_post( $posts[0]->ID, 'de' ) : 0;
		if ( ! $post_id || 'de' !== pll_get_post_language( $post_id ) ) {
			WP_CLI::error( 'Missing German page: ' . $slug );
		}
		$values = array( '_seopress_titles_desc' => $fields[1] );
		if ( isset( $fields[2] ) ) {
			$values['_seopress_titles_title'] = $fields[2];
		}
		foreach ( $values as $meta_key => $value ) {
			if ( get_post_meta( $post_id, $meta_key, true ) === $value ) {
				continue;
			}
			if ( $write ) {
				update_post_meta( $post_id, $meta_key, $value );
			}
			WP_CLI::log( ( $write ? 'Updated ' : 'Would update ' ) . $slug . ' ' . $meta_key );
		}
	}
} )( $args ?? array() );
