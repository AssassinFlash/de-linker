<?php
/**
 * Tests for the stock push audit rows.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Stock;

use Linker\Commerce\Stock\BatchLog;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;

/**
 * Tests for BatchLog.
 *
 * @covers \Linker\Commerce\Stock\BatchLog
 */
final class BatchLogTest extends TestCase {

	/**
	 * A recorded push is a private post of its own type with the payload in meta.
	 */
	public function test_record_writes_a_private_row_with_the_payload(): void {
		WP_Mock::userFunction(
			'current_time',
			array(
				'args'   => array( 'mysql', true ),
				'return' => '2026-10-11 08:00:00',
			)
		);
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'   => BatchLog::POST_TYPE,
						'post_status' => 'private',
						'post_title'  => 'Stock push 2026-10-11 08:00:00, 2 applied, 1 unchanged, 1 errors',
					),
					true,
				),
				'return' => 55,
			)
		);
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				'return' => static fn ( $value ): string => (string) json_encode( $value ),
			)
		);
		WP_Mock::userFunction(
			'wp_slash',
			array(
				'return' => static fn ( string $value ): string => $value,
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'times' => 1,
				'args'  => array( 55, '_linker_stock_batch', '{"received_at":"2026-10-11 08:00:00","applied":2,"unchanged":1,"errors":1}' ),
			)
		);

		$id = ( new BatchLog() )->record(
			array(
				'received_at' => '2026-10-11 08:00:00',
				'applied'     => 2,
				'unchanged'   => 1,
				'errors'      => 1,
			)
		);

		$this->assertSame( 55, $id );
		$this->assertConditionsMet();
	}

	/**
	 * A write WordPress refuses is answered with 0, not with a fake row id.
	 */
	public function test_record_refused_write_answers_zero(): void {
		WP_Mock::userFunction( 'current_time', array( 'return' => '2026-10-11 08:00:00' ) );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'return' => new WP_Error( 'db_error', 'no' ),
			)
		);
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );

		$this->assertSame( 0, ( new BatchLog() )->record( array( 'received_at' => 'x' ) ) );
	}

	/**
	 * A stored row reads back; a wrong post type or broken payload does not.
	 */
	public function test_load_reads_only_its_own_rows(): void {
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'return' => static fn ( int $id ): string => 55 === $id ? BatchLog::POST_TYPE : 'post',
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 55, '_linker_stock_batch', true ),
				'return' => '{"applied":2,"results":[]}',
			)
		);

		$row = ( new BatchLog() )->load( 55 );
		$this->assertSame(
			array(
				'applied' => 2,
				'results' => array(),
			),
			$row
		);
		$this->assertNull( ( new BatchLog() )->load( 56 ) );
	}
}
