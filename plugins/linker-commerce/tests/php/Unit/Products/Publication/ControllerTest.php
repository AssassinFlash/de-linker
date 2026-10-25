<?php
/**
 * Unavailable authority is a service error, never an empty current scope.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Publication\Controller;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Public consumers distinguish unreadable authority from current empty scope.
 *
 * @covers \Linker\Commerce\Products\Publication\Controller
 */
final class ControllerTest extends TestCase {
	/** Every public authority action must fail explicitly when fresh reads cannot run. */
	public function test_missing_runtime_refresh_is_service_unavailable(): void {
		WP_Mock::userFunction( 'nocache_headers' );
		WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( false );
		$request = Mockery::mock( \WP_REST_Request::class );
		$request->shouldReceive( 'get_json_params' )->andReturn(
			array(
				'models'    => array( 'unknown' ),
				'products'  => array(),
				'documents' => array(),
			)
		);
		foreach ( array( 'manifest', 'validate', 'identify' ) as $path ) {
			$response = ( new Controller() )->dispatch( $path, $request );
			$this->assertInstanceOf( \WP_Error::class, $response );
			$this->assertSame( 'publication_unavailable', $response->get_error_code() );
			$this->assertSame( array( 'status' => 503 ), $response->get_error_data() );
		}
	}

	/** The engineering feed also exposes a failed actual refresh as unavailable. */
	public function test_failed_cache_refresh_cannot_return_a_feed(): void {
		WP_Mock::userFunction( 'nocache_headers' );
		WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( false );
		$request = Mockery::mock( \WP_REST_Request::class );
		$request->shouldReceive( 'get_param' )->with( 'since' )->andReturn( null );
		$response = ( new \Linker\Commerce\Products\EngineeringFeedController() )->get_items( $request );
		$this->assertInstanceOf( \WP_Error::class, $response );
		$this->assertSame( 'publication_unavailable', $response->get_error_code() );
		$this->assertSame( array( 'status' => 503 ), $response->get_error_data() );
	}
}
