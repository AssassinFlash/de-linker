<?php
/**
 * Retire the translated success pages while retaining their original HTML.
 *
 * Run with wp eval-file tools/migrate/1170-retire-static-receipts.php plan|apply.
 *
 * @package Linker\Commerce
 */

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

( static function ( array $arguments ): void {
	if ( ! in_array( $arguments, array( array( 'plan' ), array( 'apply' ) ), true ) ) {
		WP_CLI::error( 'Use plan or apply.' );
	}

	global $wpdb;
	$slugs = array( 623 => 'thank-you', 6873 => 'danke' );
	$pages = array();
	foreach ( $slugs as $id => $slug ) {
		$page = get_post( $id );
		if ( ! $page instanceof WP_Post || 'page' !== $page->post_type || $slug !== $page->post_name || ! in_array( $page->post_status, array( 'publish', 'draft' ), true ) ) {
			WP_CLI::error( "Unexpected static receipt page at {$id}." );
		}
		if ( 'publish' === $page->post_status ) {
			$pages[] = $page;
		}
	}
	if ( ! function_exists( 'pll_get_post' ) || (int) pll_get_post( 623, 'de' ) !== 6873 || (int) pll_get_post( 6873, 'en' ) !== 623 ) {
		WP_CLI::error( 'The receipt pages are not the expected language pair.' );
	}

	if ( 'apply' === $arguments[0] && $pages ) {
		// Change only status in one statement: the retired HTML and both translation terms are original records.
		$updated = $wpdb->query( "UPDATE {$wpdb->posts} SET post_status = 'draft' WHERE ID IN (623, 6873) AND post_type = 'page' AND post_status = 'publish'" );
		if ( false === $updated ) {
			WP_CLI::error( 'Could not retire the receipt pages.' );
		}
		foreach ( $pages as $old ) {
			clean_post_cache( $old->ID );
			$page              = clone $old;
			$page->post_status = 'draft';
			wp_transition_post_status( 'draft', 'publish', $page );
		}
	}
	WP_CLI::log( json_encode( array( 'to_draft' => wp_list_pluck( $pages, 'ID' ) ), JSON_THROW_ON_ERROR ) );
} )( $args ?? array() );
