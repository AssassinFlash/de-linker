<?php
/**
 * Tests for the digest's operations-health block.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Health;

use Linker\Commerce\Health\OperationsHealth;
use Linker\Commerce\Health\OperationsProbe;
use Linker\Commerce\Health\ReviewSummary;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Protection\BusinessCapacity;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;

/**
 * Every threshold of OperationsHealth at its exact boundary: the line fires at
 * the value and not one step below it, an unreadable dimension is never zero,
 * and a quiet day prints one compact sentence.
 *
 * @covers \Linker\Commerce\Health\OperationsHealth
 * @covers \Linker\Commerce\Health\OperationsProbe
 */
final class OperationsHealthTest extends TestCase {

	/**
	 * Unix time the digest runs at: 2026-11-11 09:00 Berlin (CET).
	 */
	private const NOW = 1_794_393_600;

	/**
	 * Translation and dates return their input; the email renders in English.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::passthruFunction( '_n' );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( mixed $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'http://linker.test/wp-admin/' ) );
		WP_Mock::userFunction( 'size_format', array( 'return' => static fn ( int $bytes ): string => $bytes . ' B' ) );
		WP_Mock::userFunction(
			'wp_date',
			array(
				'return' => static fn ( string $format ): string => 'H:i' === $format ? '07:12' : 'November 10, 2026',
			)
		);
	}

	/**
	 * A quiet day is one line that still names all four measurements.
	 */
	public function test_all_within_bounds_is_one_compact_line(): void {
		$block = $this->block(
			array(
				'pending'  => 17,
				'capped'   => false,
				'lateness' => 0,
				'overdue'  => 0,
			),
			array(
				'php'  => 12,
				'smtp' => 4,
			),
			array(
				'unhandled'   => 15,
				'bytes'       => 35_685,
				'quarantined' => 0,
			),
			array(
				'engineering' => 88,
				'knowledge'   => 85,
				'total'       => 88,
			)
		);

		$this->assertSame( array(), $block->entries() );
		$this->assertSame(
			'All within bounds — queue 17 (nothing late), mail 12/80 PHP, 4/400 SMTP, intake 15/128 unhandled, 0 quarantined, publication 88/88 engineering, 85 knowledge.',
			$block->empty_text()
		);
	}

	/**
	 * Production on 2026-11-11 held 17 pending actions, every one scheduled
	 * ahead (the earliest 36 minutes out). A queue whose actions all wait for a
	 * future slot is healthy and must stay quiet: pending means "not due yet".
	 */
	public function test_a_queue_of_actions_scheduled_ahead_is_quiet(): void {
		$block = $this->block( $this->queue( 17, 0 ), $this->mail(), $this->intake(), $this->publication() );

		$this->assertSame( array(), $block->entries() );
		$this->assertStringContainsString( 'queue 17 (nothing late)', $block->empty_text() );
	}

	/**
	 * An action exactly a day late is still inside the last retry step: the
	 * digest stays quiet.
	 */
	public function test_an_action_exactly_a_day_late_is_not_yet_overdue(): void {
		$block = $this->block( $this->queue( 1, DAY_IN_SECONDS ), $this->mail(), $this->intake(), $this->publication() );

		$this->assertSame( array(), $block->entries() );
	}

	/**
	 * One second past the last retry delay the action is stuck, and the line
	 * reports it with the moment it entered the queue.
	 */
	public function test_one_second_past_a_day_is_overdue(): void {
		$block = $this->block( $this->queue( 1, DAY_IN_SECONDS + 1 ), $this->mail(), $this->intake(), $this->publication() );

		$rows = $block->entries();
		$this->assertCount( 1, $rows );
		$this->assertSame( '1 queued delivery action(s) are more than a day overdue.', $rows[0]['label'] );
		$this->assertStringContainsString( 'Queue: 1 pending in total', $rows[0]['detail'] );
		$this->assertStringContainsString( 'The latest action was due 24 hours ago.', $rows[0]['detail'] );
	}

	/**
	 * A full sample page reports the count as a floor, not as the total.
	 */
	public function test_a_full_queue_sample_is_reported_as_a_floor(): void {
		$block = $this->block(
			array(
				'pending'  => OperationsProbe::QUEUE_SAMPLE,
				'capped'   => true,
				'lateness' => DAY_IN_SECONDS + 3600,
				'overdue'  => 4,
			),
			$this->mail(),
			$this->intake(),
			$this->publication()
		);

		$rows = $block->entries();
		$this->assertCount( 1, $rows );
		$this->assertSame( '4 queued delivery action(s) are more than a day overdue.', $rows[0]['label'] );
		$this->assertStringContainsString( 'Queue: at least 500 pending in total', $rows[0]['detail'] );
	}

