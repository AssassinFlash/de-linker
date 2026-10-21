<?php
/**
 * A private deterministic reference to validated semantic request data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** Transport fields (nonce/proof/request UUID) are not part of the caller's payload. */
final class Fingerprint {
	// Initial protocol nesting ceiling, docs/specs/519-public-admission.md.
	private const MAX_DEPTH = 16;

	/**
	 * Include current identity/action, while object-key ordering is immaterial.
	 *
	 * @param Identity            $identity Server identity.
	 * @param string              $action Server action.
	 * @param array<string,mixed> $payload Already validated business data only.
	 * @return string|WP_Error HMAC, never a stored body.
	 */
	public static function make( Identity $identity, string $action, array $payload ): string|WP_Error {
		try {
			$json = wp_json_encode( self::canonical( $payload, 0 ) );
			if ( ! is_string( $json ) ) {
				return new WP_Error( 'linker_admission_input' );
			}
			return hash_hmac( 'sha256', $identity->binding() . '|' . $action . '|' . $json, wp_salt( 'nonce' ) );
		} catch ( \InvalidArgumentException $error ) {
			return new WP_Error( 'linker_admission_input' );
		}
	}

	/**
	 * Lists preserve their meaning; associative keys have a fixed order.
	 *
	 * @param mixed $value JSON-compatible semantic value.
	 * @param int   $depth Current nesting.
	 * @return mixed Canonical value.
	 * @throws \InvalidArgumentException Objects/resources or excessive nesting.
	 */
	private static function canonical( mixed $value, int $depth ): mixed {
		if ( $depth > self::MAX_DEPTH || is_object( $value ) || is_resource( $value ) ) {
			throw new \InvalidArgumentException( 'invalid_admission_payload' );
		}
		if ( is_array( $value ) ) {
			if ( ! array_is_list( $value ) ) {
				ksort( $value, SORT_STRING );
			}
			foreach ( $value as $key => $item ) {
				$value[ $key ] = self::canonical( $item, $depth + 1 );
			}
		}
		return $value;
	}
}
