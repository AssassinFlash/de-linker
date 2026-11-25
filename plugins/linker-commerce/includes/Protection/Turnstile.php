<?php
/**
 * Canonical, bounded server-side Turnstile verification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** Siteverify's result never grants account, conversation or private-data access. */
final class Turnstile {
	// Official server-side validation, fixed research #506, captured 2026-10-21.
	private const ENDPOINT    = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
	private const TOKEN_LIMIT = 2048;
	// The measured provider round trip from this deployment is 2.45–3.47 seconds.
	private const TIMEOUT = 12;

	/**
	 * The WordPress HTTP API remains the single production transport.
	 *
	 * @param Configuration $configuration Private keys and expected hostname.
	 */
	public function __construct( private readonly Configuration $configuration ) {}

	/**
	 * Check a native submission immediately before its business action.
	 *
	 * @param string              $action Server-selected form action.
	 * @param array<string,mixed> $submitted Native form or REST fields.
	 * @return true|WP_Error
	 */
	public static function check( string $action, array $submitted ): true|WP_Error {
		if ( ! Configuration::verification_required( $action ) ) {
			return new WP_Error( 'linker_admission_configuration', Business::verification_message( 'unavailable' ), array( 'status' => 503 ) );
		}
		if ( is_user_logged_in() ) {
			return true;
		}
		$token = $submitted['cf-turnstile-response'] ?? '';
		if ( ! is_string( $token ) || '' === $token ) {
			return new WP_Error( 'linker_admission_proof', Business::verification_message( 'failed' ), array( 'status' => 400 ) );
		}
		$result = ( new self( Configuration::current() ) )->verify( $token, $action );
		return match ( $result->status ) {
			'valid' => true,
			'unavailable' => new WP_Error( 'linker_admission_configuration', Business::verification_message( 'unavailable' ), array( 'status' => 503 ) ),
			default => new WP_Error( 'linker_admission_proof', Business::verification_message( 'failed' ), array( 'status' => 400 ) ),
		};
	}

	/**
	 * Bind the one-time provider token to this hostname and form.
	 *
	 * @param string $token  Native cf-turnstile-response.
	 * @param string $action Server-selected anonymous submit action.
	 */
	public function verify( string $token, string $action ): Verification {
		if ( ! $this->configuration->configured() ) {
			return new Verification( 'unavailable', 'configuration' );
		}
		if ( '' === $token || strlen( $token ) > self::TOKEN_LIMIT || ! Configuration::verification_required( $action ) ) {
			return new Verification( 'invalid', 'input' );
		}
		$response = wp_remote_post(
			self::ENDPOINT,
			array(
				'timeout'     => self::TIMEOUT,
				'redirection' => 0,
				'body'        => $this->configuration->verification_body( $token ),
			)
		);
		if ( is_wp_error( $response ) ) {
			return new Verification( 'unavailable', 'network' );
		}
		if ( 200 !== wp_remote_retrieve_response_code( $response ) ) {
			return new Verification( 'unavailable', 'http' );
		}
		$body = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( ! is_array( $body ) || ! is_bool( $body['success'] ?? null ) ) {
			return new Verification( 'unavailable', 'response' );
		}
		if ( true !== $body['success'] ) {
			$errors = is_array( $body['error-codes'] ?? null ) ? array_filter( $body['error-codes'], 'is_string' ) : array();
			if ( array_intersect( $errors, array( 'missing-input-secret', 'invalid-input-secret', 'internal-error' ) ) ) {
				return new Verification( 'unavailable', 'provider' );
			}
			return new Verification( 'invalid', in_array( 'timeout-or-duplicate', $errors, true ) ? 'expired_or_replayed' : 'rejected' );
		}
		if ( ! is_string( $body['hostname'] ?? null ) || strtolower( $body['hostname'] ) !== strtolower( $this->configuration->hostname ) ) {
			return new Verification( 'invalid', 'hostname' );
		}
		if ( ( $body['action'] ?? null ) !== $action && ( isset( $body['action'] ) || ! $this->configuration->test_keys() ) ) {
			// Cloudflare's official testing keys report no action at all; a
			// reported action stays exactly bound, with or without test keys.
			return new Verification( 'invalid', 'action' );
		}
		return new Verification( 'valid', 'verified' );
	}
}
