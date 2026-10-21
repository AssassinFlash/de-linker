<?php
/**
 * Same-origin challenge preparation and canonical verification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** The browser selects only a public action, never limits, permissions or identity. */
final class Controller {
	public const NAMESPACE = 'linker/v1';
	public const ROUTE     = '/protection';
	// Initial operational bounds, docs/specs/519-public-admission.md.
	private const LEASE           = 10;
	private const BROWSER_MINUTE  = 20;
	private const CONNECTION_HOUR = 100;
	private const SITE_DAY        = 5000;
	private const IN_FLIGHT       = 2;

	/**
	 * Share one private configuration and journal with native consumers.
	 *
	 * @param Configuration $configuration Private settings.
	 * @param Ledger|null   $ledger Native journal.
	 */
	public function __construct( private readonly Configuration $configuration, private readonly ?Ledger $ledger = null ) {}

	/** Register the only public endpoints; neither creates business data. */
	public function register(): void {
		foreach ( array( 'prepare', 'verify' ) as $operation ) {
			register_rest_route(
				self::NAMESPACE,
				self::ROUTE . '/' . $operation,
				array(
					'methods'             => 'POST',
					'permission_callback' => array( $this, 'same_origin' ),
					'callback'            => array( $this, $operation ),
					'args'                => array(
						'action'  => array(
							'type'     => 'string',
							'required' => true,
							'enum'     => Actions::ALL,
						),
						'prepare' => array(
							'type'      => 'string',
							'required'  => 'verify' === $operation,
							'maxLength' => 2048,
						),
						'token'   => array(
							'type'      => 'string',
							'required'  => 'verify' === $operation,
							'maxLength' => 2048,
						),
					),
				)
			);
		}
	}

	/**
	 * Browser Origin is serialized authority only, including the effective port.
	 * Native REST authentication still owns signed-in identity.
	 *
	 * @param WP_REST_Request $request Request.
	 * @return true|WP_Error Same-origin or explicit refusal.
	 */
	public function same_origin( WP_REST_Request $request ): true|WP_Error {
		$given = wp_parse_url( $request->get_header( 'origin' ) ?? '' );
		$home  = wp_parse_url( home_url() );
		if ( ! is_array( $given ) || ! is_array( $home ) || isset( $given['user'] ) || isset( $given['pass'] ) || isset( $given['query'] ) || isset( $given['fragment'] ) || ! empty( $given['path'] ) ) {
			return self::failure( 'origin', 403 );
		}
		$port = static fn ( array $parts ): int => (int) ( $parts['port'] ?? ( 'https' === ( $parts['scheme'] ?? '' ) ? 443 : 80 ) );
		return ( $given['scheme'] ?? '' ) === ( $home['scheme'] ?? '' ) && strtolower( (string) ( $given['host'] ?? '' ) ) === strtolower( (string) ( $home['host'] ?? '' ) ) && $port( $given ) === $port( $home ) ? true : self::failure( 'origin', 403 );
	}

	/**
	 * Start a cookie-bound attempt on actual interaction, never on ordinary browsing.
	 *
	 * @param WP_REST_Request $request Validated request.
	 * @return WP_REST_Response|WP_Error Public key and signed prepare stamp.
	 */
	public function prepare( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$identity = $this->identity( $request );
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		$action = (string) $request->get_param( 'action' );
		return self::response(
			array(
				'mode'     => $this->configuration->mode,
				'site_key' => $this->configuration->site_key,
				'action'   => $action,
				'prepare'  => ( new Proof() )->issue( 'prepare', $action, $identity, wp_generate_uuid4() ),
				'lifetime' => Proof::LIFETIME,
			)
		);
	}

