<?php
/**
 * Search indexing of the WooCommerce transaction pages and archive URLs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

/** Woo page assignments and their translations own the public URLs. */
final class PageIndexing {
	/** Register the SEOPress and core robots policies. */
	public function register(): void {
		add_filter( 'seopress_titles_noindex_bypass', array( $this, 'noindex' ) );
		add_filter( 'seopress_titles_robots_attrs', array( $this, 'robots' ) );
		add_filter( 'wp_robots', array( $this, 'native_robots' ) );
		add_filter( 'pll_rel_hreflang_attributes', array( $this, 'alternates' ), 50 );
		add_filter( 'seopress_titles_canonical_on_noindex', array( $this, 'canonical' ), 50 );
		add_filter( 'seopress_sitemaps_single_url', array( $this, 'sitemap' ), 20, 2 );
	}

	/**
	 * Keep transactional pages out of the index.
	 *
	 * @param mixed $value Current SEOPress indexing decision.
	 * @return mixed
	 */
	public function noindex( mixed $value ): mixed {
		return $this->transaction() ? '1' : $value;
	}

	/**
	 * Set the SEOPress transaction directives.
	 *
	 * @param string[] $robots SEOPress directives.
	 * @return string[]
	 */
	public function robots( array $robots ): array {
		return $this->transaction() ? array_values( array_unique( array_merge( array_diff( $robots, array( 'index', 'nofollow' ) ), array( 'noindex', 'follow' ) ) ) ) : $robots;
	}

	/**
	 * Use the core directives when WordPress owns the robots tag.
	 *
	 * @param array<string,mixed> $robots Core directives.
	 * @return array<string,mixed>
	 */
	public function native_robots( array $robots ): array {
		if ( ! function_exists( 'seopress_get_service' ) && $this->transaction() ) {
			unset( $robots['index'], $robots['nofollow'] );
			$robots['noindex'] = true;
			$robots['follow']  = true;
		}
		return $robots;
	}

	/**
	 * Omit alternate index URLs for private workspaces.
	 *
	 * @param array<string,string> $links Language alternates.
	 * @return array<string,string>
	 */
	public function alternates( array $links ): array {
		return $this->transaction() ? array() : $links;
	}

	/**
	 * Leave transactional pages without a canonical link.
	 *
	 * @param bool $allow Canonical on noindex.
	 */
	public function canonical( bool $allow ): bool {
		return $allow && ! $this->transaction();
	}

	/**
	 * The post and product sitemaps already emit both archive translations.
	 *
	 * @param mixed $url Existing URL element.
	 * @param mixed $post Sitemap post.
	 * @return mixed
	 */
	public function sitemap( mixed $url, mixed $post ): mixed {
		if ( ! $post instanceof \WP_Post || 'page' !== $post->post_type ) {
			return $url;
		}
		$id = $this->source( $post->ID );
		return $this->transaction_id( $id ) || in_array( $id, array( (int) get_option( 'page_for_posts' ), (int) get_option( 'woocommerce_shop_page_id' ) ), true ) ? null : $url;
	}

	/** The Woo endpoint's queried object remains the assigned page. */
	private function transaction(): bool {
		$post = get_queried_object();
		return $post instanceof \WP_Post && 'page' === $post->post_type && $this->transaction_id( $this->source( $post->ID ) );
	}

	/**
	 * Resolve the assigned English page for a translated post.
	 *
	 * @param int $id Queried page ID.
	 */
	private function source( int $id ): int {
		$source = function_exists( 'pll_get_post' ) ? (int) pll_get_post( $id, 'en' ) : 0;
		return $source > 0 ? $source : $id;
	}

	/**
	 * Match one of the three native WooCommerce page assignments.
	 *
	 * @param int $id Source page ID.
	 */
	private function transaction_id( int $id ): bool {
		return in_array( $id, array( (int) get_option( 'woocommerce_cart_page_id' ), (int) get_option( 'woocommerce_myaccount_page_id' ), (int) get_option( 'woocommerce_checkout_page_id' ) ), true );
	}
}
