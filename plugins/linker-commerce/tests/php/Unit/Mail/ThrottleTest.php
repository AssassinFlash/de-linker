<?php
/** Tests of transport and priority rolling windows.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Tests\Fixtures\BudgetMemory;
use Linker\Commerce\Tests\TestCase;

/** Pure window evidence.
 *
 * @covers \Linker\Commerce\Mail\Throttle
 */
final class ThrottleTest extends TestCase {
	private const NOW = 1_760_000_000;
	/** Fixture ledger.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array();

	/** Both pools inherit old attempts exactly once, preserving the legacy option. */
	public function test_legacy_and_reserved_capacity(): void {
		$legacy                            = array_fill( 0, 80, self::NOW - 120 );
		$this->options[ Throttle::OPTION ] = $legacy;
		$t                                 = new Throttle( new BudgetMemory( $this->options ) );
		$this->assertSame( self::NOW, $t->reserve( self::NOW, Throttle::SMTP ) );
		$this->assertSame( self::NOW - 120 + DAY_IN_SECONDS, $t->next_slot( self::NOW, Throttle::PHP, true ) );
		$this->assertSame( $legacy, $this->options[ Throttle::OPTION ] );
		$this->assertCount( 161, $this->options[ OptionBudgetLedger::OPTION ]['entries'] );
		$t->next_slot( self::NOW );
		$this->assertCount( 161, $this->options[ OptionBudgetLedger::OPTION ]['entries'] );
	}

	/** Standard traffic cannot consume the last 16 PHP slots. */
	public function test_critical_reserve_and_minute_limits(): void {
		$this->options[ Throttle::OPTION ] = array_fill( 0, 64, self::NOW - 120 );
		$t                                 = new Throttle( new BudgetMemory( $this->options ) );
		$this->assertGreaterThan( self::NOW, $t->reserve( self::NOW ) );
		for ( $i = 0; $i < Throttle::PER_MINUTE; ++$i ) {
			$this->assertSame( self::NOW, $t->reserve( self::NOW, Throttle::PHP, true ) );
		}
		$this->assertSame( self::NOW + MINUTE_IN_SECONDS, $t->reserve( self::NOW, Throttle::PHP, true ) );
	}

	/** Future scheduling reads never expire actual recent charges in storage. */
	public function test_future_next_slot_does_not_refund_history(): void {
		$t = new Throttle( new BudgetMemory( $this->options ) );
		$this->assertSame( self::NOW, $t->reserve( self::NOW ) );
		$before = $this->options;
		$this->assertSame( self::NOW + DAY_IN_SECONDS, $t->next_slot( self::NOW + DAY_IN_SECONDS ) );
		$this->assertSame( $before, $this->options );
	}
}
