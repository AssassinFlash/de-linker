<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce;

use Linker\Commerce\Abilities\Registrar;
use Linker\Commerce\Catalog\SelectionFactsController;

/**
 * Hooks Linker Commerce into WordPress.
 */
final class Plugin {

	/**
	 * Sets up the plugin.
	 *
	 * @param string                   $file            Absolute path of the main plugin file.
	 * @param Registrar                $abilities       Registers the plugin's abilities.
	 * @param SelectionFactsController $selection_facts REST route of the selection facts.
	 */
	public function __construct(
		private readonly string $file,
		private readonly Registrar $abilities,
		private readonly SelectionFactsController $selection_facts
	) {}

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this, 'load_textdomain' ) );
		add_action( 'wp_abilities_api_categories_init', array( $this->abilities, 'register_category' ) );
		add_action( 'wp_abilities_api_init', array( $this->abilities, 'register_abilities' ) );
		add_action( 'rest_api_init', array( $this->selection_facts, 'register_routes' ) );
	}

	/**
	 * Loads the translations shipped in the plugin's languages/ directory.
	 */
	public function load_textdomain(): void {
		load_plugin_textdomain( 'linker-commerce', false, dirname( plugin_basename( $this->file ) ) . '/languages' );
	}
}
