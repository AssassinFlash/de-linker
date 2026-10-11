<?php
/**
 * Tests for the digest schedule.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use DateTimeImmutable;
use DateTimeZone;
use Linker\Commerce\Digest\Scheduler;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Scheduler: the next send is always 09:00 Europe/Berlin, through
 * both time offsets.
 *
 * @covers \Linker\Commerce\Digest\Scheduler
 */
final class SchedulerTest extends TestCase {

	/**
	 * Before 09:00 the send is the same day's 09:00, in summer time.
	 */
	public function test_next_send_is_nine_berlin_in_summer(): void {
		$now = new DateTimeImmutable( '2026-06-03 08:00', new DateTimeZone( Scheduler::TIMEZONE ) );

		$next = Scheduler::next_send( $now );

		$this->assertSame( '2026-06-03 09:00:00', $next->format( 'Y-m-d H:i:s' ) );
		$this->assertSame( 'Europe/Berlin', $next->getTimezone()->getName() );
		// CEST is UTC+2.
		$this->assertSame( 1_780_470_000, $next->getTimestamp() );
		$this->assertSame( '2026-06-03 07:00', $next->setTimezone( new DateTimeZone( 'UTC' ) )->format( 'Y-m-d H:i' ) );
	}

	/**
	 * After 09:00 the send is the next day's 09:00, in winter time.
	 */
	public function test_next_send_is_the_next_morning_in_winter(): void {
		$now = new DateTimeImmutable( '2026-11-20 14:30', new DateTimeZone( Scheduler::TIMEZONE ) );

		$next = Scheduler::next_send( $now );

		$this->assertSame( '2026-11-21 09:00:00', $next->format( 'Y-m-d H:i:s' ) );
		// CET is UTC+1.
		$this->assertSame( '2026-11-21 08:00', $next->setTimezone( new DateTimeZone( 'UTC' ) )->format( 'Y-m-d H:i' ) );
	}

	/**
	 * Exactly at 09:00 the current moment is the send itself, so the next one
	 * is tomorrow's.
	 */
	public function test_next_send_on_the_hour_is_tomorrow(): void {
		$now = new DateTimeImmutable( '2026-06-03 09:00', new DateTimeZone( Scheduler::TIMEZONE ) );

		$this->assertSame( '2026-06-04 09:00', Scheduler::next_send( $now )->format( 'Y-m-d H:i' ) );
	}

	/**
	 * The day the clock falls back, the next send is still 09:00 Berlin, an
	 * hour later in UTC than it was before.
	 */
	public function test_next_send_across_the_fall_back(): void {
		$now = new DateTimeImmutable( '2026-10-25 10:00', new DateTimeZone( Scheduler::TIMEZONE ) );

		$next = Scheduler::next_send( $now );

		$this->assertSame( '2026-10-26 09:00', $next->format( 'Y-m-d H:i' ) );
		$this->assertSame( '2026-10-26 08:00', $next->setTimezone( new DateTimeZone( 'UTC' ) )->format( 'Y-m-d H:i' ) );
	}

	/**
	 * The ensure() hook schedules when nothing is scheduled and leaves an
	 * existing schedule alone.
	 */
	public function test_ensure_schedules_only_when_none_is_scheduled(): void {
		$scheduler = new Scheduler();

		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => false ) );
		WP_Mock::userFunction(
			'wp_schedule_single_event',
			array(
				'times' => 1,
				'args'  => array( WP_Mock\Functions::type( 'int' ), Scheduler::HOOK ),
			)
		);
		$scheduler->ensure();
		$this->assertConditionsMet();

		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => 1_780_470_000 ) );
		WP_Mock::userFunction( 'wp_schedule_single_event', array( 'times' => 0 ) );
		$scheduler->ensure();
		$this->assertConditionsMet();
	}

	/**
	 * The reschedule() hook clears what is there and schedules the next 09:00.
	 */
	public function test_reschedule_clears_and_schedules(): void {
		WP_Mock::userFunction(
			'wp_clear_scheduled_hook',
			array(
				'times' => 1,
				'args'  => array( Scheduler::HOOK ),
			)
		);
		WP_Mock::userFunction(
			'wp_schedule_single_event',
			array(
				'times' => 1,
				'args'  => array( WP_Mock\Functions::type( 'int' ), Scheduler::HOOK ),
			)
		);

		( new Scheduler() )->reschedule();

		$this->assertConditionsMet();
	}
}
