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
	 * @param callable $work Mutation.
	 * @param bool     $write Whether to commit a change, or only inspect a fresh snapshot.
	 * @phpstan-param callable(array<string, mixed>): array{state: array<string, mixed>, slot: int} $work
	 * @return int|null Result, or null when storage cannot be locked or written.
	 */
	public function transact( callable $work, bool $write = true ): ?int;
}