	/**
	 * Mail alerts start exactly at the ordinary share; the last fifth of the
	 * PHP pool and the last tenth of the SMTP pool belong to critical mail.
	 */
	public function test_mail_alerts_start_at_the_ordinary_share(): void {
		$below = $this->block(
			$this->queue(),
			array(
				'php'  => 63,
				'smtp' => 359,
			),
			$this->intake(),
			$this->publication()
		);
		$this->assertSame( array(), $below->entries() );

		$at   = $this->block(
			$this->queue(),
			array(
				'php'  => 64,
				'smtp' => 360,
			),
			$this->intake(),
			$this->publication()
		);
		$rows = $at->entries();
		$this->assertCount( 2, $rows );
		$this->assertSame( 'PHP mail() has used 64 of 80 daily attempts.', $rows[0]['label'] );
		$this->assertSame( 'SMTP has used 360 of 400 daily attempts.', $rows[1]['label'] );
		$this->assertStringContainsString( 'Ordinary mail stops at 64; the last 16 attempts', $rows[0]['detail'] );
	}

	/**
	 * The backlog line opens at three quarters of the 128-inquiry envelope,
	 * the point #568 measured at 102 unhandled during the 2026-10-22 wave.
	 */
	public function test_backlog_alert_boundary_is_three_quarters_of_the_envelope(): void {
		$limit = (int) floor( BusinessCapacity::LIMITS['ordinary']['count'] * OperationsHealth::BACKLOG_SHARE );
		$this->assertSame( 96, $limit );

		$below = $this->block(
			$this->queue(),
			$this->mail(),
			array(
				'unhandled'   => 95,
				'bytes'       => 1_000,
				'quarantined' => 0,
			),
			$this->publication()
		);
		$this->assertSame( array(), $below->entries() );

		$at   = $this->block(
			$this->queue(),
			$this->mail(),
			array(
				'unhandled'   => 96,
				'bytes'       => 1_000,
				'quarantined' => 0,
			),
			$this->publication()
		);
		$rows = $at->entries();
		$this->assertCount( 1, $rows );
		$this->assertSame( '96 unhandled inquiries are near the site envelope of 128.', $rows[0]['label'] );
	}

	/**
	 * Quarantine alerts at nine tenths of the 128-slot verification lane, the
	 * point where a full lane starts refusing a genuine new submission. #568
	 * measured 102 unhandled during the live wave, and production held 90 on
	 * 2026-11-11 without the lane being full: that standing backlog must not
	 * restate every morning (PendingReviews already reports the count).
	 */
	public function test_quarantine_alert_boundary_is_the_verification_lane(): void {
		$this->assertSame( 0.9, OperationsHealth::QUARANTINE_SHARE );

		$production = $this->block(
			$this->queue(),
			$this->mail(),
			array(
				'unhandled'   => 0,
				'bytes'       => 0,
				'quarantined' => 90,
			),
			$this->publication()
		);
		$this->assertSame( array(), $production->entries(), 'A standing backlog of 90 must not alert daily.' );

		$below = $this->block(
			$this->queue(),
			$this->mail(),
			array(
				'unhandled'   => 0,
				'bytes'       => 0,
				'quarantined' => 114,
			),
			$this->publication()
		);
		$this->assertSame( array(), $below->entries() );

		$at   = $this->block(
			$this->queue(),
			$this->mail(),
			array(
				'unhandled'   => 0,
				'bytes'       => 0,
				'quarantined' => 115,
			),
			$this->publication()
		);
		$rows = $at->entries();
		$this->assertCount( 1, $rows );
		$this->assertSame( '115 inquiries are quarantined against a review lane of 128.', $rows[0]['label'] );
	}

	/**
	 * One unprepared product is the whole point of the publication line: the
	 * planner builds from this feed, and 0/88 was the 2026-11-11 signature.
	 */
	public function test_publication_alert_when_any_product_is_unprepared(): void {
		$ready = $this->block(
			$this->queue(),
			$this->mail(),
			$this->intake(),
			array(
				'engineering' => 88,
				'knowledge'   => 85,
				'total'       => 88,
			)
		);
		$this->assertSame( array(), $ready->entries() );

		$short = $this->block(
			$this->queue(),
			$this->mail(),
			$this->intake(),
			array(
				'engineering' => 87,
				'knowledge'   => 85,
				'total'       => 88,
			)
		);
		$rows  = $short->entries();
		$this->assertCount( 1, $rows );
		$this->assertSame( 'Engineering feed prepared 87 of 88 products.', $rows[0]['label'] );
	}

