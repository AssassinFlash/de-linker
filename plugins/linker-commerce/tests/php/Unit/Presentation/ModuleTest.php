<?php
/**
 * Tests for the presentation module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\AccountTemplates;
use Linker\Commerce\Presentation\BlogShortcodes;
use Linker\Commerce\Presentation\ComparePage;
use Linker\Commerce\Presentation\FamilyNavigation;
use Linker\Commerce\Presentation\LibraryPage;
use Linker\Commerce\Presentation\JournalTitles;
use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Presentation\Module;
use Linker\Commerce\Presentation\Shortcodes;
use Linker\Commerce\Presentation\WindPress;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Mock\Matcher\AnyInstance;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Presentation\Module
 */
final class ModuleTest extends TestCase {

	/** The standalone native draft also receives the saved-quantity guard. */
	public function test_cart_loads_account_interactions(): void {
		WP_Mock::userFunction( 'is_account_page' )->andReturn( false );
		WP_Mock::userFunction( 'is_checkout' )->andReturn( false );
		WP_Mock::userFunction( 'is_cart' )->andReturn( true );
		WP_Mock::userFunction( 'is_wc_endpoint_url' )->andReturn( false );
		WP_Mock::userFunction( 'plugins_url' )->andReturn( 'https://example.test/assets/' );
		WP_Mock::userFunction( 'wp_enqueue_script' )->once()->with(
			'linker-account-ui',
			'https://example.test/assets/account-ui.js',
			array(),
			(string) filemtime( dirname( __DIR__, 4 ) . '/assets/account-ui.js' ),
			true
		);
		( new Module( new Shortcodes(), new LoginGate(), new WindPress() ) )->enqueue_account_scripts();
		$this->assertConditionsMet();
	}

	/**
	 * The module's hooks, and no other: the shortcodes of the three page
	 * families (the product and checkout shortcodes, the comparison page's
	 * table and chip, the library page's two registers), the login gate's
	 * filter, the WindPress provider, and the comparison page's address
	 * normalizer, selection script and chip. WP_Mock's strict mode fails the
	 * run on any further hook — there is deliberately no body_class filter
	 * left, because the sf-account-page body class had no consumer after the
	 * storefront CSS was retired.
	 */
	public function test_register_adds_exactly_the_module_hooks(): void {
		$shortcodes = new Shortcodes();
		$gate       = new LoginGate();
		$windpress  = new WindPress();
		$compare    = new ComparePage();
		$library    = new LibraryPage();
		$account    = new AccountTemplates();
		$blog       = new BlogShortcodes();
		$module     = new Module( $shortcodes, $gate, $windpress, null, $compare, $library, $account, $blog );

		// 67 data-only registrations across the product, checkout, comparison,
		// library, account and blog families, including the product's configurator
		// entry. The price gate remains separate from the shortcode surface.
		WP_Mock::userFunction( 'add_shortcode', array( 'times' => 67 ) );
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $account, 'template' ), 20, 2 );
		WP_Mock::expectFilterAdded( 'pre_get_document_title', array( $blog, 'empty_search_title' ), 60 );
		WP_Mock::expectFilterAdded( 'woocommerce_my_account_my_orders_query', array( $account, 'orders_query' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_checkout_redirect_empty_cart', array( $gate, 'keep_empty_checkout' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/integration/livecanvas/compile:get_contents.render', array( $windpress, 'render_raw' ), 10, 2 );
		WP_Mock::expectActionAdded( 'template_redirect', array( $compare, 'canonical_address' ), 5 );
		WP_Mock::expectActionAdded( 'wp_head', array( $library, 'print_schema' ) );
		$families     = new AnyInstance( FamilyNavigation::class );
		$family_hooks = array(
			array( 'action', 'template_redirect', 'redirect', 1 ),
			array( 'filter', 'seopress_titles_noindex_bypass', 'noindex', 10 ),
			array( 'filter', 'seopress_titles_canonical', 'canonical', 10 ),
			array( 'filter', 'pll_rel_hreflang_attributes', 'hreflangs', 20 ),
		);
		$registered   = array_fill_keys( array_column( $family_hooks, 1 ), 0 );
		foreach ( $family_hooks as list( $type, $hook, $method, $priority ) ) {
			$responder = WP_Mock::onHookAdded( $hook, $type )->with( array( $families, $method ), $priority, 1 );
			self::assertInstanceOf( \WP_Mock\HookedCallbackResponder::class, $responder );
			$responder->perform(
				static function () use ( &$registered, $hook ): void {
					++$registered[ $hook ];
				}
			);
		}
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $compare, 'assets' ) );
		WP_Mock::expectActionAdded( 'wp_footer', array( $compare, 'standing_chip' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $module, 'enqueue_product_scripts' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $module, 'enqueue_account_scripts' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( \Linker\Commerce\Presentation\LegalNavigation::class, 'enqueue' ) );

		WP_Mock::expectActionAdded( 'init', array( JournalTitles::class, 'register' ) );
		$module->register();
		self::assertSame( array_fill_keys( array_column( $family_hooks, 1 ), 1 ), $registered );

		$this->assertConditionsMet();
	}
}
