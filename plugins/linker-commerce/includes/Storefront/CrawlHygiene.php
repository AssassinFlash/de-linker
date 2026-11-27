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
		add_filter( 'wp_headers', array( $this, 'headers' ) );
		add_action( 'template_redirect', array( $this, 'respond' ), 2 );
	}

	/**
	 * Keep all feeds out of the search index.
	 *
	 * @param array<string,string|false> $headers Native HTTP headers.
	 * @return array<string,string|false>
	 */
	public function headers( array $headers ): array {
		// WP::send_headers() can end a conditional feed request with 304 before template_redirect.
		if ( $this->retired_feed() ) {
			status_header( 410 );
			header( 'X-Robots-Tag: noindex, follow' );
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
