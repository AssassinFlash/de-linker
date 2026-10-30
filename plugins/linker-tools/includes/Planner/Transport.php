<?php
/**
 * Bounded private RPC: native server identity headers are never forwarded.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/** The existing service TLS pin still applies to the same engine origin. */
final class Transport {

	/** Deployment resource policy, not a numerical/engineering threshold. */
	public const MAX_REPLY_BYTES = 32 * 1024 * 1024;
	/**
	 * Product reads and operations using their facts check current Woo permission.
	 * Each shared Python Publication.read has a 10-second network budget;
	 * this native route allows both checks plus cold-load/transport overhead.
	 * Operational policy, not an engineering limit. Read-only project/history
	 * RPCs retain their existing five-second budget.
	 */
	private const SOURCE_OPERATION_TIMEOUT = 30.0;
	private const SOURCE_OPERATIONS        = array( 'products/current', 'projects/create', 'projects/revise', 'installation/review', 'battery/scenario', 'runs/pv', 'runs/direct-beam', 'runs/geometric-pv', 'runs/pvgis-reference', 'runs/energy', 'runs/equipment', 'runs/equipment-search', 'runs/report' );

	/**
	 * Select the native HTTP transport or a test adapter.
	 *
	 * @param (callable(string,array<string,mixed>):(array<string,mixed>|WP_Error))|null $fetch Native HTTP test seam.
	 */
	public function __construct( private mixed $fetch = null ) {}

	/**
	 * Send a bounded authenticated server-to-server command.
	 *
	 * @param Principal $principal Verified server identity.
	 * @param string    $path Server-selected protocol path.
	 * @param string    $body Bounded JSON bytes.
	 * @param string    $previous_guest Verified native transition only.
	 * @return array{status:int,type:string,body:string}|WP_Error Raw private reply.
	 */
	public function call( Principal $principal, string $path, string $body, string $previous_guest = '' ): array|WP_Error {
		$base  = rtrim( (string) get_option( 'linker_planner_url', '' ), '/' );
		$token = defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ? (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ) : '';
		if ( '' === $base || '' === $token || 1 !== preg_match( '/\A[a-z]+(?:\/[a-z-]+)*\z/', $path ) ) {
			return Failure::make( 'configuration', 503 );
		}
		$headers = array(
			'Content-Type'                       => 'application/json; charset=utf-8',
			'X-Linker-Service-Token'             => $token,
			'X-Linker-Planner-Principal-Kind'    => $principal->kind,
			'X-Linker-Planner-Principal-Subject' => $principal->subject,
		);
		if ( '' !== $previous_guest ) {
			$headers['X-Linker-Planner-Previous-Guest'] = $previous_guest;
		}
		$args     = array(
			'timeout'             => in_array( $path, self::SOURCE_OPERATIONS, true ) ? self::SOURCE_OPERATION_TIMEOUT : 5.0,
			'redirection'         => 0,
			'sslverify'           => true,
			'limit_response_size' => self::MAX_REPLY_BYTES + 1,
			'headers'             => $headers,
			'body'                => $body,
		);
		$response = is_callable( $this->fetch ) ? ( $this->fetch )( $base . '/' . $path, $args ) : wp_remote_post( $base . '/' . $path, $args );
		if ( is_wp_error( $response ) ) {
			return Failure::make( 'unavailable', 503 );
		}
		$status = (int) wp_remote_retrieve_response_code( $response );
		$body   = (string) wp_remote_retrieve_body( $response );
		$type   = wp_remote_retrieve_header( $response, 'content-type' );
		if ( ! is_string( $type ) || $status < 200 || $status >= 600 || ( $status >= 300 && $status < 400 ) || strlen( $body ) > self::MAX_REPLY_BYTES ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		return array(
			'status' => $status,
			'type'   => $type,
			'body'   => $body,
		);
	}

	/**
	 * JSON is used by bootstrap/claim handlers; raw assets keep the byte path.
	 *
	 * @param Principal           $principal Verified identity.
	 * @param string              $path Server-selected protocol path.
	 * @param array<string,mixed> $command Versioned protocol command.
	 * @param string              $previous_guest Verified native former guest.
	 * @return array<string,mixed>|WP_Error Successful object or private refusal.
	 */
	public function object( Principal $principal, string $path, array $command, string $previous_guest = '' ): array|WP_Error {
		$body = wp_json_encode( $command );
		if ( ! is_string( $body ) ) {
			return Failure::make( 'input', 400 );
		}
		$reply = $this->call( $principal, $path, $body, $previous_guest );
		if ( is_wp_error( $reply ) ) {
			return $reply;
		}
		$value = json_decode( $reply['body'], true, 64 );
		if ( $reply['status'] >= 400 ) {
			return Failure::make( self::refusal_code( $reply['status'], $value ), $reply['status'] );
		}
		return is_array( $value ) && str_starts_with( $reply['type'], 'application/json' ) ? $value : Failure::make( 'invalid_reply', 502 );
	}

	/**
	 * Name the engine's own refusal instead of flattening a whole status class.
	 *
	 * Several distinct 409s reach this seam: a lease that moved on, a project
	 * revision that changed, and published Woo evidence that changed. Only the
	 * first is a claim conflict; retrying the others cannot succeed. The
	 * engine's code is a stable machine name, so it carries the distinction
	 * while the message stays the reviewed generic copy.
	 *
	 * @param int   $status HTTP status from the engine.
	 * @param mixed $value  Decoded engine reply, if it parsed.
	 * @return string Stable gateway code.
	 */
	private static function refusal_code( int $status, mixed $value ): string {
		$code = is_array( $value ) && is_array( $value['error'] ?? null ) ? ( $value['error']['code'] ?? null ) : null;
		if ( is_string( $code ) && 1 === preg_match( '/\A[a-z][a-z0-9_]{0,63}\z/', $code ) ) {
			return $code;
		}
		return match ( $status ) {
			409 => 'claim_conflict',
			404 => 'not_found',
			422 => 'input',
			503 => 'unavailable',
			default => 'upstream',
		};
	}
}
