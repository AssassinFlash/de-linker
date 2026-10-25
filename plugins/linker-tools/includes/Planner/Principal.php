<?php
/**
 * Server-verified project principal, separate from rate-limit identity.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

/** No request JSON or forwarded browser header constructs this value. */
final class Principal {

	/**
	 * Accept a verified native ownership value.
	 *
	 * @throws \InvalidArgumentException Invalid server principal.
	 *
	 * @param string $kind Native guest/account, or a trusted server-only order reader.
	 * @param string $subject Stable private engine subject.
	 */
	public function __construct( public readonly string $kind, public readonly string $subject ) {
		if ( ! in_array( $kind, array( 'guest', 'user', 'team' ), true ) || 1 !== preg_match( '/\A[a-zA-Z0-9][a-zA-Z0-9:_-]{0,255}\z/', $subject ) ) {
			throw new \InvalidArgumentException( 'invalid_planner_principal' );
		}
	}
}
