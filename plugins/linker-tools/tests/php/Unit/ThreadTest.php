<?php
/**
 * The conversation thread kept on the conversation post.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Thread;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Thread.
 *
 * @covers \Linker\Tools\Genie\Thread
 */
final class ThreadTest extends TestCase {

	/**
	 * What GET_LOCK answers. '0' is the lock not being acquired (#373).
	 *
	 * @var string
	 */
	public string $lock_answer = '1';

	/**
	 * GET_LOCK answers in order. An empty list falls through to lock_answer.
	 *
	 * @var list<string>|null
	 */
	public ?array $lock_answers = null;

	/**
	 * IS_USED_LOCK = CONNECTION_ID() answers in order. Null is a failed
	 * lookup. An empty list falls through to owned ('1').
	 *
	 * @var list<string|null>|null
	 */
	public ?array $owns_answers = null;

	/**
	 * How many RELEASE_LOCK queries this test has run.
	 *
	 * @var int
	 */
	public int $releases = 0;

	/**
	 * Prepare calls, so a test can see the lock name.
	 *
	 * @var list<array{0: string, 1: list<mixed>}>
	 */
	public array $prepares = array();

	/**
	 * Whether $GLOBALS['wpdb'] existed before setUp replaced it.
	 *
	 * @var bool
	 */
	private bool $had_wpdb = false;

	/**
	 * The database global setUp replaced, when there was one.
	 *
	 * @var mixed
	 */
	private mixed $previous_wpdb = null;

	/**
	 * Database name in the lock. Reference, staging and live share post ids.
	 *
	 * @var string
	 */
	public string $dbname = 'linker_reference';

	/**
	 * Table prefix in the lock.
	 *
	 * @var string
	 */
	public string $prefix = 'wp_';

	/**
	 * Storage escaping is exercised against real WordPress in the route fixture.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->had_wpdb      = array_key_exists( 'wpdb', $GLOBALS );
		$this->previous_wpdb = $GLOBALS['wpdb'] ?? null;
		WP_Mock::userFunction( 'wp_slash', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction( 'has_action', array( 'return' => false ) );
		$owner    = $this;
		$database = new class( $owner ) {
			/**
			 * The test, which holds the lock answer and the name parts.
			 *
			 * @var ThreadTest
			 */
			private ThreadTest $owner;

			/**
			 * Keeps the test that holds the lock answer.
			 *
			 * @param ThreadTest $owner The test, which holds the lock answer.
			 */
			public function __construct( ThreadTest $owner ) {
				$this->owner = $owner;
			}

			/**
			 * The lock name reads dbname and prefix. They live on the test.
			 *
			 * @param string $name Property name.
			 */
			public function __isset( string $name ): bool {
				return 'dbname' === $name || 'prefix' === $name;
			}

			/**
			 * The lock name reads dbname and prefix. They live on the test.
			 *
			 * @param string $name Property name.
			 */
			public function __get( string $name ): string {
				if ( 'dbname' === $name ) {
					return $this->owner->dbname;
				}
				if ( 'prefix' === $name ) {
					return $this->owner->prefix;
				}
				return '';
			}

			/**
			 * The query unchanged. The bound values are kept for the lock name.
			 *
			 * @param string $query SQL text.
			 * @param mixed  ...$args Bound values.
			 */
			public function prepare( string $query, mixed ...$args ): string {
				$this->owner->prepares[] = array( $query, array_values( $args ) );
				return $query;
			}

