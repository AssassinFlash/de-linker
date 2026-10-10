<?php
/**
 * Tests for the plugin bootstrap.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit;

use Linker\Commerce\Abilities\Registrar;
use Linker\Commerce\Admin\FiguresMetaBox;
use Linker\Commerce\Catalog\EngineeringFeedController;
use Linker\Commerce\Catalog\SelectionFactsController;
use Linker\Commerce\Plugin;
use Linker\Commerce\Storefront\CatalogFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Storefront\Storefront;
use WP_Mock;
use WP_Mock\Matcher\AnyInstance;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Plugin.
 *
 * @covers \Linker\Commerce\Plugin
 */
final class PluginTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-commerce/linker-commerce.php';

	/**
	 * The plugin hooks text domain loading (first thing on init), both Abilities
	 * API registration points, both REST routes, the figure meta box, the
	 * inquiry chain (once all plugins are loaded) and the presentation CLI.
	 */
	public function test_register_adds_the_hooks(): void {
		$abilities       = new Registrar( self::FILE );
		$selection_facts = new SelectionFactsController();
		$engineering     = new EngineeringFeedController();
		$figures         = new FiguresMetaBox();
		$plugin          = new Plugin( self::FILE, $abilities, $selection_facts, $engineering, $figures );

		WP_Mock::expectActionAdded( 'init', array( $plugin, 'load_textdomain' ), 0 );
		WP_Mock::expectActionAdded( 'wp_abilities_api_categories_init', array( $abilities, 'register_category' ) );
		WP_Mock::expectActionAdded( 'wp_abilities_api_init', array( $abilities, 'register_abilities' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $selection_facts, 'register_routes' ) );
		WP_Mock::expectActionAdded( 'plugins_loaded', array( $plugin, 'register_commerce' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $engineering, 'register_routes' ) );
		WP_Mock::expectActionAdded( 'add_meta_boxes', array( $figures, 'register' ) );
		WP_Mock::expectActionAdded( 'save_post_product', array( $figures, 'save' ) );
		WP_Mock::expectActionAdded( 'admin_notices', array( $figures, 'notice_refused' ) );
		WP_Mock::expectActionAdded( 'cli_init', array( $plugin, 'register_cli' ) );

		// AnyInstance matches the object the registration constructs.
		WP_Mock::expectActionAdded( 'pre_get_posts', array( new AnyInstance( CatalogFilters::class ), 'filter' ), 99 ); // @phpstan-ignore argument.type
		WP_Mock::expectFilterAdded( 'template_include', array( new AnyInstance( Storefront::class ), 'template' ), 99999 ); // @phpstan-ignore argument.type
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( new AnyInstance( Storefront::class ), 'assets' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectFilterAdded( 'woocommerce_show_page_title', '__return_false' );

		$plugin->register();

		$this->assertConditionsMet();
	}

	/**
	 * Without WooCommerce the inquiry chain adds nothing (WP_Mock's strict mode would fail on any hook).
	 * The full chain is wired against a real WooCommerce in tests/php/Integration.
	 */
	public function test_register_commerce_needs_woocommerce(): void {
		( new Plugin( self::FILE, new Registrar( self::FILE ), new SelectionFactsController(), new EngineeringFeedController(), new FiguresMetaBox() ) )->register_commerce();

		$this->assertFalse( class_exists( 'WooCommerce' ) );
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

		( new Plugin( self::FILE, new Registrar( self::FILE ), new SelectionFactsController(), new EngineeringFeedController(), new FiguresMetaBox() ) )->load_textdomain();

		$this->assertConditionsMet();
	}
}
