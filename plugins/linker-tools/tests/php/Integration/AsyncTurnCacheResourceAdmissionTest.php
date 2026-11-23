<?php
/**
 * Native Genie progress is private and changes between consecutive polls.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Genie\Proxy;
use PHPUnit\Framework\TestCase;
use WP_REST_Request;
use WP_REST_Response;

/** Native cache control for owner-bound turn routes.
 *
 * @coversNothing
 */
final class AsyncTurnCacheResourceAdmissionTest extends TestCase {
	/** The public REST server marks every owner-bound job response private to LiteSpeed.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_native_job_responses_never_enter_the_litespeed_page_cache(): void {
		define( 'REST_REQUEST', true ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- An actual public REST request.
		$server  = rest_get_server();
		$route   = '/' . Proxy::NAMESPACE . Proxy::ROUTE;
		$job     = $route . '/' . wp_generate_uuid4();
		$unknown = $server->dispatch( new WP_REST_Request( 'GET', $job ) );
		$this->assertSame( 404, $unknown->get_status() );
		foreach ( array(
			array( 'POST', $route . '/start', new WP_REST_Response( array( 'status' => 'running' ), 202 ) ),
			array( 'GET', $job, new WP_REST_Response( array( 'status' => 'running' ) ) ),
			array( 'GET', $job, new WP_REST_Response( array( 'status' => 'completed' ) ) ),
			array( 'HEAD', $job, new WP_REST_Response( array(), 409 ) ),
			array( 'GET', $job, $unknown ),
		) as list( $method, $path, $reply ) ) {
			$sent = apply_filters( 'rest_post_dispatch', $reply, $server, new WP_REST_Request( $method, $path ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Invoke WordPress's own serving boundary.
			$this->assertSame( 'no-cache', $sent->get_headers()['X-LiteSpeed-Cache-Control'] ?? null );
			$this->assertStringContainsString( 'no-store', $sent->get_headers()['Cache-Control'] );
		}
		$this->assertTrue( defined( 'DONOTCACHEPAGE' ) && DONOTCACHEPAGE );
	}
}
