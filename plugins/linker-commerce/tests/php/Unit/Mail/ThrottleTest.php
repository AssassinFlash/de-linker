<?php
/**
 * Tests for the sending rate.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Throttle.
 *
 * @covers \Linker\Commerce\Mail\Throttle
 */
final class ThrottleTest extends TestCase {

	private const NOW = 1_760_000_000;

	/**
	 * The stored send times.
	 *
	 * @var mixed
	 */
	private $stored = array();

	/**
	 * The options get_option() and update_option() work on $stored.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_option', array( 'return' => fn () => $this->stored ) );
		WP_Mock::userFunction(
			'update_option',
			array(
				'return' => function ( string $name, $value ): bool {
					$this->stored = $value;
					return true;
				},
			)
		);
	}

	/**
	 * Under both limits, a send may go now.
	 */
	public function test_free_slot_is_now(): void {
		$this->stored = array_map( static fn ( int $i ): int => self::NOW - 120 - $i * 60, range( 0, 70 ) );

		$this->assertSame( self::NOW, ( new Throttle() )->next_slot( self::NOW ) );
	}

	/**
	 * After 8 sends within a minute, the next waits until the oldest of them is a minute old
	 * (docs/research/2026-10-09/mail-root-cause.md §9: at most 8 per minute).
	 */
	public function test_minute_limit(): void {
		$this->stored = range( self::NOW - 50, self::NOW - 43 );

		$this->assertSame( self::NOW - 50 + 60, ( new Throttle() )->next_slot( self::NOW ) );
	}

	/**
	 * After 80 sends within 24 hours, the next waits until the oldest of them is 24 hours old
	 * (mail-root-cause.md §9: at most 80 per rolling 24 hours).
	 */
	public function test_day_limit(): void {
		$this->stored = array_map( static fn ( int $i ): int => self::NOW - 80_000 + $i * 900, range( 0, 79 ) );

		$this->assertSame( self::NOW - 80_000 + 86_400, ( new Throttle() )->next_slot( self::NOW ) );
	}

	/**
	 * Recording keeps the last 24 hours and drops junk.
	 */
	public function test_record_prunes(): void {
		$this->stored = array( self::NOW - 90_000, 'junk', self::NOW - 10 );

		( new Throttle() )->record( self::NOW );

		$this->assertSame( array( self::NOW - 10, self::NOW ), $this->stored );
	}
}
