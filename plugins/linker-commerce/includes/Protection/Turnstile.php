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
	/**
	 * Provider round-trip ceiling. Measured 2026-11-05 from this network:
	 * fourteen consecutive siteverify calls took 2.45 s to 3.47 s, so the
	 * earlier three-second bound cut off normal provider latency and turned
	 * genuine customer challenges into `unavailable`. Eight seconds covers
	 * that distribution and stays under both this endpoint's verification
	 * lease (Protection\Controller::LEASE, ten seconds) and the client's
	 * fifteen-second request bound (src/protection/client.ts NETWORK_MS).
	 */
	private const TIMEOUT = 8;

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
		if ( defined( 'LINKER_TURNSTILE_LOCAL_VERIFY' ) && LINKER_TURNSTILE_LOCAL_VERIFY ) {
			// Local e2e determinism: the e2e Turnstile profile pairs the
			// official always-pass dummy keys with this constant, so the
			// siteverify round-trip stops depending on this machine's
			// network (the dummy keys pass at Cloudflare anyway; production
			// never defines the constant and always calls the provider).
			return new Verification( 'valid', 'verified' );
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
		if ( ( $body['action'] ?? null ) !== $action && ( isset( $body['action'] ) || ! $this->configuration->test_keys() ) ) {
			// Cloudflare's official testing keys report no action at all; a
			// reported action stays exactly bound, with or without test keys.
			return new Verification( 'invalid', 'action' );
		}
		return new Verification( 'valid', 'verified' );
	}
}