	/**
	 * Deduplicate the actual provider attempt and preserve its original proof expiry.
	 *
	 * @param WP_REST_Request $request Validated request.
	 * @return WP_REST_Response|WP_Error Verified scoped proof or retryable failure.
	 */
	public function verify( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$identity = $this->identity( $request );
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		$action = (string) $request->get_param( 'action' );
		$stamp  = ( new Proof() )->read( (string) $request->get_param( 'prepare' ), 'prepare', $action, $identity );
		$token  = (string) $request->get_param( 'token' );
		if ( null === $stamp || '' === $token || strlen( $token ) > 2048 ) {
			return self::failure( 'input', 400 );
		}
		$fingerprint = hash_hmac( 'sha256', $identity->binding() . '|' . $action . '|' . $token, wp_salt( 'nonce' ) );
		$ledger      = $this->ledger ?? new Ledger();
		$receipt     = $ledger->reserve( $stamp['id'], $fingerprint, $this->allowances( $identity ), self::LEASE, array(), 'verification_' . $action, $identity->binding(), $identity->owners() );
		if ( is_wp_error( $receipt ) ) {
			$code = $receipt->get_error_code();
			if ( 'linker_admission_payload_changed' === $code ) {
				return self::failure( 'input', 409 );
			}
			if ( 'linker_admission_quota' === $code ) {
				$error = self::failure( 'quota', 429 );
				$data  = $receipt->get_error_data();
				$error->add_data(
					array(
						'status'      => 429,
						'retry_after' => is_array( $data ) ? (int) ( $data['retry_after'] ?? 1 ) : 1,
					)
				);
				return $error;
			}
			return self::failure( 'unavailable', 503 );
		}
		if ( 'reserved' === $receipt['status'] ) {
			$dispatch = $ledger->dispatch( $stamp['id'], $fingerprint );
			if ( is_wp_error( $dispatch ) ) {
				return self::failure( 'pending', 409 );
			}
			$result  = ( new Turnstile( $this->configuration ) )->verify( $token, $action, $stamp['id'] );
			$receipt = $ledger->complete( $stamp['id'], $fingerprint, $result->code() );
			if ( is_wp_error( $receipt ) ) {
				return self::failure( 'unavailable', 503 );
			}
		}
		if ( 'completed' !== $receipt['status'] ) {
			return self::failure( 'dispatched' === $receipt['status'] ? 'pending' : 'unavailable', 'dispatched' === $receipt['status'] ? 409 : 503 );
		}
		$result = Verification::from_code( (int) $receipt['outcome'] );
		if ( 'valid' !== $result->status ) {
			return self::failure( $result->reason, 'invalid' === $result->status ? 400 : 503 );
		}
		$at    = (int) $receipt['created_at'];
		$proof = new Proof( static fn (): int => $at );
		return self::response(
			array(
				'proof'   => $proof->issue( 'verified', $action, $identity, $stamp['id'] ),
				'expires' => $at + Proof::LIFETIME,
				'ttl'     => max( 0, $at + Proof::LIFETIME - time() ),
			)
		);
	}

	/**
	 * Reject off/broken setup and invalid scopes before a cookie or journal is created.
	 *
	 * @param WP_REST_Request $request Request.
	 * @return Identity|WP_Error Current server-derived identity.
	 */
	private function identity( WP_REST_Request $request ): Identity|WP_Error {
		$origin = $this->same_origin( $request );
		if ( is_wp_error( $origin ) ) {
			return $origin;
		}
		if ( ! Actions::valid( (string) $request->get_param( 'action' ) ) ) {
			return self::failure( 'input', 400 );
		}
		if ( ! $this->configuration->ready() ) {
			return self::failure( 'configuration', 503 );
		}
		$identity = Identity::current();
		return is_wp_error( $identity ) ? self::failure( 'cookie', 503 ) : $identity;
	}

	/**
	 * All dispatched attempts consume this budget, including rejected challenges.
	 *
	 * @param Identity $identity Current private subject.
	 * @return Allowance[] Verification-only dimensions, separate from customer turns.
	 */
	private function allowances( Identity $identity ): array {
		$address    = isset( $_SERVER['REMOTE_ADDR'] ) && is_string( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
		$connection = hash_hmac( 'sha256', 'direct-connection|' . $address, wp_salt( 'auth' ) );
		return array(
			new Allowance( 'verification_browser_minute', $identity->browser, self::BROWSER_MINUTE, MINUTE_IN_SECONDS ),
			new Allowance( 'verification_connection_hour', $connection, self::CONNECTION_HOUR, HOUR_IN_SECONDS ),
			new Allowance( 'verification_site_day', 'site', self::SITE_DAY, DAY_IN_SECONDS ),
			new Allowance( 'verification_browser_flight', $identity->browser, 1, 0 ),
			new Allowance( 'verification_site_flight', 'site', self::IN_FLIGHT, 0 ),
		);
	}

	/**
	 * Failures contain fixed reason keys, never request/provider body or credential.
	 *
	 * @param string $reason Safe reason.
	 * @param int    $status HTTP status.
	 */
	private static function failure( string $reason, int $status ): WP_Error {
		return new WP_Error(
			'linker_verification_' . $reason,
			__( 'Verification could not be completed. Please try again.', 'linker-commerce' ),
			array(
				'status'      => $status,
				'retry_after' => 1,
			)
		);
	}

	/**
	 * A personalized proof must never enter a shared cache.
	 *
	 * @param array<string,mixed> $data Response.
	 */
	private static function response( array $data ): WP_REST_Response {
		$response = new WP_REST_Response( $data );
		$response->header( 'Cache-Control', 'no-store, private, max-age=0' );
		return $response;
	}
}
