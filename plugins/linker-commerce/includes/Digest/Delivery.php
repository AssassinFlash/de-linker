<?php
/**
 * Native delivery boundary for the daily digest.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

/**
 * Lets the scheduled task use a deterministic boundary in unit tests.
 */
interface Delivery {

	/**
	 * Delivers at most the digest for this native Berlin day.
	 *
	 * @param DigestEmail $email Complete native email producer.
	 * @param Block[]     $blocks Frozen business blocks.
	 */
	public function send( DigestEmail $email, array $blocks ): void;
}
