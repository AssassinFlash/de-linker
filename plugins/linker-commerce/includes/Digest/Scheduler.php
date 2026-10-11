<?php
/**
 * The daily 9:00 Berlin schedule of the digest.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use DateTimeImmutable;
use DateTimeZone;

/**
 * Schedules the digest with WordPress's own cron as a chain of single events:
 * every send schedules the next 09:00 Europe/Berlin, so the clock follows the
 * change between summer and winter time without a recurring interval (the one
 * send right after a change goes out at the previous offset and corrects the
 * schedule for everything after it; docs/specs/74-daily-digest.md).
 */
final class Scheduler {

	/**
	 * Cron hook of the digest.
	 */
	public const HOOK = 'linker_commerce_digest';

	/**
	 * The timezone the digest is scheduled in (docs/specs/74-daily-digest.md).
	 */
	public const TIMEZONE = 'Europe/Berlin';

	/**
	 * The hour the digest goes out.
	 */
	public const SEND_HOUR = 9;

	/**
	 * Schedules the first send, when nothing is scheduled; runs on init.
	 */
	public function ensure(): void {
		if ( false !== wp_next_scheduled( self::HOOK ) ) {
			return;
		}
		$this->schedule_after( $this->now() );
	}

	/**
	 * Schedules the next send after this one; runs after every digest.
	 */
	public function reschedule(): void {
		wp_clear_scheduled_hook( self::HOOK );
		$this->schedule_after( $this->now() );
	}

	/**
	 * The next 09:00 Europe/Berlin strictly after $now: today 09:00 while it
	 * has not struck yet, otherwise tomorrow's. Exactly on the hour the current
	 * moment is the send itself, so the next one is tomorrow's.
	 *
	 * @param DateTimeImmutable $now The moment to schedule from, in any timezone.
	 */
	public static function next_send( DateTimeImmutable $now ): DateTimeImmutable {
		$candidate = $now->setTime( self::SEND_HOUR, 0 );
		return $candidate > $now ? $candidate : $candidate->modify( '+1 day' );
	}

	/**
	 * Now in Berlin time.
	 */
	private function now(): DateTimeImmutable {
		return new DateTimeImmutable( 'now', new DateTimeZone( self::TIMEZONE ) );
	}

	/**
	 * Puts the next send after $now on the cron.
	 *
	 * @param DateTimeImmutable $after The moment to schedule after.
	 */
	private function schedule_after( DateTimeImmutable $after ): void {
		wp_schedule_single_event( self::next_send( $after )->getTimestamp(), self::HOOK );
	}
}
