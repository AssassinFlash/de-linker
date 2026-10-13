<?php
/**
 * Linker's child theme: the theme's own behaviours, and nothing else.
 *
 * This checkout owns this file; the deploy writes it over the theme's copy —
 * the local stack's `just up` and the cutover's deploy step both install it.
 * Everything else of the site belongs to its owner, not to the theme:
 * hreflang and canonical links are Polylang's with linker-i18n's x-default,
 * the archive's structured data is linker-commerce's Storefront, and the
 * security headers and the REST guard are mu-plugins/linker-site-guards.php.
 * The theme is picostrap5's child; the parent carries the Bootstrap assets.
 *
 * @package Linker\ChildTheme
 */

declare( strict_types = 1 );

/**
 * The `js` class on the root element: the progressive-enhancement flag the
 * theme's styles expect.
 */
function linker_child_theme_js_class(): void {
	echo "<script>document.documentElement.classList.add('js');</script>\n";
}
add_action( 'wp_head', 'linker_child_theme_js_class', 1 );

/**
 * Picostrap's light-theme marker, written when the parent's own output did
 * not already carry it.
 *
 * @param string $output The `<html>` element's attributes.
 * @return string
 */
function linker_child_theme_light_marker( string $output ): string {
	if ( false !== strpos( $output, 'data-theme=' ) ) {
		return $output;
	}
	return trim( $output ) . ' data-theme="light"';
}
add_filter( 'language_attributes', 'linker_child_theme_light_marker' );
