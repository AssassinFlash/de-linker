<?php
/**
 * Native claim discovery respects an event's existing retry backoff.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\ClaimOutbox;
use Linker\Tools\Planner\Transport;
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
	 * Actual private deliveries, independent of the AS row count.
	 *
	 * @var int
	 */
	private int $transport_calls = 0;

	/**
	 * A valid engine receipt allows the same original event to complete.
	 *
	 * @var bool
	 */
	private bool $acknowledge = false;

	/**
	 * Whether Action Scheduler has completed its init priority-1 bootstrap.
	 *
	 * @var int
	 */
	private int $scheduler_ready = 1;

	/**
	 * Unresolved native event IDs returned for the current account.
	 *
	 * @var list<int>
	 */
	private array $user_events = array( 42 );

	/**
	 * `numberposts` windows each account discovery asked for.
	 *
	 * @var list<int>
	 */
	private array $event_windows = array();

	/**
	 * The discovery database fixture of the running case, its recorded
	 * statement bounds included.
	 *
	 * @var object{bounds: list<mixed>}
	 */
	private object $database_fixture;

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
			 * The discovery bound each prepared statement was limited by.
			 *
			 * @var list<mixed>
			 */
			public array $bounds = array();

			/**
			 * Keep the discovery fixture inside this process.
			 *
			 * @param string $query Native query template.
			 * @param mixed  ...$args Native query arguments.
			 */
			public function prepare( string $query, mixed ...$args ): string {
				$this->bounds[] = $args[ array_key_last( $args ) ] ?? null;
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
		$this->database_fixture  = $database;
		WP_Mock::userFunction( 'get_post' )->with( 42 )->andReturn(
			new \WP_Post(
				(object) array(
					'ID'           => 42,
					'post_type'    => ClaimOutbox::POST_TYPE,
					'post_status'  => 'private',
					'post_author'  => 7,
					// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- Valid immutable native event fixture.
					'post_content' => json_encode(
						array(
							'schema_version' => 1,
							'guest'          => 'wp:1:guest:' . str_repeat( 'a', 64 ),
							'user'           => 7,
							'key'            => str_repeat( 'b', 64 ),
						)
					),
				)
			)
		);
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			define( 'LINKER_GENIE_SERVICE_TOKEN', 'unit-test-only' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Synthetic private transport credential.
		}
		WP_Mock::userFunction( 'get_userdata' )->with( 7 )->andReturn( new \WP_User() );
		WP_Mock::userFunction( 'get_current_blog_id' )->andReturn( 1 );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value ): string|false => json_encode( $value ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- Native encoder double.
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing( static fn ( mixed $value ): bool => $value instanceof \WP_Error );
		WP_Mock::userFunction( '__' )->andReturnUsing( static fn ( string $value ): string => $value );
		WP_Mock::userFunction( 'get_option' )->with( 'linker_planner_url', '' )->andReturn( 'https://engine.test/planning' );
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code' )->andReturn( 200 );
		WP_Mock::userFunction( 'wp_remote_retrieve_header' )->andReturn( 'application/json' );
		WP_Mock::userFunction( 'wp_remote_retrieve_body' )->andReturn( '{"schema_version":1,"status":"claimed","guest_retired":true,"transferred_count":2}' );
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			function ( array $query ): array {
				if ( isset( $query['name'] ) ) {
					return array();
				}
				$this->event_windows[] = (int) $query['numberposts'];
				return $this->user_events;
			}
		);
		WP_Mock::userFunction( 'get_option' )->with( 'linker_planner_claim_cursor', 0 )->andReturn( 0 );
		WP_Mock::userFunction( 'update_option' )->with( 'linker_planner_claim_cursor', 0, false )->andReturn( true );
		WP_Mock::userFunction( 'did_action' )->with( 'action_scheduler_init' )->andReturnUsing( fn (): int => $this->scheduler_ready );
		WP_Mock::userFunction( 'as_get_scheduled_actions' )->andReturnUsing(
			function ( array $query, string $format ): array {
				$this->assertSame( ClaimOutbox::HOOK, $query['hook'] );
				$this->assertSame( ClaimOutbox::GROUP, $query['group'] );
				$this->assertSame( 1, $query['per_page'] );
				$this->assertSame( 'ids', $format );
				if ( isset( $query['date'] ) ) {
					$this->assertSame( '>', $query['date_compare'] );
				}
				foreach ( $this->actions as $index => $action ) {
					// Native AS searches its JSON argument string and accepts a status list.
					if ( str_contains( (string) json_encode( $action['args'] ), $query['search'] ) && in_array( $action['status'], (array) $query['status'], true ) && ( ! isset( $query['date'] ) || $action['date'] > $query['date'] ) ) { // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- native scheduler argument fixture.
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
		$outbox          = $this->outbox();
		$outbox->sweep();
		$this->assertCount( 1, $this->actions );
		$outbox->settle( 7 );
		$this->assertSame( 0, $this->transport_calls, 'A running delivery owns the event.' );
		$before = time();
		$outbox->run( 42, 4 );
		$this->assertSame( 1, $this->transport_calls );
		$this->assertCount( 2, $this->actions );
		$this->assertSame( array( 42, 5 ), $this->actions[1]['args'] );
		$this->assertGreaterThanOrEqual( $before + 15 * MINUTE_IN_SECONDS, $this->actions[1]['date'] );
		$this->actions[0]['status'] = 'complete';
		$outbox->sweep();
		$outbox->settle( 7 );
		$this->assertSame( 1, $this->transport_calls, 'Foreground checks cannot bypass the delayed retry.' );
		$this->assertCount( 2, $this->actions );
	}

	/** A different native event, including an older backoff or ID prefix, must not block recovery. */
	public function test_another_events_retry_does_not_block_this_event(): void {
		$this->user_events = array( 41, 42 );
		$this->actions[]   = array(
			'args'   => array( 41, 2 ),
			'status' => 'pending',
			'date'   => time() + 15 * MINUTE_IN_SECONDS,
		);
		$this->actions[]   = array(
			'args'   => array( 420, 5 ),
			'status' => 'pending',
			'date'   => time() + 15 * MINUTE_IN_SECONDS,
		);
		$outbox            = $this->outbox();
		$before            = time();
		$outbox->settle( 7 );
		$this->assertSame( 1, $this->transport_calls, 'Another event must not block immediate foreground delivery.' );
		$this->assertCount( 3, $this->actions );
		$this->assertSame( array( 42, 1 ), $this->actions[2]['args'] );
		$this->assertGreaterThanOrEqual( $before + MINUTE_IN_SECONDS, $this->actions[2]['date'] );
		$this->actions[2]['date'] = time() - 1;
		$this->acknowledge        = true;
		WP_Mock::userFunction( 'wp_delete_post' )->once()->with( 42, true )->andReturn( new \WP_Post( (object) array( 'ID' => 42 ) ) );
		$outbox->settle( 7 );
		$this->assertSame( 2, $this->transport_calls, 'A due retry can complete with its original engine receipt.' );
	}

	/** A served request settles a bounded window, never the background batch. */
	public function test_foreground_recovery_reads_a_smaller_window_than_the_sweep(): void {
		$outbox = $this->outbox();
		$outbox->settle( 7 );
		$this->assertSame( array( 8 ), $this->event_windows, 'One request settles at most 8 recent events.' );
		$this->event_windows = array();
		$outbox->sweep();
		$this->assertSame( array(), $this->event_windows, 'The sweep discovers through its own SQL window, not account queries.' );
		$this->assertSame(
			32,
			$this->database_fixture->bounds[0] ?? null,
			'Background discovery keeps its 32-event batch.'
		);
	}

	/** Early init priority-0 captures defer scheduling until action_scheduler_init runs. */
	public function test_early_enqueue_flushes_when_action_scheduler_initializes(): void {
		$this->scheduler_ready = 0;
		$guest                 = 'wp:1:guest:' . str_repeat( 'a', 64 );
		$key                   = str_repeat( 'b', 64 );
		WP_Mock::userFunction( 'wp_hash' )->with( 'linker-planner-claim:v1|' . $guest . '|7', 'auth', 'sha256' )->andReturn( $key );
		WP_Mock::userFunction( 'wp_slash' )->andReturnUsing( static fn ( mixed $value ): mixed => $value );
		WP_Mock::userFunction( 'wp_insert_post' )->once()->andReturn( 42 );
		WP_Mock::userFunction( 'wp_next_scheduled' )->with( ClaimOutbox::SWEEP )->andReturn( time() + 60 );
		$outbox = $this->outbox();
		$this->assertSame( 42, $outbox->enqueue( $guest, 7 ) );
		$this->assertCount( 0, $this->actions );
		$this->scheduler_ready = 1;
		$outbox->schedule();
		$this->assertCount( 1, $this->actions );
		$this->assertSame( array( 42, 0 ), $this->actions[0]['args'] );
	}

	/** Exercise the real event validation and transport, without any network. */
	private function outbox(): ClaimOutbox {
		return new ClaimOutbox(
			new Transport(
				function ( string $url, array $args ): array|\WP_Error {
					++$this->transport_calls;
					$this->assertSame( 'https://engine.test/planning/identity/claim-session', $url );
					$this->assertSame( 'wp:1:user:7', $args['headers']['X-Linker-Planner-Principal-Subject'] );
					$this->assertSame( 'wp:1:guest:' . str_repeat( 'a', 64 ), $args['headers']['X-Linker-Planner-Previous-Guest'] );
					$this->assertSame(
						array(
							'schema_version' => 1,
							'key'            => str_repeat( 'b', 64 ),
						),
						json_decode( $args['body'], true )
					);
					return $this->acknowledge ? array() : new \WP_Error( 'offline' );
				}
			)
		);
	}
}
