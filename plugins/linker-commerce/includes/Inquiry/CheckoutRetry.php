<?php
/**
 * Native Woo handoff for a failed preliminary inquiry's navigation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Protection\FormRecovery;

/** An opaque handle addresses one Woo session's retained form. */
final class CheckoutRetry {

	public const HANDLE   = 'linker_inquiry_retry';
	private const SESSION = 'linker_inquiry_checkout_retries';

	/** Preserve the native WordPress authentication context inside the Woo session. */
	public static function context(): string {
		return hash_hmac( 'sha256', get_current_user_id() . '|' . wp_get_session_token(), wp_salt( 'nonce' ) );
	}

	/**
	 * Retain one server-validated form with the native recovery window.
	 *
	 * @param array<string,mixed> $flash    Already retained fields and outcome.
	 * @param string              $previous Previous handle for this checkout retry.
	 */
	public static function remember( array $flash, string $previous ): string {
		$entries        = self::active();
		$actor          = self::context();
		$id             = isset( $entries[ $previous ] ) && $entries[ $previous ]['actor'] === $actor ? $previous : wp_generate_uuid4();
		$entries[ $id ] = array(
			'actor' => $actor,
			'until' => time() + FormRecovery::RETENTION_SECONDS,
			'flash' => $flash,
		);
		WC()->session->set( self::SESSION, $entries );
		return $id;
	}

	/** Read only the explicitly continued attempt, under its original native authentication context.
	 *
	 * @param string $id Opaque link handle.
	 * @return array<string,mixed>|null
	 */
	public static function read( string $id ): ?array {
		if ( ! wp_is_uuid( $id, 4 ) ) {
			return null;
		}
		$entry = self::active()[ $id ] ?? null;
		return null !== $entry && hash_equals( $entry['actor'], self::context() ) ? $entry['flash'] : null;
	}

	/** Clear this attempt after the native receipt has been found.
	 *
	 * @param string $id Opaque form handle.
	 */
	public static function forget( string $id ): void {
		if ( ! wp_is_uuid( $id, 4 ) ) {
			return;
		}
		$entries = self::active();
		if ( isset( $entries[ $id ] ) && hash_equals( $entries[ $id ]['actor'], self::context() ) ) {
			unset( $entries[ $id ] );
			WC()->session->set( self::SESSION, $entries );
		}
	}

	/** Checkout attempts still inside the native recovery window.
	 *
	 * @return array<string,array{actor:string,until:int,flash:array<string,mixed>}>
	 */
	private static function active(): array {
		$now = time();
		return array_filter( (array) WC()->session->get( self::SESSION, array() ), static fn ( array $entry ): bool => $entry['until'] > $now );
	}
}
