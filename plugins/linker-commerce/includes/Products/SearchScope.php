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