			/**
			 * GET_LOCK answers the test's lock answer. IS_USED_LOCK answers
			 * the ownership script. RELEASE_LOCK is counted.
			 *
			 * @param string $query SQL text.
			 */
			public function get_var( string $query ): ?string {
				if ( str_contains( $query, 'RELEASE_LOCK' ) ) {
					++$this->owner->releases;
					return '1';
				}
				if ( str_contains( $query, 'IS_USED_LOCK' ) ) {
					$answers = $this->owner->owns_answers;
					if ( is_array( $answers ) && array() !== $answers ) {
						$next                      = array_shift( $answers );
						$this->owner->owns_answers = $answers;
						return is_string( $next ) ? $next : null;
					}
					return '1';
				}
				if ( str_contains( $query, 'GET_LOCK' ) ) {
					$answers = $this->owner->lock_answers;
					if ( is_array( $answers ) && array() !== $answers ) {
						$next                      = array_shift( $answers );
						$this->owner->lock_answers = $answers;
						return $next;
					}
					return $this->owner->lock_answer;
				}
				return '1';
			}
		};
		// phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the database double stands in for the named lock.
		$GLOBALS['wpdb'] = $database;
	}

	/**
	 * Puts the previous database global back. A later test must not see this double.
	 */
	public function tearDown(): void {
		parent::tearDown();
		if ( $this->had_wpdb ) {
			// phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- restores the database double setUp installed.
			$GLOBALS['wpdb'] = $this->previous_wpdb;
		} else {
			unset( $GLOBALS['wpdb'] );
		}
	}

	/**
	 * Reading a conversation that does not exist answers empty, without a write.
	 */
	public function test_read_without_a_conversation_is_empty(): void {
		$this->assertSame(
			array(
				'messages' => array(),
				'stream'   => '',
			),
			( new Thread() )->read( 0 )
		);
		$this->assertConditionsMet();
	}

	/**
	 * The stored meta comes back as it went in.
	 */
	public function test_read_returns_the_stored_messages_and_stream(): void {
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn( $id, $key ) => Thread::MESSAGES === $key
					? array(
						array(
							'role'    => 'user',
							'content' => 'Hello',
						),
					)
					: 'event: done' . "\n" . 'data: {}' . "\n\n",
			)
		);

		$store = ( new Thread() )->read( 51 );

		$this->assertSame(
			array(
				array(
					'role'    => 'user',
					'content' => 'Hello',
				),
			),
			$store['messages']
		);
		$this->assertSame( 'event: done' . "\n" . 'data: {}' . "\n\n", $store['stream'] );
		$this->assertConditionsMet();
	}

	/**
	 * A corrupt store is not a fatal: it reads as empty.
	 */
	public function test_read_tolerates_a_store_of_the_wrong_shape(): void {
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn( $id, $key ) => Thread::MESSAGES === $key ? 'not an array' : array( 'not a string' ),
			)
		);

		$this->assertSame(
			array(
				'messages' => array(),
				'stream'   => '',
			),
			( new Thread() )->read( 51 )
		);
		$this->assertConditionsMet();
	}

	/**
	 * Only message-shaped entries are kept, and the newest ones at the cap.
	 */
	public function test_record_keeps_messages_only_and_caps_the_thread(): void {
		$written = array();
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => static function ( $id, $key, $value ) use ( &$written ): bool {
					$written[ $key ] = $value;
					return true;
				},
			)
		);

		$messages = array(
			array(
				'role'    => 'system',
				'content' => 'x',
			),
		);
		for ( $i = 0; $i < Thread::LIMIT + 5; $i++ ) {
			$messages[] = array(
				'role'    => 0 === $i % 2 ? 'user' : 'assistant',
				'content' => "message {$i}",
			);
		}
		$messages[] = array( 'role' => 'user' );
		$messages[] = 'not a message';

		( new Thread() )->record( 51, $messages, 'stream' );

		$kept = $written[ Thread::MESSAGES ];
		$this->assertCount( Thread::LIMIT, $kept );
		$this->assertSame( 'stream', $written[ Thread::STREAM ] );
		foreach ( $kept as $message ) {
			$this->assertContains( $message['role'], array( 'user', 'assistant' ) );
			$this->assertNotSame( '', $message['content'] );
		}
		// The newest stay, the oldest fall off the front. The two dropped
		// entries shift the window: 65 valid messages, the last 60 kept.
		$this->assertSame( 'message 5', $kept[0]['content'] );
		$this->assertSame(
			'message ' . ( Thread::LIMIT + 4 ),
			$kept[ Thread::LIMIT - 1 ]['content']
		);
		$this->assertConditionsMet();
	}

	/**
	 * Without a conversation there is nothing to write to.
	 */
	public function test_record_without_a_conversation_writes_nothing(): void {
		( new Thread() )->record(
			0,
			array(
				array(
					'role'    => 'user',
					'content' => 'Hello',
				),
			),
			'stream'
		);
		$this->assertConditionsMet();
	}

	/**
	 * A turn's `reading` events go to the conversation's readings and out of
	 * the stored stream; the newest ten are kept (#236).
	 */
	public function test_record_keeps_the_readings_apart_from_the_stream(): void {
		$earlier = array();
		for ( $n = 1; $n <= 10; $n++ ) {
			$earlier[] = array(
				'id'   => 'att' . $n,
				'kind' => 'document',
			);
		}
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn( $id, $key ) => Thread::READINGS === $key ? $earlier : array(),
			)
		);
		$written = array();
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => static function ( $id, $key, $value ) use ( &$written ): bool {
					$written[ $key ] = $value;
					return true;
				},
			)
		);
		$stream = "event: meta\ndata: {}\n\nevent: attachment\ndata: {\"id\":\"att11\"}\n\n"
			. "event: reading\ndata: {\"id\":\"att11\",\"kind\":\"nameplate\",\"model\":\"H2-10K-T3\"}\n\n"
			. "event: done\ndata: {\"ok\":true}\n\n";

		$split = Thread::split( $stream );
		( new Thread() )->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Attached: plate.jpg',
				),
			),
			$split['stream'],
			$split['readings']
		);

		$kept = $written[ Thread::READINGS ];
		$this->assertCount( Thread::READINGS_LIMIT, $kept );
		$this->assertSame( 'att2', $kept[0]['id'] );
		$this->assertSame( 'H2-10K-T3', $kept[9]['model'] );
		$this->assertStringNotContainsString( 'event: reading', $written[ Thread::STREAM ] );
		$this->assertStringContainsString( 'event: attachment', $written[ Thread::STREAM ] );
		$this->assertStringContainsString( 'event: done', $written[ Thread::STREAM ] );
	}

	/**
	 * Without a conversation there are no readings, and a corrupt store reads empty.
	 */
	public function test_readings_tolerate_no_conversation_and_a_corrupt_store(): void {
		$this->assertSame( array(), ( new Thread() )->readings( 0 ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => array( 'junk', array( 'no' => 'id' ) ) ) );
		$this->assertSame( array(), ( new Thread() )->readings( 51 ) );
	}

	/**
	 * Two writers snap the same history. The second commit must keep the
	 * first turn and append its own, in commit order (#373).
	 */
	public function test_a_stale_second_writer_keeps_both_turns(): void {
		$this->remember_meta();
		$thread = new Thread();
		$first  = $this->stream( 'The hybrid inverter is three-phase.', array( 4107 ) );
		$this->assertTrue(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
				),
				$first
			)
		);

		$ev   = $this->stream( 'EV chargers in the range are these.', array( 11 ) );
		$wall = $this->stream( 'Wallboxen in der Auswahl sind diese.', array( 22 ) );
		$this->assertTrue(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'EV chargers',
					),
				),
				$ev
			)
		);
		// The same base the first writer used. It does not contain "EV chargers".
		$this->assertTrue(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'Wallboxen',
					),
				),
				$wall
			)
		);

		$transcript = $thread->transcript( 51 );
		$this->assertSame(
			array(
				'Which inverter?',
				'The hybrid inverter is three-phase.',
				'EV chargers',
				'EV chargers in the range are these.',
				'Wallboxen',
				'Wallboxen in der Auswahl sind diese.',
			),
			array_column( $transcript, 'content' )
		);
		$this->assertSame( array( 11 ), $transcript[3]['products'] );
		$this->assertSame( array( 22 ), $transcript[5]['products'] );
	}

	/**
	 * A follow-up that already echoes the stored history is stored as the
	 * browser sent it: the previous answer is not duplicated.
	 */
	public function test_a_follow_up_that_contains_the_history_is_stored_as_sent(): void {
		$this->remember_meta();
		$thread = new Thread();
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$sent = array(
			array(
				'role'    => 'user',
				'content' => 'Which inverter?',
			),
			array(
				'role'    => 'assistant',
				'content' => 'The hybrid inverter is three-phase.',
			),
			array(
				'role'    => 'user',
				'content' => 'And a battery?',
			),
		);
		$this->assertTrue( $thread->record( 51, $sent, $this->stream( 'This battery pairs with it.' ) ) );
		$this->assertSame( $sent, $thread->read( 51 )['messages'] );
	}

	/**
	 * A snapshot whose answer text forks the stored thread is not written
	 * over it.
	 */
	public function test_a_snapshot_that_forks_the_thread_is_not_written(): void {
		$this->remember_meta();
		$thread = new Thread();
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$before   = $thread->read( 51 );
		$releases = $this->releases;
		$this->assertFalse(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'A different answer.',
					),
					array(
						'role'    => 'user',
						'content' => 'EV chargers',
					),
				),
				$this->stream( 'Would have replaced the thread.' )
			)
		);
		$this->assertSame( $before, $thread->read( 51 ) );
		$this->assertSame( $releases + 1, $this->releases );
	}

	/**
	 * No lock, no write. Falling through to an unlocked replace is the bug.
	 */
	public function test_a_commit_without_the_lock_writes_nothing(): void {
		$this->remember_meta();
		$thread = new Thread();
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$before            = $thread->read( 51 );
		$releases          = $this->releases;
		$this->lock_answer = '0';
		$this->assertFalse(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'EV chargers',
					),
				),
				$this->stream( 'Not stored.' )
			)
		);
		$this->assertSame( $before, $thread->read( 51 ) );
		// The lock was never acquired, so it is not released.
		$this->assertSame( $releases, $this->releases );
	}

	/**
	 * The lock name carries the database and the table prefix, so reference,
	 * staging and live on one server do not share it (#373).
	 */
	public function test_the_lock_name_includes_the_database_and_prefix(): void {
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );

		( new Thread() )->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Hello',
				),
			),
			'stream'
		);

		$this->assertContains( 'linker_reference/wp_linker_genie_turn_51', $this->lock_names() );
	}

	/**
	 * MySQL 8.0 rejects a GET_LOCK name longer than 64 characters. The name
	 * is then the sha256 of the database, prefix and conversation.
	 */
	public function test_a_lock_name_past_64_characters_is_its_sha256(): void {
		$this->dbname = str_repeat( 'd', 80 );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		$full = str_repeat( 'd', 80 ) . '/wp_linker_genie_turn_51';
		$this->assertGreaterThan( 64, strlen( $full ) );

		( new Thread() )->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Hello',
				),
			),
			'stream'
		);

		$this->assertContains( hash( 'sha256', $full ), $this->lock_names() );
	}

	/**
	 * A null ownership lookup aborts. A second GET_LOCK would raise the
	 * counter if this connection still held the name (#373).
	 */
	public function test_a_failed_ownership_lookup_aborts_without_taking_the_lock_again(): void {
		$this->remember_meta();
		$thread = new Thread();
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$before             = $thread->read( 51 );
		$releases           = $this->releases;
		$attempts           = $this->lock_attempts();
		$this->owns_answers = array( null );
		$this->assertFalse(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'EV chargers',
					),
				),
				$this->stream( 'Not stored.' )
			)
		);
		$this->assertSame( $before, $thread->read( 51 ) );
		$this->assertSame( $attempts + 1, $this->lock_attempts() );
		$this->assertSame( $releases + 1, $this->releases );
	}

	/**
	 * The connection no longer holds the lock. It is taken again, the
	 * thread is read again, and the peer's turn is kept (#373).
	 */
	public function test_a_lost_lock_is_reacquired_and_reread_before_the_write(): void {
		$this->remember_meta();
		( new Thread() )->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$peer               = array(
			array(
				'role'    => 'user',
				'content' => 'Which inverter?',
			),
			array(
				'role'    => 'assistant',
				'content' => 'The hybrid inverter is three-phase.',
			),
			array(
				'role'    => 'user',
				'content' => 'EV chargers',
			),
			array(
				'role'    => 'assistant',
				'content' => 'EV chargers in the range are these.',
			),
		);
		$thread             = new class( $peer ) extends Thread {
			/**
			 * The peer's committed thread, written while this commit holds the lock.
			 *
			 * @var list<array{role: string, content: string}>
			 */
			private array $peer;

			/**
			 * Keeps the peer's committed thread.
			 *
			 * @param list<array{role: string, content: string}> $peer Peer messages.
			 */
			public function __construct( array $peer ) {
				$this->peer = $peer;
			}

			/**
			 * The other commit lands, and this connection then loses the lock.
			 *
			 * @param int $conversation Conversation post ID.
			 */
			protected function while_locked( int $conversation ): void {
				update_post_meta( $conversation, self::MESSAGES, $this->peer );
				update_post_meta( $conversation, self::STREAM, '' );
			}
		};
		$this->owns_answers = array( '0', '1' );
		$this->assertTrue(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'Wallboxen',
					),
				),
				$this->stream( 'Wallboxen in der Auswahl sind diese.' )
			)
		);
		$this->assertSame(
			array(
				'Which inverter?',
				'The hybrid inverter is three-phase.',
				'EV chargers',
				'EV chargers in the range are these.',
				'Wallboxen',
				'Wallboxen in der Auswahl sind diese.',
			),
			array_column( ( new Thread() )->transcript( 51 ), 'content' )
		);
	}

	/**
	 * An explicit miss on the second acquire writes nothing and still releases.
	 */
	public function test_a_lost_lock_that_cannot_be_reacquired_writes_nothing(): void {
		$this->remember_meta();
		$thread = new Thread();
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$before             = $thread->read( 51 );
		$releases           = $this->releases;
		$this->owns_answers = array( '0' );
		$this->lock_answers = array( '1', '0' );
		$this->assertFalse(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'EV chargers',
					),
				),
				$this->stream( 'Not stored.' )
			)
		);
		$this->assertSame( $before, $thread->read( 51 ) );
		$this->assertSame( $releases + 1, $this->releases );
	}

	/** A completed operation is bound to precisely the committed messages and stream. */
	public function test_completed_operation_receipt_follows_the_committed_answer(): void {
		$this->remember_meta();
		$thread   = new Thread();
		$messages = array(
			array(
				'role'    => 'user',
				'content' => 'Check test.pdf',
			),
		);
		$id       = '56300000-0000-4000-8000-000000000001';
		$this->assertTrue( $thread->record( 51, $messages, $this->stream( 'File A.' ), array(), null, $id ) );
		$this->assertSame( $id, $thread->read( 51 )['operation_id'] ?? '' );
		update_post_meta( 51, Thread::STREAM, $this->stream( 'File B.' ) );
		$this->assertArrayNotHasKey( 'operation_id', $thread->read( 51 ) );
		update_post_meta( 51, Thread::MESSAGES, array() );
		$this->assertArrayNotHasKey( 'operation_id', $thread->read( 51 ) );
	}

	/** Off/observe and old writers invalidate a former trusted completion. */
	public function test_a_write_without_trusted_operation_clears_the_receipt(): void {
		$this->remember_meta();
		$thread   = new Thread();
		$messages = array(
			array(
				'role'    => 'user',
				'content' => 'Same question',
			),
		);
		$this->assertTrue( $thread->record( 51, $messages, $this->stream( 'First.' ), array(), null, '56300000-0000-4000-8000-000000000001' ) );
		$this->assertTrue( $thread->record( 51, $messages, $this->stream( 'Next.' ) ) );
		$this->assertSame( array(), get_post_meta( 51, 'linker_genie_completion', true ) );
		$this->assertArrayNotHasKey( 'operation_id', $thread->read( 51 ) );
	}

	/**
	 * All members of the native commit restore together on a failed write.
	 *
	 * @dataProvider completion_failures
	 * @param string $key Failed member.
	 * @param bool   $raise Throw instead of returning false.
	 */
	public function test_failed_receipt_write_rolls_back_the_whole_completion( string $key, bool $raise ): void {
		$armed = false;
		$this->remember_meta( $key, $armed, $raise );
		$thread   = new Thread();
		$messages = array(
			array(
				'role'    => 'user',
				'content' => 'Same question',
			),
		);
		$id       = '56300000-0000-4000-8000-000000000001';
		$this->assertTrue( $thread->record( 51, $messages, $this->stream( 'File A.' ), array(), null, $id ) );
		$before = $thread->read( 51 );
		$armed  = true;
		$this->assertFalse(
			$thread->record(
				51,
				array_merge(
					$messages,
					array(
						array(
							'role'    => 'assistant',
							'content' => 'File A.',
						),
						array(
							'role'    => 'user',
							'content' => 'Next question',
						),
					)
				),
				$this->stream( 'File B.' ),
				array(),
				null,
				'56300000-0000-4000-8000-000000000002'
			)
		);
		$this->assertSame( $before, $thread->read( 51 ) );
		$this->assertSame( $id, $thread->read( 51 )['operation_id'] ?? '' );
	}

	/**
	 * Main data and receipt failures, including native exceptions.
	 *
	 * @return list<array{string, bool}>
	 */
	public static function completion_failures(): array {
		return array(
			array( Thread::MESSAGES, false ),
			array( Thread::MESSAGES, true ),
			array( Thread::STREAM, false ),
			array( Thread::STREAM, true ),
			array( Thread::COMPLETION, false ),
			array( Thread::COMPLETION, true ),
		);
	}

	/**
	 * The stream write fails after the messages were replaced. The previous
	 * messages come back and the commit is not a success (#373).
	 */
	public function test_a_failed_stream_write_restores_the_previous_messages(): void {
		$armed = false;
		$this->remember_meta( Thread::STREAM, $armed );
		$thread = new Thread();
		$first  = $this->stream( 'The hybrid inverter is three-phase.' );
		$this->assertTrue(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
				),
				$first
			)
		);
		$before   = $thread->read( 51 );
		$releases = $this->releases;
		$armed    = true;
		$this->assertFalse(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'EV chargers',
					),
				),
				$this->stream( 'EV chargers in the range are these.' )
			)
		);
		$this->assertSame( $before, $thread->read( 51 ) );
		$this->assertSame( $releases + 1, $this->releases );
	}

	/**
	 * A thrown meta write is a failed commit, the lock is released, and
	 * the messages already replaced are put back.
	 */
	public function test_a_thrown_meta_write_releases_the_lock_and_restores(): void {
		$armed = false;
		$this->remember_meta( Thread::STREAM, $armed, true );
		$thread = new Thread();
		$this->assertTrue(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
				),
				$this->stream( 'The hybrid inverter is three-phase.' )
			)
		);
		$before   = $thread->read( 51 );
		$releases = $this->releases;
		$armed    = true;
		$this->assertFalse(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'EV chargers',
					),
				),
				$this->stream( 'Would have been stored.' )
			)
		);
		$this->assertSame( $before, $thread->read( 51 ) );
		$this->assertSame( $releases + 1, $this->releases );
	}

	/**
	 * Assistant text that differs only by whitespace still matches. The
	 * stored text stays the canonical one (#373).
	 */
	public function test_whitespace_in_the_clients_answer_still_matches(): void {
		$this->remember_meta();
		$thread = new Thread();
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$this->assertTrue(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => "The hybrid inverter  is\nthree-phase.",
					),
					array(
						'role'    => 'user',
						'content' => 'And a battery?',
					),
				),
				$this->stream( 'This battery pairs with it.' )
			)
		);
		$messages = $thread->read( 51 )['messages'];
		$this->assertSame( 'The hybrid inverter is three-phase.', $messages[1]['content'] );
		$this->assertSame( 'And a battery?', $messages[2]['content'] );
	}

	/**
	 * The response was lost. Sending the stored messages again accepts the
	 * turn and does not store the question twice (#373).
	 */
	public function test_resending_the_last_committed_turn_is_idempotent(): void {
		$this->remember_meta();
		$thread = new Thread();
		$prior  = array(
			array(
				'role'    => 'user',
				'content' => 'Which inverter?',
			),
			array(
				'role'    => 'assistant',
				'content' => 'The hybrid inverter is three-phase.',
			),
			array(
				'role'    => 'user',
				'content' => 'And a battery?',
			),
		);
		$thread->record( 51, array( $prior[0] ), $this->stream( 'The hybrid inverter is three-phase.' ) );
		$thread->record( 51, $prior, $this->stream( 'This battery pairs with it.' ) );
		$retry = $this->stream( 'This battery still pairs with it.' );
		$this->assertTrue( $thread->record( 51, $prior, $retry ) );
		$messages = $thread->read( 51 )['messages'];
		$this->assertSame( $prior, $messages );
		$this->assertSame( $retry, $thread->read( 51 )['stream'] );
		$this->assertSame(
			array(
				'Which inverter?',
				'The hybrid inverter is three-phase.',
				'And a battery?',
				'This battery still pairs with it.',
			),
			array_column( $thread->transcript( 51 ), 'content' )
		);
	}

	/**
	 * The other tab's turns were merged, and this snapshot still carries
	 * its own answer. Only the new question is appended (#373).
	 */
	public function test_a_snapshot_that_already_contains_its_own_answer_appends_the_next_question(): void {
		$this->remember_meta();
		$thread = new Thread();
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
				array(
					'role'    => 'assistant',
					'content' => 'The hybrid inverter is three-phase.',
				),
				array(
					'role'    => 'user',
					'content' => 'EV chargers',
				),
			),
			$this->stream( 'EV chargers in the range are these.' )
		);
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
				array(
					'role'    => 'assistant',
					'content' => 'The hybrid inverter is three-phase.',
				),
				array(
					'role'    => 'user',
					'content' => 'EV chargers',
				),
				array(
					'role'    => 'assistant',
					'content' => 'EV chargers in the range are these.',
				),
				array(
					'role'    => 'user',
					'content' => 'Wallboxen',
				),
			),
			$this->stream( 'Wallboxen in der Auswahl sind diese.' )
		);
		$this->assertTrue(
			$thread->record(
				51,
				array(
					array(
						'role'    => 'user',
						'content' => 'Which inverter?',
					),
					array(
						'role'    => 'assistant',
						'content' => 'The hybrid inverter is three-phase.',
					),
					array(
						'role'    => 'user',
						'content' => 'Wallboxen',
					),
					array(
						'role'    => 'assistant',
						'content' => "Wallboxen  in\nder Auswahl sind diese.",
					),
					array(
						'role'    => 'user',
						'content' => 'And a battery?',
					),
				),
				$this->stream( 'This battery pairs with it.' )
			)
		);
		$this->assertSame(
			array(
				'Which inverter?',
				'The hybrid inverter is three-phase.',
				'EV chargers',
				'EV chargers in the range are these.',
				'Wallboxen',
				'Wallboxen in der Auswahl sind diese.',
				'And a battery?',
				'This battery pairs with it.',
			),
			array_column( $thread->transcript( 51 ), 'content' )
		);
	}

	/**
	 * A refused question left in the browser and sent again is stored once.
	 * Asking it again after its answer is a new turn (#373).
	 */
	public function test_a_duplicated_user_tail_is_stored_once(): void {
		$this->remember_meta();
		$thread = new Thread();
		$thread->record(
			51,
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverter?',
				),
			),
			$this->stream( 'The hybrid inverter is three-phase.' )
		);
		$base = array(
			array(
				'role'    => 'user',
				'content' => 'Which inverter?',
			),
			array(
				'role'    => 'assistant',
				'content' => 'The hybrid inverter is three-phase.',
			),
		);
		$this->assertTrue(
			$thread->record(
				51,
				array_merge(
					$base,
					array(
						array(
							'role'    => 'user',
							'content' => 'And a battery?',
						),
						array(
							'role'    => 'user',
							'content' => 'And a battery?',
						),
					)
				),
				$this->stream( 'This battery pairs with it.' )
			)
		);
		$this->assertSame(
			array(
				'Which inverter?',
				'The hybrid inverter is three-phase.',
				'And a battery?',
				'This battery pairs with it.',
			),
			array_column( $thread->transcript( 51 ), 'content' )
		);

		// The answer is stored. Sending the question twice more does not append it.
		$again = array_merge(
			$base,
			array(
				array(
					'role'    => 'user',
					'content' => 'And a battery?',
				),
				array(
					'role'    => 'user',
					'content' => 'And a battery?',
				),
			)
		);
		$this->assertTrue( $thread->record( 51, $again, $this->stream( 'This battery pairs with it.' ) ) );
		$this->assertSame(
			array(
				'Which inverter?',
				'The hybrid inverter is three-phase.',
				'And a battery?',
				'This battery pairs with it.',
			),
			array_column( $thread->transcript( 51 ), 'content' )
		);

		// The same words after the answer are a new question.
		$this->assertTrue(
			$thread->record(
				51,
				array_merge(
					$base,
					array(
						array(
							'role'    => 'user',
							'content' => 'And a battery?',
						),
						array(
							'role'    => 'assistant',
							'content' => 'This battery pairs with it.',
						),
						array(
							'role'    => 'user',
							'content' => 'And a battery?',
						),
					)
				),
				$this->stream( 'A second battery does too.' )
			)
		);
		$this->assertSame(
			array(
				'Which inverter?',
				'The hybrid inverter is three-phase.',
				'And a battery?',
				'This battery pairs with it.',
				'And a battery?',
				'A second battery does too.',
			),
			array_column( $thread->transcript( 51 ), 'content' )
		);
	}

	/**
	 * Post meta kept in the test, so a second record() sees the first.
	 *
	 * When `$armed` is set, a write of `$fail` does not land: it throws if
	 * `$raise` is set, otherwise it returns false and leaves the old value.
	 *
	 * @param string|null $fail  Meta key that fails once armed.
	 * @param bool        $armed Shared flag. The caller sets it after the seed commit.
	 * @param bool        $raise Throw instead of returning false.
	 */
	private function remember_meta( ?string $fail = null, bool &$armed = false, bool $raise = false ): void {
		$box = new class() {
			/**
			 * Meta written during the test, by post id and key.
			 *
			 * @var array<int, array<string, mixed>>
			 */
			public array $stored = array();
		};
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ) use ( $box ): mixed {
					return $box->stored[ $id ][ $key ] ?? '';
				},
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => static function ( int $id, string $key, mixed $value ) use ( $box, $fail, &$armed, $raise ): bool {
					if ( $armed && $fail === $key ) {
						if ( $raise ) {
							throw new \RuntimeException( 'meta write failed' );
						}
						return false;
					}
					$box->stored[ $id ][ $key ] = $value;
					return true;
				},
			)
		);
	}

	/**
	 * GET_LOCK names this test has prepared.
	 *
	 * @return list<string>
	 */
	private function lock_names(): array {
		$names = array();
		foreach ( $this->prepares as $prepared ) {
			if ( str_contains( $prepared[0], 'SELECT GET_LOCK' ) ) {
				$names[] = (string) ( $prepared[1][0] ?? '' );
			}
		}
		return $names;
	}

	/**
	 * How many times this test has tried to acquire the lock.
	 */
	private function lock_attempts(): int {
		return count( $this->lock_names() );
	}

	/**
	 * One finished turn's stream: a text block, optional cards, done.
	 *
	 * @param string $text     The answer text.
	 * @param int[]  $products Card product ids.
	 */
	private function stream( string $text, array $products = array() ): string {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- a unit test has no wp_json_encode.
		$events = 'event: block' . "\n" . 'data: ' . (string) json_encode(
			array(
				'type' => 'text',
				'text' => $text,
				'refs' => array(),
			)
		) . "\n\n";
		if ( array() !== $products ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- a unit test has no wp_json_encode.
			$events .= 'event: block' . "\n" . 'data: ' . (string) json_encode(
				array(
					'type'        => 'cards',
					'product_ids' => $products,
				)
			) . "\n\n";
		}
		return $events . 'event: done' . "\n" . 'data: {}' . "\n\n";
	}
}
