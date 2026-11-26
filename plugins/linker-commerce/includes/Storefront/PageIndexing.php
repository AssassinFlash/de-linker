<?php
/**
 * Search indexing of the WooCommerce transaction pages and archive URLs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\ComparePage;

/** Woo page assignments and their translations own the public URLs. */
final class PageIndexing {
	/** Register the SEOPress and core robots policies. */
	public function register(): void {
		add_filter( 'seopress_titles_desc', array( $this, 'description' ), 45 );
		add_filter( 'seopress_titles_noindex_bypass', array( $this, 'noindex' ) );
		add_filter( 'seopress_titles_robots_attrs', array( $this, 'robots' ) );
		add_filter( 'wp_headers', array( $this, 'headers' ) );
		add_filter( 'wp_robots', array( $this, 'native_robots' ) );
		add_filter( 'pll_rel_hreflang_attributes', array( $this, 'alternates' ), 50 );
		add_filter( 'seopress_titles_canonical_on_noindex', array( $this, 'canonical' ), 50 );
		add_filter( 'seopress_titles_canonical', array( $this, 'canonical_tag' ), 20 );
		add_filter( 'seopress_sitemaps_single_url', array( $this, 'sitemap' ), 20, 2 );
	}

	/**
	 * Supply missing discovery descriptions. SEOPress also uses these for Open Graph.
	 *
	 * @param string $existing Existing expanded description.
	 */
	public function description( string $existing ): string {
		if ( '' !== trim( $existing ) ) {
			return $existing;
		}
		if ( ComparePage::is_comparison_page() ) {
			return __( 'Compare hybrid inverters, battery storage systems and accessories side by side by AC power, usable capacity, phase and manufacturer datasheets.', 'linker-commerce' );
		}
		$term = get_queried_object();
		if ( ! $term instanceof \WP_Term || 'category' !== $term->taxonomy ) {
			return $existing;
		}
		if ( in_array( $term->slug, array( 'monitoring-energy-management', 'ueberwachung-energiemanagement' ), true ) ) {
			return __( 'Read about monitoring solar and storage systems, using meter data and managing energy flows. Find practical guidance for installers working on site.', 'linker-commerce' );
		}
		/* translators: %s: translated blog category name. */
		return sprintf( __( 'Explore %s in the Linker journal. Read practical guidance on solar and storage projects for installers.', 'linker-commerce' ), wp_strip_all_tags( $term->name ) );
	}

	/**
	 * Keep private pages and temporary archive views out of the index.
	 *
	 * @param mixed $value Current SEOPress indexing decision.
	 * @return mixed
	 */
	public function noindex( mixed $value ): mixed {
		return $this->excluded() ? '1' : $value;
	}

	/**
	 * Set the SEOPress robots directives.
	 *
	 * @param string[] $robots SEOPress directives.
	 * @return string[]
	 */
	public function robots( array $robots ): array {
		return $this->excluded() ? array_values( array_unique( array_merge( array_diff( $robots, array( 'index', 'nofollow' ) ), array( 'noindex', 'follow' ) ) ) ) : $robots;
	}

	/**
	 * Use the core directives when WordPress owns the robots tag.
	 *
	 * @param array<string,mixed> $robots Core directives.
	 * @return array<string,mixed>
	 */
	public function native_robots( array $robots ): array {
		if ( ! function_exists( 'seopress_get_service' ) && $this->excluded() ) {
			unset( $robots['index'], $robots['nofollow'] );
			$robots['noindex'] = true;
			$robots['follow']  = true;
		}
		return $robots;
	}

	/**
	 * Omit language alternates on pages excluded from indexing.
	 *
	 * @param array<string,string> $links Language alternates.
	 * @return array<string,string>
	 */
	public function alternates( array $links ): array {
		return $this->excluded() ? array() : $links;
	}

	/**
	 * Leave transactional pages without a canonical link.
	 *
	 * @param bool $allow Canonical on noindex.
	 */
	public function canonical( bool $allow ): bool {
		return ! $this->transaction() && ( $allow || $this->parameterized_view() );
	}

	/**
	 * Point every filtered or compared selection at its localized landing page.
	 *
	 * @param string $tag SEOPress canonical element.
	 */
	public function canonical_tag( string $tag ): string {
		if ( ! $this->parameterized_view() ) {
			return $tag;
		}
		if ( ComparePage::is_comparison_page() ) {
			$url = get_permalink( get_queried_object_id() );
		} elseif ( is_shop() ) {
			$url = wc_get_page_permalink( 'shop' );
		} else {
			$term = get_queried_object();
			$url  = $term instanceof \WP_Term ? get_term_link( $term ) : false;
		}
		return is_string( $url ) ? '<link rel="canonical" href="' . esc_url( explode( '?', $url, 2 )[0] ) . '">' : $tag;
	}

	/**
	 * Match the robots meta tag on selection URLs and empty brands.
	 *
	 * @param array<string,string|false> $headers Existing response headers.
	 * @return array<string,string|false>
	 */
	public function headers( array $headers ): array {
		if ( $this->parameterized_view() || $this->empty_brand_archive() ) {
			$headers['X-Robots-Tag'] = 'noindex, follow';
		}
		return $headers;
	}

	/** WordPress and SEOPress use the same indexing policy. */
	private function excluded(): bool {
		return $this->transaction() || $this->parameterized_view() || $this->empty_brand_archive();
	}

	/** Query keys identify selections even if the visitor supplies an empty value. */
	private function parameterized_view(): bool {
		$keys = array_keys( $_GET ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only indexing policy compares query keys only.
		if ( array() === $keys || ! in_array( $_SERVER['REQUEST_METHOD'] ?? 'GET', array( 'GET', 'HEAD' ), true ) || is_admin() ) { // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Fixed method comparison.
			return false;
		}
		if ( array_intersect( array( 'ids', 'capped' ), $keys ) && ComparePage::is_comparison_page() ) {
			return true;
		}
		$facets = array( 'application', 'anwendung', 'brand', 'phase', 'power', 'kw_min', 'kw_max', 'kwh_min', 'kwh_max', 'sort', 'q' );
		return array() !== array_intersect( $facets, $keys ) && function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() ) && is_main_query() && ! is_404();
	}

	/** Preserve empty brand landing pages for people following their old URLs. */
	private function empty_brand_archive(): bool {
		return is_tax( 'product_brand' ) && is_main_query() && ! is_404() && ! have_posts();
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
