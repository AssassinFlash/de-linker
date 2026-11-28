<?php
/**
 * The home hero's Genie entry (ticket #232).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Loads `src/hero/` on the front page only.
 *
 * The hero itself is the LiveCanvas page's own markup (`section.hero-cinematic`
 * with its textarea, send button, capsules and photo/attachment/voice
 * buttons); this entry binds those controls and unfolds the conversation in
 * place. The page is untouched until the visitor asks, which is what keeps
 * the owner's pixel gate on the resting hero.
 */
final class Hero {

	/**
	 * Handle of the built `hero` entry (registered by Assets on init).
	 */
	public const HANDLE = 'linker-tools-hero';

	/**
	 * Hooks the entry; runs during plugin registration.
	 */
	public function register(): void {
		add_action( 'wp_enqueue_scripts', array( $this, 'assets' ) );
		add_action( 'wp_footer', array( $this, 'config' ) );
	}

	/**
	 * Loads the hero's script and stylesheet on the front page.
	 */
	public function assets(): void {
		if ( is_admin() || ! is_front_page() ) {
			return;
		}
		EntryAssets::enqueue_loader( 'hero', array( 'linker-tools-genie-loader' ) );
	}

	/** Print only the URLs for the first interaction with the homepage hero. */
	public function config(): void {
		if ( is_admin() || ! is_front_page() ) {
			return;
		}
		$config           = EntryAssets::config( 'hero' );
		$config['styles'] = array( EntryAssets::url( self::HANDLE, true ), EntryAssets::url( Entries::HANDLE, true ) );
		wp_print_inline_script_tag(
			(string) wp_json_encode( $config, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES ),
			array(
				'type'                    => 'application/json',
				'data-linker-hero-loader' => true,
			)
		);
	}
}
