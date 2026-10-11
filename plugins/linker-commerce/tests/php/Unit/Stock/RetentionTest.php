<?php
/**
 * Tests for the retention of the stock push audit rows.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Stock;

use Linker\Commerce\Stock\BatchLog;
use Linker\Commerce\Stock\Retention;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Retention, with the audit rows in memory (WP_Mock).
 *
 * @covers \Linker\Commerce\Stock\Retention
 */
final class RetentionTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-commerce/linker-commerce.php';

	/**
	 * The rows as get_posts() answers them: row id → creation time (UTC).
	 *
	 * @var array<int, string>
	 */
	private array $rows = array();

	/**
	 * The row ids the sweep deleted, in deletion order.
	 *
	 * @var list<int>
	 */
	private array $deleted = array();

	/**
	 * The cutoff of every get_posts() call, in order.
	 *
	 * @var list<string>
	 */
	private array $cutoffs = array();

	/**
	 * A row's creation time past the retention days (UTC).
	 */
	private static function expired(): string {
		return gmdate( 'Y-m-d H:i:s', time() - ( Retention::RETENTION_DAYS + 1 ) * DAY_IN_SECONDS );
	}

	/**
	 * A row's creation time inside the retention days (UTC).
	 */
	private static function fresh(): string {
		return gmdate( 'Y-m-d H:i:s', time() - DAY_IN_SECONDS );
	}

	/**
	 * An audit row, written at the given time (UTC); ids ascend with the time.
	 *
	 * @param string $date_gmt Creation time (UTC).
	 */
	private function row( string $date_gmt ): int {
		$id                = 100 + count( $this->rows );
		$this->rows[ $id ] = $date_gmt;
		return $id;
	}

	/**
	 * Mocks the sweep's two WordPress calls: get_posts() answers the expired
	 * rows oldest first (checking the query it was asked for), wp_delete_post()
	 * deletes for good.
	 */
	private function mock_expired_rows_query(): void {
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => function ( array $args ): array {
					$this->assertSame( BatchLog::POST_TYPE, $args['post_type'] );
					$this->assertSame( 'private', $args['post_status'] );
					$this->assertSame( 'ids', $args['fields'] );
					$this->assertSame( Retention::SCAN_BATCH, $args['posts_per_page'] );
					$this->assertSame( 1, $args['paged'], 'The deleted rows leave the window, so page one is the oldest still there.' );
					$this->assertSame( 'date', $args['orderby'] );
					$this->assertSame( 'ASC', $args['order'] );
					$this->assertSame( 'post_date_gmt', $args['date_query'][0]['column'] );

					$cutoff          = (string) $args['date_query'][0]['before'];
					$this->cutoffs[] = $cutoff;
					$cutoff_time     = strtotime( $cutoff . ' UTC' );
					$this->assertIsInt( $cutoff_time );
					$this->assertEqualsWithDelta( time() - Retention::RETENTION_DAYS * DAY_IN_SECONDS, $cutoff_time, 5 );

					$ids = array();
					foreach ( $this->rows as $id => $date_gmt ) {
						if ( $date_gmt < $cutoff ) {
							$ids[] = $id;
						}
					}
					return array_slice( $ids, 0, (int) $args['posts_per_page'] );
				},
			)
		);
		WP_Mock::userFunction(
			'wp_delete_post',
			array(
				'return' => function ( int $id, bool $force ): bool {
					$this->assertTrue( $force, 'An audit row goes at once, not into the trash.' );
					$this->deleted[] = $id;
					unset( $this->rows[ $id ] );
					return true;
				},
			)
		);
	}

	/**
	 * Without a daily event, one is scheduled.
	 */
	public function test_schedules_the_daily_sweep(): void {
		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => false ) );
		WP_Mock::userFunction(
			'wp_schedule_event',
			array(
				'times'  => 1,
				'args'   => array( \WP_Mock\Functions::type( 'int' ), 'daily', Retention::HOOK ),
				'return' => true,
			)
		);

		( new Retention( self::FILE ) )->schedule();
		$this->assertConditionsMet();
	}

	/**
	 * An event already on the schedule is left alone: no second daily event.
	 */
	public function test_leaves_the_scheduled_event_alone(): void {
		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => 12345 ) );
		WP_Mock::userFunction( 'wp_schedule_event', array( 'times' => 0 ) );

		( new Retention( self::FILE ) )->schedule();
		$this->assertConditionsMet();
	}

	/**
	 * Deactivation removes the daily event.
	 */
	public function test_deactivate_clears_the_event(): void {
		WP_Mock::userFunction(
			'wp_clear_scheduled_hook',
			array(
				'times' => 1,
				'args'  => array( Retention::HOOK ),
			)
		);

		( new Retention( self::FILE ) )->deactivate();
		$this->assertConditionsMet();
	}

	/**
	 * The sweep deletes the rows past their retention days and leaves the
	 * ones inside them alone.
	 */
	public function test_sweep_deletes_expired_rows_and_keeps_the_fresh_ones(): void {
		$oldest  = $this->row( gmdate( 'Y-m-d H:i:s', time() - ( Retention::RETENTION_DAYS + 30 ) * DAY_IN_SECONDS ) );
		$expired = $this->row( self::expired() );
		$fresh   = $this->row( self::fresh() );
		$this->mock_expired_rows_query();

		( new Retention( self::FILE ) )->sweep();

		$this->assertSame( array( $oldest, $expired ), $this->deleted );
		$this->assertSame( array( $fresh ), array_keys( $this->rows ) );
		// One query: the batch came back short, so the window is drained.
		$this->assertCount( 1, $this->cutoffs );
	}

	/**
	 * A full batch is followed by another one — the window is drained batch by
	 * batch — and the sweep stops as soon as a batch comes back short.
	 */
	public function test_sweep_walks_full_batches_and_stops_at_a_short_one(): void {
		$rows = array();
		for ( $i = 0; $i < Retention::SCAN_BATCH + 3; ++$i ) {
			$rows[] = $this->row( self::expired() );
		}
		$this->row( self::fresh() );
		$this->mock_expired_rows_query();

		( new Retention( self::FILE ) )->sweep();

		$this->assertSame( $rows, $this->deleted );
		// A full batch, then the short one that ends the walk.
		$this->assertCount( 2, $this->cutoffs );
	}

	/**
	 * A sweep that finds nothing to delete asks once and stops.
	 */
	public function test_sweep_of_an_empty_window_asks_once(): void {
		$this->row( self::fresh() );
		$this->mock_expired_rows_query();

		( new Retention( self::FILE ) )->sweep();

		$this->assertSame( array(), $this->deleted );
		$this->assertCount( 1, $this->cutoffs );
	}
}
