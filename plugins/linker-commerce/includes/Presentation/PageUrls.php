<?php
/**
 * The site's own pages in the reader's language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * One page of this site, addressed the way the header's own links are: the
 * page the slug resolves to, or its Polylang twin when the request is German.
 * The chain's gates, the tool entries and the workspace all point at pages by
 * slug, and every one of them resolved the twin its own way until ticket #184
 * folded the copies into this one place.
 *
 * A missing page or a page without a permalink answers '' — never a guessed
 * address: the caller knows what its own surface shows instead.
 */
final class PageUrls {

	/**
	 * The current language's address of one of the site's own pages.
	 *
	 * @param string $slug The page's path (its English slug, as the site keeps it).
	 */
	public static function translated( string $slug ): string {
		$page = get_page_by_path( $slug );
		if ( ! $page instanceof \WP_Post ) {
			return '';
		}
		$id = (int) $page->ID;
		if ( function_exists( 'pll_get_post' ) && function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			$twin = (int) pll_get_post( $id, 'de' );
			if ( $twin > 0 ) {
				$id = $twin;
			}
		}
		$link = get_permalink( $id );
		return is_string( $link ) ? $link : '';
	}
}
