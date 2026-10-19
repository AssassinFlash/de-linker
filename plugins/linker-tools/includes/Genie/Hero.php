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
 *
 * The dock's mount (`[data-linker-app="genie"]`, Entries) carries the routes,
 * nonce, language and page context the hero app reads (config.ts); the hero
 * adds no second configuration block. The dock's stylesheet is enqueued here
 * as well so the shared components (GenieCard, Reply, AttachmentCard) never
 * depend on the dock's own enqueue order.
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
	}

	/**
	 * Loads the hero's script and stylesheet on the front page.
	 */
	public function assets(): void {
		if ( is_admin() || ! is_front_page() ) {
			return;
		}
		wp_enqueue_style( Entries::HANDLE );
		wp_enqueue_style( self::HANDLE );
		wp_enqueue_script( self::HANDLE );
	}
}
