<?php
/**
 * The browser/PHP/Python protocol's shared numeric representation window.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

/** Reject unsupported numbers; never cast them to strings or round them. */
final class JsonNumbers {

	/** Binary64's exact integer window, transport policy rather than physics. */
	private const MAX_NUMBER = 9007199254740991;

	/**
	 * Check a bounded, already decoded JSON tree before native re-encoding.
	 *
	 * @param mixed $value Decoded JSON only.
	 */
	public static function supported( mixed $value ): bool {
		if ( is_int( $value ) || is_float( $value ) ) {
			return is_finite( (float) $value ) && abs( $value ) <= self::MAX_NUMBER;
		}
		if ( $value instanceof \stdClass || is_array( $value ) ) {
			foreach ( (array) $value as $item ) {
				if ( ! self::supported( $item ) ) {
					return false;
				}
			}
		}
		return true;
	}
}
