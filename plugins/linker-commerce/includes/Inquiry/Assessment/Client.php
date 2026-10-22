<?php
/**
 * Authenticated background call to the existing Genie service.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

/** No OpenRouter credential is copied into WordPress. */
final class Client {
	/**
	 * Read configuration only; never make a health request in a customer submit.
	 */
	public static function configured(): bool {
		return '' !== (string) get_option( 'linker_genie_url', '' ) && defined( 'LINKER_GENIE_SERVICE_TOKEN' ) && '' !== (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' );
	}

	/** One service request bounded by the current background model-attempt deadline.
	 *
	 * @param array<string, mixed> $state Frozen current submission.
	 * @param float                $deadline Absolute claimed model-attempt deadline.
	 * @param array<string,mixed>  $binding Exact server source binding.
	 * @return array<string, mixed>
	 */
	public function assess( array $state, float $deadline, array $binding = array() ): array {
		$remaining = $deadline - microtime( true );
		if ( $remaining <= 0 ) {
			return SendVerdict::unknown( 'deadline' );
		}
		if ( ! self::configured() ) {
			return SendVerdict::unknown( 'service_unavailable' );
		}
		$body = wp_json_encode(
			array(
				'state'             => $state,
				'binding'           => $binding,
				'remaining_seconds' => min( Queue::WAIT_SECONDS, $remaining ),
			)
		);
		if ( false === $body ) {
			return SendVerdict::unknown( 'input_encoding_error' );
		}
		$response = wp_remote_post(
			rtrim( (string) get_option( 'linker_genie_url', '' ), '/' ) . '/inquiries/assess',
			array(
				'timeout'     => $remaining,
				'redirection' => 0,
				'headers'     => array(
					'Content-Type'           => 'application/json',
					'X-Linker-Service-Token' => (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ),
				),
				'body'        => $body,
			)
		);
		if ( is_wp_error( $response ) ) {
			return SendVerdict::unknown( microtime( true ) >= $deadline ? 'deadline' : 'service_unavailable' );
		}
		if ( microtime( true ) >= $deadline ) {
			return SendVerdict::unknown( 'deadline' ); }
		if ( 200 !== wp_remote_retrieve_response_code( $response ) ) {
			return SendVerdict::unknown( 'service_unavailable' );
		}
		return SendVerdict::validate( json_decode( wp_remote_retrieve_body( $response ), true ), $binding );
	}
}
