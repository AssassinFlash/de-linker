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
	 * Content translated automatically (owner ruling, 2026-10-17).
	 */
	public const POST_TYPES = array( 'page', 'post', 'product' );

	/**
	 * Language pairs owned by present. Polylang must still select the correct
	 * language's template, but a machine translator must never write them.
	 */
	public const PRESENT_TYPES = array( 'lc_partial', 'lc_dynamic_template' );

	/**
	 * Public proper-name archives: one term, language-filtered product results.
	 * Polylang's pll_filtered_taxonomies owns their route and link generation.
	 */
	public const SHARED_ARCHIVES = array( 'product_brand', 'pa_brand', 'pa_series' );

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
		foreach ( array_merge( self::POST_TYPES, self::PRESENT_TYPES ) as $post_type ) {
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

	/**
	 * Declares untranslated archives before Polylang caches its taxonomy list.
	 * Native Polylang intersects these names with registered taxonomies later.
	 *
	 * @param array<int, string> $taxonomies Native and other plugins' shared archives.
	 * @return array<int, string>
	 */
	public function shared_archives( array $taxonomies ): array {
		return array_values( array_unique( array_merge( $taxonomies, self::SHARED_ARCHIVES ) ) );
	}

	/**
	 * Declares the inferred product type before Polylang counts archive twins.
	 * WooCommerce leaves taxonomy post_type empty; Polylang otherwise counts
	 * blog posts and hides valid language links for these shared product terms.
	 *
	 * @param \WP_Query $query WooCommerce's native product query.
	 */
	public function shared_archive_query( \WP_Query $query ): void {
		if ( ! $query->is_main_query() || ! $query->is_tax( self::SHARED_ARCHIVES ) ) {
			return;
		}
		if ( in_array( $query->get( 'post_type' ), array( '', null ), true ) ) {
			$query->set( 'post_type', 'product' );
		}
	}

	/**
	 * A valid shared root stays reachable even when the other language is empty.
	 * Polylang still builds its URL; counts, products and term identity stay native.
	 * Paged, feed, missing and unrelated archives keep the native hide decision.
	 *
	 * @param bool                 $hide     Native archive-count decision.
	 * @param string               $language Native target language slug.
	 * @param array<string, mixed> $args     Native count arguments for this archive.
	 */
	public function hide_shared_archive( bool $hide, string $language, array $args ): bool {
		if ( ! $hide || ! is_main_query() || is_404() || is_paged() || is_feed() || is_search() ) {
			return $hide;
		}
		$term = get_queried_object();
		if ( ! $term instanceof \WP_Term || 0 >= $term->term_id || ! in_array( $term->taxonomy, self::SHARED_ARCHIVES, true ) || pll_is_translated_taxonomy( $term->taxonomy ) ) {
			return $hide;
		}
		$taxonomy = get_taxonomy( $term->taxonomy );
		if ( ! $taxonomy || ! $taxonomy->public || ! $taxonomy->publicly_queryable || ! in_array( 'product', $taxonomy->object_type, true ) || ! is_string( $taxonomy->query_var ) ) {
			return $hide;
		}
		$argument_slug = $args[ $taxonomy->query_var ] ?? null;
		if ( 'product' !== ( $args['post_type'] ?? null ) || $term->slug !== $argument_slug || ! in_array( $language, pll_languages_list( array( 'fields' => 'slug' ) ), true ) ) {
			return $hide;
		}
		return false;
	}
}
