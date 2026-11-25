<?php
/**
 * The scope of the site's search results.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * The general search is shared by recovery pages and public site navigation.
 * Journal forms explicitly request posts and retain that narrower scope.
 * Search results have separate native LC branches for these two consumers;
 * current product publication remains enforced by Publication\Visibility.
 */
final class SearchScope {


	/** Public pages, products and posts; attachments are not search results. */
	public const POST_TYPES = array( 'post', 'page', 'product' );

	/**
	 * Adds the plugin's hook.
	 */
	public function register(): void {
		add_action( 'pre_get_posts', array( $this, 'scope' ) );
		add_filter( 'posts_search', array( $this, 'include_models' ), 10, 2 );
	}

	/**
	 * Include catalogue SKU/model and rated-power matches in the native results.
	 * The native language, status and publication clauses apply to both sets.
	 *
	 * @param string    $search Native keyword predicate starting with AND.
	 * @param \WP_Query $query  Active query.
	 */
	public function include_models( string $search, \WP_Query $query ): string {
		if ( '' === $search || is_admin() || ! $query->is_main_query() || ! $query->is_search() || ! in_array( 'product', (array) $query->get( 'post_type' ), true ) ) {
			return $search;
		}
		$term = (string) $query->get( 's' );
		if ( ! preg_match( '/[0-9]/', $term ) ) {
			return $search;
		}
		global $wpdb;
		// A power mentioned in the body (for example, a compatible device) is not the product's own rating.
		$native = preg_match( ProductSearch::POWER_QUERY, $term ) ? $search . " AND {$wpdb->posts}.post_type <> 'product'" : $search;
		$ids    = ( new ProductSearch() )->matching_ids( $term, null );
		if ( array() === $ids ) {
			return $native;
		}
		$matches = implode( ',', array_map( 'absint', $ids ) );
		return " AND ((1=1 {$native}) OR ({$wpdb->posts}.ID IN ({$matches}) AND {$wpdb->posts}.post_password = '')) ";
	}

	/**
	 * Narrows a main search query to the searchable post types when the
	 * request did not name any.
	 *
	 * @param \WP_Query $query The running query.
	 */
	public function scope( \WP_Query $query ): void {
		if ( is_admin() || ! $query->is_main_query() || ! $query->is_search() ) {
			return;
		}
		$post_type = $query->get( 'post_type' );
		$implicit  = null === $post_type || '' === $post_type || 'any' === $post_type;
		if ( is_array( $post_type ) ) {
			$implicit = array() === $post_type || in_array( 'any', $post_type, true );
		}
		if ( ! $implicit ) {
			return;
		}
		$query->set( 'post_type', self::POST_TYPES );
	}
}
