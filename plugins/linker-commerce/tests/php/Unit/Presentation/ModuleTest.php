<?php
/**
 * Tests for the presentation module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\AccountTemplates;
use Linker\Commerce\Presentation\ComparePage;
use Linker\Commerce\Presentation\LibraryPage;
use Linker\Commerce\Presentation\JournalTitles;
use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Presentation\Module;
use Linker\Commerce\Presentation\Shortcodes;
use Linker\Commerce\Presentation\WindPress;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Presentation\Module
 */
final class ModuleTest extends TestCase {

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
		$module     = new Module( $shortcodes, $gate, $windpress, null, $compare, $library, $account );

		// 63 (including the four guest account entry tags for #223): the product, checkout, comparison, library and account shortcodes,
		// the empty-draft state, the contact invitation band, the catalogue's
		// mobile actions bar and chips strip, the blog single template's two
		// data fragments, and the site origin the blog index's JSON-LD composes
		// (#175) — plus the product page's FAQ side panel (2026-10-16). The
		// price gate is not a shortcode: prices are hidden at their source
		// (Gating\PriceDisplay), and the registration nothing consumed went
		// with it.
		WP_Mock::userFunction( 'add_shortcode', array( 'times' => 63 ) );
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $account, 'template' ), 20, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_my_account_my_orders_query', array( $account, 'orders_query' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_checkout_redirect_empty_cart', array( $gate, 'keep_empty_checkout' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/integration/livecanvas/compile:get_contents.render', array( $windpress, 'render_raw' ), 10, 2 );
		WP_Mock::expectActionAdded( 'template_redirect', array( $compare, 'canonical_address' ), 5 );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $compare, 'assets' ) );
		WP_Mock::expectActionAdded( 'wp_footer', array( $compare, 'standing_chip' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $module, 'enqueue_product_scripts' ) );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $module, 'enqueue_account_scripts' ) );

		WP_Mock::expectActionAdded( 'init', array( JournalTitles::class, 'register' ) );
		$module->register();

		$this->assertConditionsMet();
	}
}
