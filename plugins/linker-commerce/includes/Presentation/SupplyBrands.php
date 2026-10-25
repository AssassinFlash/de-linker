<?php
/**
 * Current Woo supply names for sentence fragments owned by LiveCanvas.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Products\Publication;

/** Aggregate native product attributes without reading technical documents. */
final class SupplyBrands {
	/** Register the data fragment; LC retains its words, markup and styling. */
	public function register(): void {
		add_shortcode( 'linker_supply_brands', array( $this, 'render' ) );
	}

	/**
	 * Names belonging to currently published sales products in these branches.
	 *
	 * @param array<string,string>|string $atts LC sentence and category scope.
	 */
	public function render( $atts = array() ): string {
		$atts       = shortcode_atts(
			array(
				'categories'  => '',
				'prefix'      => '',
				'suffix'      => '',
				'conjunction' => 'and',
			),
			is_array( $atts ) ? $atts : array(),
			'linker_supply_brands'
		);
		$categories = array_values( array_filter( array_map( 'sanitize_title', explode( ',', $atts['categories'] ) ) ) );
		if ( array() === $categories ) {
			return '';
		}
		$ids = array_values( array_filter( Publication::published_ids( fn (): array => $this->candidate_ids( $categories ) ), static fn ( int $id ): bool => ! EngineeringReference::is_reference( $id ) ) );
		if ( array() === $ids ) {
			return '';
		}
		$names = get_terms(
			array(
				'taxonomy'   => 'pa_brand',
				'object_ids' => $ids,
				'fields'     => 'names',
				'hide_empty' => false,
				'orderby'    => 'name',
				'order'      => 'ASC',
			)
		);
		if ( ! is_array( $names ) || array() === $names ) {
			return '';
		}
		$names = array_values( array_unique( array_filter( array_map( 'trim', $names ) ) ) );
		if ( array() === $names ) {
			return '';
		}
		$last = array_pop( $names );
		$list = array() === $names ? $last : implode( ', ', $names ) . ' ' . $atts['conjunction'] . ' ' . $last;
		return esc_html( $atts['prefix'] . $list . $atts['suffix'] );
	}

	/**
	 * Read native candidates only inside Publication's freshly opened batch.
	 *
	 * Visibility term names are Woo's own identifiers. Resolve them natively,
	 * without wc_get_product_visibility_term_ids()'s unflushable static ID map.
	 *
	 * @param string[] $categories Native category branches.
	 * @return int[]
	 */
	private function candidate_ids( array $categories ): array {
		// Resolve outside WP_Tax_Query: Polylang otherwise scopes its internal
		// English-slug lookup to the active German frontend language.
		$terms = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'slug'       => $categories,
				'fields'     => 'ids',
				'hide_empty' => false,
				'lang'       => '',
			)
		);
		if ( ! is_array( $terms ) || array() === $terms ) {
			return array();
		}
		$tax_query = array(
			array(
				'taxonomy'         => 'product_cat',
				'field'            => 'term_id',
				'terms'            => array_map( 'intval', $terms ),
				'include_children' => true,
			),
		);
		$hidden    = array( 'exclude-from-catalog' );
		if ( 'yes' === get_option( 'woocommerce_hide_out_of_stock_items' ) ) {
			$hidden[] = 'outofstock';
		}
		$tax_query[] = array(
			'taxonomy' => 'product_visibility',
			'field'    => 'name',
			'terms'    => $hidden,
			'operator' => 'NOT IN',
		);
		$ids         = get_posts(
			array(
				'post_type'                   => 'product',
				'post_status'                 => 'publish',
				'fields'                      => 'ids',
				'posts_per_page'              => -1,
				'suppress_filters'            => true,
				'lang'                        => '',
				'linker_publication_internal' => true,
				'cache_results'               => false,
				'tax_query'                   => $tax_query, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- the native category/visibility intersection, one query per fragment.
			)
		);
		return array_map( 'intval', $ids );
	}
}
