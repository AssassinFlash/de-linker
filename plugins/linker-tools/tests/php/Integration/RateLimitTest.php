<?php
/**
 * The atomic limit, on the instance's real database.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Genie\RateLimit;
use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- the parallel test starts PHP processes.

/**
 * RateLimit takes one unit in a single statement (ticket #235, review round
 * 1: check-and-increment in one step), so requests arriving together never
 * pass the limit between them.
 *
 * @coversNothing
 */
final class RateLimitTest extends TestCase {

	/**
	 * The limiter name of this run; its rows are removed afterwards.
	 *
	 * @var string
	 */
	private string $name = '';

	/**
	 * Skips unless the integration configuration ran the bootstrap.
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just up); the unit suite does not load WordPress.' );
		}
	}

	/**
	 * A limiter name of its own.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->name = 'it' . strtolower( wp_generate_password( 6, false ) );
	}

	/**
	 * Removes this run's rows.
	 */
	protected function tearDown(): void {
		global $wpdb;
		$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( RateLimit::PREFIX . $this->name . '.' ) . '%' ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows.
		parent::tearDown();
	}

	/**
	 * Up to the limit and no further, per caller.
	 */
	public function test_it_allows_the_limit_and_refuses_the_next(): void {
		$limit = new RateLimit( $this->name, 3, HOUR_IN_SECONDS );

		$this->assertSame( array( true, true, true, false ), array( $limit->take( 'a' ), $limit->take( 'a' ), $limit->take( 'a' ), $limit->take( 'a' ) ) );
		$this->assertTrue( $limit->take( 'b' ), 'Another caller has its own allowance.' );
	}

	/**
	 * A limiter whose name starts with another's keeps its rows when the
	 * shorter-windowed one moves to a new window.
	 */
	public function test_limiters_do_not_purge_each_other(): void {
		$day  = new RateLimit( $this->name . '_day', 1, DAY_IN_SECONDS );
		$hour = new RateLimit( $this->name, 1, HOUR_IN_SECONDS );
		$this->assertTrue( $day->take( '' ) );
		$this->assertTrue( $hour->take( 'a' ) );
		$this->assertFalse( $day->take( '' ), 'The day is still used up.' );
		global $wpdb;
		$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( RateLimit::PREFIX . $this->name . '_day.' ) . '%' ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows.
	}

	/**
	 * A new window starts afresh, and the old window's rows go.
	 */
	public function test_a_new_window_starts_afresh(): void {
		$now   = 1_800_000_000;
		$limit = new RateLimit(
			$this->name,
			1,
			HOUR_IN_SECONDS,
			static function () use ( &$now ): int {
				return $now;
			}
		);
		$this->assertTrue( $limit->take( 'a' ) );
		$this->assertFalse( $limit->take( 'a' ) );

		$now += HOUR_IN_SECONDS;
		$this->assertTrue( $limit->take( 'a' ) );
		$this->assertSame( 1, $this->rows(), 'Only the current window keeps a row.' );
	}

	/**
	 * Eight processes at once against a limit of three: exactly three pass.
	 */
	public function test_parallel_requests_cannot_pass_the_limit(): void {
		$root      = (string) getenv( 'LINKER_WP_ROOT' );
		$fixture   = __DIR__ . '/fixtures/take.php';
		$processes = array();
		$pipes     = array();
		for ( $i = 0; $i < 8; ++$i ) {
			$process = proc_open(
				array( PHP_BINARY, $fixture, $root, $this->name, '3', 'parallel' ),
				array(
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes[ $i ]
			);
			$this->assertIsResource( $process );
			$processes[ $i ] = $process;
		}
		$allowed = 0;
		foreach ( $processes as $i => $process ) {
			$out = (string) stream_get_contents( $pipes[ $i ][1] );
			fclose( $pipes[ $i ][1] );
			fclose( $pipes[ $i ][2] );
			proc_close( $process );
			$allowed += '1' === substr( trim( $out ), -1 ) ? 1 : 0;
		}

		$this->assertSame( 3, $allowed );
	}

	/**
	 * How many rows this limiter keeps.
	 */
	private function rows(): int {
		global $wpdb;
		return (int) $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( RateLimit::PREFIX . $this->name . '.' ) . '%' ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows.
	}
}
