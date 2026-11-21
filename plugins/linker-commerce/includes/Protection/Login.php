<?php
/**
 * Origin-specific backoff for sustained failed credential attempts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\RateLimit;
use WP_Error;
use WP_User;

/** WordPress checks the credentials and any configured second factor. */
final class Login {
	/** Server-side threshold previously used for repeated failures from one connection. */
	private const FAILURES = 100;

	/** Count only rejected passwords, independently for each account and source. */
	public function register(): void {
		add_action( 'wp_login_failed', array( $this, 'failed' ), 10, 2 );
		add_filter( 'wp_authenticate_user', array( $this, 'before_password' ), 5 );
		add_action( Module::MAINTENANCE, array( $this, 'cleanup' ) );
	}

	/**
	 * @param string   $login Native login identifier.
	 * @param WP_Error $error Reason supplied by the WordPress authenticator.
	 */
	public function failed( string $login, WP_Error $error ): void {
		if ( ! in_array( 'incorrect_password', $error->get_error_codes(), true ) ) {
			return;
		}
		$user = get_user_by( 'login', $login );
		if ( ! $user && is_email( $login ) ) {
			$user = get_user_by( 'email', $login );
		}
		if ( $user instanceof WP_User ) {
			$this->counter()->take( $this->source( $user ) );
		}
	}

	/**
	 * @param WP_User|WP_Error $user Native account or an earlier refusal.
	 */
	public function before_password( WP_User|WP_Error $user ): WP_User|WP_Error {
		if ( $user instanceof WP_User && ( $this->counter()->spent( $this->source( $user ) ) ?? 0 ) >= self::FAILURES ) {
			return new WP_Error( 'linker_login_attempts', __( 'Too many failed sign-in attempts. Please try again later.', 'linker-commerce' ) );
		}
		return $user;
	}

	/** Discard expired counters. */
	public function cleanup(): void {
		$this->counter()->prune();
	}

	private function counter(): RateLimit {
		return new RateLimit( 'login_failed_account_connection', self::FAILURES, 10 * MINUTE_IN_SECONDS );
	}

	/**
	 * @param WP_User $user Native account.
	 */
	private function source( WP_User $user ): string {
		$address = isset( $_SERVER['REMOTE_ADDR'] ) && is_string( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
		return hash_hmac( 'sha256', $user->ID . '|' . $address, wp_salt( 'auth' ) );
	}
}
