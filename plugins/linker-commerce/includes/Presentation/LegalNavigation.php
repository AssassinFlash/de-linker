<?php
/**
 * Language-aware destinations for navigation created by saved legal documents.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/** Supplies native page URLs; the browser handles the generated links. */
final class LegalNavigation {

	/** Registers the document's interaction asset. */
	public static function register(): void {
		add_action( 'wp_enqueue_scripts', array( self::class, 'enqueue' ) );
	}

	/** Legal scripts create their links after server-side localization has run. */
	public static function enqueue(): void {
		$post = get_post();
		if ( ! is_page() || ! $post instanceof \WP_Post || ! str_contains( $post->post_content, 'id="tv-legal"' ) ) {
			return;
		}
		$routes = array();
		foreach ( array( 'imprint', 'privacy-policy', 'terms-of-sale', 'refund-returns' ) as $slug ) {
			$url = PageUrls::translated( $slug );
			if ( '' !== $url ) {
				$routes[ '/' . $slug . '/' ] = $url;
			}
		}
		$file = dirname( __DIR__, 2 ) . '/assets/legal-navigation.js';
		wp_enqueue_script( 'linker-legal-navigation', plugins_url( 'assets/legal-navigation.js', dirname( __DIR__, 2 ) . '/linker-commerce.php' ), array(), (string) filemtime( $file ), true );
		wp_add_inline_script( 'linker-legal-navigation', 'window.LinkerLegalRoutes = ' . wp_json_encode( $routes ) . ';', 'before' );
	}
}
