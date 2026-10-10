<?php
/**
 * Tests for the conversation posts.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Conversations;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Conversations.
 *
 * @covers \Linker\Tools\Genie\Conversations
 */
final class ConversationsTest extends TestCase {

	/**
	 * The post type, the cookie-writing listener and the login hook are
	 * registered on init.
	 */
	public function test_register_registers_the_post_type(): void {
		$captured      = null;
		$conversations = $this->conversations();
		WP_Mock::userFunction(
			'register_post_type',
			array(
				'times'  => 1,
				'return' => static function ( string $type, array $args ) use ( &$captured ): void {
					$captured = array( $type, $args );
				},
			)
		);
		WP_Mock::expectActionAdded( 'linker_tools_set_conversation_cookie', array( $conversations, 'send_cookie' ), 10, 5 );
		WP_Mock::expectActionAdded( 'wp_login', array( $conversations, 'claim' ), 10, 2 );

		$conversations->register();

		$this->assertNotNull( $captured );
		$this->assertSame( 'linker_conversation', $captured[0] );
		$this->assertFalse( $captured[1]['public'] );
		$this->assertConditionsMet();
	}

	/**
	 * The registered listener really sends the Set-Cookie header: a fresh
	 * browser with no cookie reads it back and reuses the conversation on its
	 * next turn instead of opening a new post every time.
	 */
	public function test_send_cookie_sends_the_header_the_readback_reuses(): void {
		$conversation = new class() extends Conversations {
			/**
			 * The headers this instance sent.
			 *
			 * @var list<array{name: string, value: string, options: array<string, mixed>}>
			 */
			public array $sent = array();

			/**
			 * Records instead of writing a header.
			 *
			 * @param string               $name    Cookie name.
			 * @param string               $value   Cookie value.
			 * @param array<string, mixed> $options setcookie() options.
			 */
			protected function send_header( string $name, string $value, array $options ): bool {
				$this->sent[] = array(
					'name'    => $name,
					'value'   => $value,
					'options' => $options,
				);
				return true;
			}

			/**
			 * The fixed expiry second.
			 */
			protected function cookie_expire(): int {
				return 1000000;
			}
		};

		$this->logged_out();
		$_COOKIE = array();
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'return' => static fn( array $post ): int => 51, // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.Found -- shape only.
			)
		);
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
		WP_Mock::expectAction(
			'linker_tools_set_conversation_cookie',
			'51',
			1000000,
			'/',
			'',
			false
		);

		// The same flow a turn uses: no cookie -> open() fires the action, the
		// registered listener sends the header, and the NEXT request (the
		// readback below) reuses the conversation from it.
		$id = $conversation->open();
		$conversation->send_cookie( (string) $id, 1000000, '/', '', false );

		$this->assertSame( 51, $id );
		$this->assertCount( 1, $conversation->sent );
		$this->assertSame( 'linker_conversation', $conversation->sent[0]['name'] );
		$this->assertSame( '51', $conversation->sent[0]['value'] );
		$this->assertSame( 1000000, $conversation->sent[0]['options']['expires'] );
		$this->assertTrue( $conversation->sent[0]['options']['httponly'] );
		$this->assertSame( 'Lax', $conversation->sent[0]['options']['samesite'] );

		// Readback: with the cookie the header just sent, the conversation is
		// reused instead of opened again.
		$_COOKIE = array( 'linker_conversation' => $conversation->sent[0]['value'] );
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( 51 ),
				'return' => 'linker_conversation',
			)
		);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'args'   => array( 'post_author', 51 ),
				'return' => '0',
			)
		);
		$this->assertSame( 51, $conversation->current_id() );
		$this->assertConditionsMet();
	}

	/**
	 * A guest with no cookie gets a new conversation and the cookie.
	 */
	public function test_open_inserts_a_post_and_sets_the_cookie(): void {
		$this->logged_out();
		$_COOKIE  = array();
		$inserted = array();
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'return' => static function ( array $post ) use ( &$inserted ): int { // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.Found -- captures the inserted row.
					$inserted = $post;
					return 51;
				},
			)
		);
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
		WP_Mock::expectAction(
			'linker_tools_set_conversation_cookie',
			'51',
			1000000,
			'/',
			'',
			false
		);

		$this->assertSame( 51, $this->conversations()->open() );
		$this->assertSame( 0, (int) $inserted['post_author'] );
		$this->assertSame( Conversations::POST_TYPE, $inserted['post_type'] );
		$this->assertSame( 'private', $inserted['post_status'] );
		$this->assertConditionsMet();
	}

	/**
	 * The request reuses the conversation its cookie names while the post is
	 * still a guest conversation.
	 */
	public function test_current_id_reuses_the_cookie_conversation(): void {
		$this->logged_out();
		$_COOKIE = array( 'linker_conversation' => '51' );
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( 51 ),
				'return' => 'linker_conversation',
			)
		);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'args'   => array( 'post_author', 51 ),
				'return' => '0',
			)
		);

		$this->assertSame( 51, ( new Conversations() )->current_id() );
		$this->assertTrue( ( new Conversations() )->may_use( 51 ) );
		$this->assertConditionsMet();
	}

	/**
	 * A cookie for a foreign or deleted conversation is ignored.
	 */
	public function test_current_id_ignores_a_foreign_conversation(): void {
		$this->logged_out();
		$_COOKIE = array( 'linker_conversation' => '51' );
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( 51 ),
				'return' => 'post',
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'return' => static fn( array $post ): int => 52, // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.Found -- shape only.
			)
		);
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
		WP_Mock::expectAction(
			'linker_tools_set_conversation_cookie',
			'52',
			1000000,
			'/',
			'',
			false
		);

		$this->assertSame( 52, $this->conversations()->current_id() );
		$this->assertFalse( ( new Conversations() )->may_use( 51 ) );
		$this->assertConditionsMet();
	}

	/**
	 * On login, a guest conversation becomes the user's.
	 */
	public function test_claim_assigns_the_user(): void {
		$user     = new \WP_User();
		$user->ID = 7;
		$_COOKIE  = array( 'linker_conversation' => '51' );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( 51 ),
				'return' => 'linker_conversation',
			)
		);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'args'   => array( 'post_author', 51 ),
				'return' => '0',
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					array(
						'ID'          => 51,
						'post_author' => 7,
					),
				),
			)
		);

		( new Conversations() )->claim( 'shopper', $user );

		$this->assertConditionsMet();
	}

	/**
	 * Guest state: is_user_logged_in() false, get_current_user_id() zero.
	 */
	private function logged_out(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
	}

	/**
	 * A Conversations whose guest cookie always expires at one fixed second.
	 */
	private function conversations(): Conversations {
		return new class() extends Conversations {
			/**
			 * The fixed expiry second.
			 */
			protected function cookie_expire(): int {
				return 1000000;
			}
		};
	}
}
