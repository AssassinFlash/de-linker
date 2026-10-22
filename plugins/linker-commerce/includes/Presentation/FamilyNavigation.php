<?php
/**
 * Native addresses and head metadata for the family-based product archive.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * Preserve the existing product-page contract without paging individual models.
 */
final class FamilyNavigation {

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
		add_action( 'template_redirect', array( $this, 'redirect' ), 1 );
		add_filter( 'seopress_titles_noindex_bypass', array( $this, 'noindex' ) );
		add_filter( 'seopress_titles_canonical', array( $this, 'canonical' ) );
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
	 * Explicit product-page takes precedence over a native path page. Native
	 * unknown-term/out-of-range 404 responses remain native 404 responses.
	 */
	public function normalization_target(): string {
		if ( ! $this->active() ) {
			return '';
		}
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- public GET pagination.
		$present = array_key_exists( 'product-page', $_GET );
		if ( ! $present && (int) get_query_var( 'paged' ) < 1 ) {
			return '';
		}
		$page = ( $this->page )();
		if ( $present && (int) get_query_var( 'paged' ) < 1 ) {
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- compared to the validated integer, never output.
			$requested = wp_unslash( $_GET['product-page'] );
			if ( $page->current > 1 && \is_string( $requested ) && (string) $page->current === $requested ) {
				return '';
			}
		}
		return $this->address( $page );
	}

	/**
	 * Respect SEOPress's existing paged-noindex option for real family pages.
	 *
	 * @param mixed $noindex Native effective noindex decision.
	 * @return mixed The existing decision or the native paged decision.
	 */
	public function noindex( mixed $noindex ): mixed {
		if ( ! $this->active() || ( $this->page )()->current < 2 || ! \function_exists( 'seopress_get_service' ) || ! empty( $noindex ) ) {
			return $noindex;
		}
		$options = seopress_get_service( 'TitleOption' );
		if ( ! \is_object( $options ) || ! method_exists( $options, 'getPagedNoIndex' ) ) {
			return $noindex;
		}
		$paged = $options->getPagedNoIndex();
		return empty( $paged ) ? $noindex : $paged;
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
		return $page->current < 2 ? $canonical : '<link rel="canonical" href="' . esc_url( $this->address( $page ) ) . '">';
	}

	/**
	 * Match Polylang's native omission of alternates on later archive pages.
	 *
	 * @param array<string, string> $links Native language alternates.
	 * @return array<string, string> Unchanged root links or no paged alternates.
	 */
	public function hreflangs( array $links ): array {
		return $this->active() && ( $this->page )()->current > 1 ? array() : $links;
	}

	/**
	 * Native localized root plus the one validated family page parameter.
	 *
	 * @param FamilyPage $page Validated current family page.
	 */
	private function address( FamilyPage $page ): string {
		$base = ( $this->base )();
		return $page->current > 1 ? (string) add_query_arg( 'product-page', $page->current, $base ) : $base;
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
