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
	/**
	 * A checked result, an explicit refusal, or an unavailable service.
	 *
	 * @param string $status valid, invalid or unavailable.
	 * @param string $reason Safe diagnostic key.
	 */
	public function __construct( public readonly string $status, public readonly string $reason ) {}
}
