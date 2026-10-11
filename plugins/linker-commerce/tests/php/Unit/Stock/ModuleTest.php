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
use Linker\Commerce\Stock\Retention;
use Linker\Commerce\Stock\StockController;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Stock\Module
 */
final class ModuleTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-commerce/linker-commerce.php';

	/**
	 * The audit row type, the push route and the retention's cron event are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$log        = new BatchLog();
		$controller = new StockController( $log );
		$retention  = new Retention( self::FILE );

		WP_Mock::expectActionAdded( 'init', array( $log, 'register_post_type' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $controller, 'register_routes' ) );
		WP_Mock::expectActionAdded( 'init', array( $retention, 'schedule' ) );
		WP_Mock::expectActionAdded( Retention::HOOK, array( $retention, 'sweep' ) );
		WP_Mock::userFunction(
			'register_deactivation_hook',
			array(
				'times' => 1,
				'args'  => array( self::FILE, array( $retention, 'deactivate' ) ),
			)
		);

		( new Module( $controller, $log, $retention ) )->register();

		$this->assertConditionsMet();
	}
}
