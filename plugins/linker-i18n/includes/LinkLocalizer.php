<?php
/**
 * Links in German content point at German pages.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

use Linker\I18n\Translation\HtmlToken;
use Linker\I18n\Translation\HtmlTokenizer;

/**
 * Rewrites the site's English links in German HTML to the German pages, when
 * the German is written, not on every view
 * (docs/research/2026-10-09/i18n-opensource-replication.md §1, R10).
 */
final class LinkLocalizer {

	/**
	 * Sets up the localizer.
	 *
	 * @param Languages     $languages The site's languages.
	 * @param HtmlTokenizer $tokenizer The HTML tokenizer.
	 */
	public function __construct( private readonly Languages $languages, private readonly HtmlTokenizer $tokenizer ) {}

	/**
	 * The HTML with the href of every link to an English page that has a
	 * German version replaced by the German page's URL.
	 *
	 * @param string $html HTML.
	 */
	public function localize( string $html ): string {
		if ( ! str_contains( $html, 'href' ) ) {
			return $html;
		}
		$out = '';
		foreach ( $this->tokenizer->tokens( $html ) as $token ) {
			$href = HtmlToken::TAG === $token->type && 'a' === $token->name ? $token->attribute( 'href' ) : null;
			if ( null !== $href ) {
				$german = $this->url( $href );
				if ( $german !== $href ) {
					$out .= $token->with_attribute( 'href', $german );
					continue;
				}
			}
			$out .= $token->raw;
		}
		return $out;
	}

	/**
	 * The German URL of a URL of this site; unchanged when it is external,
	 * already German, or has no German page.
	 *
	 * @param string $url URL, absolute or root-relative.
	 */
	public function url( string $url ): string {
		$parts = wp_parse_url( $url );
		$home  = $this->languages->home_url( Languages::SOURCE );
		if ( ! is_array( $parts ) || ( isset( $parts['scheme'] ) && ! in_array( strtolower( $parts['scheme'] ), array( 'http', 'https' ), true ) ) ) {
			return $url;
		}
		$relative = ! isset( $parts['host'] );
		if ( $relative ? ! str_starts_with( $url, '/' ) || str_starts_with( $url, '//' ) : strtolower( $parts['host'] ) !== strtolower( (string) wp_parse_url( $home, PHP_URL_HOST ) ) ) {
			return $url;
		}
		$path        = $parts['path'] ?? '/';
		$german_home = $this->languages->home_url( Languages::TARGET );
		if ( str_starts_with( trailingslashit( $path ), (string) wp_parse_url( $german_home, PHP_URL_PATH ) ) ) {
			return $url;
		}
		$german = $this->german( $path );
		if ( null === $german ) {
			return $url;
		}
		if ( $relative ) {
			$german = (string) wp_parse_url( $german, PHP_URL_PATH );
		}
		return $german . ( isset( $parts['query'] ) ? '?' . $parts['query'] : '' ) . ( isset( $parts['fragment'] ) ? '#' . $parts['fragment'] : '' );
	}

	/**
	 * The German URL for a path of an English page, product, category or the
	 * home page; null when there is none.
	 *
	 * @param string $path Path.
	 */
	private function german( string $path ): ?string {
		if ( '' === trim( $path, '/' ) ) {
			return $this->languages->home_url( Languages::TARGET );
		}
		$post_id = url_to_postid( home_url( $path ) );
		if ( $post_id > 0 ) {
			$source = $this->languages->source_post( $post_id ) ?? $post_id;
			$twin   = $this->languages->post_translation( $source, Languages::TARGET );
			$link   = null === $twin ? false : get_permalink( $twin );
			return false === $link ? null : $link;
		}
		$segments = explode( '/', trim( $path, '/' ) );
		$base     = trim( (string) wc_get_permalink_structure()['category_rewrite_slug'], '/' );
		if ( count( $segments ) > 1 && $segments[0] === $base ) {
			$terms = get_terms(
				array(
					'taxonomy'   => 'product_cat',
					'slug'       => (string) end( $segments ),
					'lang'       => Languages::SOURCE,
					'hide_empty' => false,
					'number'     => 1,
				)
			);
			$term  = is_array( $terms ) ? reset( $terms ) : false;
			$twin  = $term instanceof \WP_Term ? $this->languages->term_translation( $term->term_id, Languages::TARGET ) : null;
			$link  = null === $twin ? null : get_term_link( $twin, 'product_cat' );
			return is_string( $link ) ? $link : null;
		}
		$shop = (int) get_option( 'woocommerce_shop_page_id' );
		if ( $shop > 0 && trim( $path, '/' ) === get_page_uri( $shop ) ) {
			$twin = $this->languages->post_translation( $shop, Languages::TARGET );
			$link = null === $twin ? false : get_permalink( $twin );
			return false === $link ? null : $link;
		}
		return null;
	}
}
