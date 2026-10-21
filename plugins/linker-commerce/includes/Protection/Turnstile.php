<?php
/**
 * Canonical, bounded server-side Turnstile verification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Siteverify's result never grants account, conversation or private-data access. */
final class Turnstile {
	// Official server-side validation, fixed research #506, captured 2026-10-21.
	private const ENDPOINT    = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
	private const TOKEN_LIMIT = 2048;
	// Initial form-wait ceiling, docs/specs/519-public-admission.md.
	private const TIMEOUT = 3;

	/**
	 * The WordPress HTTP API remains the single production transport.
	 *
	 * @param Configuration $configuration Private keys and expected hostname.
	 */
	public function __construct( private readonly Configuration $configuration ) {}

	/**
	 * A retry uses its original UUID; optional remoteip is deliberately omitted.
	 *
	 * @param string $token Client challenge response, never logged or stored.
	 * @param string $action Expected server-selected action.
	 * @param string $request_id Stable UUID for this verification attempt.
	 */
	public function verify( string $token, string $action, string $request_id ): Verification {
		if ( ! $this->configuration->ready() ) {
			return new Verification( 'unavailable', 'configuration' );
		}
		if ( '' === $token || strlen( $token ) > self::TOKEN_LIMIT || 1 !== preg_match( '/\A[a-zA-Z0-9_-]{1,32}\z/', $action ) || ! wp_is_uuid( $request_id, 4 ) ) {
			return new Verification( 'invalid', 'input' );
		}
		$response = wp_remote_post(
			self::ENDPOINT,
			array(
				'timeout'     => self::TIMEOUT,
				'redirection' => 0,
				'body'        => $this->configuration->verification_body( $token, $request_id ),
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
		if ( ( $body['action'] ?? null ) !== $action ) {
			return new Verification( 'invalid', 'action' );
		}
		return new Verification( 'valid', 'verified' );
	}
}
