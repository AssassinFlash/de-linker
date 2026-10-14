<?php
/**
 * The configurator's same-origin route to the sizing engine.
 *
 * The app used to fetch the engine's address from the browser. That breaks
 * on the production engine's certificate: `https://<ip>:8443` is self-signed
 * (CN=linker-design-engine), and a browser cannot pin it the way the site's
 * own PHP does (mu-plugins/linker-engine-pin.php) — the request is refused
 * before any response (measured in-page 2026-10-14: `TypeError: Failed to
 * fetch`). So the browser talks to this route instead, and the site's PHP
 * makes the hop the Genie already makes: server to server, with the pin.
 *
 * Everything else stays where it was: the engine's address is still the
 * option `linker_engine_url`, the app still calls the same paths, and the
 * upstream's status codes travel back unchanged (the app's screens read 422,
 * 404 and 503 by value). Only paths the app actually calls are forwarded —
 * this is a window, not a general proxy. `report/pdf` answers with bytes,
 * so it is served as a stream, not as JSON.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Configurator;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * FORWARD to the engine, from the machine that can verify its certificate.
 */
final class EngineProxy {

	/**
	 * REST namespace, shared with the Genie's routes (one plugin, one surface).
	 */
	public const NAMESPACE = 'linker-ai/v1';

	/**
	 * Route the mount point hands to the app as its engine base URL.
	 */
	public const ROUTE = '/engine';

	/**
	 * The engine's base URL: `just serve <name>` writes it locally, the
	 * cutover writes it in production (docs/local-stack.md).
	 */
	public const OPTION = 'linker_engine_url';

	/**
	 * Paths the app calls (src/configurator/api/engine.ts), and nothing else.
	 */
	private const PATHS = array(
		'~^geo/plz/\d{4,5}$~',
		'~^design/residential$~',
		'~^design/commercial$~',
		'~^roof/outline$~',
		'~^roof/pack$~',
		'~^report/pdf$~',
		'~^health$~',
	);

	/**
	 * Constructor.
	 *
	 * @param callable( string, string, string ): (array{0:int,1:array<string,string>,2:string}|WP_Error)|null $fetch Optional upstream double for tests: method, URL, body.
	 */
	public function __construct( private mixed $fetch = null ) {}

