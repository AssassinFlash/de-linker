<?php
/**
 * Native addresses and head metadata for the family-based product archive.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Storefront\ProductFamilies;

/**
 * Publish family archive paths and preserve filtered catalog selections.
 */
final class FamilyNavigation {

	/**
	 * Last family page of the other language's archive.
	 *
	 * @var array<string,int>
	 */
	private array $translated_pages = array();

	/**
	 * Read the same request-local family state as the LC fragments.
	 *
	 * @param \Closure $page Current family state.
	 * @param \Closure $base Native root with validated selection.
	 * @phpstan-param \Closure(): FamilyPage $page
	 * @phpstan-param \Closure(): string $base
	 */
	public function __construct(
		private readonly \Closure $page,
		private readonly \Closure $base
	) {}

	/** Register native redirect and SEO extension points. */
	public function register(): void {
		add_action( 'template_redirect', array( $this, 'redirect' ), 0 );
		add_filter( 'seopress_titles_canonical', array( $this, 'canonical' ) );
		add_filter( 'pll_translation_url', array( $this, 'translated_page' ), 55, 2 );
		add_filter( 'seopress_titles_title', array( $this, 'paged_title' ), 50 );
		add_filter( 'pre_get_document_title', array( $this, 'paged_title' ), 50 );
		add_filter( 'pll_rel_hreflang_attributes', array( $this, 'hreflangs' ), 20 );
	}

	/** Redirect a recognized HTML paging alias before the native template renders. */
	public function redirect(): void {
		$target = $this->normalization_target();
		if ( '' !== $target && wp_safe_redirect( $target, 301 ) ) {
			exit;
		}
	}

	/**
	 * An alias or invalid page resolves to one normalized family address.
	 *
	 * Explicit product-page takes precedence over the native path page.
	 *
	 * @phpstan-impure Reads request query and path state.
	 */
	public function normalization_target(): string {
		if ( ! $this->active() ) {
			return '';
		}
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- public GET pagination.
		$present = array_key_exists( 'product-page', $_GET );
		$native  = self::native_page();
		if ( ! $present && $native < 1 ) {
			return '';
		}
		$page   = ( $this->page )();
		$base   = ( $this->base )();
		$target = self::page_url( $base, $page->current );
		if ( ! $present && ! str_contains( $base, '?' ) && $native === $page->current && $native > 1 ) {
			$path = wp_parse_url( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ), PHP_URL_PATH ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Compared against the native target only.
			if ( wp_parse_url( $target, PHP_URL_PATH ) === $path ) {
				return '';
			}
		}
		if ( $present && $native < 1 && $page->current > 1 && str_contains( $base, '?' ) ) {
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Compare the public value with the normalized integer.
			$requested = wp_unslash( $_GET['product-page'] );
			if ( is_string( $requested ) && (string) $page->current === $requested ) {
				return '';
			}
		}
		return $target;
	}

	/** Requested native path page before the individual-product query is reset. */
	public static function native_page(): int {
		return (int) get_query_var( 'linker_family_paged', get_query_var( 'paged' ) );
	}

	/**
	 * Put the localized page number before the site-name suffix.
	 *
	 * @param string $title Expanded document title.
	 */
	public function paged_title( string $title ): string {
		if ( '' === $title || ! $this->active() ) {
			return $title;
		}
		$current = ( $this->page )()->current;
		if ( $current < 2 ) {
			return $title;
		}
		/* translators: %d: product archive page number. */
		$label = ' – ' . sprintf( __( 'Page %d', 'linker-commerce' ), $current );
		$site  = ' | ' . get_bloginfo( 'name' );
		$end   = str_ends_with( $title, $site ) ? $site : '';
		$base  = '' === $end ? $title : substr( $title, 0, -strlen( $end ) );
		return str_ends_with( $base, $label ) ? $title : $base . $label . $end;
	}

	/**
	 * When SEOPress emits its default canonical, use the actual family slice.
	 *
	 * Its native noindex/custom-canonical gates remain authoritative.
	 *
	 * @param string $canonical Native default canonical element.
	 */
	public function canonical( string $canonical ): string {
		if ( ! $this->active() || ( \function_exists( 'seopress_titles_canonical_term_option' ) && seopress_titles_canonical_term_option() ) ) {
			return $canonical;
		}
		$page = ( $this->page )();
		$base = ( $this->base )();
		return $page->current < 2 ? $canonical : ( str_contains( $base, '?' ) ? '' : '<link rel="canonical" href="' . esc_url( self::page_url( $base, $page->current ) ) . '">' );
	}

