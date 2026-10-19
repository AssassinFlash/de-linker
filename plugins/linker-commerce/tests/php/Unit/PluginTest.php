<?php
/**
 * Tests for the plugin bootstrap.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit;

use Linker\Commerce\Abilities\Registrar;
use Linker\Commerce\Admin\DocumentsMetaBox;
use Linker\Commerce\Admin\FaqsMetaBox;
use Linker\Commerce\Admin\FiguresMetaBox;
use Linker\Commerce\Products\ProductSearchController;
use Linker\Commerce\Products\EngineeringFeedController;
use Linker\Commerce\Products\SearchScope;
use Linker\Commerce\Products\SelectionFactsController;
use Linker\Commerce\Contact\Module as ContactModule;
use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Plugin;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductSchema;
use Linker\Commerce\Storefront\ProductView;
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
	 * API registration points, both REST routes, the figure and FAQ meta boxes,
	 * the inquiry chain (once all plugins are loaded) and the presentation CLI.
	 */
	public function test_register_adds_the_hooks(): void {
		$d      = $this->dependencies();
		[
			'abilities'       => $abilities,
			'selection_facts' => $selection_facts,
			'engineering'     => $engineering,
			'product_search'  => $product_search,
			'search_scope'    => $search_scope,
			'figures'         => $figures,
			'faqs'            => $faqs,
			'documents'       => $documents,
		]       = $d;
		$plugin = new Plugin( self::FILE, $abilities, $selection_facts, $engineering, $product_search, $search_scope, new ContactModule(), $figures, $faqs, $documents );

		WP_Mock::expectActionAdded( 'init', array( $plugin, 'load_textdomain' ), 0 );
		WP_Mock::expectActionAdded( 'wp_abilities_api_categories_init', array( $abilities, 'register_category' ) );
		WP_Mock::expectActionAdded( 'wp_abilities_api_init', array( $abilities, 'register_abilities' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $selection_facts, 'register_routes' ) );
		WP_Mock::expectActionAdded( 'plugins_loaded', array( $plugin, 'register_commerce' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $engineering, 'register_routes' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $product_search, 'register_routes' ) );
		WP_Mock::expectActionAdded( 'add_meta_boxes', array( $figures, 'register' ) );
		WP_Mock::expectActionAdded( 'save_post_product', array( $figures, 'save' ) );
		WP_Mock::expectActionAdded( 'admin_notices', array( $figures, 'notice_refused' ) );
		WP_Mock::expectActionAdded( 'add_meta_boxes', array( $faqs, 'register' ) );
		WP_Mock::expectActionAdded( 'save_post_product', array( $faqs, 'save' ) );
		WP_Mock::expectActionAdded( 'admin_notices', array( $faqs, 'notice_refused' ) );
		WP_Mock::expectActionAdded( 'add_meta_boxes', array( $documents, 'register' ) );
		WP_Mock::expectActionAdded( 'save_post_product', array( $documents, 'save' ) );
		WP_Mock::expectActionAdded( 'cli_init', array( $plugin, 'register_cli' ) );
		WP_Mock::expectActionAdded( 'plugins_loaded', array( $plugin, 'stand_down_legacy_template_preemption' ) );

		// The contact module mounts its shortcode and handler and keeps the
		// email classes known to WooCommerce.
		$shortcode = null;
		WP_Mock::userFunction(
			'add_shortcode',
			array(
				'times'  => 1,
				'return' => static function ( string $tag, $callback ) use ( &$shortcode ): void {
					$shortcode = array( $tag, $callback );
				},
			)
		);
			WP_Mock::expectFilterAdded( 'the_content', array( new AnyInstance( ContactModule::class ), 'mount_form' ), 9 ); // @phpstan-ignore argument.type
		WP_Mock::expectActionAdded( 'admin_post_nopriv_linker_contact', array( new \WP_Mock\Matcher\AnyInstance( \Linker\Commerce\Contact\Handler::class ), 'handle' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectActionAdded( 'admin_post_linker_contact', array( new \WP_Mock\Matcher\AnyInstance( \Linker\Commerce\Contact\Handler::class ), 'handle' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectActionAdded( 'pre_get_posts', array( $search_scope, 'scope' ) );

		// AnyInstance matches the object the registration constructs.
		WP_Mock::expectActionAdded( 'pre_get_posts', array( new AnyInstance( ProductFilters::class ), 'filter' ), 99 ); // @phpstan-ignore argument.type
		WP_Mock::expectActionAdded( 'wp_head', array( new AnyInstance( ProductSchema::class ), 'print_block' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectActionAdded( 'wp_head', array( new AnyInstance( \Linker\Commerce\Storefront\ArchiveSchema::class ), 'print_block' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectActionAdded( 'init', array( new AnyInstance( Monitor::class ), 'schedule' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectActionAdded( Monitor::HOOK, array( new AnyInstance( Monitor::class ), 'run' ) ); // @phpstan-ignore argument.type
		WP_Mock::userFunction( 'register_deactivation_hook' );

		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( new AnyInstance( \Linker\Commerce\Consent\BasicMode::class ), 'enqueue_withdrawal' ), 0 ); // @phpstan-ignore argument.type
		WP_Mock::expectFilterAdded( 'wp_get_consent_type', array( new AnyInstance( \Linker\Commerce\Consent\BasicMode::class ), 'opt_in' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectFilterAdded( 'script_loader_tag', array( new AnyInstance( \Linker\Commerce\Consent\BasicMode::class ), 'hold_google_tag' ), 30, 2 ); // @phpstan-ignore argument.type
		WP_Mock::expectFilterAdded( 'googlesitekit_consent_defaults', array( new AnyInstance( \Linker\Commerce\Consent\BasicMode::class ), 'deny_everywhere' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectFilterAdded( 'googlesitekit_consent_category_map', array( new AnyInstance( \Linker\Commerce\Consent\BasicMode::class ), 'without_ads' ) ); // @phpstan-ignore argument.type

		$plugin->register();

		$this->assertSame( 'linker_contact_form', $shortcode[0] ?? null );
		$this->assertInstanceOf( \Linker\Commerce\Contact\Form::class, $shortcode[1][0] ?? null );
		$this->assertSame( 'render', $shortcode[1][1] ?? null );
		$this->assertConditionsMet();
	}

	/**
	 * The plugin's dependencies, fresh for one test.
	 *
	 * @return array{abilities: Registrar, selection_facts: SelectionFactsController, engineering: EngineeringFeedController, product_search: ProductSearchController, search_scope: SearchScope, figures: FiguresMetaBox, faqs: FaqsMetaBox, documents: DocumentsMetaBox}
	 */
	private function dependencies(): array {
		return array(
			'abilities'       => new Registrar( self::FILE ),
			'selection_facts' => new SelectionFactsController(),
			'engineering'     => new EngineeringFeedController(),
			'product_search'  => new ProductSearchController(),
			'search_scope'    => new SearchScope(),
			'figures'         => new FiguresMetaBox(),
			'faqs'            => new FaqsMetaBox(),
			'documents'       => new DocumentsMetaBox(),
		);
	}

	/**
	 * The legacy commerce renderer (terravolt-b2b-core) filters
	 * template_include at PHP_INT_MAX, above LiveCanvas's 99998, and takes the
	 * commerce page types away from the dynamic templates for as long as it is
	 * installed. The stand-down removes exactly that callback; without the old
	 * plugin it removes nothing.
	 */
	public function test_stand_down_removes_the_legacy_template_filter(): void {
		WP_Mock::userFunction(
			'remove_filter',
			array(
				'times' => 1,
				'args'  => array( 'template_include', 'tv_b2b_template_include', PHP_INT_MAX ),
			)
		);

		$d = $this->dependencies();
		( new Plugin( self::FILE, $d['abilities'], $d['selection_facts'], $d['engineering'], $d['product_search'], $d['search_scope'], new ContactModule(), $d['figures'], $d['faqs'], $d['documents'] ) )->stand_down_legacy_template_preemption();

		$this->assertConditionsMet();
	}

	/**
	 * Without WooCommerce the inquiry chain adds nothing (WP_Mock's strict mode would fail on any hook).
	 * The full chain is wired against a real WooCommerce in tests/php/Integration.
	 */
	public function test_register_commerce_needs_woocommerce(): void {
		$d = $this->dependencies();
		( new Plugin( self::FILE, $d['abilities'], $d['selection_facts'], $d['engineering'], $d['product_search'], $d['search_scope'], new ContactModule(), $d['figures'], $d['faqs'], $d['documents'] ) )->register_commerce();

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

		$d = $this->dependencies();
		( new Plugin( self::FILE, $d['abilities'], $d['selection_facts'], $d['engineering'], $d['product_search'], $d['search_scope'], new ContactModule(), $d['figures'], $d['faqs'], $d['documents'] ) )->load_textdomain();

		$this->assertConditionsMet();
	}
}
