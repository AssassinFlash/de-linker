<?php
/**
 * Language-specific public brand URLs and fresh SEOPress sitemap index dates.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;

/** SEOPress enumerates each shared WooCommerce manufacturer term once. */
final class SitemapSync {
	/** Attach to the native sitemap serializers and content lifecycle. */
	public function register(): void {
		add_filter( 'seopress_sitemaps_term_single_url', array( $this, 'brand_urls' ), 20, 2 );
		add_filter( 'seopress_sitemaps_url', array( $this, 'brand_xml' ), 20, 2 );
		add_filter( 'seopress_sitemaps_cache_duration', array( $this, 'cache_duration' ) );
		add_action( 'save_post', array( $this, 'post_changed' ), 10, 2 );
		add_action( 'deleted_post', array( $this, 'post_changed' ), 10, 2 );
		add_action( 'transition_post_status', array( $this, 'transition' ), 10, 3 );
		add_action( 'woocommerce_new_product', array( $this, 'product_changed' ), 10, 0 );
		add_action( 'woocommerce_update_product', array( $this, 'product_changed' ), 10, 0 );
	}

	/**
	 * Choose the first indexable language and carry its twin to the XML serializer.
	 *
	 * @param array<string,mixed>|null $entry SEOPress term URL.
	 * @param \WP_Term                 $term  Term selected for this sitemap.
	 * @return array<string,mixed>|null
	 */
	public function brand_urls( ?array $entry, \WP_Term $term ): ?array {
		if ( empty( $entry['loc'] ) || 'product_brand' !== $term->taxonomy ) {
			return $entry;
		}
		$en = $this->has_models( $term->term_id, 'en' );
		$de = $this->has_models( $term->term_id, 'de' );
		if ( ! $en && ! $de ) {
			return null;
		}

		$root         = PageUrls::root();
		$path         = 'brand/' . $term->slug . '/';
		$entry['loc'] = esc_url( $root . ( $en ? '' : 'de/' ) . $path );
		if ( $en && $de ) {
			$entry['linker_brand_twin'] = esc_url( $root . 'de/' . $path );
		}
		return $entry;
	}

	/**
	 * Append a second URL only for the manufacturer that owns this entry.
	 *
	 * @param string              $xml   SEOPress's current URL element.
	 * @param array<string,mixed> $entry URL data supplied to its serializer.
	 */
	public function brand_xml( string $xml, array $entry ): string {
		return isset( $entry['linker_brand_twin'] ) ? $xml . "\n<url><loc>" . $entry['linker_brand_twin'] . '</loc></url>' : $xml;
	}

	/**
	 * The sitemap runs outside a frontend language and suppresses pre_get_posts.
	 * Match the native language relationship explicitly for each archive.
	 *
	 * @param int    $term_id Shared manufacturer ID.
	 * @param string $lang    Archive language.
	 */
	private function has_models( int $term_id, string $lang ): bool {
		return ! empty(
			get_posts(
				array(
					'post_type'   => 'product',
					'post_status' => 'publish',
					'fields'      => 'ids',
					'numberposts' => 1,
					'orderby'     => 'none',
					'lang'        => '',
					'tax_query'   => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- Each URL requires one catalog-visible product in its language.
						array(
				'taxonomy' => 'product_brand',
				'field'    => 'term_id',
				'terms'    => $term_id,
					),
						array(
					'taxonomy' => 'language',
					'field'    => 'slug',
					'terms'    => $lang,
					),
						array(
					'taxonomy' => 'product_visibility',
					'field'    => 'name',
					'terms'    => 'exclude-from-catalog',
					'operator' => 'NOT IN',
					),
					),
				)
			)
		);
	}

	/**
	 * Zero has special meaning for WordPress transients: it never expires.
	 *
	 * @param int $duration Native duration in seconds.
	 */
	public function cache_duration( int $duration ): int {
		return $duration > 0 ? min( $duration, 15 * MINUTE_IN_SECONDS ) : 15 * MINUTE_IN_SECONDS;
	}

	/**
	 * Refresh the affected type's index after WordPress saves or deletes it.
	 *
	 * @param int      $id   Post ID supplied by the action.
	 * @param \WP_Post $post Post including its type, even after deletion.
	 */
	public function post_changed( int $id, \WP_Post $post ): void {
		if ( in_array( $post->post_type, array( 'post', 'page', 'product' ), true ) ) {
			$this->invalidate( $post->post_type );
		}
	}

	/**
	 * Publication state changes affect membership in the native index query.
	 *
	 * @param string   $to  New status.
	 * @param string   $from  Previous status.
	 * @param \WP_Post $post Changed post.
	 */
	public function transition( string $to, string $from, \WP_Post $post ): void {
		if ( $to !== $from ) {
			$this->post_changed( $post->ID, $post );
		}
	}

	/** A native WooCommerce product save refreshes the product sitemap index. */
	public function product_changed(): void {
		$this->invalidate( 'product' );
	}

	/**
	 * SEOPress keys the post-type index dates by the configured page size.
	 *
	 * @param string $type Post type in this sitemap.
	 */
	private function invalidate( string $type ): void {
		$max = (int) apply_filters( 'seopress_sitemaps_max_posts_per_sitemap', 1000 ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Reuse the page size that SEOPress passes to its index query.
		foreach ( array_unique( array( 1000, $max ) ) as $size ) {
			delete_transient( 'seopress_sitemap_lastmod_all_' . $type . '_' . $size );
		}
	}
}
