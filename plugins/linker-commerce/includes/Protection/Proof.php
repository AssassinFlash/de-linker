<?php
/**
 * Short-lived, scope-bound admission proof; never an authentication credential.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Only a verified proof may enter quota admission; prepare proofs only start a check. */
final class Proof {
	// Initial scoped permission lifetime, docs/specs/519-public-admission.md.
	public const LIFETIME = 300;

	/**
	 * Fixed server clock for expiry fixtures, time() in normal requests.
	 *
	 * @param (callable():int)|null $clock Server clock.
	 */
	public function __construct( private mixed $clock = null ) {}

	/**
	 * The endpoint selects the kind and action; neither grants native account access.
	 *
	 * @phpstan-impure
	 *
	 * @param string   $kind prepare or verified.
	 * @param string   $action Server-selected scope.
	 * @param Identity $identity Current native account/browser binding.
	 * @param string   $id Stable challenge UUID.
	 * @throws \InvalidArgumentException Invalid caller contract.
	 */
	public function issue( string $kind, string $action, Identity $identity, string $id ): string {
		if ( ! in_array( $kind, array( 'prepare', 'verified' ), true ) || ! Actions::valid( $action ) || ! wp_is_uuid( $id, 4 ) ) {
			throw new \InvalidArgumentException( 'invalid_admission_scope' );
		}
		$now     = $this->now();
		$json    = (string) wp_json_encode(
			array(
				'v'       => 1,
				'kind'    => $kind,
				'action'  => $action,
				'subject' => $identity->binding(),
				'id'      => strtolower( $id ),
				'issued'  => $now,
				'expires' => $now + self::LIFETIME,
			)
		);
		$payload = bin2hex( $json );
		return $payload . '.' . hash_hmac( 'sha256', $payload, wp_salt( 'secure_auth' ) );
	}

	/**
	 * Check the MAC before parsing any client-controlled JSON.
	 *
	 * @phpstan-impure
	 *
	 * @param string   $token Proof returned to this browser.
	 * @param string   $kind Required prepare/verified boundary.
	 * @param string   $action Required server-selected scope.
	 * @param Identity $identity Current native account/browser binding.
	 * @return array{id:string,expires:int}|null Checked UUID/expiry, or no authority.
	 */
	public function read( string $token, string $kind, string $action, Identity $identity ): ?array {
		if ( strlen( $token ) > 2048 || 1 !== preg_match( '/\A((?:[a-f0-9]{2})+)\.([a-f0-9]{64})\z/', $token, $parts ) || ! hash_equals( hash_hmac( 'sha256', $parts[1], wp_salt( 'secure_auth' ) ), $parts[2] ) ) {
			return null;
		}
		$raw  = hex2bin( $parts[1] );
		$data = is_string( $raw ) ? json_decode( $raw, true ) : null;
		if ( ! is_array( $data ) || 1 !== ( $data['v'] ?? null ) || ( $data['kind'] ?? null ) !== $kind || ( $data['action'] ?? null ) !== $action || ( $data['subject'] ?? null ) !== $identity->binding() || ! is_string( $data['id'] ?? null ) || ! wp_is_uuid( $data['id'], 4 ) || ! is_int( $data['issued'] ?? null ) || ! is_int( $data['expires'] ?? null ) ) {
			return null;
		}
		$now = $this->now();
		if ( $data['issued'] > $now || $data['expires'] <= $now || self::LIFETIME !== $data['expires'] - $data['issued'] ) {
			return null;
		}
		return array(
			'id'      => $data['id'],
			'expires' => $data['expires'],
		);
	}

	/** Current server time; client clocks have no authority. */
	private function now(): int {
		return is_callable( $this->clock ) ? (int) ( $this->clock )() : time();
	}
}
