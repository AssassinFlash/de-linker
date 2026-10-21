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

	/**
	 * One service request bounded by the original acceptance deadline.
	 *
	 * @param array<string, mixed> $state Frozen current submission.
	 * @param float                $deadline Absolute acceptance deadline.
	 * @return array<string, mixed>
	 */
	public function assess( array $state, float $deadline ): array {
		$remaining = $deadline - microtime( true );
		if ( $remaining <= 0 ) {
			return Result::unknown( 'deadline' );
		}
		if ( ! self::configured() ) {
			return Result::unknown( 'service_unavailable' );
		}
		$body = wp_json_encode(
			array(
				'state'             => $state,
				'remaining_seconds' => min( Queue::WAIT_SECONDS, $remaining ),
			)
		);
		if ( false === $body ) {
			return Result::unknown( 'input_encoding_error' );
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
			return Result::unknown( microtime( true ) >= $deadline ? 'deadline' : 'service_unavailable' );
		}
		if ( 200 !== wp_remote_retrieve_response_code( $response ) ) {
			return Result::unknown( 'service_unavailable' );
		}
		return Result::validate( json_decode( wp_remote_retrieve_body( $response ), true ) );
	}
}
