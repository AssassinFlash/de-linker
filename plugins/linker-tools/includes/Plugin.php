<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

/**
 * Hooks Linker Tools into WordPress.
 */
final class Plugin {

	/**
	 * Sets up the plugin.
	 *
	 * @param Assets     $assets      Registers the built apps as scripts.
	 * @param Redirects  $redirects   Retires the tool entry addresses that moved.
	 * @param SiteChrome $site_chrome The chrome's scripts (menu images, hover).
	 */
	public function __construct(
		private readonly Assets $assets,
		private readonly Redirects $redirects,
		private readonly SiteChrome $site_chrome
	) {}

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this->assets, 'register' ) );
		$this->redirects->register();
		$this->site_chrome->register();
	}
}
