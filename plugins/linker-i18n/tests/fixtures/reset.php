<?php
/**
 * Removes what the #9 migration and the tests made on a fixture instance,
 * so seed.php and the migration start again from the live state: the German
 * versions (posts and terms in German), test orders, and queued translations.
 * Runs with Polylang active, which clears its translation groups as the
 * German objects go: `wp eval-file plugins/linker-i18n/tests/fixtures/reset.php`.
 *
 * The file has no strict_types declaration: wp eval-file evaluates it.
 *
 * @package Linker\I18n
 */

// phpcs:disable WordPress.NamingConventions.PrefixAllGlobals -- a WP-CLI script, not plugin code.

( static function (): void {
	// Before the first `wp linker-i18n setup` there is no German language, and
	// a `lang=de` query then matches the objects without a language (Polylang
	// only filters once languages exist): the default terms WordPress and
	// WooCommerce made at installation. Nothing of the migration's is there
	// to remove on such a site, so the German section waits for the language.
	$german_exists = ( function_exists( 'PLL' ) ? PLL()->model->get_language( 'de' ) : null ) instanceof PLL_Language;
	$german_posts  = $german_exists ? get_posts(
		array(
			'post_type'   => 'any',
			'post_status' => 'any',
			'lang'        => 'de',
			'fields'      => 'ids',
			'numberposts' => -1,
		)
	) : array();
	foreach ( $german_posts as $post_id ) {
		wp_delete_post( (int) $post_id, true );
	}

	$german_terms = 0;
	if ( $german_exists ) {
		foreach ( get_taxonomies() as $taxonomy ) {
			if ( ! function_exists( 'pll_is_translated_taxonomy' ) || ! pll_is_translated_taxonomy( $taxonomy ) ) {
				continue;
			}
			$terms = get_terms(
				array(
					'taxonomy'   => $taxonomy,
					'lang'       => 'de',
					'hide_empty' => false,
					'fields'     => 'ids',
				)
			);
			foreach ( is_array( $terms ) ? $terms : array() as $term_id ) {
				wp_delete_term( (int) $term_id, $taxonomy );
				++$german_terms;
			}
		}
	}

	$orders = wc_get_orders(
		array(
			'limit'  => -1,
			'return' => 'ids',
			'status' => 'any',
		)
	);
	foreach ( $orders as $order_id ) {
		$order = wc_get_order( $order_id );
		if ( $order instanceof WC_Order ) {
			$order->delete( true );
		}
	}

	as_unschedule_all_actions( 'linker_i18n_translate' );

	WP_CLI::success( sprintf( 'Removed %d German posts, %d German terms, %d orders.', count( $german_posts ), $german_terms, count( $orders ) ) );
} )();
