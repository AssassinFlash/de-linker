<?php
/**
 * Unit transport/storage fixtures use an isolated capacity port.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

use Linker\Commerce\Mail\JobCapacity;
use Linker\Commerce\Mail\Message;

/** Native count/byte/CAS/transaction evidence lives in MailCapacityTest. */
final class JobCapacityMemory implements JobCapacity {
	/**
	 * Execute the unit's native post fixture, without pretending to prove DB safety.
	 *
	 * @param Message  $message Native fixture message.
	 * @param callable $write In-memory post write/readback.
	 * @phpstan-param callable():int $write
	 */
	public function create( Message $message, callable $write ): int {
		return $write();
	}

	/**
	 * Execute the unit's native priority fixture.
	 *
	 * @param int      $id Existing native fixture id.
	 * @param callable $write In-memory priority write/readback.
	 */
	public function promote( int $id, callable $write ): void {
		$write();
	}

	/**
	 * No DB registry is touched by a transport unit test.
	 *
	 * @param int $id Deleted in-memory fixture id.
	 */
	public function deleted( int $id ): void {}

	/**
	 * Record the unit's next attempt without pretending to prove SQL atomicity.
	 *
	 * @param int $id In-memory job.
	 * @param int $time Next fixture attempt.
	 */
	public function reschedule( int $id, int $time ): void {
		as_schedule_single_action( $time, \Linker\Commerce\Mail\Outbox::HOOK, array( $id ), \Linker\Commerce\Mail\Outbox::GROUP );
	}

	/** The unit transport runs outside DB transactions; native tests cover joins. */
	public function transaction_active(): bool {
		return false;
	}

	/** Unit post metadata retains its existing in-memory hold behavior.
	 *
	 * @param int $id In-memory job.
	 */
	public function held( int $id ): bool {
		return \Linker\Commerce\Mail\NotificationHold::job_held( $id );
	}
}
