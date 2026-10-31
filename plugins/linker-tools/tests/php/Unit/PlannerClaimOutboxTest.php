<?php
/**
 * Native claim discovery respects an event's existing retry backoff.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\ClaimOutbox;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Sweep and foreground recovery share one pending action per native event.
 *
 * @covers \Linker\Tools\Planner\ClaimOutbox
 */
final class PlannerClaimOutboxTest extends TestCase {

	/**
	 * Native scheduler rows with different retry arguments.
	 *
	 * @var list<array{args:array{int,int},status:string,date:int}>
	 */
	private array $actions = array();

	/**
	 * Previous native database fixture, restored after each case.
	 *
	 * @var mixed
	 */
	private mixed $previous_database;

	/** An unresolved event needs retry without any network or account writes. */
	public function setUp(): void {
		parent::setUp();
		$this->previous_database = $GLOBALS['wpdb'] ?? null;
		$database                = new class() {
			/**
			 * Native table name for this discovery fixture.
			 *
			 * @var string
			 */
			public string $posts = 'wp_posts';

			/**
			 * Keep the discovery fixture inside this process.
			 *
			 * @param string $query Native query template.
			 * @param mixed  ...$args Native query arguments.
			 */
			public function prepare( string $query, mixed ...$args ): string {
				return $query;
			}

			/**
			 * Return the one unresolved native event.
			 *
			 * @param string $query Native discovery query.
			 * @return list<string>
			 */
			public function get_col( string $query ): array {
				return array( '42' );
			}
		};
		$GLOBALS['wpdb']         = $database; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- bounded native database fixture, restored in tearDown.
		WP_Mock::userFunction( 'get_post' )->with( 42 )->andReturn(
			new \WP_Post(
				(object) array(
					'ID'           => 42,
					'post_type'    => ClaimOutbox::POST_TYPE,
					'post_status'  => 'private',
					'post_content' => '{}',
				)
			)
		);
		WP_Mock::userFunction( 'get_posts' )->andReturn( array( 42 ) );
		WP_Mock::userFunction( 'get_option' )->with( 'linker_planner_claim_cursor', 0 )->andReturn( 0 );
		WP_Mock::userFunction( 'update_option' )->with( 'linker_planner_claim_cursor', 0, false )->andReturn( true );
		WP_Mock::userFunction( 'did_action' )->with( 'action_scheduler_init' )->andReturn( 1 );
		WP_Mock::userFunction( 'as_get_scheduled_actions' )->andReturnUsing(
			function ( array $query, string $format ): array {
				$this->assertSame( ClaimOutbox::HOOK, $query['hook'] );
				$this->assertSame( ClaimOutbox::GROUP, $query['group'] );
				$this->assertSame( 1, $query['per_page'] );
				$this->assertSame( 'ids', $format );
				foreach ( $this->actions as $index => $action ) {
					// Native AS searches its JSON argument string and accepts a status list.
					if ( str_contains( (string) json_encode( $action['args'] ), $query['search'] ) && in_array( $action['status'], $query['status'], true ) ) { // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- native scheduler argument fixture.
						return array( $index + 1 );
					}
				}
				return array();
			}
		);
		WP_Mock::userFunction( 'as_schedule_single_action' )->andReturnUsing(
			function ( int $date, string $hook, array $args, string $group, bool $unique ): int {
				$this->assertSame( ClaimOutbox::HOOK, $hook );
				$this->assertSame( ClaimOutbox::GROUP, $group );
				$this->assertTrue( $unique );
				$this->assertIsInt( $args[0] );
				$this->assertIsInt( $args[1] );
				$this->actions[] = array(
					'args'   => array( $args[0], $args[1] ),
					'status' => 'pending',
					'date'   => $date,
				);
				return count( $this->actions );
			}
		);
	}

	/** No instance, process, scheduler row or database survives this fixture. */
	public function tearDown(): void {
		$GLOBALS['wpdb'] = $this->previous_database; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- restore the previous fixture.
		parent::tearDown();
	}

	/** Discovery cannot reset a running event or bypass its delayed retry. */
	public function test_sweep_and_foreground_recovery_preserve_existing_retry(): void {
		$this->actions[] = array(
			'args'   => array( 42, 4 ),
			'status' => 'in-progress',
			'date'   => time(),
		);
		$outbox          = new ClaimOutbox();
		$outbox->sweep();
		$this->assertCount( 1, $this->actions );
		$before = time();
		$outbox->run( 42, 4 );
		$this->assertCount( 2, $this->actions );
		$this->assertSame( array( 42, 5 ), $this->actions[1]['args'] );
		$this->assertGreaterThanOrEqual( $before + 15 * MINUTE_IN_SECONDS, $this->actions[1]['date'] );
		$this->actions[0]['status'] = 'complete';
		$outbox->sweep();
		$outbox->settle( 7 );
		$this->assertCount( 2, $this->actions );
	}

	/** A different native event, including an ID prefix, must not block recovery. */
	public function test_another_events_retry_does_not_block_this_event(): void {
		$this->actions[] = array(
			'args'   => array( 420, 5 ),
			'status' => 'pending',
			'date'   => time() + 15 * MINUTE_IN_SECONDS,
		);
		$outbox          = new ClaimOutbox();
		$before          = time();
		$outbox->run( 42 );
		$this->assertCount( 2, $this->actions );
		$this->assertSame( array( 42, 1 ), $this->actions[1]['args'] );
		$this->assertGreaterThanOrEqual( $before + MINUTE_IN_SECONDS, $this->actions[1]['date'] );
	}
}
