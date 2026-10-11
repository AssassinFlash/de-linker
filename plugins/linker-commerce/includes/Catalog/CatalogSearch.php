<?php
/**
 * The catalogue search: what the search box of the product pages resolves.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Catalog;

use WC_Product;

/**
 * One reader of "which products did the visitor type": the search box of the
 * catalogue (ticket #68) and the archive's `q` filter (docs/specs/12-site-chrome.md
 * item 5) ask the same rule, so the instant resolution of a model or item
 * number and the filtered archive can never disagree.
 *
 * The rule is the one the catalogue serves today: the model or item number,
 * reduced to letters and digits, is looked up in the product's name and SKU
 * the same way. The products are the published, catalogue-visible ones — a
 * product set to WooCommerce's "hidden" visibility is not enumerable here,
 * the same way the shop and the native search do not show it (a secondary
 * query runs without WooCommerce's main-query visibility filter).
 *
 * The facts of each hit come from SelectionFacts, the one layer of what a
 * product is (#7): the search answers with the same facts the catalogue
 * shows, never with a second reading.
 */
final class CatalogSearch {


	/**
	 * Most hits one request answers with.
	 */
	public const MAX_LIMIT = 12;

	/**
	 * Hits per request when the caller names none (the old catalogue's 8).
	 */
	public const DEFAULT_LIMIT = 8;

	/**
	 * Shortest query that is looked up (the old catalogue's two characters).
	 */
	public const MIN_LENGTH = 2;

	/**
	 * The published, catalogue-visible products whose name or SKU holds the
	 * query, in the catalogue's own order, at most $limit of them.
	 *
	 * @param  string $query What the visitor typed.
	 * @param  int    $limit Most hits, 1 to MAX_LIMIT.
	 * @return list<int> Product IDs.
	 */
	public function matching_ids( string $query, int $limit = self::DEFAULT_LIMIT ): array {
		$needle = self::normalize( $query );
		if ( strlen( $needle ) < self::MIN_LENGTH ) {
			return array();
		}
		$limit = max( 1, min( self::MAX_LIMIT, $limit ) );
		$facts = array();
		foreach ( $this->catalogue_ids() as $product_id ) {
			$product = wc_get_product( $product_id );
			if ( $product instanceof WC_Product && self::matches( $product, $needle ) ) {
				$facts[] = $product_id;
				if ( count( $facts ) >= $limit ) {
					break;
				}
			}
		}
		return $facts;
	}

	/**
	 * The catalogue's published, visible products, in the catalogue's order.
	 *
	 * @return list<int>
	 */
	private function catalogue_ids(): array {
		$hidden = array();
		if ( function_exists( 'wc_get_product_visibility_term_ids' ) ) {
			$terms  = wc_get_product_visibility_term_ids();
			$hidden = array_filter(
				array( (int) ( $terms['exclude-from-search'] ?? 0 ), (int) ( $terms['exclude-from-catalog'] ?? 0 ) ),
				static fn( int $term_id ): bool => $term_id > 0
			);
		}
		$args = array(
			'post_type'      => 'product',
			'post_status'    => 'publish',
			'posts_per_page' => -1,
			'fields'         => 'ids',
			'orderby'        => 'menu_order title',
			'order'          => 'ASC',
		);
		if ( array() !== $hidden ) {
         // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- one query per search request, the same exclusion WooCommerce's own product visibility applies.
			$args['tax_query'] = array(
				array(
					'taxonomy' => 'product_visibility',
					'field'    => 'term_taxonomy_id',
					'terms'    => array_values( $hidden ),
					'operator' => 'NOT IN',
				),
			);
		}
		/** The product IDs, in the catalogue's order.
		 *
		 * @var list<int> $ids
		 */
		$ids = get_posts( $args );
		return $ids;
	}

	/**
	 * The query as it is compared: lower case, without the separators model
	 * and item numbers alternate between ("GW60K-STS-G10" and "gw60k sts g10"
	 * are the same number).
	 *
	 * @param string $text The raw text.
	 */
	public static function normalize( string $text ): string {
		return \mb_strtolower( \str_replace( array( '-', ' ', '.', '/' ), '', $text ) );
	}

	/**
	 * Whether one product's name or SKU holds the normalized query.
	 *
	 * @param WC_Product $product The product.
	 * @param string     $needle  The normalized query.
	 */
	public static function matches( WC_Product $product, string $needle ): bool {
		if ( '' === $needle ) {
			return false;
		}
		return \str_contains( self::normalize( $product->get_name() . ' ' . $product->get_sku() ), $needle );
	}

	/**
	 * One hit as the search box reads it: the product, the way to it, and the
	 * selection facts of the catalogue's data layer. No price: the endpoint is
	 * anonymous and cacheable, and a price belongs behind the login gate
	 * (docs/specs/11-commerce.md, Gating).
	 *
	 * @param  int $product_id Product ID.
	 * @return array{id: int, title: string, sku: string, url: string, facts: array<string, mixed>}
	 */
	public function payload( int $product_id ): array {
		$product = wc_get_product( $product_id );
		return array(
			'id'    => $product_id,
			'title' => $product instanceof WC_Product ? $product->get_name() : get_the_title( $product_id ),
			'sku'   => $product instanceof WC_Product ? (string) $product->get_sku() : '',
			'url'   => (string) get_permalink( $product_id ),
			'facts' => SelectionFacts::for_product( $product_id )->to_array(),
		);
	}
}
