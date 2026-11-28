<?php
/**
 * Public bilingual links and modification dates for the native SEOPress sitemaps.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\DocumentLibrary;
use Linker\Commerce\Products\DocumentThumbnails;

/** SEOPress enumerates each shared WooCommerce manufacturer term once. */
final class SitemapSync {
	/**
	 * Request-local catalogue and journal archive dates.
	 *
	 * @var SitemapDates|null
	 */
	private ?SitemapDates $dates = null;

	/** Attach to the native sitemap serializers and content lifecycle. */
	public function register(): void {
		add_filter( 'seopress_sitemaps_urlset', array( $this, 'xmlns' ) );
		add_filter( 'seopress_sitemaps_single_img', array( $this, 'page_images' ), 20, 2 );
		add_filter( 'seopress_sitemaps_single_url', array( $this, 'post_entry' ), 30, 2 );
		add_filter( 'seopress_sitemaps_term_single_url', array( $this, 'term_entry' ), 30, 2 );
		add_filter( 'seopress_sitemaps_no_archive_link', array( $this, 'archive_xml' ), 20, 2 );
		add_filter( 'seopress_sitemaps_xml_index', array( $this, 'index_xml' ) );
		add_filter( 'seopress_sitemaps_url', array( $this, 'entry_xml' ), 20, 2 );
		add_filter( 'seopress_sitemaps_cache_duration', array( $this, 'cache_duration' ) );
		add_action( 'clean_term_cache', array( $this, 'clear_dates' ), 10, 0 );
		add_action( 'set_object_terms', array( $this, 'clear_dates' ), 10, 0 );
		add_action( 'save_post', array( $this, 'post_changed' ), 10, 2 );
		add_action( 'deleted_post', array( $this, 'post_changed' ), 10, 2 );
		add_action( 'transition_post_status', array( $this, 'transition' ), 10, 3 );
		add_action( 'woocommerce_new_product', array( $this, 'product_changed' ), 10, 0 );
		add_action( 'woocommerce_update_product', array( $this, 'product_changed' ), 10, 0 );
	}

	/**
	 * Add the tool's published images when SEOPress finds no static page images.
	 *
	 * @param string   $xml Native URL entry before its closing tag.
	 * @param \WP_Post $post Page included in the sitemap.
	 */
	public function page_images( string $xml, \WP_Post $post ): string {
		if ( 'page' !== $post->post_type || str_contains( $xml, '<image:image>' ) ) {
			return $xml;
		}
		$source = function_exists( 'pll_get_post' ) ? (int) pll_get_post( $post->ID, 'en' ) : $post->ID;
		$slug   = $source && $source !== $post->ID ? get_post_field( 'post_name', $source ) : $post->post_name;
		$lang   = function_exists( 'pll_get_post_language' ) && 'de' === pll_get_post_language( $post->ID, 'slug' ) ? 'de' : 'en';
		$images = array();
		if ( 'solution-configurator' === $slug || 'compare-products' === $slug ) {
			$views = 'compare-products' === $slug ? array( 'compare' ) : array( 'compare', 'equipment', 'roof' );
			foreach ( $views as $view ) {
				$images[] = plugins_url( "assets/home-configurator/{$view}-{$lang}-1440.webp", dirname( __DIR__, 2 ) . '/linker-commerce.php' );
			}
		}
		if ( 'faq-download' === $slug ) {
			$thumbs = new DocumentThumbnails();
			foreach ( ( new DocumentLibrary() )->documents( $lang ) as $document ) {
				if ( 'datasheet' !== $document['type'] ) {
					continue;
				}
				$cover = $thumbs->of( $document['url'] );
				if ( $cover ) {
					$images[ $cover['src'] ] = $cover['src'];
				}
				if ( 4 === count( $images ) ) {
					break;
				}
			}
		}
		if ( 'inverter-battery-compatibility' === $slug || 'compare-products' === $slug ) {
			$images = array_merge( $images, self::paired_images( $lang, 'compare-products' === $slug ? 2 : 4 ) );
		}
		foreach ( array_unique( $images ) as $image ) {
			if ( preg_match( '~^https?://~i', $image ) ) {
				$xml .= "\n<image:image><image:loc><![CDATA[" . esc_url_raw( $image ) . ']]></image:loc></image:image>';
			}
		}
		return $xml;
	}

