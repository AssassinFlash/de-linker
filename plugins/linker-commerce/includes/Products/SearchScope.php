<?php
/**
 * The scope of the site's search results.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * What the site search (the `?s=` results page) may return: blog posts only
 * (docs/specs/13-genie.md, the search box of the catalogue; ticket #68,
 * narrowed by the 2026-10-14 live recheck, families 17 and 23).
 *
 * WordPress defaults an unspecified search to every public post type. The
 * results page is the blog's article template (Blog / Search, article cards,
 * category chips). Products belong in the catalogue search (`q` and
 * `linker/v1/catalog-search`), not in that template: feeding them in renders
 * product rows as article cards and paginates them. The live site's previous
 * search scope kept the implicit search to posts for the same reason.
 *
 * Only the implicit case is scoped — a request that names its own post_type
 * (an explicit product search, an integration) keeps control.
 */
final class SearchScope {


	/**
	 * The post types the search results may hold.
	 *
	 * One type: the blog post. The catalogue is searched by its own box, not
	 * by `?s=` (2026-10-14 live recheck, families 17 and 23: `?s=PV` is seven
	 * article cards, no product rows, no pagination).
	 *
	 * @var list<string>
	 */
	public const POST_TYPES = array( 'post' );

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
