<?php
/**
 * Atomic mail budget storage contract.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * One serialized read/modify/write, including first migration.
 */
interface BudgetLedger {

	/**
	 * Run one atomic budget operation.
	 *
	 * @param  callable(array<string, mixed>): array{state: array<string, mixed>, slot: int} $work Mutation.
	 * @return int|null Result, or null when storage cannot be locked or written.
	 */
	public function transact( callable $work ): ?int;
}
