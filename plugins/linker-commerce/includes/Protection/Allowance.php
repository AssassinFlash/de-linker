<?php
/**
 * One server-selected rate or in-flight dimension.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** A zero window is an in-flight allowance; other windows are fixed UTC buckets. */
final class Allowance {
	/**
	 * Values originate in policy, never directly from browser JSON.
	 *
	 * @throws \InvalidArgumentException Invalid server policy dimension.
	 *
	 * @param string $name Logical policy dimension.
	 * @param string $subject Server-derived pseudonymous subject, or site.
	 * @param int    $capacity Allowed units.
	 * @param int    $window Seconds, zero for in-flight.
	 * @param int    $units Units this operation reserves.
	 */
	public function __construct(
		public readonly string $name,
		private readonly string $subject,
		public readonly int $capacity,
		public readonly int $window,
		public readonly int $units = 1
	) {
		if ( 1 !== preg_match( '/\A[a-z0-9_]{1,64}\z/', $name ) || '' === $subject || strlen( $subject ) > 128 || $capacity < 1 || $window < 0 || $units < 1 || $units > $capacity ) {
			throw new \InvalidArgumentException( 'invalid_allowance' );
		}
	}

	/**
	 * Pseudonymous keys contain neither email, account ID nor raw address.
	 *
	 * @param int $now Server clock.
	 */
	public function key( int $now ): string {
		$bucket = $this->window > 0 ? intdiv( $now, $this->window ) : 0;
		return hash_hmac( 'sha256', $this->name . '|' . $this->subject . '|' . $this->window . '|' . $bucket, wp_salt( 'auth' ) );
	}

	/** Pseudonymous ownership makes native privacy requests target only this subject. */
	public function owner(): string {
		return self::owner_for( $this->subject );
	}

	/**
	 * Resolve the same owner without exposing the raw subject in a ledger row.
	 *
	 * @param string $subject Server-derived account/browser/recipient scope.
	 */
	public static function owner_for( string $subject ): string {
		return hash_hmac( 'sha256', 'public-owner|' . $subject, wp_salt( 'auth' ) );
	}

	/**
	 * The next fixed-window boundary, or zero for an in-flight dimension.
	 *
	 * @param int $now Server clock.
	 */
	public function ends( int $now ): int {
		return $this->window > 0 ? ( intdiv( $now, $this->window ) + 1 ) * $this->window : 0;
	}
}
