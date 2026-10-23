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
		$tax_query  = array(
			array(
				'taxonomy'         => 'product_cat',
				'field'            => 'slug',
				'terms'            => $categories,
				'include_children' => true,
			),
		);
		$visibility = wc_get_product_visibility_term_ids();
		$hidden     = array( (int) ( $visibility['exclude-from-catalog'] ?? 0 ) );
		if ( 'yes' === get_option( 'woocommerce_hide_out_of_stock_items' ) ) {
			$hidden[] = (int) ( $visibility['outofstock'] ?? 0 );
		}
		$hidden = array_filter( $hidden );
		if ( array() !== $hidden ) {
			$tax_query[] = array(
				'taxonomy' => 'product_visibility',
				'field'    => 'term_taxonomy_id',
				'terms'    => $hidden,
				'operator' => 'NOT IN',
			);
		}
		$ids = get_posts(
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
		$ids = array_values( array_filter( Publication::published_ids( array_map( 'intval', $ids ) ), static fn ( int $id ): bool => ! EngineeringReference::is_reference( $id ) ) );
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
}
