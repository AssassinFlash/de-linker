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
}
