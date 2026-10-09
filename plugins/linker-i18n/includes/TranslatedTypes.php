<?php
/**
 * Which post types and taxonomies Polylang translates.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * Puts the site's content types under Polylang's translation, whatever the
 * settings page says (Polylang shows them as set by code).
 */
final class TranslatedTypes {

	/**
	 * Post types with a German version: pages, posts, WooCommerce products and
	 * LiveCanvas's header/footer partials and dynamic templates (both
	 * `public => false`, so Polylang lists them only when told to;
	 * docs/research/2026-10-09/i18n-opensource-replication.md §7.1).
	 */
	public const POST_TYPES = array( 'page', 'post', 'product', 'lc_partial', 'lc_dynamic_template' );

	/**
	 * Taxonomies with German terms: post categories, product categories, and
	 * the product attributes whose values are words. The live attributes on
	 * 2026-10-09: phase (Single-phase, Three-phase), battery voltage (High
	 * Voltage, Low Voltage), application (Home, Commercial, Commercial &
	 * Industrial) and product family (Hybrid Inverters, …) are words;
	 * installation type and monitoring/communication have no terms yet and
	 * would hold words. Brand and model are proper names, series (B, H, Link,
	 * One) are model-line codes and power range is figures: those stay one
	 * term for both languages.
	 */
	public const TAXONOMIES = array(
		'category',
		'product_cat',
		'pa_phase',
		'pa_battery-voltage',
		'pa_application',
		'pa_product-family',
		'pa_installation-type',
		'pa_monitoring-communication',
	);

	/**
	 * Adds the post types (filter `pll_get_post_types`).
	 *
	 * @param array<string, string>|array<int, string> $post_types  Post types Polylang translates.
	 * @param bool                                     $is_settings Whether the list is for the settings page.
	 * @return array<string, string>|array<int, string>
	 */
	public function post_types( array $post_types, bool $is_settings ): array {
		unset( $is_settings );
		foreach ( self::POST_TYPES as $post_type ) {
			$post_types[ $post_type ] = $post_type;
		}
		return $post_types;
	}

	/**
	 * Adds the taxonomies (filter `pll_get_taxonomies`).
	 *
	 * @param array<string, string>|array<int, string> $taxonomies  Taxonomies Polylang translates.
	 * @param bool                                     $is_settings Whether the list is for the settings page.
	 * @return array<string, string>|array<int, string>
	 */
	public function taxonomies( array $taxonomies, bool $is_settings ): array {
		unset( $is_settings );
		foreach ( self::TAXONOMIES as $taxonomy ) {
			$taxonomies[ $taxonomy ] = $taxonomy;
		}
		return $taxonomies;
	}
}
