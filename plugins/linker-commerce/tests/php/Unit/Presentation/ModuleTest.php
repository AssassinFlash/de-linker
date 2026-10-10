<?php
/**
 * Tests for the presentation module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

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
	 * Exactly three hooks: the two shortcodes, the login gate's filter and the
	 * WindPress provider. WP_Mock's strict mode fails the run on any further
	 * hook — there is deliberately no body_class filter left, because the
	 * sf-account-page body class had no consumer after the storefront CSS was
	 * retired.
	 */
	public function test_register_adds_exactly_the_module_hooks(): void {
		$shortcodes = new Shortcodes( new LoginGate() );
		$gate       = new LoginGate();
		$windpress  = new WindPress();
		$module     = new Module( $shortcodes, $gate, $windpress );

		WP_Mock::userFunction( 'add_shortcode', array( 'times' => 3 ) );
		WP_Mock::expectFilterAdded( 'woocommerce_checkout_redirect_empty_cart', array( $gate, 'keep_empty_checkout' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );

		$module->register();

		$this->assertConditionsMet();
	}
}
