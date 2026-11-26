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
use Linker\Tools\Planner\Transport;
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
		foreach ( array( 'inquiry/form', 'profiles/standard', 'runs/energy', 'runs/calculate', 'runs/find-equipment', 'runs/check-equipment', 'runs/inputs', 'runs/pv', 'runs/direct-beam', 'runs/geometric-pv', 'weather/assets', 'weather/preview', 'runs/pvgis-reference', 'runs/equipment', 'runs/equipment-search', 'runs/report', 'equipment/candidates/read', 'equipment/certificates/read', 'runs/weather', 'runs/weather/status', 'runs/cancel', 'products/current', 'installation/review', 'sources/saved-solution', 'projects/create', 'projects/delete', 'projects/list', 'projects/read', 'projects/revise', 'projects/runs' ) as $path ) {
			$this->assertSame( 1, preg_match( $pattern, '/planner/rpc/' . $path ), $path );
		}
		foreach ( array( 'projects/assistant', 'projects/delete-after-inquiry-check', 'projects/prepared-handoffs', 'projects/admit-inquiry', 'handoffs/admit-inquiry', 'runs/weather/acknowledge', 'runs/weather/resume', 'runs/weather/stop', 'operations/replay/runs/weather', 'identity/status', 'worker/control', 'runs/weather/status/extra' ) as $path ) {
			$this->assertSame( 0, preg_match( $pattern, '/planner/rpc/' . $path ), $path );
		}
		$this->assertConditionsMet();
	}

	/** A preliminary inquiry form must always bind an explicit project revision. */
	public function test_inquiry_form_requires_the_reviewed_revision(): void {
		$request = new WP_REST_Request( 'POST', '/linker/v1/planner/rpc/inquiry/form' );
		$request->set_url_params( array( 'path' => 'inquiry/form' ) );
		$request->set_header( 'content-type', 'application/json' );
		$request->set_header( 'x-wp-nonce', 'synthetic-rest-nonce' );
		$request->set_body( '{"schema_version":1,"lang":"en","project_id":"b94de53435f84797900b710f5b2a948a"}' );
		WP_Mock::userFunction( 'get_current_user_id' )->once()->andReturn( 17 );
		WP_Mock::userFunction( 'wp_get_session_token' )->once()->andReturn( 'synthetic-session-token' );
		WP_Mock::userFunction( 'wp_verify_nonce' )->once()->with( 'synthetic-rest-nonce', 'wp_rest' )->andReturn( true );
		WP_Mock::userFunction( 'get_current_blog_id' )->once()->andReturn( 1 );
		WP_Mock::userFunction( 'is_wp_error' )->zeroOrMoreTimes()->andReturnUsing( static fn ( mixed $value ): bool => $value instanceof WP_Error );
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $message ): string => $message ) );
		$refused = ( new Gateway() )->forward( $request );
		$this->assertInstanceOf( WP_Error::class, $refused );
		$this->assertSame( 'linker_planner_input', $refused->get_error_code() );
		$this->assertSame( 422, $refused->get_error_data()['status'] ?? null );
		$this->assertConditionsMet();
	}

	/**
	 * A new guest makes no private service request. Returning the cookie still
	 * checks live identity on every bootstrap, including a version-cache hit.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_cookie_confirmation_and_version_cache_do_not_cache_identity(): void {
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			define( 'LINKER_GENIE_SERVICE_TOKEN', 'fixture' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Existing service credential name in an isolated process.
		}
		$expiry  = time() + 3600;
		$key     = 't_' . str_repeat( 'x', 30 );
		$handler = \Mockery::mock( \WC_Session_Handler::class );
		$handler->shouldReceive( 'get_session_cookie' )->andReturn( false, array( $key, (string) $expiry, (string) $expiry, 'fixture' ) );
		$handler->shouldReceive( 'get_customer_id' )->andReturn( $key );
		$handler->shouldReceive( 'destroy_session', 'set', 'set_customer_session_cookie', 'save_data' )->once();
		$woo = \Mockery::mock( \WooCommerce::class );
		$woo->shouldReceive( 'initialize_session' );
		$woo->session = $handler;
		WP_Mock::userFunction( 'WC' )->andReturn( $woo );
		$db         = \Mockery::mock( \wpdb::class );
		$db->prefix = 'wp_';
		$db->shouldReceive( 'prepare' )->andReturn( '' );
		$db->shouldReceive( 'get_var' )->andReturn( $expiry );
		$GLOBALS['wpdb'] = $db; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Native guest row read in the isolated fixture.
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing( static fn( $v ) => $v instanceof WP_Error );
		WP_Mock::userFunction( 'get_current_user_id' )->andReturn( 0 );
		WP_Mock::userFunction( 'wp_validate_auth_cookie' )->andReturn( false );
		WP_Mock::userFunction( 'get_current_blog_id' )->andReturn( 1 );
		WP_Mock::userFunction( 'wp_hash' )->andReturn( str_repeat( 'a', 64 ) );
		WP_Mock::userFunction( 'wp_create_nonce' )->andReturn( 'fixture' );
		WP_Mock::userFunction( 'get_option' )->with( 'linker_planner_url', '' )->andReturn( 'https://planner.test' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code' )->andReturn( 200 );
		WP_Mock::userFunction( 'wp_remote_retrieve_header' )->andReturn( 'application/json' );
		WP_Mock::userFunction( 'wp_remote_retrieve_body' )->andReturnUsing( static fn( $reply ) => $reply['body'] );
		$cache = false;
		WP_Mock::userFunction( 'get_transient' )->andReturnUsing(
			static function () use ( &$cache ) {
				return $cache;
			}
		);
		WP_Mock::userFunction( 'set_transient' )->andReturnUsing(
			static function ( $name, $value, $ttl ) use ( &$cache ) {
				self::assertSame( 300, $ttl );
				$cache = $value;
				return true;
			}
		);
		$paths     = array();
		$transport = new Transport(
			static function ( $url ) use ( &$paths ) {
				$path    = substr( $url, strlen( 'https://planner.test/' ) );
				$paths[] = $path;
				$reply   = 'identity/status' === $path ? array(
					'schema_version' => 1,
					'status'         => 'active',
				)
				: array(
					'schema_version' => 1,
					'runtime_sha256' => str_repeat( 'a', 64 ),
					'models'         => array(),
					'limits'         => array(
						'max_body_bytes' => 1024,
						'max_csv_bytes'  => 512,
						'max_json_depth' => 10,
						'max_page_size'  => 20,
					),
					'private_field'  => 'not public',
				);
				return array( 'body' => wp_json_encode( $reply ) );
			}
		);
		$gateway   = new Gateway( new NativeIdentity(), $transport );
		$request   = new WP_REST_Request( 'POST', '/linker/v1/planner/bootstrap' );
		$request->set_header( 'content-type', 'application/json' );
		$request->set_body( '{"schema_version":1}' );
		$first = $gateway->bootstrap( $request );
		$this->assertInstanceOf( WP_REST_Response::class, $first );
		$this->assertSame(
			array(
				'schema_version'   => 1,
				'cookie_confirmed' => false,
			),
			$first->get_data()
		);
		$this->assertSame( array(), $paths );
		foreach ( array( 1, 2 ) as $attempt ) {
			$response = $gateway->bootstrap( $request );
			$this->assertInstanceOf( WP_REST_Response::class, $response );
			$this->assertTrue( $response->get_data()['cookie_confirmed'] );
			$this->assertArrayNotHasKey( 'private_field', $response->get_data()['runtime'] );
		}
		$this->assertSame( array( 'identity/status', 'version', 'identity/status' ), $paths );
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
