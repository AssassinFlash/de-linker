<?php
/**
 * The Solution Configurator's mount point.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Configurator;

/**
 * Prints the page's mount point and loads the built app.
 *
 * The LiveCanvas template of the configurator page prints
 * `[linker_configurator]`; the app is the built entry `build/configurator.js`
 * that Assets registers as `linker-tools-configurator`. The markup carries
 * what the app cannot know server-side — the engine's address (the option
 * `linker_engine_url`, docs/specs/14-solution-configurator.md), the REST root
 * and a REST nonce (shape: linker-tools src/configurator/config.ts) — and
 * nothing else: zero design, no word of copy, and the app's own stylesheet
 * sizes and colours it.
 *
 * It prints on the page it is written into and nowhere else. The page is the
 * one place the tool lives; without this mount the page would keep whatever
 * markup it held before, which is what the old site's planner page did.
 */
final class Mount {

	/**
	 * Script and style handle of the built app (Assets registers one per
	 * entry).
	 */
	public const HANDLE = 'linker-tools-configurator';

	/**
	 * Option holding the configurator engine's base URL: `just serve <name>`
	 * writes it locally, the cutover writes it in production
	 * (docs/local-stack.md, docs/specs/17-cutover.md).
	 */
	public const ENGINE_URL_OPTION = 'linker_engine_url';

	/**
	 * Hooks the shortcode; runs during plugin registration.
	 */
	public function register(): void {
		add_shortcode( 'linker_configurator', array( $this, 'shortcode' ) );
	}

	/**
	 * The configurator's mount point.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes (none).
	 */
	public function shortcode( $atts = array() ): string {
		unset( $atts );
		if ( is_admin() ) {
			return '';
		}
		wp_enqueue_script( self::HANDLE );
		wp_enqueue_style( self::HANDLE );

		return sprintf(
			'<div data-linker-app="configurator" data-engine-url="%1$s" data-rest-url="%2$s" data-rest-nonce="%3$s"></div>',
			esc_attr( (string) get_option( self::ENGINE_URL_OPTION, '' ) ),
			esc_attr( esc_url_raw( rest_url() ) ),
			esc_attr( wp_create_nonce( 'wp_rest' ) )
		);
	}
}
