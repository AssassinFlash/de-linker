<?php
/**
 * Registered public task paths keep operator commands private.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\Gateway;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Public customer task routes do not expose private operator controls.
 *
 * @covers \Linker\Tools\Planner\Gateway
 */
final class PlannerTaskGatewayTest extends TestCase {

	/** Native registration accepts customer tasks and refuses private control. */
	public function test_registered_task_routes_keep_operator_actions_private(): void {
		$registered = array();
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times'  => 2,
				'return' => static function ( string $route_namespace, string $route, array $args ) use ( &$registered ): bool {
					$registered[] = array( $route_namespace, $route, $args );
					return true;
				},
			)
		);
		( new Gateway() )->register();
		$this->assertCount( 2, $registered );
		$this->assertSame( 'linker/v1', $registered[1][0] );
		$this->assertSame( 'POST', $registered[1][2]['methods'] );
		$this->assertSame( 'permission', $registered[1][2]['permission_callback'][1] );
		$pattern = '~\A' . $registered[1][1] . '\z~';
		foreach ( array( 'runs/energy', 'runs/pv', 'runs/weather', 'runs/weather/status', 'runs/cancel', 'products/current' ) as $path ) {
			$this->assertSame( 1, preg_match( $pattern, '/planner/rpc/' . $path ), $path );
		}
		foreach ( array( 'runs/weather/acknowledge', 'runs/weather/resume', 'runs/weather/stop', 'operations/replay/runs/weather', 'identity/status', 'worker/control', 'runs/weather/status/extra' ) as $path ) {
			$this->assertSame( 0, preg_match( $pattern, '/planner/rpc/' . $path ), $path );
		}
		$this->assertConditionsMet();
	}
}
