<?php
/**
 * Registered public task paths keep operator commands private.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\Gateway;
use Linker\Tools\Planner\NativeIdentity;
use WP_Error;
use WP_Mock;
use WP_REST_Request;
use WP_REST_Response;
use WP_Mock\Tools\TestCase;

/**
 * Public customer task routes do not expose private operator controls.
 *
 * @covers \Linker\Tools\Planner\Gateway
 * @covers \Linker\Tools\Planner\NativeIdentity
 */
final class PlannerTaskGatewayTest extends TestCase {

	/** Native registration accepts customer tasks and refuses private control. */
	public function test_registered_task_routes_keep_operator_actions_private(): void {
		$registered = array();
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times'  => 3,
				'return' => static function ( string $route_namespace, string $route, array $args ) use ( &$registered ): bool {
					$registered[] = array( $route_namespace, $route, $args );
					return true;
				},
			)
		);
		( new Gateway() )->register();
		$this->assertCount( 3, $registered );
		$this->assertSame( 'linker/v1', $registered[2][0] );
		$this->assertSame( 'POST', $registered[2][2]['methods'] );
		$this->assertSame( 'permission', $registered[2][2]['permission_callback'][1] );
		$pattern = '~\A' . $registered[2][1] . '\z~';
		foreach ( array( 'runs/energy', 'runs/pv', 'runs/direct-beam', 'runs/geometric-pv', 'weather/assets', 'weather/preview', 'runs/pvgis-reference', 'runs/equipment', 'runs/equipment-search', 'runs/report', 'equipment/candidates/read', 'equipment/certificates/read', 'runs/weather', 'runs/weather/status', 'runs/cancel', 'products/current', 'installation/review', 'sources/saved-solution' ) as $path ) {
			$this->assertSame( 1, preg_match( $pattern, '/planner/rpc/' . $path ), $path );
		}
		foreach ( array( 'projects/assistant', 'runs/weather/acknowledge', 'runs/weather/resume', 'runs/weather/stop', 'operations/replay/runs/weather', 'identity/status', 'worker/control', 'runs/weather/status/extra' ) as $path ) {
			$this->assertSame( 0, preg_match( $pattern, '/planner/rpc/' . $path ), $path );
		}
		$this->assertConditionsMet();
	}

	/** The revalidation probe answers with the scope only, after one resolution. */
	public function test_scope_route_returns_only_the_compared_query_scope(): void {
		$request = new WP_REST_Request( 'POST', '/linker/v1/planner/scope' );
		$request->set_header( 'x-wp-nonce', 'synthetic-rest-nonce' );
		$identity = new NativeIdentity();
		WP_Mock::userFunction( 'get_current_user_id' )->once()->andReturn( 17 );
		WP_Mock::userFunction( 'is_wp_error' )->twice()->andReturn( false );
		WP_Mock::userFunction( 'wp_get_session_token' )->once()->andReturn( 'synthetic-session-token' );
		WP_Mock::userFunction( 'wp_verify_nonce' )->once()->with( 'synthetic-rest-nonce', 'wp_rest' )->andReturn( true );
		WP_Mock::userFunction( 'get_current_blog_id' )->once()->andReturn( 1 );
		WP_Mock::userFunction( 'wp_hash' )->once()->andReturn( '3' . str_repeat( 'a', 63 ) );
		$response = ( new Gateway( $identity ) )->scope( $request );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame(
			array(
				'schema_version' => 1,
				'query_scope'    => '3' . str_repeat( 'a', 63 ),
			),
			$response->get_data()
		);
		$this->assertConditionsMet();
	}

	/** A probe without a valid native session admission is refused, not answered. */
	public function test_scope_route_refuses_an_unauthenticated_probe(): void {
		$request = new WP_REST_Request( 'POST', '/linker/v1/planner/scope' );
		$request->set_header( 'x-wp-nonce', 'synthetic-rest-nonce' );
		$identity = new NativeIdentity();
		WP_Mock::userFunction( 'get_current_user_id' )->once()->andReturn( 17 );
		WP_Mock::userFunction( 'is_wp_error' )->zeroOrMoreTimes()->andReturnUsing( static fn ( mixed $value ): bool => $value instanceof WP_Error );
		WP_Mock::userFunction( 'wp_get_session_token' )->once()->andReturn( 'synthetic-session-token' );
		WP_Mock::userFunction( 'wp_verify_nonce' )->once()->with( 'synthetic-rest-nonce', 'wp_rest' )->andReturn( false );
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $message ): string => $message ) );
		$refused = ( new Gateway( $identity ) )->scope( $request );
		$this->assertInstanceOf( WP_Error::class, $refused );
		$this->assertSame( 401, $refused->get_error_data()['status'] ?? null );
		$this->assertConditionsMet();
	}

	/** Core rest-nonce AJAX action resolves the logged_in cookie owner so wp_rest nonce matches REST requests. */
	public function test_rest_nonce_ajax_uses_logged_in_cookie_owner(): void {
		$identity           = new NativeIdentity();
		$_REQUEST['action'] = 'rest-nonce';
		WP_Mock::userFunction( 'wp_doing_ajax' )->once()->andReturn( true );
		WP_Mock::userFunction( 'wp_validate_auth_cookie' )->once()->with( '', 'logged_in' )->andReturn( 17 );
		try {
			$this->assertSame( 17, $identity->rest_nonce_user( false ) );
		} finally {
			unset( $_REQUEST['action'] );
		}
	}
}
