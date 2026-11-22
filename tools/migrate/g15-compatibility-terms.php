<?php
/**
 * Correct product wording on existing Woo pairing declarations. Preview by
 * default; pass apply to wp eval-file to write the same conditions in place.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\Publication\CompatibilityClaims;

defined( 'ABSPATH' ) || exit;

( static function ( bool $write ): void {
	global $wpdb;
	$owners  = $wpdb->get_col( $wpdb->prepare( "SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key = %s ORDER BY post_id", CompatibilityClaims::META_KEY ) );
	$changed = array();
	foreach ( $owners as $owner ) {
		$claims = get_post_meta( (int) $owner, CompatibilityClaims::META_KEY, true );
		$next   = $claims;
		$count  = 0;
		foreach ( array( 'pairs', 'requirements' ) as $kind ) {
			foreach ( $claims[ $kind ] ?? array() as $index => $row ) {
				foreach ( $row['conditions'] ?? array() as $key => $condition ) {
					$edited = $condition;
					foreach ( array( 'en', 'de' ) as $lang ) {
						if ( isset( $condition[ $lang ] ) && preg_match( '/article|artikel/i', $condition[ $lang ] ) ) {
							$edited[ $lang ] = Materials::apply_terms( $condition[ $lang ], 'de' === $lang );
						}
					}
					if ( $edited !== $condition ) {
						$next[ $kind ][ $index ]['conditions'][ $key ] = $edited;
						++$count;
					}
				}
			}
		}
		if ( 0 === $count ) {
			continue;
		}
		if ( $write && ! update_post_meta( (int) $owner, CompatibilityClaims::META_KEY, wp_slash( $next ), $claims ) ) {
			WP_CLI::error( sprintf( 'Concurrent edit to product %d. Read current conditions before retrying.', $owner ) );
		}
		$changed[ $owner ] = $count;
	}
	WP_CLI::log(
		wp_json_encode(
			array(
				'written'            => $write,
				'changed_conditions' => $changed,
			)
		)
	);
} )( 'apply' === ( $args[0] ?? '' ) );
