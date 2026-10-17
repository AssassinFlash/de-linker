<?php
/**
 * Sending rate below the host's mail quota.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * Keeps this site under the hosting account's mail quota. Hostinger allows 10
 * messages per minute and 100 per rolling 24 hours through PHP mail(), shared
 * by the four sites of the account; this site takes at most 8 and 80, so the
 * other sites keep room (docs/research/2026-10-09/mail-root-cause.md §3, §9).
 * The same 8/80 also bounds each SMTP and fallback channel (#297 review):
 * that research lists 100/day for trial mailboxes and 1000/day for Business
 * Starter, both rolling 24h and shared with the mailbox's own sending. The
 * actual sunriver plan is read by Claude from hPanel at deployment.
 */
final class Throttle {

	/**
	 * Option holding the times of the sends of the last 24 hours.
	 */
	public const OPTION = 'linker_commerce_mail_sends';

	/**
	 * Sends allowed per minute (mail-root-cause.md §9: at most 8 of the host's 10).
	 */
	public const PER_MINUTE = 8;

	/**
	 * Sends allowed per rolling 24 hours (mail-root-cause.md §9: at most 80 of the host's 100).
	 */
	public const PER_DAY = 80;

	/**
	 * The earliest time, from $now on, at which one more send stays within both limits.
	 *
	 * @param int $now Unix time.
	 */
	public function next_slot( int $now ): int {
		$sends  = $this->sends( $now );
		$minute = array_values( array_filter( $sends, static fn ( int $time ): bool => $time > $now - MINUTE_IN_SECONDS ) );
		$slot   = $now;
		if ( count( $minute ) >= self::PER_MINUTE ) {
			$slot = max( $slot, $minute[ count( $minute ) - self::PER_MINUTE ] + MINUTE_IN_SECONDS );
		}
		if ( count( $sends ) >= self::PER_DAY ) {
			$slot = max( $slot, $sends[ count( $sends ) - self::PER_DAY ] + DAY_IN_SECONDS );
		}
		return $slot;
	}

	/**
	 * Counts a send.
	 *
	 * @param int $now Unix time of the send.
	 */
	public function record( int $now ): void {
		$sends   = $this->sends( $now );
		$sends[] = $now;
		update_option( self::OPTION, $sends, false );
	}

	/**
	 * Times of the sends of the last 24 hours, oldest first.
	 *
	 * @param int $now Unix time.
	 * @return list<int>
	 */
	private function sends( int $now ): array {
		$stored = get_option( self::OPTION, array() );
		$times  = array();
		foreach ( is_array( $stored ) ? $stored : array() as $time ) {
			if ( is_int( $time ) && $time > $now - DAY_IN_SECONDS ) {
				$times[] = $time;
			}
		}
		sort( $times );
		return $times;
	}
}
