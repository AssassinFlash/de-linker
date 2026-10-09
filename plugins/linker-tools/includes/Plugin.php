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
	 * @param string $file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $file ) {}

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this, 'register_assets' ) );
	}

	/**
	 * Registers the built apps as scripts.
	 */
	public function register_assets(): void {
		( new Assets( $this->file ) )->register();
	}
}