	/**
	 * Featured images from released inverter and battery pairs, one per brand and role.
	 *
	 * @param string $lang Page language.
	 * @param int    $limit Number of images to include.
	 * @return list<string>
	 */
	private static function paired_images( string $lang, int $limit ): array {
		$manifest = CompatibilityIndex::manifest();
		$pairs    = CompatibilityIndex::declarations( $manifest )['pairs'];
		$products = array_column( $manifest['products'], null, 'product_id' );
		$images   = array();
		foreach ( $pairs as $pair ) {
			if ( 'not_released' === $pair['verdict'] ) {
				continue;
			}
			foreach ( array( 'inverter_product_id', 'battery_product_id' ) as $role ) {
				$item = $products[ $pair[ $role ] ];
				$id   = $item['locale_product_ids'][ $lang ] ?? 0;
				$key  = $item['brand'] . '/' . $role;
				if ( isset( $images[ $key ] ) || ! in_array( $id, $item['published_locale_ids'], true ) ) {
					continue;
				}
				$url = get_the_post_thumbnail_url( $id, 'full' );
				if ( $url && ! in_array( $url, $images, true ) ) {
					$images[ $key ] = $url;
					if ( count( $images ) === $limit ) {
						return array_values( $images );
					}
				}
			}
		}
		return array_values( $images );
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
		$root   = PageUrls::root();
		$latest = $this->dates();
		$links  = array();
		foreach ( array(
			'en' => 'brand/',
			'de' => 'de/marke/',
		) as $lang => $base ) {
			if ( $latest->latest( 'product_brand', $term->term_id, $lang ) ) {
				$links[ $lang ] = $root . $base . $term->slug . '/';
			}
		}
		if ( ! $links ) {
			return null;
		}

		$lang                       = array_key_first( $links );
		$entry['loc']               = esc_url( $links[ $lang ] );
		$entry['linker_alternates'] = $links;
		$entry['linker_date']       = $latest->latest( 'product_brand', $term->term_id, $lang );
		if ( isset( $links['en'], $links['de'] ) ) {
			$entry['linker_brand_twin'] = esc_url( $links['de'] );
			$entry['linker_twin_date']  = $latest->latest( 'product_brand', $term->term_id, 'de' );
		}
		return $entry;
	}

	/** Load archive dates only on a request that uses them. */
	private function dates(): SitemapDates {
		return $this->dates ??= new SitemapDates();
	}

	/** Relationship and publication changes affect archive membership. */
	public function clear_dates(): void {
		$this->dates = null;
	}

	/**
	 * Declare the namespace used for language alternates.
	 *
	 * @param string $tag Native opening urlset tag.
	 */
	public function xmlns( string $tag ): string {
		return str_contains( $tag, 'xmlns:xhtml=' ) ? $tag : str_replace( '>', ' xmlns:xhtml="http://www.w3.org/1999/xhtml">', $tag );
	}

	/**
	 * Resolve both members against the same post exclusion filters as the primary row.
	 *
	 * @param array<string,mixed>|null $entry SEOPress URL.
	 * @param \WP_Post                 $post  Published object.
	 * @return array<string,mixed>|null
	 */
	public function post_entry( ?array $entry, \WP_Post $post ): ?array {
		if ( str_contains( (string) ( $entry['loc'] ?? '' ), '?' ) ) {
			return null;
		}
		if ( empty( $entry['loc'] ) || isset( $entry['linker_alternates'] ) ) {
			return $entry;
		}
		$entry['linker_alternates'] = array();
		foreach ( pll_get_post_translations( $post->ID ) as $lang => $id ) {
			$twin = get_post( $id );
			if ( ! in_array( $lang, array( 'en', 'de' ), true ) || ! $twin || 'publish' !== $twin->post_status || '' !== $twin->post_password ) {
				continue;
			}
			if ( $post->ID === $twin->ID ) {
				$row = $entry;
			} else {
				// Mark the membership lookup so it does not resolve its own alternates recursively.
				$candidate = array(
					'loc'               => get_permalink( $twin ),
					'linker_alternates' => array(),
				);
				$row       = $candidate['loc'] ? apply_filters( 'seopress_sitemaps_single_url', $candidate, $twin ) : null; // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Use the native noindex, canonical and workspace exclusions.
			}
			if ( ! empty( $row['loc'] ) ) {
				$entry['linker_alternates'][ $lang ] = html_entity_decode( $row['loc'], ENT_QUOTES | ENT_HTML5, 'UTF-8' );
			}
		}
		return $entry;
	}

