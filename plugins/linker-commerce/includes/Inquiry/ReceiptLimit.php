<?php
/**
 * Site-wide allowance for automated public-door customer receipts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

/** Only receipts consume this allowance; inquiries and team notifications continue. */
final class ReceiptLimit {

	/**
	 * PR #290 round 2: a tenth of Hostinger's shared 100/24h allowance
	 * (AGENTS.md §4; docs/research/2026-10-09/mail-root-cause.md §3, §9).
	 * Same small allocation as #235. This is a fixed UTC-day window, as in
	 * #235's RateLimit, not a claim to measure the host's rolling usage.
	 */
	public const DAILY_CAP = 10;

	/** The saved reason a public-door receipt was omitted. */
	public const SKIPPED_META = '_linker_receipt_skipped';

	/** Reserve a receipt atomically, independently of the connection address. */
	public function take(): bool {
		return ( new RateLimit( 'public_receipts', self::DAILY_CAP, DAY_IN_SECONDS ) )->take( '' );
	}
}
