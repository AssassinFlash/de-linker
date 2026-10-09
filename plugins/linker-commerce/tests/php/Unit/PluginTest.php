<?php
/**
 * Tests for the plugin bootstrap.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit;

use Linker\Commerce\Abilities\GetVersion;
use Linker\Commerce\Plugin;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Plugin.
 *
 * @covers \Linker\Commerce\Plugin
 */
final class PluginTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-commerce/linker-commerce.php';

	/**
	 * The plugin hooks text domain loading and both Abilities API registration points.
	 */
	public function test_register_adds_the_hooks(): void {
		$plugin = new Plugin( self::FILE );

		WP_Mock::expectActionAdded( 'init', array( $plugin, 'load_textdomain' ) );
		WP_Mock::expectActionAdded( 'wp_abilities_api_categories_init', array( $plugin, 'register_ability_category' ) );
		WP_Mock::expectActionAdded( 'wp_abilities_api_init', array( $plugin, 'register_abilities' ) );

		$plugin->register();

		$this->assertConditionsMet();
	}

	/**
	 * Translations load from the plugin's own languages/ directory.
	 */
	public function test_load_textdomain_uses_the_languages_directory(): void {
		WP_Mock::userFunction(
			'plugin_basename',
			array(
				'args'   => array( self::FILE ),
				'return' => 'linker-commerce/linker-commerce.php',
			)
		);
		WP_Mock::userFunction(
			'load_plugin_textdomain',
			array(
				'times' => 1,
				'args'  => array( 'linker-commerce', false, 'linker-commerce/languages' ),
			)
		);

		( new Plugin( self::FILE ) )->load_textdomain();

		$this->assertConditionsMet();
	}

	/**
	 * The category is registered first, then the ability inside it.
	 */
	public function test_registers_the_category_and_the_ability(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction(
			'wp_register_ability_category',
			array(
				'times' => 1,
				'args'  => array(
					Plugin::ABILITY_CATEGORY,
					array(
						'label'       => 'Linker Commerce',
						'description' => 'Products and inquiries of de-linker.com.',
					),
				),
			)
		);
		WP_Mock::userFunction(
			'wp_register_ability',
			array(
				'times' => 1,
				'args'  => array(
					GetVersion::NAME,
					Mockery::on(
						static fn ( array $args ): bool => Plugin::ABILITY_CATEGORY === $args['category']
					),
				),
			)
		);

		$plugin = new Plugin( self::FILE );
		$plugin->register_ability_category();
		$plugin->register_abilities();

		$this->assertConditionsMet();
	}

	/**
	 * Without the Abilities API the plugin registers nothing and does not fail.
	 *
	 * Runs in its own process, where no test has defined the API functions yet.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_skips_registration_without_the_abilities_api(): void {
		$plugin = new Plugin( self::FILE );
		$plugin->register_ability_category();
		$plugin->register_abilities();

		$this->assertFalse( function_exists( 'wp_register_ability_category' ) );
		$this->assertFalse( function_exists( 'wp_register_ability' ) );
	}
}