	/**
	 * Native translated categories keep their separate term IDs and descendants.
	 *
	 * @param array<string,mixed>|null $entry SEOPress term URL.
	 * @param \WP_Term                 $term  Term selected for this sitemap.
	 * @return array<string,mixed>|null
	 */
	public function term_entry( ?array $entry, \WP_Term $term ): ?array {
		if ( empty( $entry['loc'] ) || ! in_array( $term->taxonomy, array( 'category', 'product_cat' ), true ) ) {
			return $this->brand_urls( $entry, $term );
		}
		$entry['linker_alternates'] = array();
		foreach ( pll_get_term_translations( $term->term_id ) as $lang => $id ) {
			$date = $this->dates()->latest( $term->taxonomy, $id, $lang );
			if ( ! $date || get_term_meta( $id, '_seopress_robots_index', true ) ) {
				continue;
			}
			$url       = get_term_link( $id, $term->taxonomy );
			$canonical = get_term_meta( $id, '_seopress_robots_canonical', true );
			if ( ! is_string( $url ) || ( $canonical && $canonical !== $url ) ) {
				continue;
			}
			$entry['linker_alternates'][ $lang ] = $url;
			if ( $id === $term->term_id ) {
				$entry['linker_date'] = $date;
			}
		}
		return isset( $entry['linker_date'] ) ? $entry : null;
	}

	/**
	 * Serialize only complete, reciprocal language sets.
	 *
	 * @param array<string,string> $links Language URLs.
	 */
	private function links_xml( array $links ): string {
		if ( ! isset( $links['en'], $links['de'] ) ) {
			return '';
		}
		$xml = '';
		foreach ( array( 'en', 'de', 'x-default' ) as $lang ) {
			$url  = $links[ 'x-default' === $lang ? 'en' : $lang ];
			$xml .= sprintf( '<xhtml:link rel="alternate" hreflang="%s" href="%s"/>', $lang, htmlspecialchars( $url, ENT_XML1 | ENT_QUOTES, 'UTF-8' ) );
		}
		return $xml;
	}

	/**
	 * Extend native rows without changing image or post modification data.
	 *
	 * @param string                   $xml   Native URL element (may be empty).
	 * @param array<string,mixed>|null $entry Native URL metadata.
	 */
	public function entry_xml( string $xml, ?array $entry ): string {
		if ( ! $xml || ! isset( $entry['linker_alternates'] ) ) {
			return $xml;
		}
		$links = $this->links_xml( $entry['linker_alternates'] );
		$date  = isset( $entry['linker_date'] ) ? '<lastmod>' . $entry['linker_date'] . '</lastmod>' : '';
		$xml   = str_replace( '</url>', $date . $links . '</url>', $xml );
		if ( isset( $entry['linker_brand_twin'] ) ) {
			$xml .= "\n<url><loc>" . $entry['linker_brand_twin'] . '</loc><lastmod>' . $entry['linker_twin_date'] . '</lastmod>' . $links . '</url>';
		}
		return $xml;
	}

	/**
	 * SEOPress emits shop and journal archives outside the post-entry filter.
	 *
	 * @param string $xml  Native archive URL element.
	 * @param string $type Archive post type.
	 */
	public function archive_xml( string $xml, string $type ): string {
		if ( ! $xml || ! in_array( $type, array( 'post', 'product' ), true ) ) {
			return $xml;
		}
		$id    = (int) get_option( 'post' === $type ? 'page_for_posts' : 'woocommerce_shop_page_id' );
		$links = array();
		$date  = '';
		foreach ( pll_get_post_translations( $id ) as $lang => $page_id ) {
			$page = get_post( $page_id );
			if ( ! $page || 'publish' !== $page->post_status || '' !== $page->post_password || 'yes' === get_post_meta( $page_id, '_seopress_robots_index', true ) ) {
				continue;
			}
			$url = get_permalink( $page );
			if ( $url ) {
				$links[ $lang ] = $url;
				if ( str_contains( $xml, '<loc>' . esc_url( $url ) . '</loc>' ) ) {
					$date = $this->dates()->latest( $type, 0, $lang );
				}
			}
		}
		return str_replace( '</url>', ( $date ? '<lastmod>' . $date . '</lastmod>' : '' ) . $this->links_xml( $links ) . '</url>', $xml );
	}

	/**
	 * SEOPress exposes the complete index after emitting its undated taxonomy rows.
	 *
	 * @param string $xml Native XML index.
	 */
	public function index_xml( string $xml ): string {
		return (string) preg_replace_callback(
			'~/(category|product_cat|product_brand)-sitemap[0-9]+\.xml</loc>(\s*)</sitemap>~',
			function ( array $matches ): string {
				$date = max( $this->dates()->latest( $matches[1], 0, 'en' ), $this->dates()->latest( $matches[1], 0, 'de' ) );
				return $date ? str_replace( '</sitemap>', '<lastmod>' . $date . '</lastmod></sitemap>', $matches[0] ) : $matches[0];
			},
			$xml
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
		$this->clear_dates();
		$max = (int) apply_filters( 'seopress_sitemaps_max_posts_per_sitemap', 1000 ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Reuse the page size that SEOPress passes to its index query.
		foreach ( array_unique( array( 1000, $max ) ) as $size ) {
			delete_transient( 'seopress_sitemap_lastmod_all_' . $type . '_' . $size );
		}
	}
}