	/**
	 * Knowledge readiness is reported in the healthy line but is not an alert:
	 * no recipe-aware worker exists on a pulled instance, so 0/88 there is the
	 * documented state, not a defect (review-readiness-fix.md, unresolved list).
	 */
	public function test_knowledge_readiness_alone_never_alerts(): void {
		$block = $this->block(
			$this->queue(),
			$this->mail(),
			$this->intake(),
			array(
				'engineering' => 88,
				'knowledge'   => 0,
				'total'       => 88,
			)
		);

		$this->assertSame( array(), $block->entries() );
		$this->assertStringContainsString( '88/88 engineering, 0 knowledge', $block->empty_text() );
	}

	/**
	 * A failed measurement is an alert line of its own, never a zero, and the
	 * other dimensions still report.
	 */
	public function test_an_unreadable_dimension_is_reported_not_zeroed(): void {
		$block = $this->block( new WP_Error( 'operations_queue_unreadable' ), $this->mail(), $this->intake(), $this->publication() );

		$rows = $block->entries();
		$this->assertCount( 1, $rows );
		$this->assertSame( 'The delivery queue could not be read.', $rows[0]['label'] );
		$this->assertStringContainsString( 'This is not a zero reading', $rows[0]['detail'] );
		$this->assertStringContainsString( 'queue unreadable', $block->empty_text() );
		$this->assertStringContainsString( 'publication 88/88 engineering', $block->empty_text() );
	}

	/**
	 * The block reads its probes once per instance: the template asks for the
	 * entries and the empty sentence separately.
	 */
	public function test_the_probes_are_read_once(): void {
		$calls = 0;
		$probe = new OperationsProbe(
			new Throttle( $this->ledger( $this->mail() ) ),
			new ReviewSummary(
				static function () use ( &$calls ): array {
					++$calls;
					return array(
						'count'  => 0,
						'oldest' => 0,
						'url'    => 'http://linker.test/wp-admin/',
					);
				}
			),
			static fn (): array => array(
				'unhandled' => 3,
				'bytes'     => 1_000,
			),
			static fn (): array => array(
				'products' => array(),
			)
		);
		WP_Mock::userFunction( 'as_get_scheduled_actions', array( 'return' => array() ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'http://linker.test/wp-admin/' ) );

		$block = new OperationsHealth( self::NOW, $probe );
		$block->entries();
		$block->empty_text();

		$this->assertSame( 1, $calls );
	}

	/**
	 * A block wired to the four measurements.
	 *
	 * @param array<string,mixed>|WP_Error $queue       Queue measurement.
	 * @param array{php: int, smtp: int}   $mail        Mail measurement.
	 * @param array<string,int>            $intake      Intake measurement.
	 * @param array<string,int>            $publication Publication measurement.
	 */
	private function block( array|WP_Error $queue, array $mail, array $intake, array $publication ): OperationsHealth {
		return new OperationsHealth( self::NOW, $this->probe( $queue, $mail, $intake, $publication ) );
	}

	/**
	 * A probe whose four readers are fixed closures.
	 *
	 * @param array<string,mixed>|WP_Error $queue       Queue measurement.
	 * @param array{php: int, smtp: int}   $mail        Mail measurement.
	 * @param array<string,int>            $intake      Intake measurement.
	 * @param array<string,int>            $publication Publication measurement.
	 */
	private function probe( array|WP_Error $queue, array $mail, array $intake, array $publication ): OperationsProbe {
		$throttle = new Throttle( $this->ledger( $mail ) );
		$reviews  = new ReviewSummary(
			static fn (): array => array(
				'count'  => (int) ( $intake['quarantined'] ?? 0 ),
				'oldest' => (int) ( $intake['quarantined'] ?? 0 ) > 0 ? self::NOW - 3600 : 0,
				'url'    => 'http://linker.test/wp-admin/',
			)
		);
		WP_Mock::userFunction( 'as_get_scheduled_actions', array( 'return' => $queue instanceof WP_Error ? null : $this->actions( $queue ) ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'http://linker.test/wp-admin/' ) );

		$products = $this->products( $publication );

		return new OperationsProbe(
			$throttle,
			$reviews,
			static fn (): array => array(
				'unhandled' => (int) ( $intake['unhandled'] ?? 0 ),
				'bytes'     => (int) ( $intake['bytes'] ?? 0 ),
			),
			static fn (): array => array(
				'products' => $products,
			)
		);
	}

