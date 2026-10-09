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
	 * @param Assets $assets Registers the built apps as scripts.
	 */
	public function __construct( private readonly Assets $assets ) {}

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this->assets, 'register' ) );
	}
}
