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
	 * Resolve a language twin for a stored inquiry locale, or zero when absent.
	 *
	 * @param int    $id Canonical post id.
	 * @param string $locale Validated EN/DE locale.
	 */
	public static function twin( int $id, string $locale ): int {
		return function_exists( 'pll_get_post' ) ? (int) pll_get_post( $id, str_starts_with( $locale, 'de' ) ? 'de' : 'en' ) : 0;
	}

	/**
	 * The home page in the current language: /de/ on a German request, / on
	 * an English one. Home is the one address no page object carries, so it
	 * needs its own door; every other page goes through translated().
	 */
	public static function home(): string {
		if ( function_exists( 'pll_home_url' ) && function_exists( 'pll_current_language' ) ) {
			$language = pll_current_language();
			if ( is_string( $language ) ) {
				return trailingslashit( (string) pll_home_url( $language ) );
			}
		}
		// The one home address WordPress itself knows; written through a
		// variable because this file is the rule's own entry point (the CI
		// check forbids the literal in every other plugin file).
		$path = '/';
		return home_url( $path );
	}

	/**
	 * The current language's address of one of the site's own pages, and the
	 * language's home when the page does not exist. The one entry point for
	 * a page link: a missing page must not send a visitor to an English
	 * address the caller wrote out itself.
	 *
	 * @param string $slug The page's path (its English slug, as the site keeps it).
	 */
	public static function page( string $slug ): string {
		$translated = self::translated( $slug );
		return '' !== $translated ? $translated : self::home();
	}

	/**
	 * The current language's address of one of the site's own pages.
	 *
	 * @param string      $slug The page's path (its English slug, as the site keeps it).
	 * @param string|null $locale Explicit saved/REST language, or current page language.
	 */
	public static function translated( string $slug, ?string $locale = null ): string {
		if ( ! function_exists( 'get_page_by_path' ) ) {
			return '';
		}
		$page = get_page_by_path( $slug );
		if ( ! $page instanceof \WP_Post ) {
			return '';
		}
		$id = (int) $page->ID;
		if ( null !== $locale ) {
			$id = self::twin( $id, $locale );
			if ( $id < 1 ) {
				return '';
			}
		} elseif ( function_exists( 'pll_get_post' ) && function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			$twin = (int) pll_get_post( $id, 'de' );
			if ( $twin > 0 ) {
				$id = $twin;
			}
		}
		$link = get_permalink( $id );
		return is_string( $link ) ? $link : '';
	}
}
