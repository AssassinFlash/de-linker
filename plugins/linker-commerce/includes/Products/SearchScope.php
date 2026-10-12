<?php
/**
 * The scope of the site's search results.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * What the site search (the `?s=` results page) may return: products and
 * posts (docs/specs/13-genie.md, the search box of the catalogue; ticket #68).
 *
 * WordPress defaults an unspecified search to every public post type, which
 * would feed pages, templates and other objects into the results. The site
 * the search box lives on (its results page and its catalogue) serves two
 * searchable kinds: the products of the catalogue and the entries of the
 * blog; everything else is reached by navigation.
 *
 * Only the implicit case is scoped — a request that names its own post_type
 * (an explicit product search, an integration) keeps control, as the site's
 * previous search scope did (the newsletter's article-only template).
 */
final class SearchScope {


	/**
	 * The post types the search results may hold.
	 *
	 * @var list<string>
	 */
	public const POST_TYPES = array( 'product', 'post' );

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
