<?php
/**
 * Public responses for RSS feeds and media attachment pages.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

/** Keep editorial feeds readable and point media pages at their published owner. */
final class CrawlHygiene {
	/** Resolve after the site's retired aliases and before core attachment handling. */
	public function register(): void {
		add_filter( 'robots_txt', array( $this, 'robots_txt' ), 99, 2 );
		add_filter( 'wp_headers', array( $this, 'headers' ) );
		add_action( 'template_redirect', array( $this, 'respond' ), 2 );
	}

	/**
	 * Extend the site's first wildcard group without changing named crawler groups.
	 *
	 * @param string $text WordPress or SEOPress virtual robots.txt.
	 * @param bool   $visible Site visibility.
	 */
	public function robots_txt( string $text, bool $visible ): string {
		if ( ! $visible ) {
			return $text;
		}
		$lines = explode( "\n", $text );
		$at    = null;
		foreach ( $lines as $i => $line ) {
			if ( 0 === strcasecmp( trim( $line ), 'User-agent: *' ) ) {
				$at = $i + 1;
				break;
			}
		}
		if ( null === $at ) {
			$lines[] = 'User-agent: *';
			$at      = count( $lines );
		}
		$existing = array();
		foreach ( array_slice( $lines, $at ) as $line ) {
			if ( str_starts_with( strtolower( ltrim( $line ) ), 'user-agent:' ) ) {
				break;
			}
			$existing[] = trim( $line );
		}
		$rules = array();
		foreach ( array( 'redirect_to', 'intent', 'linker_contact_selection', 'wc-ajax' ) as $key ) {
			$rules[] = 'Disallow: /*?' . $key . '=';
			$rules[] = 'Disallow: /*?*' . $key . '=';
		}
		array_splice( $lines, $at, 0, array_diff( $rules, $existing ) );
		return implode( "\n", $lines );
	}

	/**
	 * Keep all feeds out of the search index.
	 *
	 * @param array<string,string|false> $headers Native HTTP headers.
	 * @return array<string,string|false>
	 */
	public function headers( array $headers ): array {
		// WP::send_headers() can end a conditional feed request with 304 before template_redirect.
		$trap = $this->retired_query();
		if ( $trap || $this->retired_feed() ) {
			status_header( 410 );
			header( $trap ? 'X-Robots-Tag: noindex' : 'X-Robots-Tag: noindex, follow' );
			header( 'Content-Type: text/plain; charset=utf-8' );
			header( 'Cache-Control: public, max-age=3600' );
			echo 'Gone';
			exit;
		}
		if ( is_feed() ) {
			$headers['X-Robots-Tag'] = 'noindex, follow';
		}
		return $headers;
	}

	/** Retired search, placeholder and malformed catalogue URLs on public reads. */
	private function retired_query(): bool {
		// phpcs:disable WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- Classify public read-only requests; inputs are never rendered.
		if ( empty( $_GET ) || ! in_array( $_SERVER['REQUEST_METHOD'] ?? 'GET', array( 'GET', 'HEAD' ), true ) || is_admin() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ) ) {
			return false;
		}
		// Woo marks even this unexpanded template placeholder as DOING_AJAX on init.
		if ( '%%endpoint%%' === ( $_GET['wc-ajax'] ?? null ) ) {
			return true;
		}
		if ( wp_doing_ajax() ) {
			return false;
		}
		if ( array_key_exists( 's', $_GET ) && 'product' === ( $_GET['post_type'] ?? null ) ) {
			return true;
		}
		foreach ( array( 'phase', 'power', 'brand', 'application' ) as $facet ) {
			$value = $_GET[ $facet ] ?? '';
			if ( ! is_string( $value ) || ! str_contains( $value, ',' ) ) {
				continue;
			}
			$tokens = array_diff( array_map( 'trim', explode( ',', $value ) ), array( '' ) );
			if ( count( $tokens ) !== count( array_unique( $tokens ) ) ) {
				return is_shop() || is_product_taxonomy();
			}
		}
		// phpcs:enable
		return false;
	}

	/** Whether this request is for a retired commerce or comments feed. */
	private function retired_feed(): bool {
		return is_feed() && ( is_comment_feed() || is_post_type_archive( 'product' ) || is_tax( array( 'product_cat', 'product_brand' ) ) || is_singular( 'product' ) );
	}

	/**
	 * Resolve an attachment's published and publicly queryable owner.
	 *
	 * @param \WP_Post $attachment Queried media item.
	 */
	public function attachment_parent( \WP_Post $attachment ): ?string {
		if ( ! $attachment->post_parent ) {
			return null;
		}
		$parent = get_post( $attachment->post_parent );
		if ( ! $parent instanceof \WP_Post || 'publish' !== $parent->post_status || ! is_post_publicly_viewable( $parent ) ) {
			return null;
		}
		$url = get_permalink( $parent );
		return $url ? trailingslashit( $url ) : null;
	}

	/** Media pages without a public parent render the site's 404. */
	public function respond(): void {
		if ( ! is_attachment() ) {
			return;
		}
		$post   = get_queried_object();
		$target = $post instanceof \WP_Post ? $this->attachment_parent( $post ) : null;
		if ( null !== $target && wp_safe_redirect( $target, 301 ) ) {
			exit;
		}
		global $wp_query;
		$wp_query->set_404();
		remove_action( 'template_redirect', 'redirect_canonical' );
		status_header( 404 );
		nocache_headers();
	}
}
