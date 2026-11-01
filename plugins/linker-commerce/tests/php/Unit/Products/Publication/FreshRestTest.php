<?php
/**
 * Fresh Woo authority responses must not be stored by the server cache.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Publication\FreshRest;
use Linker\Commerce\Products\Publication\Controller;
use Linker\Commerce\Products\EngineeringFeedController;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Verify route-scoped server-cache policy.
 *
 * @covers \Linker\Commerce\Products\Publication\FreshRest
 */
final class FreshRestTest extends TestCase {
	/** Install at REST response time, including core validation and permission errors. */
	public function test_registers_the_native_response_filter(): void {
		$policy = new FreshRest();
		WP_Mock::expectFilterAdded( 'rest_post_dispatch', array( $policy, 'response' ), 20, 3 );
		$policy->register();
		$this->assertConditionsMet();
	}

	/**
	 * Registered controller callbacks that fail their fresh read still reach the
	 * same policy after WordPress converts their errors to REST responses.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_registered_authority_callbacks_fail_closed_without_cache(): void {
		$routes = array();
		WP_Mock::userFunction( 'register_rest_route' )->andReturnUsing(
			static function ( string $route_namespace, string $route, array $args ) use ( &$routes ): bool {
				$routes[ '/' . $route_namespace . $route ] = $args;
				return true;
			}
		);
		WP_Mock::userFunction( 'nocache_headers' )->zeroOrMoreTimes();
		WP_Mock::userFunction( '__' )->andReturnUsing( static fn ( string $text ): string => $text );
		WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( false );
		( new Controller() )->register_routes();
		( new EngineeringFeedController() )->register_routes();
		$policy = new FreshRest();
		foreach ( array( '/linker/v1/publication/manifest', '/linker/v1/engineering-feed' ) as $route ) {
			$this->assertArrayHasKey( $route, $routes );
			$request = Mockery::mock( WP_REST_Request::class );
			$request->shouldReceive( 'get_route' )->andReturn( $route );
			$request->shouldReceive( 'get_json_params' )->andReturn( array() );
			$request->shouldReceive( 'get_param' )->with( 'since' )->andReturn( null );
			$callback = '/linker/v1/engineering-feed' === $route ? $routes[ $route ][0]['callback'] : $routes[ $route ]['callback'];
			$error    = $callback( $request );
			$this->assertInstanceOf( \WP_Error::class, $error );
			$this->assertSame( 503, $error->get_error_data()['status'] );
			$response = new WP_REST_Response( array( 'code' => $error->get_error_code() ), 503 );
			$policy->response( $response, null, $request );
			$this->assertSame( 'no-cache', $response->get_headers()['X-LiteSpeed-Cache-Control'] );
		}
	}

	/**
	 * A non-REST page can preload both real GET callbacks without changing its
	 * global cache state or emitting HTTP headers for the outer HTML.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_registered_get_callbacks_return_uncacheable_current_data(): void {
		$routes = array();
		WP_Mock::userFunction( 'register_rest_route' )->andReturnUsing(
			static function ( string $route_namespace, string $route, array $args ) use ( &$routes ): bool {
				$routes[ '/' . $route_namespace . $route ] = $args;
				return true;
			}
		);
		WP_Mock::userFunction( '__' )->andReturnUsing( static fn ( string $text ): string => $text );
		WP_Mock::userFunction( 'nocache_headers' )->never();
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'get_posts' )->andReturn( array() );
		WP_Mock::userFunction( '_prime_post_caches' );
		WP_Mock::userFunction( 'update_postmeta_cache' );
		WP_Mock::userFunction( 'update_object_term_cache' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing( static fn ( mixed $value ): bool => $value instanceof \WP_Error );
		( new Controller() )->register_routes();
		( new EngineeringFeedController() )->register_routes();
		foreach ( array( '/linker/v1/publication/manifest', '/linker/v1/engineering-feed' ) as $route ) {
			$request = Mockery::mock( WP_REST_Request::class );
			$request->shouldReceive( 'get_route' )->andReturn( $route );
			$request->shouldReceive( 'get_json_params' )->andReturn( array() );
			$request->shouldReceive( 'get_param' )->with( 'since' )->andReturn( null );
			$callback = '/linker/v1/engineering-feed' === $route ? $routes[ $route ][0]['callback'] : $routes[ $route ]['callback'];
			$actual   = $callback( $request );
			$response = $actual instanceof WP_REST_Response ? $actual : new WP_REST_Response( $actual );
			( new FreshRest() )->response( $response, null, $request );
			$this->assertSame( 200, $response->get_status() );
			$this->assertSame( 'no-cache', $response->get_headers()['X-LiteSpeed-Cache-Control'] );
			$this->assertNotEmpty( (array) $response->get_data() );
		}
		$this->assertFalse( defined( 'DONOTCACHEPAGE' ) );
	}

	/**
	 * The no-cache instruction covers both successful responses and errors, and
	 * does not change adjacent routes' caching contract.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_current_authority_routes_are_not_cacheable(): void {
		define( 'REST_REQUEST', true ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- simulate WordPress's direct REST request.
		$policy = new FreshRest();
		$other  = new WP_REST_Response( array( 'ok' => true ) );
		$this->assertSame( $other, $policy->response( $other, null, new WP_REST_Request( 'GET', '/linker/v1/selection-facts' ) ) );
		$this->assertArrayNotHasKey( 'X-LiteSpeed-Cache-Control', $other->get_headers() );
		$this->assertFalse( defined( 'DONOTCACHEPAGE' ) );

		WP_Mock::userFunction( 'nocache_headers' )->zeroOrMoreTimes();
		foreach ( array( '/linker/v1/publication/manifest', '/linker/v1/publication/validate', '/linker/v1/publication/identify', '/linker/v1/publication/jobs/claim', '/linker/v1/publication/jobs/ack', '/linker/v1/engineering-feed' ) as $route ) {
			foreach ( array( 200, 400, 403, 503 ) as $status ) {
				$response = new WP_REST_Response( array( 'status' => $status ), $status );
				$this->assertSame( $response, $policy->response( $response, null, new WP_REST_Request( 'GET', $route ) ) );
				$this->assertSame( $status, $response->get_status() );
				$this->assertSame( 'no-cache', $response->get_headers()['X-LiteSpeed-Cache-Control'] );
				$this->assertSame( 'no-store, private, max-age=0', $response->get_headers()['Cache-Control'] );
			}
		}
		$this->assertTrue( defined( 'DONOTCACHEPAGE' ) && DONOTCACHEPAGE );
	}
}
