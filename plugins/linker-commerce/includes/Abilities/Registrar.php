<?php
/**
 * Registration of this plugin's abilities.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

/**
 * Registers the ability category and every ability of this plugin with the
 * WordPress Abilities API. Each ability class supplies its own arguments; the
 * category is assigned here, so all of them land in it.
 */
final class Registrar {

	/**
	 * Category slug of this plugin's abilities.
	 */
	public const CATEGORY = 'linker';

	/**
	 * Sets up the registrar.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Registers the category; runs on wp_abilities_api_categories_init.
	 */
	public function register_category(): void {
		if ( ! function_exists( 'wp_register_ability_category' ) ) {
			return;
		}

		wp_register_ability_category(
			self::CATEGORY,
			array(
				'label'       => __( 'Linker', 'linker-commerce' ),
				'description' => __( 'Products and inquiries of de-linker.com.', 'linker-commerce' ),
			)
		);
	}

	/**
	 * Registers the abilities; runs on wp_abilities_api_init.
	 */
	public function register_abilities(): void {
		if ( ! function_exists( 'wp_register_ability' ) ) {
			return;
		}

		$ability = new GetCommerceVersion( $this->plugin_file );
		wp_register_ability( GetCommerceVersion::NAME, array( 'category' => self::CATEGORY ) + $ability->args() );
	}
}
