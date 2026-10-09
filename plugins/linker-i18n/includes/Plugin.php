<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * Hooks Linker i18n into WordPress.
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
		add_action( 'init', array( $this, 'load_textdomain' ) );
	}

	/**
	 * Loads the translations shipped in the plugin's languages/ directory.
	 */
	public function load_textdomain(): void {
		load_plugin_textdomain( 'linker-i18n', false, dirname( plugin_basename( $this->file ) ) . '/languages' );
	}
}
