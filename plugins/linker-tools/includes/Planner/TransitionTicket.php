<?php
/**
 * Native-signed recovery of one verified guest-to-account transition.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

/** This ticket can enqueue a claim; it cannot authenticate a project read. */
final class TransitionTicket {

	public const COOKIE_PREFIX = 'linker_planner_transition_';
	/** Transport bound for a fixed signed record, not a retention policy. */
	private const MAX_BYTES = 1024;
	/** Bounded recovery work; further native tickets remain for the next request. */
	private const BATCH = 8;

	/**
	 * Issue recovery proof already bound by the native login event.
	 *
	 * @param string      $guest Verified native guest subject.
	 * @param int         $expires Native guest expiry, never extended here.
	 * @param int         $user Verified target account from the native login event.
	 * @param string|null $scope Native guest query scope, if captured by this version.
	 */
	public function issue( string $guest, int $expires, int $user, ?string $scope = null ): bool {
		if ( ! self::subject( $guest ) || $expires <= time() || $user < 1 || ( null !== $scope && ! RecoveryScopes::valid( $scope ) ) || headers_sent() ) {
			return false;
		}
		$json = wp_json_encode(
			array(
				'schema_version' => 1,
				'guest'          => $guest,
				'expires'        => $expires,
				'user'           => $user,
			)
		);
		if ( null !== $scope ) {
			$json = wp_json_encode(
				array(
					'schema_version' => 2,
					'guest'          => $guest,
					'expires'        => $expires,
					'user'           => $user,
					'recovery_scope' => $scope,
				)
			);
		}
		if ( ! is_string( $json ) ) {
			return false;
		}
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- URL-safe encoding of fixed JSON fields, never executable code.
		$payload = rtrim( strtr( base64_encode( $json ), '+/', '-_' ), '=' );
		$value   = $payload . '.' . wp_hash( 'linker-planner-transition:v1|' . $payload, 'auth', 'sha256' );
		return $this->cookie( self::name( $guest, $user ), $value, $expires );
	}

	/**
	 * Verify a bounded batch of native transition tickets.
	 *
	 * Separate purpose-bound cookie names preserve account A's failed native
	 * insert when the same browser later logs into account B. No unbound
	 * guest-to-whichever-user token is issued.
	 *
	 * @return list<array{schema_version:int,guest:string,expires:int,user:int,recovery_scope?:string}> Verified transitions, no owner-read authority.
	 */
	public function read_all(): array {
		$tickets = array();
		foreach ( $_COOKIE as $name => $raw ) {
			if ( ! is_string( $name ) || ! str_starts_with( $name, self::COOKIE_PREFIX ) || ! is_string( $raw ) ) {
				continue;
			}
			// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- fixed signed bytes; strict alphabet, length, signature and fields are checked by decode.
			$data = $this->decode( wp_unslash( $raw ) );
			if ( null !== $data && self::name( $data['guest'], $data['user'] ) === $name ) {
				$tickets[] = $data;
				if ( count( $tickets ) >= self::BATCH ) {
					break;
				}
			}
		}
		return $tickets;
	}

	/**
	 * Clear one ticket only after its complete native outbox was read back.
	 *
	 * @param string $guest Verified subject.
	 * @param int    $user Verified target account.
	 */
	public function clear( string $guest, int $user ): bool {
		return $this->cookie( self::name( $guest, $user ), '', time() - YEAR_IN_SECONDS );
	}

	/**
	 * Decode one complete purpose-bound record.
	 *
	 * @param string $raw Exact cookie bytes.
	 * @return array{schema_version:int,guest:string,expires:int,user:int,recovery_scope?:string}|null Verified transition.
	 */
	private function decode( string $raw ): ?array {
		if ( strlen( $raw ) > self::MAX_BYTES || 1 !== preg_match( '/\A([a-zA-Z0-9_-]+)\.([a-f0-9]{64})\z/', $raw, $match ) || ! hash_equals( wp_hash( 'linker-planner-transition:v1|' . $match[1], 'auth', 'sha256' ), $match[2] ) ) {
			return null;
		}
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- signature verified first; fixed JSON payload only, never evaluated.
		$json = base64_decode( strtr( $match[1], '-_', '+/' ), true );
		$data = is_string( $json ) ? json_decode( $json, true, 8 ) : null;
		if ( ! is_array( $data ) || ! in_array( $data['schema_version'] ?? null, array( 1, 2 ), true ) || array_keys( $data ) !== ( 2 === $data['schema_version'] ? array( 'schema_version', 'guest', 'expires', 'user', 'recovery_scope' ) : array( 'schema_version', 'guest', 'expires', 'user' ) ) || ! is_string( $data['guest'] ) || ! self::subject( $data['guest'] ) || ! is_int( $data['expires'] ) || $data['expires'] <= time() || ! is_int( $data['user'] ) || $data['user'] < 1 || ( 2 === $data['schema_version'] && ( ! is_string( $data['recovery_scope'] ) || ! RecoveryScopes::valid( $data['recovery_scope'] ) ) ) ) {
			return null;
		}
		return $data;
	}

	/**
	 * Recognise a purpose-separated native guest subject.
	 *
	 * @param string $subject Purpose-separated native guest hash.
	 */
	public static function subject( string $subject ): bool {
		return 1 === preg_match( '/\Awp:[1-9][0-9]*:guest:[a-f0-9]{64}\z/', $subject );
	}

	/**
	 * Write or remove the host-only native recovery cookie.
	 *
	 * @param string $name Purpose-bound transition name.
	 * @param string $value Signed ticket or empty deletion.
	 * @param int    $expires Native expiry.
	 */
	private function cookie( string $name, string $value, int $expires ): bool {
		if ( headers_sent() || ! setcookie(
			$name,
			$value,
			array(
				'expires'  => $expires,
				'path'     => defined( 'COOKIEPATH' ) && '' !== COOKIEPATH ? COOKIEPATH : '/',
				'secure'   => is_ssl(),
				'httponly' => true,
				'samesite' => 'Lax',
			)
		) ) {
			return false;
		}
		if ( '' === $value ) {
			unset( $_COOKIE[ $name ] );
		} else {
			$_COOKIE[ $name ] = $value;
		}
		return true;
	}

	/**
	 * Bind each native guest/account transition to its own recovery slot.
	 *
	 * @param string $guest Verified guest subject.
	 * @param int    $user Verified account ID.
	 */
	private static function name( string $guest, int $user ): string {
		return self::COOKIE_PREFIX . substr( hash( 'sha256', $guest . '|' . $user ), 0, 24 );
	}
}