	/**
	 * Native pending actions carrying only their slot.
	 *
	 * @param array<string,mixed> $queue Queue measurement.
	 * @return list<object>
	 */
	private function actions( array $queue ): array {
		$lateness = (int) ( $queue['lateness'] ?? 0 );
		$count    = (int) ( $queue['pending'] ?? 0 );
		$overdue  = min( (int) ( $queue['overdue'] ?? 0 ), $count );
		$slots    = array();
		for ( $i = 0; $i < $count; ++$i ) {
			// The ASC page starts with the overdue tail; everything else is scheduled ahead.
			$slots[] = $i < $overdue ? self::NOW - $lateness : self::NOW + 60;
		}
		return array_map(
			static fn ( int $slot ): object => new class( $slot ) {
				/**
				 * Bind the action's slot.
				 *
				 * @param int $slot Unix time.
				 */
				public function __construct( private readonly int $slot ) {}

				/**
				 * Native schedule with one date.
				 */
				public function get_schedule(): object {
					return new class( $this->slot ) {
						/**
						 * Bind the schedule date.
						 *
						 * @param int $slot Unix time.
						 */
						public function __construct( private readonly int $slot ) {}

						/**
						 * The scheduled moment.
						 */
						public function get_date(): \DateTimeImmutable {
							return new \DateTimeImmutable( '@' . $this->slot );
						}
					};
				}
			},
			$slots
		);
	}

	/**
	 * Product readiness entries for the manifest fixture.
	 *
	 * @param array<string,int> $publication Publication measurement.
	 * @return list<array{ready: array{engineering: bool, knowledge: bool}}>
	 */
	private function products( array $publication ): array {
		$total       = (int) ( $publication['total'] ?? 0 );
		$engineering = (int) ( $publication['engineering'] ?? 0 );
		$knowledge   = (int) ( $publication['knowledge'] ?? 0 );
		$products    = array();
		for ( $i = 0; $i < $total; ++$i ) {
			$products[] = array(
				'ready' => array(
					'engineering' => $i < $engineering,
					'knowledge'   => $i < $knowledge,
				),
			);
		}
		return $products;
	}

	/**
	 * A ledger that already charges the measured attempts in both channels.
	 *
	 * @param array{php: int, smtp: int} $mail Charged attempts.
	 */
	private function ledger( array $mail ): \Linker\Commerce\Mail\BudgetLedger {
		$entries = array();
		for ( $i = 0; $i < (int) $mail['php']; ++$i ) {
			$entries[] = array(
				'time'      => self::NOW - 60,
				'transport' => Throttle::PHP,
				'origin'    => 'attempt',
				'category'  => 'standard',
				'id'        => $i + 1,
			);
		}
		for ( $i = 0; $i < (int) $mail['smtp']; ++$i ) {
			$entries[] = array(
				'time'      => self::NOW - 60,
				'transport' => Throttle::SMTP,
				'origin'    => 'attempt',
				'category'  => 'standard',
				'id'        => 1_000 + $i,
			);
		}
		$options = array(
			\Linker\Commerce\Mail\OptionBudgetLedger::OPTION => array(
				'entries' => $entries,
				'next_id' => 2_000,
			),
		);
		return new \Linker\Commerce\Tests\Fixtures\BudgetMemory( $options );
	}

	/**
	 * A quiet mail measurement.
	 *
	 * @return array{php: int, smtp: int}
	 */
	private function mail(): array {
		return array(
			'php'  => 12,
			'smtp' => 4,
		);
	}

	/**
	 * A queue measurement whose overdue count follows how late its latest action is.
	 *
	 * @param int $pending  Pending actions.
	 * @param int $lateness How late the latest action is; 0 schedules everything ahead.
	 * @return array{pending: int, capped: bool, lateness: int, overdue: int}
	 */
	private function queue( int $pending = 17, int $lateness = 0 ): array {
		return array(
			'pending'  => $pending,
			'capped'   => false,
			'lateness' => $lateness,
			'overdue'  => $lateness > DAY_IN_SECONDS ? 1 : 0,
		);
	}

	/**
	 * A quiet intake measurement.
	 *
	 * @return array{unhandled: int, bytes: int, quarantined: int}
	 */
	private function intake(): array {
		return array(
			'unhandled'   => 15,
			'bytes'       => 35_685,
			'quarantined' => 0,
		);
	}

	/**
	 * A quiet publication measurement.
	 *
	 * @return array{engineering: int, knowledge: int, total: int}
	 */
	private function publication(): array {
		return array(
			'engineering' => 88,
			'knowledge'   => 85,
			'total'       => 88,
		);
	}
}
