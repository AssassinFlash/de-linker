<?php
/**
 * A provider outcome is separate from any content classification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Fixed reasons carry no customer token, provider body or credential. */
final class Verification {
	/** Stable protocol outcomes; no provider/customer text is persisted. */
	private const CODES = array(
		1  => array( 'valid', 'verified' ),
		21 => array( 'invalid', 'input' ),
		22 => array( 'invalid', 'hostname' ),
		23 => array( 'invalid', 'action' ),
		24 => array( 'invalid', 'expired_or_replayed' ),
		25 => array( 'invalid', 'rejected' ),
		31 => array( 'unavailable', 'network' ),
		32 => array( 'unavailable', 'http' ),
		33 => array( 'unavailable', 'response' ),
		34 => array( 'unavailable', 'provider' ),
		35 => array( 'unavailable', 'configuration' ),
	);

	/** A retry receipt stores only this fixed code. */
	public function code(): int {
		$code = array_search( array( $this->status, $this->reason ), self::CODES, true );
		return false === $code ? 33 : $code;
	}

	/**
	 * Decode a stored result without treating an unknown version as success.
	 *
	 * @param int $code Stored protocol outcome.
	 */
	public static function from_code( int $code ): self {
		$value = self::CODES[ $code ] ?? self::CODES[33];
		return new self( $value[0], $value[1] );
	}

	/**
	 * A checked result, an explicit refusal, or an unavailable service.
	 *
	 * @param string $status valid, invalid or unavailable.
	 * @param string $reason Safe diagnostic key.
	 */
	public function __construct( public readonly string $status, public readonly string $reason ) {}
}
