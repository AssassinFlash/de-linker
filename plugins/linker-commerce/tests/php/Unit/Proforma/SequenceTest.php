<?php
/**
 * Tests for Proforma numbers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Proforma;

use Linker\Commerce\Proforma\Sequence;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Tests for Sequence, on an in-memory options table.
 *
 * @covers \Linker\Commerce\Proforma\Sequence
 */
final class SequenceTest extends TestCase {

	/**
	 * The options table: name → value.
	 *
	 * @var array<string, string>
	 */
	private array $table = array();

	/**
	 * A $wpdb whose prepare/get_var/query work on $table, with MySQL's compare-and-set semantics.
	 */
	public function setUp(): void {
		parent::setUp();
		$wpdb          = Mockery::mock( \stdClass::class );
		$wpdb->options = 'wp_options';
		$wpdb->allows( 'prepare' )->andReturnUsing( static fn ( string $sql, ...$args ): array => array( $sql, $args ) );
		$wpdb->allows( 'get_var' )->andReturnUsing( fn ( array $query ) => $this->table[ $query[1][0] ] ?? null );
		$wpdb->allows( 'query' )->andReturnUsing(
			function ( array $query ): int {
				[ $value, $name, $expected ] = $query[1];
				if ( ( $this->table[ $name ] ?? null ) !== $expected ) {
					return 0;
				}
				$this->table[ $name ] = $value;
				return 1;
			}
		);
		$GLOBALS['wpdb'] = $wpdb;
		WP_Mock::userFunction(
			'add_option',
			array(
				'return' => function ( string $name, $value ): bool {
					if ( isset( $this->table[ $name ] ) ) {
						return false;
					}
					$this->table[ $name ] = (string) $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
	}

	/**
	 * Removes the fake $wpdb.
	 */
	public function tearDown(): void {
		unset( $GLOBALS['wpdb'] );
		parent::tearDown();
	}

	/**
	 * Numbers read PREFIX-YYYY-NNNN (docs/specs/11-commerce.md).
	 */
	public function test_format(): void {
		$this->assertSame( 'PI-2026-0001', Sequence::format( 'PI', 2026, 1 ) );
		$this->assertSame( 'PI-2026-0420', Sequence::format( 'PI', 2026, 420 ) );
		$this->assertSame( 'PI-2027-12345', Sequence::format( 'PI', 2027, 12345 ) );
	}

	/**
	 * Numbers follow each other without gaps and start at 1 in a new year.
	 */
	public function test_consecutive_per_year(): void {
		$sequence = new Sequence();
		foreach ( array( 1, 2, 3 ) as $expected ) {
			$next = $sequence->next( 2026 );
			$this->assertSame( $expected, $next );
			$this->assertTrue( $sequence->commit( 2026, $next ) );
		}
		$this->assertSame( 1, $sequence->next( 2027 ) );
	}

	/**
	 * Of two requests that read the same next number, only one claims it; the other must take the following one.
	 */
	public function test_a_number_is_claimed_once(): void {
		$sequence = new Sequence();
		$first    = $sequence->next( 2026 );
		$second   = $sequence->next( 2026 );

		$this->assertSame( $first, $second );
		$this->assertTrue( $sequence->commit( 2026, $first ) );
		$this->assertFalse( $sequence->commit( 2026, $second ) );
		$this->assertSame( 2, $sequence->next( 2026 ) );
	}
}
