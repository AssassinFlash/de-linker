<?php
/**
 * Tests for the presentation module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Account\Documents;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
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
	 * Shortcodes, the login gate, WindPress and the account body class are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$saved      = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
		$shortcodes = new Shortcodes( new LoginGate(), $saved, new Documents( $saved, '/plugin/templates/' ) );
		$gate       = new LoginGate();
		$windpress  = new WindPress();
		$module     = new Module( $shortcodes, $gate, $windpress );

			WP_Mock::userFunction( 'add_shortcode', array( 'times' => 7 ) );
		WP_Mock::expectFilterAdded( 'woocommerce_checkout_redirect_empty_cart', array( $gate, 'keep_empty_checkout' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );
		WP_Mock::expectFilterAdded( 'body_class', array( $module, 'body_class' ) );

		$module->register();

		$this->assertConditionsMet();
	}

	/**
	 * Account pages keep the live scope class.
	 */
	public function test_body_class_on_account(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_cart', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_checkout', array( 'return' => false ) );

		$saved = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/' );
		$this->assertContains(
			'sf-account-page',
			( new Module(
				new Shortcodes( new LoginGate(), $saved, new Documents( $saved, '/' ) ),
				new LoginGate(),
				new WindPress()
			) )->body_class( array() )
		);
	}
}
