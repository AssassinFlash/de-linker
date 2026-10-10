<?php
/**
 * Finding a page or product by slug in the right language.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\SameSlug;

use Linker\I18n\Languages;

/**
 * Resolves a slug to the post of the requested language.
 *
 * `get_page_by_path()` does not know languages: with /compare-products/ and
 * /de/compare-products/ sharing a slug it answers with whichever page the
 * database returns first. WordPress uses it for every page URL and the
 * Store API for /wc/store/v1/products/<slug>
 * (docs/research/2026-10-09/i18n-opensource-replication.md §5.3, §6.1).
 */
final class Lookup {

	/**
	 * Sets up the lookups.
	 *
	 * @param Languages $languages The site's languages.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/**
	 * Turns the slug of a request into the post of the URL's language
	 * (filter `request`): a page path, a product (`product=<slug>`) or a post
	 * (`name=<slug>`). WordPress drops taxonomy conditions, and so the
	 * language, from queries for a single post, and finds the first post with
	 * the slug. A slug that only names a post of the other language is a 404:
	 * /de/about/ is not a German address.
	 *
	 * @param array<string, mixed> $vars Query variables of the request.
	 * @return array<string, mixed>
	 */
	public function request( array $vars ): array {
		$language = isset( $vars['lang'] ) && is_string( $vars['lang'] ) && '' !== $vars['lang'] ? $vars['lang'] : $this->languages->current();
		if ( ! empty( $vars['pagename'] ) && is_string( $vars['pagename'] ) ) {
			$page_id = $this->page( $vars['pagename'], $language );
			if ( null !== $page_id ) {
				unset( $vars['pagename'] );
				$vars['page_id'] = $page_id;
				return $vars;
			}
			$elsewhere = get_page_by_path( $vars['pagename'] );
			if ( $elsewhere instanceof \WP_Post && $this->languages->translates_post_type( $elsewhere->post_type ) ) {
				$vars['error'] = '404';
			}
			return $vars;
		}
		foreach ( $this->slug_vars( $vars ) as $post_type => $var ) {
			$slug = sanitize_title( (string) $vars[ $var ] );
			$id   = $this->post( $post_type, $slug, $language );
			if ( null !== $id ) {
				unset( $vars[ $var ] );
				$vars['p']         = $id;
				$vars['post_type'] = $post_type;
			} elseif ( null !== $this->post( $post_type, $slug, '' ) ) {
				$vars['error'] = '404';
			}
			return $vars;
		}
		return $vars;
	}

	/**
	 * The query variables of the request that name a post of a translated
	 * type by its slug.
	 *
	 * @param array<string, mixed> $vars Query variables.
	 * @return array<string, string> Post type => query variable.
	 */
	private function slug_vars( array $vars ): array {
		$found = array();
		if ( ! empty( $vars['name'] ) && is_string( $vars['name'] ) ) {
			$post_type = isset( $vars['post_type'] ) && is_string( $vars['post_type'] ) ? $vars['post_type'] : 'post';
			if ( $this->languages->translates_post_type( $post_type ) ) {
				$found[ $post_type ] = 'name';
			}
		}
		foreach ( get_post_types( array( 'publicly_queryable' => true ), 'objects' ) as $post_type => $object ) {
			$var = is_string( $object->query_var ) ? $object->query_var : '';
			if ( '' !== $var && 'post' !== $post_type && ! empty( $vars[ $var ] ) && is_string( $vars[ $var ] ) && $this->languages->translates_post_type( $post_type ) ) {
				$found[ $post_type ] = $var;
			}
		}
		return $found;
	}

	/**
	 * Answers /wc/store/v1/products/<slug> with the product of the requested
	 * language (filter `rest_dispatch_request`, which runs once the route is
	 * matched): the request is answered as the same request by ID, so the
	 * response is WooCommerce's own.
	 *
	 * @param mixed            $result  Response from an earlier filter, null to dispatch.
	 * @param \WP_REST_Request $request Request.
	 * @param string           $route   The matched route's pattern.
	 * @return mixed
	 *
	 * @phpstan-param \WP_REST_Request<array<string, mixed>> $request
	 */
	public function store_product( $result, \WP_REST_Request $request, string $route ) {
		if ( null !== $result || 1 !== preg_match( '#^/wc/store(?:/v1)?/products/\(\?P<slug>#', $route ) ) {
			return $result;
		}
		$product_id = $this->post( 'product', sanitize_title( (string) $request['slug'] ), $this->languages->current() );
		if ( null === $product_id ) {
			return new \WP_Error( 'woocommerce_rest_product_invalid_slug', __( 'Invalid product slug.', 'linker-i18n' ), array( 'status' => 404 ) );
		}
		$by_id = new \WP_REST_Request( 'GET', '/wc/store/v1/products/' . $product_id );
		$by_id->set_query_params( $request->get_query_params() );
		return rest_do_request( $by_id );
	}

	/**
	 * The page at a path (parent/child) in a language.
	 *
	 * @param string $path     Page path.
	 * @param string $language Language slug.
	 */
	public function page( string $path, string $language ): ?int {
		$parent  = 0;
		$page_id = null;
		foreach ( explode( '/', trim( $path, '/' ) ) as $segment ) {
			$page_id = $this->post( 'page', sanitize_title_for_query( $segment ), $language, $parent );
			if ( null === $page_id ) {
				return null;
			}
			$parent = $page_id;
		}
		return $page_id;
	}

	/**
	 * A post by slug in a language ('' for any language).
	 *
	 * @param string   $post_type Post type.
	 * @param string   $slug      Slug.
	 * @param string   $language  Language slug, '' for any.
	 * @param int|null $parent_id Parent post ID, null for any.
	 */
	private function post( string $post_type, string $slug, string $language, ?int $parent_id = null ): ?int {
		if ( '' === $slug ) {
			return null;
		}
		// post_name__in, not name: a query for one post by name is singular, and
		// WordPress ignores taxonomy conditions (the language) for singular queries.
		$query = array(
			'post_type'              => $post_type,
			'post_name__in'          => array( $slug ),
			'lang'                   => $language,
			'post_status'            => array( 'publish', 'private', 'future', 'draft', 'pending' ),
			'fields'                 => 'ids',
			'numberposts'            => 1,
			'orderby'                => 'ID',
			'order'                  => 'ASC',
			'no_found_rows'          => true,
			'suppress_filters'       => false,
			'update_post_meta_cache' => false,
			'update_post_term_cache' => false,
		);
		if ( null !== $parent_id ) {
			$query['post_parent'] = $parent_id;
		}
		$ids = get_posts( $query );
		return array() === $ids ? null : (int) $ids[0];
	}
}