	/**
	 * Switch to the translated slice when it exists, or its archive root.
	 *
	 * @param string|null $url Native translated archive URL.
	 * @param string      $language Target language.
	 */
	public function translated_page( ?string $url, string $language ): ?string {
		$page = self::native_page();
		if ( null === $url || $page < 2 || ! $this->active() || str_contains( ( $this->base )(), '?' ) ) {
			return $url;
		}
		$base = (string) preg_replace( '#/(?:seite|page)/[0-9]+/?$#', '/', $url );
		if ( pll_current_language() !== $language && $page > $this->translated_last_page( $language ) ) {
			return $base;
		}
		return self::page_url( $base, $page );
	}

	/**
	 * Count the translated archive by the same reciprocal model grouping as the grid.
	 *
	 * @param string $language Archive language.
	 */
	private function translated_last_page( string $language ): int {
		if ( isset( $this->translated_pages[ $language ] ) ) {
			return $this->translated_pages[ $language ];
		}
		$hidden = array( 'exclude-from-catalog' );
		if ( 'yes' === get_option( 'woocommerce_hide_out_of_stock_items' ) ) {
			$hidden[] = 'outofstock';
		}
		$taxes = array(
			array(
				'taxonomy' => 'product_visibility',
				'field'    => 'name',
				'terms'    => $hidden,
				'operator' => 'NOT IN',
			),
			array(
				'taxonomy' => 'language',
				'field'    => 'slug',
				'terms'    => $language,
			),
		);
		$term  = get_queried_object();
		if ( $term instanceof \WP_Term ) {
			if ( 'product_brand' === $term->taxonomy ) {
				$taxes[] = array(
					'taxonomy' => 'pa_brand',
					'field'    => 'slug',
					'terms'    => $term->slug,
				);
			} else {
				$id      = pll_is_translated_taxonomy( $term->taxonomy ) ? (int) pll_get_term( $term->term_id, $language ) : $term->term_id;
				$taxes[] = array(
					'taxonomy' => $term->taxonomy,
					'field'    => 'term_id',
					'terms'    => $id,
				);
			}
		}
		$ids                                 = get_posts(
			array(
				'post_type'      => 'product',
				'post_status'    => 'publish',
				'posts_per_page' => -1,
				'fields'         => 'ids',
				'lang'           => '',
				'orderby'        => 'menu_order title',
				'order'          => 'ASC',
				'tax_query'      => $taxes, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- Count one translated archive, including catalog visibility.
			)
		);
		$rows                                = ( new ProductFamilies( $ids, $language ) )->rows( $ids );
		$this->translated_pages[ $language ] = (int) ceil( count( $rows ) / ProductShortcodes::PER_PAGE_FAMILIES );
		return $this->translated_pages[ $language ];
	}

	/**
	 * A translated archive root cannot be a later page's search alternate.
	 *
	 * @param array<string,string> $links Polylang translation URLs.
	 * @return array<string,string>
	 */
	public function hreflangs( array $links ): array {
		if ( ! $this->active() || ( $this->page )()->current < 2 ) {
			return $links;
		}
		if ( str_contains( ( $this->base )(), '?' ) ) {
			return array();
		}
		$page = ( $this->page )()->current;
		return array_filter( $links, static fn( string $url ): bool => (bool) preg_match( '#/(?:seite|page)/' . $page . '/$#', $url ) );
	}

	/**
	 * Canonical address of one family page.
	 *
	 * @param string $base Native root including any selection parameters.
	 * @param int    $page Validated page number.
	 */
	public static function page_url( string $base, int $page ): string {
		if ( $page <= 1 ) {
			return $base;
		}
		if ( str_contains( $base, '?' ) ) {
			return (string) add_query_arg( 'product-page', $page, $base );
		}
		$german = str_starts_with( (string) wp_parse_url( $base, PHP_URL_PATH ), '/de/' );
		return rtrim( $base, '/' ) . ( $german ? '/seite/' : '/page/' ) . $page . '/';
	}

	/** Only the native main HTML shop/public product taxonomy surface. */
	private function active(): bool {
		$method = (string) wp_unslash( $_SERVER['REQUEST_METHOD'] ?? 'GET' ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- compared only to fixed method names.
		if ( is_admin() || wp_doing_ajax() || ( \defined( 'REST_REQUEST' ) && REST_REQUEST ) || ! \in_array( $method, array( 'GET', 'HEAD' ), true ) || ! is_main_query() || is_404() || is_feed() || is_embed() || is_preview() || is_search() ) {
			return false;
		}
		if ( is_shop() ) {
			return true;
		}
		$term = get_queried_object();
		if ( ! $term instanceof \WP_Term || ! is_tax( $term->taxonomy ) || ! \in_array( $term->taxonomy, get_object_taxonomies( 'product', 'names' ), true ) ) {
			return false;
		}
		$taxonomy = get_taxonomy( $term->taxonomy );
		return $taxonomy instanceof \WP_Taxonomy && $taxonomy->public && $taxonomy->publicly_queryable;
	}
}
