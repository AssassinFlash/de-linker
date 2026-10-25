<?php
/** In-memory storage for pure rolling-window tests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Fixtures;

use Linker\Commerce\Mail\BudgetLedger;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\Throttle;

/** Production's database behavior is separately tested with two native connections. */
final class BudgetMemory implements BudgetLedger {
	/** Test-owned options.
	 *
	 * @var array<string, mixed>
	 */
	private array $options;
	/**
	 * Bind the fixture to its test's state.
	 *
	 * @param array<string, mixed> $options Test options.
	 */
	public function __construct( array &$options ) {
		$this->options = &$options;
	}
	/**
	 * Execute a deterministic in-memory mutation.
	 *
	 * @param callable $work Mutation.
	 * @param bool     $write Whether to persist.
	 * @phpstan-param callable(array<string, mixed>): array{state: array<string, mixed>, slot: int} $work
	 */
	public function transact( callable $work, bool $write = true ): int {
		$state  = $this->options[ OptionBudgetLedger::OPTION ] ?? array( 'legacy' => $this->options[ Throttle::OPTION ] ?? array() );
		$result = $work( $state );
		if ( $write ) {
			$this->options[ OptionBudgetLedger::OPTION ] = $result['state'];
		}
		return $result['slot'];
	}
}
