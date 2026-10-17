<?php
/**
 * The page a Genie turn comes from (ticket #234).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * What page the visitor is on: its type, address and title, and the IDs of
 * what it shows. The dock prints it into its mount, the app sends it with
 * every turn, the proxy checks it, and the Genie service reads the page's
 * content from it (services/genie/src/linker_genie/page.py). The preview
 * card names the page from it (Preview).
 *
 * Eight kinds of page (docs/specs/13-genie.md, 目标 3): the home page, a
 * product, a product category, a solution or other marketing page, the blog,
 * the FAQ and documents page, the solution draft and the account. Every other
 * page — contact, the legal pages, the Proforma request, the tools — is
 * `other`; Genie still reads its address.
 */
final class PageContext {

	/**
	 * The page types the service accepts (schema.py `PageType`).
	 */
	public const TYPES = array( 'home', 'product', 'category', 'solution', 'blog', 'faq', 'draft', 'account', 'other' );

	/**
	 * The English paths whose pages, and their children, are the solution and
	 * marketing pages: the solution hub and its three solutions, About and
	 * Capability, the two audience pages and Services & Support (the page
	 * list of de-linker.com, read 2026-10-18). German pages are matched
	 * through their English twin.
	 */
	private const SOLUTION_PATHS = array( 'solution', 'about', 'for-epc', 'for-installer', 'services-support' );

	/**
	 * The English path of the FAQ and documents page.
	 */
	private const FAQ_PATH = 'faq-download';

	/**
	 * The longest title the service accepts (schema.py `PageContext.title`).
	 */
	private const TITLE_LENGTH = 300;

	/**
	 * The longest address the service accepts (schema.py `PageContext.url`).
	 */
	private const URL_LENGTH = 2048;

	/**
	 * The page of the current request.
	 *
	 * @return array{type: string, url: string, title: string, product_id?: int, post_id?: int, category_id?: int}
	 */
	public function current(): array {
		$id             = (int) get_queried_object_id();
		$context        = $this->classify( $id );
		$context['url'] = $this->url();
		return $context;
	}

