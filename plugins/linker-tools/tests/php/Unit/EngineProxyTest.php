<?php
/**
 * Tests for the configurator's same-origin route to the sizing engine.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Configurator\EngineProxy;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_REST_Request;
use WP_REST_Response;
use WP_Error;

/**
 * Tests for EngineProxy: what it forwards, what it refuses, and how the
 * upstream's answer travels back.
 *
 * @covers \Linker\Tools\Configurator\EngineProxy
 */
final class EngineProxyTest extends TestCase {

	/**
	 * Without the option there is no engine to talk to.
	 */
	public function test_unconfigured_engine_fails_closed(): void {
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( EngineProxy::OPTION, '' ),
				'return' => '',
			)
		);

		$result = $this->proxy()->forward( $this->request( 'GET', 'geo/plz/10115' ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_engine_unconfigured', $result->get_error_code() );
		$this->assertSame( 503, $result->get_error_data( 'linker_engine_unconfigured' )['status'] );
		$this->assertConditionsMet();
	}

	/**
	 * This is a window, not a general proxy: a path the app never calls does
	 * not travel, whatever it is.
	 */
	public function test_an_off_list_path_is_refused_without_reading_the_option(): void {
		WP_Mock::userFunction( 'get_option', array( 'times' => 0 ) );

		foreach ( array( 'admin/restart', 'design/residential/extra', 'geo/plz/../../etc' ) as $path ) {
			$result = $this->proxy()->forward( $this->request( 'GET', $path ) );
			$this->assertInstanceOf( WP_Error::class, $result, $path );
			$this->assertSame( 'linker_engine_path', $result->get_error_code(), $path );
			$this->assertSame( 404, $result->get_error_data( 'linker_engine_path' )['status'], $path );
		}
		$this->assertConditionsMet();
	}

	/**
	 * A GET forwards with the engine's own query, and the answer comes back
	 * decoded with the upstream's status.
	 */
	public function test_a_postcode_lookup_forwards_and_returns_the_answer(): void {
		$this->wp_functions();
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( EngineProxy::OPTION, '' ),
				'return' => 'http://127.0.0.1:8976',
			)
		);
		$caught = array( '', '' );
		$proxy  = new EngineProxy(
			static function ( string $method, string $url ) use ( &$caught ) {
				$caught = array( $method, $url );
				return array( 200, array( 'content-type' => 'application/json' ), '{"place":"Berlin"}' );
			}
		);
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static fn( array $query, string $url ): string => $url . '?' . http_build_query( $query ),
			)
		);
		$request = $this->request( 'GET', 'geo/plz/10115' );
		$request->set_query_params(
			array(
				'foo'     => 'bar',
				'_locale' => 'user',
			)
		);

		$response = $proxy->forward( $request );

		$this->assertSame( 'GET', $caught[0] );
		// The engine's URL, with the caller's query — not WordPress's own
		// plumbing (`_locale` is this route's, not the engine's).
		$this->assertSame( 'http://127.0.0.1:8976/geo/plz/10115?foo=bar', $caught[1] );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( array( 'place' => 'Berlin' ), $response->get_data() );
		$this->assertConditionsMet();
	}

	/**
	 * A POST forwards the body byte for byte and the upstream's refusal —
	 * 422 with `detail.field` — travels back with its status, because the
	 * app's screens read the status codes by value.
	 */
	public function test_a_design_post_keeps_the_body_and_the_refusal_status(): void {
		$this->wp_functions();
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( EngineProxy::OPTION, '' ),
				'return' => 'http://127.0.0.1:8976',
			)
		);
		$body    = '{"postcode":"10115","pv_kwp":10}';
		$caught  = '';
		$proxy   = new EngineProxy(
			static function ( string $method, string $url, string $sent ) use ( &$caught ) {
				$caught = $sent;
				return array( 422, array( 'content-type' => 'application/json' ), '{"detail":{"field":"pv_kwp"}}' );
			}
		);
		$request = $this->request( 'POST', 'design/residential' );
		$request->set_body( $body );

		$response = $proxy->forward( $request );

		$this->assertSame( $body, $caught );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( 422, $response->get_status() );
		$this->assertSame( array( 'detail' => array( 'field' => 'pv_kwp' ) ), $response->get_data() );
		$this->assertConditionsMet();
	}

	/**
	 * A dead engine is 502, the way a dead Genie is.
	 */
	public function test_an_unreachable_engine_is_a_gateway_error(): void {
		$this->wp_functions();
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( EngineProxy::OPTION, '' ),
				'return' => 'http://127.0.0.1:8976',
			)
		);
		$proxy = new EngineProxy(
			static fn(): WP_Error => new WP_Error( 'http_request_failed', 'timeout' )
		);

		$result = $proxy->forward( $this->request( 'POST', 'roof/outline' ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_engine_upstream', $result->get_error_code() );
		$this->assertSame( 502, $result->get_error_data( 'linker_engine_upstream' )['status'] );
		$this->assertConditionsMet();
	}

	/**
	 * The report is bytes: the payload comes back untouched under the pdf
	 * content type, which is what the serving filter keys on.
	 */
	public function test_the_pdf_travels_as_bytes_under_its_content_type(): void {
		$this->wp_functions();
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( EngineProxy::OPTION, '' ),
				'return' => 'http://127.0.0.1:8976',
			)
		);
		$bytes   = "%PDF-1.4\nbinary\x00bytes";
		$proxy   = new EngineProxy(
			static fn(): array => array( 200, array( 'content-type' => 'application/pdf' ), $bytes )
		);
		$request = $this->request( 'POST', 'report/pdf' );
		$request->set_body( '{"postcode":"10115"}' );

		$response = $proxy->forward( $request );

		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( $bytes, $response->get_data() );
		$this->assertStringStartsWith( 'application/pdf', (string) ( $response->get_headers()['Content-Type'] ?? '' ) );
		$this->assertConditionsMet();
	}

	/**
	 * The serving filter echoes a pdf response and stands down for the rest.
	 */
	public function test_the_pdf_hook_echoes_bytes_and_stands_down_for_json(): void {
		$pdf = new WP_REST_Response( '%PDF-bytes', 200 );
		$pdf->header( 'Content-Type', 'application/pdf' );

		ob_start();
		$served = EngineProxy::serve_pdf( false, $pdf );
		$echoed = ob_get_clean();

		$this->assertTrue( $served );
		$this->assertSame( '%PDF-bytes', $echoed );

		$json = new WP_REST_Response( array( 'ok' => true ), 200 );
		ob_start();
		$served = EngineProxy::serve_pdf( false, $json );
		$echoed = ob_get_clean();

		$this->assertFalse( $served );
		$this->assertSame( '', $echoed );
	}

	/**
	 * The WordPress pieces every forwarding test touches.
	 */
	private function wp_functions(): void {
		WP_Mock::userFunction(
			'is_wp_error',
			array(
				'return' => static fn( $thing ): bool => $thing instanceof \WP_Error,
			)
		);
	}

	/**
	 * The proxy under test; each test builds its own double.
	 */
	private function proxy(): EngineProxy {
		return new EngineProxy();
	}

	/**
	 * A request to the route with its path parameter set, as the router
	 * would hand it over.
	 *
	 * @param string $method HTTP method of the request.
	 * @param string $path   The engine path the route matched.
	 */
	private function request( string $method, string $path ): WP_REST_Request {
		$request = new WP_REST_Request( $method, '/linker-ai/v1/engine/' . $path );
		$request->set_param( 'path', $path );
		return $request;
	}
}
