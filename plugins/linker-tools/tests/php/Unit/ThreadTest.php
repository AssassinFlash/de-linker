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
	 * Storage escaping is exercised against real WordPress in the route fixture.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_slash', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction( 'has_action', array( 'return' => false ) );
		$owner = $this;
		// phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the database double stands in for the named lock.
		$GLOBALS['wpdb'] = new class( $owner ) {
			/**
			 * The test, which holds the lock answer.
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
			 * The query unchanged, so a test can see GET_LOCK in it.
			 *
			 * @param string $query SQL text.
			 * @param mixed  ...$args Bound values, unused.
			 */
			public function prepare( string $query, mixed ...$args ): string {
				unset( $args );
				return $query;
			}

			/**
			 * GET_LOCK answers the test's lock answer; RELEASE_LOCK answers that it ran.
			 *
			 * @param string $query SQL text.
			 */
			public function get_var( string $query ): string {
				if ( str_contains( $query, 'GET_LOCK' ) ) {
					return $this->owner->lock_answer;
				}
				return '1';
			}
		};
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
		$before = $thread->read( 51 );
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
	}

	/**
	 * Post meta kept in the test, so a second record() sees the first.
	 */
	private function remember_meta(): void {
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
				'return' => static function ( int $id, string $key, mixed $value ) use ( $box ): bool {
					$box->stored[ $id ][ $key ] = $value;
					return true;
				},
			)
		);
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
