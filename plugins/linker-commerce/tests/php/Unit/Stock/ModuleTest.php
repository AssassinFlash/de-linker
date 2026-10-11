<?php
/**
 * Tests for the stock module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Stock;

use Linker\Commerce\Stock\BatchLog;
use Linker\Commerce\Stock\Module;
use Linker\Commerce\Stock\StockController;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Stock\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * The audit row type and the push route are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$log        = new BatchLog();
		$controller = new StockController( $log );

		WP_Mock::expectActionAdded( 'init', array( $log, 'register_post_type' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $controller, 'register_routes' ) );

		( new Module( $controller, $log ) )->register();

		$this->assertConditionsMet();
	}
}
