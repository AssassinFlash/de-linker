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

	/**
	 * The digest's read of the charged attempts must be a pure read: it never
	 * initializes, prunes or charges the ledger, so a diagnostic can never
	 * consume a customer's slot.
	 */
	public function test_used_reports_without_touching_the_ledger(): void {
		$t = new Throttle( new BudgetMemory( $this->options ) );
		$t->reserve( self::NOW, Throttle::PHP );
		$t->reserve( self::NOW, Throttle::SMTP );
		$t->reserve( self::NOW - 2 * DAY_IN_SECONDS, Throttle::PHP );
		$before = $this->options;

		$this->assertSame( 1, $t->used( self::NOW, Throttle::PHP ) );
		$this->assertSame( 1, $t->used( self::NOW, Throttle::SMTP ) );
		$this->assertSame( 0, $t->used( self::NOW + DAY_IN_SECONDS + 1, Throttle::PHP ) );
		$this->assertSame( $before, $this->options, 'Reading the usage never writes the ledger.' );
		$this->assertNull( $t->used( self::NOW, 'carrier-pigeon' ) );
	}

	/** Definite failed transport releases its reservation so failed retries cannot saturate the minute or day windows. */
	public function test_release_frees_failed_attempt_slot(): void {
		$t = new Throttle( new BudgetMemory( $this->options ) );
		for ( $i = 0; $i < Throttle::PER_MINUTE; ++$i ) {
			$this->assertSame( self::NOW, $t->reserve( self::NOW, Throttle::PHP ) );
		}
		$this->assertSame( self::NOW + MINUTE_IN_SECONDS, $t->next_slot( self::NOW, Throttle::PHP ) );
		$t->release( self::NOW, Throttle::PHP );
		$this->assertSame( self::NOW, $t->next_slot( self::NOW, Throttle::PHP ) );
		$this->assertCount( Throttle::PER_MINUTE - 1, $this->options[ OptionBudgetLedger::OPTION ]['entries'] );
	}
}