	/**
	 * Registers the route; runs on rest_api_init.
	 */
	public function register(): void {
		$args = array(
			'path' => array(
				'type'     => 'string',
				'required' => true,
			),
		);
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE . '/(?P<path>.+)',
			array(
				array(
					'methods'             => 'GET',
					'callback'            => array( $this, 'forward' ),
					'permission_callback' => '__return_true',
					'args'                => $args,
				),
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, 'forward' ),
					'permission_callback' => '__return_true',
					'args'                => $args,
				),
			)
		);
		add_filter( 'rest_pre_serve_request', array( self::class, 'serve_pdf' ), 10, 2 );
	}

	/**
	 * Serves the report's PDF as bytes, not JSON.
	 *
	 * A PDF arrives as a plain string; the REST encoder would escape the
	 * whole document into a JSON string. When the route answered with that
	 * content type the payload is echoed as it came and the encoder stands
	 * down; everything else is served the normal way.
	 *
	 * @param bool             $served Whether something served the request already.
	 * @param WP_REST_Response $result The response the route built.
	 * @return bool
	 */
	public static function serve_pdf( $served, $result ): bool {
		if ( ! $result instanceof WP_REST_Response ) {
			return (bool) $served;
		}
		$content_type = (string) ( $result->get_headers()['Content-Type'] ?? '' );
		if ( str_starts_with( $content_type, 'application/pdf' ) ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- the engine's own PDF bytes.
			echo $result->get_data();
			return true;
		}
		return (bool) $served;
	}

	/**
	 * Forwards one request to the engine and brings its answer back.
	 *
	 * @param WP_REST_Request $request The app's request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function forward( WP_REST_Request $request ) {
		$path    = trim( (string) $request->get_param( 'path' ), '/' );
		$allowed = false;
		foreach ( self::PATHS as $pattern ) {
			if ( 1 === preg_match( $pattern, $path ) ) {
				$allowed = true;
				break;
			}
		}
		if ( ! $allowed ) {
			return new WP_Error(
				'linker_engine_path',
				'Unknown engine path.',
				array( 'status' => 404 )
			);
		}
		$base = rtrim( (string) get_option( self::OPTION, '' ), '/' );
		if ( '' === $base ) {
			return new WP_Error(
				'linker_engine_unconfigured',
				'The engine is not configured.',
				array( 'status' => 503 )
			);
		}

		$method = 'POST' === $request->get_method() ? 'POST' : 'GET';
		$url    = $base . '/' . $path;
		if ( 'GET' === $method ) {
			$query = array();
			foreach ( $request->get_query_params() as $key => $value ) {
				// WordPress's own plumbing (`rest_route`, the locale hint, the
				// nonce) belongs to this route, not to the engine.
				if ( str_starts_with( (string) $key, '_' ) || 'rest_route' === $key ) {
					continue;
				}
				$query[ $key ] = $value;
			}
			if ( array() !== $query ) {
				$url = add_query_arg( $query, $url );
			}
		}
		$body = 'POST' === $method ? (string) $request->get_body() : '';

		$answer = $this->call( $method, $url, $body );
		if ( is_wp_error( $answer ) ) {
			return new WP_Error(
				'linker_engine_upstream',
				'The engine did not answer.',
				array( 'status' => 502 )
			);
		}
		list( $status, $headers, $payload ) = $answer;

		$content_type = (string) ( $headers['content-type'] ?? '' );
		if ( str_starts_with( $content_type, 'application/pdf' ) && $status < 400 ) {
			$response = new WP_REST_Response( $payload, $status );
			$response->header( 'Content-Type', 'application/pdf' );
			$response->header( 'Content-Disposition', 'attachment; filename="design-report.pdf"' );
			return $response;
		}

		$decoded = json_decode( $payload, true );
		return new WP_REST_Response(
			null === $decoded ? array( 'detail' => $payload ) : $decoded,
			$status
		);
	}

	/**
	 * The one HTTP seam: wp_remote_* in serving, the double in tests.
	 *
	 * The headers come back as a flat lowercase map, single string values —
	 * the Requests dictionary's own shape (string or array of strings) is
	 * flattened here so both callers read the same thing.
	 *
	 * @param string $method HTTP method to use upstream.
	 * @param string $url    Absolute engine URL, query included.
	 * @param string $body   Raw JSON body for POST, empty for GET.
	 * @return array{0:int,1:array<string,string>,2:string}|WP_Error
	 */
	private function call( string $method, string $url, string $body ) {
		if ( is_callable( $this->fetch ) ) {
			return ( $this->fetch )( $method, $url, $body );
		}
		$args = array(
			// Generous: one roof outline can spend seconds in the LoD2 source
			// before the engine answers, and the engine caps its own work.
			'timeout' => 60.0,
			'headers' => array( 'Content-Type' => 'application/json' ),
		);
		if ( 'POST' === $method ) {
			$args['body'] = $body;
		}
		$response = 'POST' === $method
			? wp_remote_post( $url, $args )
			: wp_remote_get( $url, $args );
		if ( is_wp_error( $response ) ) {
			return $response;
		}
		$headers = array();
		foreach ( (array) wp_remote_retrieve_headers( $response ) as $key => $value ) {
			$headers[ strtolower( (string) $key ) ] = strtolower(
				is_array( $value ) ? (string) ( $value[0] ?? '' ) : (string) $value
			);
		}
		return array(
			(int) wp_remote_retrieve_response_code( $response ),
			$headers,
			(string) wp_remote_retrieve_body( $response ),
		);
	}
}
