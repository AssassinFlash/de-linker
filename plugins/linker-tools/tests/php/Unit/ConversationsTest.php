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
			$signed = $this->signed_cookie( 51 );
			WP_Mock::expectAction(
				'linker_tools_set_conversation_cookie',
				$signed,
				1000000,
				'/',
				'',
				false
			);

			// The same flow a turn uses: no cookie -> open() fires the action, the
			// registered listener sends the header, and the NEXT request (the
			// readback below) reuses the conversation from it.
			$id = $conversation->open();
			$conversation->send_cookie( $signed, 1000000, '/', '', false );

			$this->assertSame( 51, $id );
			$this->assertCount( 1, $conversation->sent );
			$this->assertSame( 'linker_conversation', $conversation->sent[0]['name'] );
			$this->assertSame( $signed, $conversation->sent[0]['value'] );
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
			$this->signed_cookie( 51 ),
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
		$_COOKIE = array( 'linker_conversation' => $this->signed_cookie( 51 ) );
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
	 * A signed-in visitor may not read or take over another visitor's
	 * unowned conversation, even by naming its id. Their own conversation
	 * and the unowned conversation their cookie names stay usable.
	 */
	public function test_a_signed_in_visitor_may_not_use_anothers_unowned_conversation(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 7 ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
		$_COOKIE = array( 'linker_conversation' => $this->signed_cookie( 52 ) );
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'return' => 'linker_conversation',
			)
		);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'return' => static function ( string $field, int $id ): string {
					unset( $field );
					if ( 51 === $id ) {
						return '7';
					}
					if ( 52 === $id ) {
						return '0';
					}
					return '8';
				},
			)
		);

		$conversations = new Conversations();

		$this->assertTrue( $conversations->may_use( 51 ) );
		$this->assertTrue( $conversations->may_use( 52 ) );
		$this->assertFalse( $conversations->may_use( 99 ) );
		$this->assertConditionsMet();
	}

		/**
		 * A cookie that is only a conversation id is not a credential. The
		 * signature is what names the conversation; a forged number is ignored
		 * at the gate and does not open that post.
		 */
	public function test_an_unsigned_numeric_cookie_is_refused(): void {
		$this->logged_out();
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
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

		$conversations = new Conversations();

		$this->assertFalse( $conversations->may_use( 51 ) );
		$this->assertSame( 0, $conversations->existing_id() );
		$this->assertConditionsMet();
	}

		/**
		 * A cookie for a foreign or deleted conversation is ignored.
		 */
	public function test_current_id_ignores_a_foreign_conversation(): void {
		$this->logged_out();
		$_COOKIE = array( 'linker_conversation' => $this->signed_cookie( 51 ) );
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
			$this->signed_cookie( 52 ),
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
		$_COOKIE  = array( 'linker_conversation' => $this->signed_cookie( 51 ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
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
		 * A guest's history is the cookie conversation, and nothing else.
		 */
	public function test_a_guest_lists_only_the_cookie_conversation(): void {
		$this->logged_out();
		$_COOKIE = array( 'linker_conversation' => $this->signed_cookie( 51 ) );
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
			'get_post',
			array(
				'args'   => array( 51 ),
				'return' => self::post( 51, 'Which inverter fits?' ),
			)
		);

		$list = $this->conversations()->list_for_visitor();

		$this->assertCount( 1, $list );
		$this->assertSame( 51, $list[0]['id'] );
		$this->assertSame( 'Which inverter fits?', $list[0]['title'] );
		$this->assertConditionsMet();
	}

		/**
		 * A signed-in customer lists the conversations they own. A conversation
		 * they may not use never appears, even if a query returned it.
		 */
	public function test_a_customer_lists_owned_conversations(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 7 ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
		$_COOKIE = array();
		WP_Mock::userFunction(
			'get_posts',
			array(
				'times'  => 1,
				'return' => array( 51, 52 ),
			)
		);
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'return' => static fn( int $id ): string => 53 === $id ? 'post' : 'linker_conversation',
			)
		);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'return' => static fn( string $field, int $id ): string => 52 === $id ? '8' : '7',
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static fn( int $id ): \WP_Post => self::post( $id, 'Conversation ' . $id ),
			)
		);

		$list = ( new Conversations() )->list_for_visitor();

		$this->assertSame( array( 51 ), array_column( $list, 'id' ) );
		$this->assertConditionsMet();
	}

		/**
		 * Selecting a conversation writes the same cookie the next turn reads.
		 * A conversation the visitor may not use is refused and writes nothing.
		 */
	public function test_activate_sets_the_cookie_only_for_an_owned_conversation(): void {
		$this->logged_out();
		$_COOKIE = array( 'linker_conversation' => $this->signed_cookie( 51 ) );
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'return' => static fn( int $id ): string => 51 === $id ? 'linker_conversation' : 'post',
			)
		);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'args'   => array( 'post_author', 51 ),
				'return' => '0',
			)
		);
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
		WP_Mock::expectAction(
			'linker_tools_set_conversation_cookie',
			$this->signed_cookie( 51 ),
			1000000,
			'/',
			'',
			false
		);

			$conversations = $this->conversations();
			$this->assertTrue( $conversations->activate( 51 ) );
			$this->assertFalse( $conversations->activate( 99 ) );
			$this->assertSame( 51, $conversations->existing_id() );
			$this->assertConditionsMet();
	}

			/**
			 * Selecting another owned conversation is visible in this request.
			 * The header alone would leave existing_id() and the list on the
			 * previous cookie until the browser came back.
			 */
	public function test_activate_is_visible_to_the_same_request(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 7 ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
		$_COOKIE = array( 'linker_conversation' => $this->signed_cookie( 51 ) );
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'return' => static fn( int $id ): string => in_array( $id, array( 51, 52 ), true ) ? 'linker_conversation' : 'post',
			)
		);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'return' => static fn( string $field, int $id ): string => in_array( $id, array( 51, 52 ), true ) ? '7' : '0',
			)
		);
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => array( 51 ),
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static fn( int $id ): \WP_Post => self::post( $id, 'Conversation ' . $id ),
			)
		);
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
		WP_Mock::expectAction(
			'linker_tools_set_conversation_cookie',
			$this->signed_cookie( 52 ),
			1000000,
			'/',
			'',
			false
		);

		$conversations = $this->conversations();
		$this->assertSame( 51, $conversations->existing_id() );
		$this->assertTrue( $conversations->activate( 52 ) );
		$this->assertSame( 52, $conversations->existing_id() );
		$this->assertSame( 52, $conversations->current_id() );
		$this->assertContains( 52, array_column( $conversations->list_for_visitor(), 'id' ) );
		$this->assertConditionsMet();
	}

		/**
		 * The first customer message names a new conversation. A conversation
		 * that already has a title keeps it.
		 */
	public function test_the_first_message_names_a_new_conversation(): void {
		$this->logged_out();
		$_COOKIE = array( 'linker_conversation' => $this->signed_cookie( 51 ) );
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
		$titles = array( 'Genie', 'Battery pairing' );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static function ( int $id ) use ( &$titles ): \WP_Post {
					return ConversationsTest::post( $id, (string) array_shift( $titles ) );
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					array(
						'ID'         => 51,
						'post_title' => 'Which battery pairs?',
					),
				),
			)
		);

		$conversations = $this->conversations();
		$conversations->title_from_first_message( 51, 'Which battery pairs?' );
		$conversations->title_from_first_message( 51, 'A later question' );
		$this->assertConditionsMet();
	}

		/**
		 * A conversation post as the list reads it.
		 *
		 * @param int    $id    Post ID.
		 * @param string $title Post title.
		 */
	public static function post( int $id, string $title ): \WP_Post {
		return new \WP_Post(
			(object) array(
				'ID'                => $id,
				'post_title'        => $title,
				'post_type'         => 'linker_conversation',
				'post_status'       => 'private',
				'post_modified_gmt' => '2026-10-12 08:00:00',
			)
		);
	}

		/**
		 * Guest state: is_user_logged_in() false, get_current_user_id() zero.
		 */
	private function logged_out(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
	}

	/**
	 * A cookie this site would have signed for `$id`.
	 *
	 * @param int $id Conversation post ID.
	 */
	private function signed_cookie( int $id ): string {
		return $id . '.' . hash_hmac( 'sha256', 'linker_conversation|' . $id, 'test-salt' );
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
