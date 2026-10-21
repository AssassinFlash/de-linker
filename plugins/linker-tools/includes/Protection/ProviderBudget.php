<?php
/**
 * Private provider dispatch budget, shared with the Python transports.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use WP_Error;

/** PHP asks Genie, never the inverse: no nested WordPress worker dependency. */
final class ProviderBudget {

	/** Register the trusted, server-only translation seam. */
	public function register(): void {
		add_filter( 'linker_tools_provider_debit', array( $this, 'take' ), 10, 2 );
	}

	/**
	 * Reserve exactly one immediate upstream send; do not retry this permission.
	 *
	 * @param mixed  $previous Earlier server decision.
	 * @param string $provider Fixed server-selected provider.
	 * @return true|WP_Error Explicit result, never a client-supplied receipt.
	 */
	public function take( mixed $previous, string $provider ): true|WP_Error {
		if ( ! in_array( $provider, array( 'deepseek', 'jev' ), true ) ) {
			return self::failure();
		}
		$base  = (string) get_option( 'linker_genie_url', '' );
		$token = defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ? (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ) : '';
		if ( '' === $base || '' === $token ) {
			return self::failure();
		}
		$response = wp_remote_post(
			rtrim( $base, '/' ) . '/budget/take',
			array(
				// SQLite busy timeout is 5s. This call has no model work and no
				// callback into WordPress (#521 worker/deadlock analysis).
				'timeout' => 8,
				'headers' => array(
					'Content-Type'           => 'application/json',
					'X-Linker-Service-Token' => $token,
				),
				'body'    => (string) wp_json_encode(
					array(
						'provider' => $provider,
						'attempt'  => wp_generate_uuid4(),
					)
				),
			)
		);
		if ( is_wp_error( $response ) ) {
			return self::failure();
		}
		$code = (int) wp_remote_retrieve_response_code( $response );
		$body = json_decode( (string) wp_remote_retrieve_body( $response ), true );
		// null means the service's guard is off: PHP enforce must fail closed.
		return 200 === $code && is_array( $body ) && is_int( $body['remaining'] ?? null ) && $body['remaining'] >= 0
			? true : self::failure( 429 === $code ? 429 : 503 );
	}

	/**
	 * Private safe diagnostic; translated customer copy belongs to the consumer.
	 *
	 * @param int $status Failure status.
	 */
	private static function failure( int $status = 503 ): WP_Error {
		return new WP_Error( 'linker_provider_budget', 'Provider request could not be admitted.', array( 'status' => $status ) );
	}
}
