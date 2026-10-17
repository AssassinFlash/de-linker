<?php
/**
 * The route the VPS quality worker hands its verdicts to.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * POST linker-ai/v1/genie/quality: `{judgments: [...], status: {...}}` from the
 * quality worker (services/genie/src/linker_genie/quality/wordpress.py). Only
 * a request carrying the shared token in `X-Linker-Judge-Token` gets in; the
 * token is the `LINKER_GENIE_JUDGE_TOKEN` constant of wp-config.php (the VPS
 * holds the same value as GENIE_JUDGE_TOKEN). A site without the constant
 * refuses every request — the route is closed until it is set.
 *
 * Not `Authorization: Bearer`: LiveCanvas's bundled template system decodes
 * every REST request's bearer token as a JWT on `rest_pre_dispatch` and dies
 * on any other token (measured on g258, 2026-10-17: HTTP 500, "Wrong number
 * of segments"), so the token travels in its own header, as the customer
 * identity does (UserContext::HEADER).
 */
class QualityRoute {

	/**
	 * Route under Proxy::NAMESPACE.
	 */
	public const ROUTE = '/genie/quality';

	/**
	 * The wp-config.php constant that holds the shared token.
	 */
	public const TOKEN_CONSTANT = 'LINKER_GENIE_JUDGE_TOKEN';

	/**
	 * The request header that carries it.
	 */
	public const HEADER = 'X-Linker-Judge-Token';

	/**
	 * Verdicts accepted per request: the worker sends at most fifty
	 * (quality/worker.py, PUSH_BATCH); twice that bounds a misbehaving client.
	 */
	public const MAX_JUDGMENTS = 100;

	/**
	 * Sets up the route.
	 *
	 * @param QualityStore $store Where the verdicts go.
	 * @param string|null  $token The shared token; read from the constant when null (tests pass one).
	 */
	public function __construct(
		private readonly QualityStore $store,
		private readonly ?string $token = null
	) {}

	/**
	 * Registers the route; runs on rest_api_init.
	 */
	public function register(): void {
		register_rest_route(
			Proxy::NAMESPACE,
			self::ROUTE,
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'receive' ),
				'permission_callback' => array( $this, 'authorized' ),
				'args'                => array(
					'judgments' => array(
						'type'     => 'array',
						'required' => true,
					),
					'status'    => array(
						'type' => 'object',
					),
				),
			)
		);
	}

	/**
	 * True when the request carries the configured token.
	 *
	 * @param WP_REST_Request $request Request.
	 * @return bool|WP_Error
	 */
	public function authorized( WP_REST_Request $request ) {
		$token = $this->token();
		if ( '' === $token ) {
			return new WP_Error( 'linker_genie_quality_closed', 'The quality route is not configured.', array( 'status' => 503 ) );
		}
		$sent = (string) $request->get_header( self::HEADER );
		if ( ! hash_equals( $token, $sent ) ) {
			return new WP_Error( 'linker_genie_quality_token', 'Wrong token.', array( 'status' => 401 ) );
		}
		return true;
	}

	/**
	 * Stores the verdicts and the status; answers the turn ids it stored.
	 *
	 * @param WP_REST_Request $request Request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function receive( WP_REST_Request $request ) {
		$judgments = $request->get_param( 'judgments' );
		if ( ! is_array( $judgments ) || count( $judgments ) > self::MAX_JUDGMENTS ) {
			return new WP_Error( 'linker_genie_quality_batch', 'Too many verdicts in one request.', array( 'status' => 400 ) );
		}
		$stored = array();
		foreach ( $judgments as $record ) {
			if ( is_array( $record ) && $this->store->store( $record ) ) {
				$stored[] = (int) $record['turn_id'];
			}
		}
		$status = $request->get_param( 'status' );
		if ( is_array( $status ) ) {
			$this->store->store_status( $status );
		}
		return new WP_REST_Response( array( 'stored' => $stored ) );
	}

	/**
	 * The configured token, empty when there is none.
	 */
	private function token(): string {
		if ( null !== $this->token ) {
			return $this->token;
		}
		return defined( self::TOKEN_CONSTANT ) ? (string) constant( self::TOKEN_CONSTANT ) : '';
	}
}
