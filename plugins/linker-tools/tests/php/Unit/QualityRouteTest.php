<?php
/**
 * The route the VPS quality worker reports to.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\QualityRoute;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Tests for QualityRoute.
 *
 * @covers \Linker\Tools\Genie\QualityRoute
 */
final class QualityRouteTest extends TestCase {

	/**
	 * A store that records instead of writing.
	 */
	private function store(): RecordingQualityStore {
		return new RecordingQualityStore();
	}

	/**
	 * A request with the given token header.
	 *
	 * @param string|null $token Header value.
	 */
	private function request( ?string $token ): WP_REST_Request {
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/quality' );
		if ( null !== $token ) {
			$request->set_header( QualityRoute::HEADER, $token );
		}
		return $request;
	}

	/**
	 * Without a configured token the route is closed to everyone.
	 */
	public function test_a_site_without_the_token_refuses_every_request(): void {
		$result = ( new QualityRoute( $this->store(), '' ) )->authorized( $this->request( '' ) );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_quality_closed', $result->get_error_code() );
	}

	/**
	 * Only the exact token gets in.
	 */
	public function test_only_the_shared_token_gets_in(): void {
		$route = new QualityRoute( $this->store(), 'tok-258' );
		$this->assertTrue( $route->authorized( $this->request( 'tok-258' ) ) );
		foreach ( array( null, '', 'tok-25', 'tok-2588', 'Bearer tok-258' ) as $header ) {
			$result = $route->authorized( $this->request( $header ) );
			$this->assertInstanceOf( WP_Error::class, $result, (string) $header );
			$this->assertSame( array( 'status' => 401 ), $result->get_error_data() );
		}
	}

	/**
	 * The answer names the turns the site stored; a verdict for a conversation
	 * the site does not have is not among them, and the status is kept.
	 */
	public function test_receive_answers_the_turns_it_stored(): void {
		$store   = $this->store();
		$request = $this->request( 'tok-258' );
		$request->set_param(
			'judgments',
			array(
				array(
					'turn_id'         => 41,
					'conversation_id' => 812,
				),
				array(
					'turn_id'         => 42,
					'conversation_id' => 9999,
				),
			)
		);
		$request->set_param( 'status', array( 'retrying' => 1 ) );

		$response = ( new QualityRoute( $store, 'tok-258' ) )->receive( $request );

		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( array( 'stored' => array( 41 ) ), $response->get_data() );
		$this->assertCount( 2, $store->records );
		$this->assertSame( array( array( 'retrying' => 1 ) ), $store->statuses );
	}

	/**
	 * A batch larger than the worker ever sends is refused whole.
	 */
	public function test_an_oversized_batch_is_refused(): void {
		$request = $this->request( 'tok-258' );
		$request->set_param( 'judgments', array_fill( 0, QualityRoute::MAX_JUDGMENTS + 1, array() ) );
		$store  = $this->store();
		$result = ( new QualityRoute( $store, 'tok-258' ) )->receive( $request );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( array(), $store->records );
	}

	/**
	 * The route registers under the proxy's namespace with the token check.
	 */
	public function test_register_adds_the_route_behind_the_token(): void {
		$route = new QualityRoute( $this->store(), 'tok-258' );
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times'  => 1,
				'args'   => array(
					'linker-ai/v1',
					'/genie/quality',
					WP_Mock\Functions::type( 'array' ),
				),
				'return' => static function ( $space, $path, $args ) use ( $route ) {
					unset( $space, $path );
					return 'POST' === $args['methods'] && array( $route, 'authorized' ) === $args['permission_callback'];
				},
			)
		);
		$route->register();
		$this->assertConditionsMet();
	}
}
