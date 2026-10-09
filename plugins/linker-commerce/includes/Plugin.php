<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce;

use Linker\Commerce\Abilities\GetVersion;

/**
 * Hooks Linker Commerce into WordPress.
 */
final class Plugin {

	/**
	 * Slug of the ability category that groups this plugin's abilities.
	 */
	public const ABILITY_CATEGORY = 'linker-commerce';

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
		add_action( 'wp_abilities_api_categories_init', array( $this, 'register_ability_category' ) );
		add_action( 'wp_abilities_api_init', array( $this, 'register_abilities' ) );
	}

	/**
	 * Loads the translations shipped in the plugin's languages/ directory.
	 */
	public function load_textdomain(): void {
		load_plugin_textdomain( 'linker-commerce', false, dirname( plugin_basename( $this->file ) ) . '/languages' );
	}

	/**
	 * Registers the category of this plugin's abilities.
	 */
	public function register_ability_category(): void {
		if ( ! function_exists( 'wp_register_ability_category' ) ) {
			return;
		}

		wp_register_ability_category(
			self::ABILITY_CATEGORY,
			array(
				'label'       => __( 'Linker Commerce', 'linker-commerce' ),
				'description' => __( 'Products and inquiries of de-linker.com.', 'linker-commerce' ),
			)
		);
	}

	/**
	 * Registers this plugin's abilities.
	 */
	public function register_abilities(): void {
		if ( ! function_exists( 'wp_register_ability' ) ) {
			return;
		}

		wp_register_ability( GetVersion::NAME, ( new GetVersion( $this->file ) )->args() );
	}
}
