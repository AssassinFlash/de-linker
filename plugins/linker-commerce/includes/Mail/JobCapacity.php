<?php
/**
 * Native queue admission boundary, independent of mail transport rendering.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/** Same narrow storage-port pattern as BudgetLedger; production uses NativeJobCapacity. */
interface JobCapacity {
	/**
	 * Admit and verify one complete native write.
	 *
	 * @param Message  $message Frozen notification.
	 * @param callable $write Native write/readback callback.
	 * @phpstan-param callable():int $write
	 */
	public function create( Message $message, callable $write ): int;

	/**
	 * Atomically move an original job to the protected pool.
	 *
	 * @param int      $id Original job.
	 * @param callable $write Native priority update/readback.
	 */
	public function promote( int $id, callable $write ): void;

	/**
	 * Account for confirmed native deletion.
	 *
	 * @param int $id Original native job.
	 */
	public function deleted( int $id ): void;

	/**
	 * Replace the original job's pending attempt under the native transaction boundary.
	 *
	 * @param int $id Original job.
	 * @param int $time Next native attempt time.
	 */
	public function reschedule( int $id, int $time ): void;

	/** An outer native transaction must defer all external transport. */
	public function transaction_active(): bool;

	/** Authoritative hold reads precede any transaction probe or transport.
	 *
	 * @param int $id Original native job.
	 */
	public function held( int $id ): bool;
}
