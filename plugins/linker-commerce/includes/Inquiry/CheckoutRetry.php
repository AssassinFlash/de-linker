<?php
/**
 * Native Woo handoff for a failed preliminary inquiry's navigation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Planning\DraftTransfer;
use Linker\Commerce\Protection\Ledger;

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
	 * @param bool                $fresh    Persist against the current native draft before redirecting.
	 */
	public static function remember( array $flash, string $previous, bool $fresh = false ): ?string {
		$session = WC()->session;
		if ( $session instanceof \WC_Session_Handler && ( $fresh || false === has_action( 'shutdown', array( $session, 'save_data' ) ) ) ) {
			return self::write_current( $session, static fn (): string => self::store( $flash, $previous ) );
		}
		return self::store( $flash, $previous );
	}

	/**
	 * The native writer saves the entire session, so reload under the draft lock.
	 *
	 * @template T
	 * @param \WC_Session_Handler $session Native Woo session.
	 * @param callable():T        $write Change to make in the current session.
	 * @return T|null
	 */
	private static function write_current( \WC_Session_Handler $session, callable $write ): mixed {
		remove_action( 'shutdown', array( $session, 'save_data' ), 20 );
		$customer  = $session->get_customer_id();
		$cookie    = $session->get_session_cookie();
		$new_guest = false === $cookie && ! is_user_logged_in();
		if ( ! $new_guest && ( $cookie[0] ?? (string) get_current_user_id() ) !== $customer ) {
			return null;
		}
		$result = null;
		try {
			Lock::run(
				DraftTransfer::session_lock( $customer ),
				static function () use ( $session, $new_guest, $write, &$result ): void {
					if ( ! $new_guest ) {
						DraftTransfer::evict_session_cache( $session );
						$session->init_session_cookie();
					}
					$result = $write();
					$session->save_data();
					DraftTransfer::evict_session_cache( $session );
					$stored = $session->get_session_data();
					if ( maybe_unserialize( $stored[ self::SESSION ] ?? null ) !== $session->get( self::SESSION ) ) {
						$result = null;
					}
				},
				wait_seconds: 1,
				guard_connection: true
			);
		} catch ( \Throwable $error ) {
			return null;
		}
		return $result;
	}

	/**
	 * Bind the recovery fields to this Woo session and WordPress identity.
	 *
	 * @param array<string,mixed> $flash Retained input and outcome.
	 * @param string              $previous Previous attempt handle.
	 */
	private static function store( array $flash, string $previous ): string {
		$entries        = self::active();
		$actor          = self::context();
		$id             = isset( $entries[ $previous ] ) && $entries[ $previous ]['actor'] === $actor ? $previous : wp_generate_uuid4();
		$entries[ $id ] = array(
			'actor' => $actor,
			'until' => time() + Ledger::RECEIPT_SECONDS,
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
	 * @param string $id    Opaque form handle.
	 * @param bool   $fresh Reload the native draft before persisting the deletion.
	 */
	public static function forget( string $id, bool $fresh = false ): void {
		$session = WC()->session;
		if ( $fresh && $session instanceof \WC_Session_Handler ) {
			remove_action( 'shutdown', array( $session, 'save_data' ), 20 );
			if ( wp_is_uuid( $id, 4 ) ) {
				self::write_current( $session, static fn () => self::remove( $id ) );
			}
			return;
		}
		self::remove( $id );
	}

	/**
	 * Drop this actor's retained form.
	 *
	 * @param string $id Opaque form handle.
	 */
	private static function remove( string $id ): void {
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
