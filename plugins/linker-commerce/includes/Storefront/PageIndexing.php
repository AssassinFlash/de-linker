<?php
/**
 * Search indexing of the WooCommerce transaction pages and archive URLs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Contact\Module as Contact;
use Linker\Commerce\Contact\SelectionContext;
use Linker\Commerce\Presentation\ComparePage;

/** Woo page assignments and their translations own the public URLs. */
final class PageIndexing {
	private const CONTACT_QUERY_KEYS = array( 'intent', 'kind', 'title', 'source_id', 'product', 'product_id', 'source', 'sku', 'model', SelectionContext::FIELD, 'contact', 'contact_order' );

	/** Register the SEOPress and core robots policies. */
	public function register(): void {
		add_filter( 'seopress_titles_title', array( $this, 'brand_title' ), 35 );
		add_filter( 'pre_get_document_title', array( $this, 'brand_title' ), 35 );
		add_filter( 'seopress_social_og_title', array( $this, 'brand_social_title' ), 35 );
		add_filter( 'seopress_social_twitter_card_title', array( $this, 'brand_social_title' ), 35 );
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
	 * Name the equipment available in each published manufacturer archive.
	 *
	 * @param string $existing Current document title.
	 */
	public function brand_title( string $existing ): string {
		$term = get_queried_object();
		if ( ! $term instanceof \WP_Term || 'product_brand' !== $term->taxonomy || $this->empty_brand_archive() ) {
			return $existing;
		}
		$title = match ( $term->slug ) {
			'goodwe' => __( 'GoodWe Hybrid Inverters & Storage Systems', 'linker-commerce' ),
			'saj' => __( 'SAJ Hybrid Inverters & Energy Storage', 'linker-commerce' ),
			'pylontech' => __( 'Pylontech LFP Batteries & Storage Systems', 'linker-commerce' ),
			'chint' => __( 'Chint Smart Meters & Energy Monitoring', 'linker-commerce' ),
			/* translators: %s: manufacturer brand name. */
			default => sprintf( __( '%s Solar & Storage Equipment', 'linker-commerce' ), wp_strip_all_tags( $term->name ) ),
		};
		return $title . ' | ' . get_bloginfo( 'name' );
	}

	/**
	 * SEOPress uses the social title filter for both field values and HTML tags.
	 *
	 * @param string $value Title field or social metadata tag.
	 */
	public function brand_social_title( string $value ): string {
		$title = $this->brand_title( '' );
		if ( '' === $title ) {
			return $value;
		}
		if ( ! str_starts_with( ltrim( $value ), '<meta' ) ) {
			return $title;
		}
		$html = new \WP_HTML_Tag_Processor( $value );
		$html->next_tag( array( 'tag_name' => 'META' ) );
		$html->set_attribute( 'content', $title );
		return $html->get_updated_html();
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
		if ( $term instanceof \WP_Term && 'product_brand' === $term->taxonomy && ! $this->empty_brand_archive() ) {
			return self::brand_description( $term->name );
		}
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
	 * Describe the models listed on the manufacturer's public archive.
	 *
	 * @param string $name WooCommerce brand name.
	 */
	public static function brand_description( string $name ): string {
		/* translators: %s: manufacturer brand name. */
		return sprintf( __( 'Browse %s models and datasheets for your next solar or storage project. Linker supports installers and EPCs across Europe.', 'linker-commerce' ), html_entity_decode( wp_strip_all_tags( $name ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
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
		return ! $this->transaction() && ! $this->parameterized_view() && ( $allow || $this->parameterized_contact() );
	}

	/**
	 * Contact handoffs share their localized form's canonical address.
	 *
	 * @param string $tag SEOPress canonical element.
	 */
	public function canonical_tag( string $tag ): string {
		if ( $this->parameterized_view() || $this->transaction() ) {
			return '';
		}
		if ( ! $this->parameterized_contact() ) {
			return $tag;
		}
		return '<link rel="canonical" href="' . esc_url( (string) get_permalink( get_queried_object_id() ) ) . '">';
	}

	/**
	 * Match the robots meta tag on selection URLs and empty brands.
	 *
	 * @param array<string,string|false> $headers Existing response headers.
	 * @return array<string,string|false>
	 */
	public function headers( array $headers ): array {
		if ( $this->excluded() ) {
			$headers['X-Robots-Tag'] = 'noindex, follow';
		}
		return $headers;
	}

	/** WordPress and SEOPress use the same indexing policy. */
	private function excluded(): bool {
		return $this->transaction() || $this->parameterized_view() || $this->parameterized_contact() || $this->empty_brand_archive();
	}

	/** A handoff or receipt opened on either native contact page. */
	private function parameterized_contact(): bool {
		if ( ! array_intersect( self::CONTACT_QUERY_KEYS, array_keys( $_GET ) ) || ! in_array( $_SERVER['REQUEST_METHOD'] ?? 'GET', array( 'GET', 'HEAD' ), true ) || is_admin() || ! is_page() ) { // phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- Read-only request classification.
			return false;
		}
		$page = get_queried_object();
		return $page instanceof \WP_Post && Contact::is_contact_page( $page );
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
		$facets   = array( 'application', 'anwendung', 'brand', 'phase', 'power', 'kw_min', 'kw_max', 'kwh_min', 'kwh_max', 'sort', 'q', 'orderby' );
		$filtered = array() !== array_intersect( $facets, $keys ) || (bool) preg_grep( '/^(?:filter_|query_type_)/', $keys );
		return $filtered && function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() ) && is_main_query() && ! is_404();
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
	public function transaction(): bool {
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
