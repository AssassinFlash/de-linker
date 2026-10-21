<?php
/**
 * Progressive native login verification after actual failures.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;
use WP_User;
use Linker\Commerce\Inquiry\RateLimit;

/** Ordinary first-attempt authentication never waits for a challenge. */
final class Login {
	/**
	 * A single native credential check can visit both WordPress auth callbacks.
	 *
	 * @var array<string,mixed>|null
	 */
	private ?array $permit = null;

	/** Preserve native credentials, account roles, sessions and approval rules. */
	public function register(): void {
		add_filter( 'wp_authenticate_user', array( $this, 'before_password' ), 5 );
		add_action( 'wp_login_failed', array( $this, 'failed' ) );
		add_action( 'wp_login', array( $this, 'complete' ) );
		add_action( 'woocommerce_login_form', array( $this, 'fields' ) );
		add_action( 'login_form', array( $this, 'fields' ) );
		add_action( Module::MAINTENANCE, array( $this, 'cleanup' ) );
	}

	/** Challenge fields appear only after actual failed use, never on a fresh visit. */
	public function fields(): void {
		if ( Business::enabled() && isset( $_COOKIE[ Identity::COOKIE ] ) && self::risky() ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped shared fields.
			echo FormFields::render( 'login' );
		}
	}

	/**
	 * Before WordPress hashes a known user's password after repeated failures.
	 *
	 * @param WP_User|WP_Error $user Native candidate; a prior refusal remains a refusal.
	 * @return WP_User|WP_Error Native candidate or explicit verification refusal.
	 */
	public function before_password( WP_User|WP_Error $user ): WP_User|WP_Error {
		if ( ! Business::enabled() || is_wp_error( $user ) || null !== $this->permit || ! self::risky() ) {
			return $user;
		}
		// No credential value enters the quota fingerprint or persisted journal.
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Woo owns its login nonce; WordPress login is additionally protected by same-origin proof.
		$post   = wp_unslash( $_POST );
		$result = Operation::begin( 'login', $post, array( 'account' => Identity::account( $user->ID ) ) );
		if ( is_wp_error( $result ) ) {
			return $result;
		}
		$this->permit = $result;
		return $user;
	}

	/** Record only actual native failures, never a cleartext username or password. */
	public function failed(): void {
		if ( ! Business::enabled() ) {
			return;
		}
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return;
		}
		// Initial broad flood threshold: 1000 failures / ten minutes (#520).
		// It raises verification rather than refusing a correct verified login.
		if ( ! ( new RateLimit( 'login_failed_site', 1000, 10 * MINUTE_IN_SECONDS ) )->take( 'site' ) ) {
			$this->complete();
			return;
		}
		// Failed unauthenticated guesses cannot fill the shared receipt journal.
		// Only native ten-minute risk counters are updated for those attempts.
		foreach ( self::hints( $identity ) as $hint ) {
			( new RateLimit( $hint['name'], $hint['capacity'], 10 * MINUTE_IN_SECONDS ) )->take( $hint['subject'] );
		}

		$this->complete();
	}

	/** Complete a verified attempt after either native success or native refusal. */
	public function complete(): void {
		if ( null !== $this->permit ) {
			Operation::finish( $this->permit );
			$this->permit = null;
		}
	}

	/**
	 * Read-only risk hint; the shared atomic dispatch remains the permission gate.
	 * Initial 3/browser and broad 100/connection failed attempts per ten minutes
	 * are #520 operating recommendations, not a measured customer distribution.
	 */
	private static function risky(): bool {
		if ( 'enforce' !== Configuration::current()->mode ) {
			return false;
		}
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return true;
		}
		$site = ( new RateLimit( 'login_failed_site', 1000, 10 * MINUTE_IN_SECONDS ) )->spent( 'site' );
		if ( null === $site || $site >= 1000 ) {
			return true; }
		foreach ( self::hints( $identity ) as $hint ) {
			$spent = ( new RateLimit( $hint['name'], $hint['capacity'], 10 * MINUTE_IN_SECONDS ) )->spent( $hint['subject'] );
			if ( null === $spent || $spent >= $hint['capacity'] ) {
				return true; }
		}
		return false;
	}

	/** Expired risk hints are removed even when no further login is attempted. */
	public function cleanup(): void {
		foreach ( array( 'login_failed_browser', 'login_failed_connection', 'login_failed_site' ) as $name ) {
			( new RateLimit( $name, 1, 10 * MINUTE_IN_SECONDS ) )->prune();
		}
	}

	/**
	 * Pseudonymous browser hint plus a broad direct connection flood threshold.
	 *
	 * @param Identity $identity Current server subject.
	 * @return list<array{name:string,subject:string,capacity:int}>
	 */
	private static function hints( Identity $identity ): array {
		$address    = isset( $_SERVER['REMOTE_ADDR'] ) && is_string( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
		$connection = hash_hmac( 'sha256', 'direct-connection|' . $address, wp_salt( 'auth' ) );
		return array(
			array(
				'name'     => 'login_failed_browser',
				'subject'  => $identity->browser,
				'capacity' => 3,
			),
			array(
				'name'     => 'login_failed_connection',
				'subject'  => $connection,
				'capacity' => 100,
			),
		);
	}
}