	/**
	 * Type, title and IDs of the current request's page.
	 *
	 * @param int $id The queried object: a post, a page or a term.
	 * @return array{type: string, title: string, product_id?: int, post_id?: int, category_id?: int}
	 */
	private function classify( int $id ): array {
		if ( is_front_page() ) {
			return array(
				'type'    => 'home',
				'title'   => $this->plain( (string) get_the_title( $id ) ),
				'post_id' => $id,
			);
		}
		if ( function_exists( 'is_product' ) && is_product() ) {
			// The turn's product IDs are the English posts (the service's
			// search-products IDs); the page shows its own language's post.
			return array(
				'type'       => 'product',
				'title'      => $this->plain( (string) get_the_title( $id ) ),
				'product_id' => $this->english( $id ),
				'post_id'    => $id,
			);
		}
		if ( function_exists( 'is_product_category' ) && is_product_category() ) {
			return array(
				'type'        => 'category',
				'title'       => $this->plain( (string) single_term_title( '', false ) ),
				'category_id' => $id,
			);
		}
		if ( function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() ) ) {
			return array(
				'type'  => 'category',
				'title' => $this->plain( (string) get_the_title( (int) wc_get_page_id( 'shop' ) ) ),
			);
		}
		if ( function_exists( 'is_cart' ) && is_cart() ) {
			return array(
				'type'  => 'draft',
				'title' => $this->plain( (string) get_the_title( $id ) ),
			);
		}
		if ( function_exists( 'is_account_page' ) && is_account_page() ) {
			return array(
				'type'  => 'account',
				'title' => $this->plain( (string) get_the_title( $id ) ),
			);
		}
		if ( is_singular( 'post' ) ) {
			return array(
				'type'    => 'blog',
				'title'   => $this->plain( (string) get_the_title( $id ) ),
				'post_id' => $id,
			);
		}
		if ( is_home() || is_category() || is_tag() ) {
			$title = is_home() ? get_the_title( (int) get_option( 'page_for_posts' ) ) : single_term_title( '', false );
			return array(
				'type'  => 'blog',
				'title' => $this->plain( (string) $title ),
			);
		}
		if ( is_page() ) {
			return array(
				'type'    => $this->page_type( $id ),
				'title'   => $this->plain( (string) get_the_title( $id ) ),
				'post_id' => $id,
			);
		}
		return array(
			'type'  => 'other',
			'title' => $this->plain( (string) wp_get_document_title() ),
		);
	}

	/**
	 * `solution`, `faq` or `other` for a page, by its English path's first
	 * segment.
	 *
	 * @param int $id The page.
	 */
	private function page_type( int $id ): string {
		$path  = (string) get_page_uri( $this->english( $id ) );
		$first = strtok( $path, '/' );
		if ( self::FAQ_PATH === $first ) {
			return 'faq';
		}
		if ( in_array( $first, self::SOLUTION_PATHS, true ) ) {
			return 'solution';
		}
		return 'other';
	}

	/**
	 * The English twin of a post, or the post itself without a twin or a
	 * language layer.
	 *
	 * @param int $id A post or page.
	 */
	private function english( int $id ): int {
		if ( ! function_exists( 'pll_get_post' ) ) {
			return $id;
		}
		$twin = (int) pll_get_post( $id, 'en' );
		return $twin > 0 ? $twin : $id;
	}

	/**
	 * The request's own address on this site: the site's scheme and host
	 * (the raw `home` option — the language layer rewrites `home_url()` per
	 * language) and the requested path, without its query.
	 */
	private function url(): string {
		$uri    = isset( $_SERVER['REQUEST_URI'] ) ? esc_url_raw( wp_unslash( (string) $_SERVER['REQUEST_URI'] ) ) : '/';
		$path   = (string) wp_parse_url( $uri, PHP_URL_PATH );
		$home   = wp_parse_url( (string) get_option( 'home' ) );
		$home   = is_array( $home ) ? $home : array();
		$origin = ( $home['scheme'] ?? 'https' ) . '://' . ( $home['host'] ?? '' ) . ( isset( $home['port'] ) ? ':' . $home['port'] : '' );
		return mb_substr( $origin . ( '' !== $path ? $path : '/' ), 0, self::URL_LENGTH );
	}

	/**
	 * A title as plain text: WordPress keeps titles entity-encoded
	 * ("EMS &amp; Monitoring").
	 *
	 * @param string $title A post title or term name.
	 */
	public function plain( string $title ): string {
		$text = trim( html_entity_decode( wp_strip_all_tags( $title ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
		return mb_substr( $text, 0, self::TITLE_LENGTH );
	}

	/**
	 * The page context a browser sent, as the service accepts it: the known
	 * keys with their types, nothing else. A solution draft's products are
	 * never the browser's: the proxy reads them from the visitor's own draft
	 * (`draft_ids()`).
	 *
	 * @param mixed $raw The `page` parameter of a turn.
	 * @return array{type: string, url?: string, title?: string, product_id?: int, post_id?: int, category_id?: int}
	 */
	public function sanitize( $raw ): array {
		$raw  = is_array( $raw ) ? $raw : array();
		$type = isset( $raw['type'] ) && in_array( $raw['type'], self::TYPES, true ) ? (string) $raw['type'] : 'other';
		$page = array( 'type' => $type );
		foreach ( array( 'product_id', 'post_id', 'category_id' ) as $key ) {
			$value = isset( $raw[ $key ] ) && is_numeric( $raw[ $key ] ) ? (int) $raw[ $key ] : 0;
			if ( $value > 0 ) {
				$page[ $key ] = $value;
			}
		}
		if ( isset( $raw['url'] ) && is_string( $raw['url'] ) ) {
			$url = esc_url_raw( mb_substr( $raw['url'], 0, self::URL_LENGTH ) );
			if ( '' !== $url ) {
				$page['url'] = $url;
			}
		}
		if ( isset( $raw['title'] ) && is_string( $raw['title'] ) ) {
			$title = mb_substr( sanitize_text_field( $raw['title'] ), 0, self::TITLE_LENGTH );
			if ( '' !== $title ) {
				$page['title'] = $title;
			}
		}
		return $page;
	}

	/**
	 * The products of the visitor's solution draft, as English posts.
	 *
	 * REST requests start without WooCommerce's session; `wc_load_cart()`
	 * loads it from the visitor's cookie (the saved-solutions precedent in
	 * linker-commerce).
	 *
	 * @return list<int>
	 */
	public function draft_ids(): array {
		if ( ! function_exists( 'wc_load_cart' ) || ! function_exists( 'WC' ) ) {
			return array();
		}
		wc_load_cart();
		$ids = array();
		foreach ( WC()->cart->get_cart() as $line ) {
			$id = (int) ( $line['product_id'] ?? 0 );
			if ( $id > 0 ) {
				$ids[] = $this->english( $id );
			}
		}
		return array_values( array_unique( $ids ) );
	}
}
