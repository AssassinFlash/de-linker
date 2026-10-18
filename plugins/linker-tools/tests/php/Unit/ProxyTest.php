<?php
/**
 * Tests for the REST proxy to the Genie service.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\ContactRequest;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Proxy;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_REST_Request;
use WP_REST_Response;
use WP_Error;

/**
 * Tests for Proxy.
 *
 * @covers \Linker\Tools\Genie\Proxy
 */
final class ProxyTest extends TestCase {

	/**
	 * Without the option there is no service to talk to.
	 */
	public function test_turn_fails_closed_without_a_service_url(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => '' ) );

		$result = $this->proxy()->turn( new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_unconfigured', $result->get_error_code() );
		$this->assertSame( 503, $result->get_error_data( 'linker_genie_unconfigured' )['status'] );
		$this->assertConditionsMet();
	}

	/**
	 * The turn carries the conversation, the normalized locale and the page
	 * context; the service's SSE comes back with the conversation ID.
	 */
	public function test_turn_posts_the_context_and_returns_the_stream(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		// The URL and body the fetch double received.
		$caught  = array( '', array() );
		$fetch   = static function ( string $url, array $body ) use ( &$caught ) {
			$caught = array( $url, $body );
			return "event: meta\ndata: {}\n\n";
		};
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
		$request->set_param(
			'messages',
			array(
				array(
					'role'    => 'user',
					'content' => 'hi',
				),
			)
		);
		$request->set_param( 'locale', 'de-DE' );
		$request->set_param(
			'page',
			array(
				'type'       => 'product',
				'product_id' => 3555,
			)
		);

		$result = $this->proxy( $fetch )->turn( $request );

		$this->assertNotInstanceOf( WP_Error::class, $result );
		$raw  = $result->get_data();
		$data = is_array( $raw ) ? $raw : array();
		$this->assertSame( 'http://127.0.0.1:8890/assistant/turn', $caught[0] );
		$this->assertSame( '51', $caught[1]['conversation_id'] );
		$this->assertSame( 'de', $caught[1]['locale'] );
		$this->assertSame(
			array(
				'type'       => 'product',
				'product_id' => 3555,
			),
			$caught[1]['page_context']
		);
		$this->assertFalse( $caught[1]['user']['logged_in'] );
		$this->assertSame( "event: meta\ndata: {}\n\n", $data['stream'] );
		$this->assertSame( 51, $data['conversation_id'] );
		$this->assertConditionsMet();
	}

	/**
	 * Whether the account is approved comes from the site's one price rule
	 * (linker-commerce answers `linker_commerce_visitor_sees_prices`, #242),
	 * never from being signed in: a signed-in pending or restricted account
	 * is not approved, and without linker-commerce nobody is.
	 *
	 * @testWith [true, true, true]
	 *           [true, false, false]
	 *           [false, false, false]
	 *           [true, null, false]
	 *
	 * @param bool      $logged_in Whether the visitor is signed in.
	 * @param bool|null $rule      The rule's answer; null when no plugin answers.
	 * @param bool      $partner   The `partner` the service receives.
	 */
	public function test_turn_sends_whether_the_account_sees_prices( bool $logged_in, ?bool $rule, bool $partner ): void {
		$this->wp_functions( $logged_in );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		if ( null !== $rule ) {
			$this->price_rule_says( $rule );
		}
		$caught  = array();
		$fetch   = static function ( string $url, array $body ) use ( &$caught ) {
			unset( $url );
			$caught = $body;
			return "event: meta\ndata: {}\n\n";
		};
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
		$request->set_param( 'messages', array() );

		$this->proxy( $fetch )->turn( $request );

		$this->assertSame( $logged_in, $caught['user']['logged_in'] );
		$this->assertSame( $partner, $caught['user']['partner'] );
	}

	/**
	 * The page the browser names is checked key by key (#234); a solution
	 * draft's products are read from the visitor's own draft, as English
	 * posts, whatever the browser sent.
	 */
	public function test_turn_sends_the_checked_page_and_the_visitors_draft(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		WP_Mock::passthruFunction( 'esc_url_raw' );
		WP_Mock::passthruFunction( 'sanitize_text_field' );
		WP_Mock::userFunction( 'wc_load_cart', array( 'times' => 1 ) );
		$cart = new class() {
			/**
			 * Lines of the draft: a German product and an English one.
			 *
			 * @return list<array{product_id: int}>
			 */
			public function get_cart(): array {
				return array( array( 'product_id' => 6741 ), array( 'product_id' => 2003 ) );
			}
		};
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'cart' => $cart ) ) );
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static fn( int $id ): int => 6741 === $id ? 4107 : $id,
			)
		);
		$caught  = array();
		$fetch   = static function ( string $url, array $body ) use ( &$caught ) {
			unset( $url );
			$caught = $body;
			return "event: done\ndata: {}\n\n";
		};
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
		$request->set_param(
			'messages',
			array(
				array(
					'role'    => 'user',
					'content' => 'Check my draft',
				),
			)
		);
		$request->set_param(
			'page',
			array(
				'type'      => 'draft',
				'url'       => 'https://de-linker.test/de/warenkorb/',
				'title'     => 'Lösungsentwurf',
				'draft_ids' => array( 1, 2, 3 ),
				'extra'     => 'dropped',
			)
		);

		$this->proxy( $fetch )->turn( $request );

		$this->assertSame(
			array(
				'type'      => 'draft',
				'url'       => 'https://de-linker.test/de/warenkorb/',
				'title'     => 'Lösungsentwurf',
				'draft_ids' => array( 4107, 2003 ),
			),
			$caught['page_context']
		);
		$this->assertConditionsMet();
	}

	/**
	 * An upstream failure maps to a 502, not to the raw service error.
	 */
	public function test_turn_maps_an_upstream_error(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		$fetch = static fn() => new WP_Error( 'http_request_failed', 'timed out' );

		$result = $this->proxy( $fetch )->turn( new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_upstream', $result->get_error_code() );
		$this->assertConditionsMet();
	}

	/**
	 * `en` when nothing says German.
	 */
	public function test_locale_defaults_to_english(): void {
		$proxy      = new Proxy(
			new class() extends Conversations {
				/**
				 * Always the same conversation.
				 */
				public function current_id(): int {
					return 1;
				}
			}
		);
			$method = new \ReflectionMethod( $proxy, 'locale' );

		$this->assertSame( 'en', $method->invoke( $proxy, null ) );
		$this->assertSame( 'de', $method->invoke( $proxy, 'de_DE_formal' ) );
	}

	/**
	 * A vote is forwarded to the service's log of the same turn.
	 */
	public function test_vote_forwards_to_the_service(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		$caught  = array( '', array() );
		$fetch   = static function ( string $url, array $body ) use ( &$caught ): int {
			$caught = array( $url, $body );
			return 200;
		};
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn/41/vote' );
		$request->set_param( 'id', 41 );
		$request->set_param( 'vote', -1 );

		$result = $this->proxy( $fetch )->vote( $request );

		$this->assertNotInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'http://127.0.0.1:8890/turn/41/vote', $caught[0] );
		$this->assertSame( array( 'vote' => -1 ), $caught[1] );
		$this->assertSame( array( 'ok' => true ), $result->get_data() );
		$this->assertConditionsMet();
	}

	/**
	 * An unknown turn maps to 404, an unreachable service to 502.
	 */
	public function test_vote_maps_the_upstream_statuses(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn/41/vote' );
		$request->set_param( 'id', 41 );
		$request->set_param( 'vote', 1 );

		$missing = $this->proxy( static fn(): int => 404 )->vote( $request );
		$this->assertInstanceOf( WP_Error::class, $missing );
		$this->assertSame( 'linker_genie_turn', $missing->get_error_code() );
		$this->assertSame( 404, $missing->get_error_data( 'linker_genie_turn' )['status'] );

		$dead = $this->proxy( static fn() => new WP_Error( 'http_request_failed', 'timed out' ) )->vote( $request );
		$this->assertInstanceOf( WP_Error::class, $dead );
		$this->assertSame( 'linker_genie_upstream', $dead->get_error_code() );
		$this->assertConditionsMet();
	}

	/**
	 * Without the option there is no service to talk to.
	 */
	public function test_vote_fails_closed_without_a_service_url(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => '' ) );

		$result = $this->proxy()->vote( new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn/41/vote' ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_unconfigured', $result->get_error_code() );
		$this->assertConditionsMet();
	}

	/**
	 * What linker-commerce's price rule answers the shell
	 * (`linker_commerce_visitor_sees_prices`, applied with false).
	 *
	 * @param bool $sees The rule's answer.
	 * @throws \LogicException When WP_Mock answers with another responder.
	 */
	private function price_rule_says( bool $sees ): void {
		$responder = WP_Mock::onFilter( 'linker_commerce_visitor_sees_prices' )->with( false );
		if ( ! $responder instanceof WP_Mock\Filter_Responder ) {
			throw new \LogicException( 'WP_Mock::onFilter() answers with a Filter_Responder.' );
		}
		$responder->reply( $sees );
	}

	/**
	 * WordPress functions every test path touches.
	 *
	 * @param bool $logged_in Whether a visitor is signed in.
	 */
	private function wp_functions( bool $logged_in = false ): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $logged_in ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		// No plugin answers the price rule: the filter's own default comes back.
		$this->price_rule_says( false );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction(
			'is_wp_error',
			array(
				'return' => static fn( $thing ): bool => $thing instanceof \WP_Error,
			)
		);
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
				WP_Mock::userFunction(
					'register_rest_route',
					array(
						'return' => static function (): void {},
					)
				);
	}

	/**
	 * A proxy whose conversations always answer 51.
	 *
	 * @param callable|null        $fetch  HTTP client.
	 * @param RecordingThread|null $thread Conversation store; a recording one by default.
	 */
	private function proxy( ?callable $fetch = null, ?RecordingThread $thread = null ): Proxy {
		$conversations = new class() extends Conversations {
			/**
			 * Always the same conversation.
			 */
			public function current_id(): int {
				return 51;
			}

			/**
			 * The same id, and 0 without one — what the thread route reads.
			 */
			public function existing_id(): int {
				return 51;
			}

			/**
			 * The one conversation this double knows.
			 *
			 * @return list<array{id: int, title: string, updated: string}>
			 */
			public function list_for_visitor(): array {
				return array(
					array(
						'id'      => 51,
						'title'   => 'Which inverter fits?',
						'updated' => '2026-10-12 08:00:00',
					),
				);
			}

			/**
			 * Selects 51 and refuses anything else.
			 *
			 * @param int $id Conversation post ID.
			 */
			public function activate( int $id ): bool {
				return 51 === $id;
			}

			/**
			 * Opens 52.
			 */
			public function open(): int {
				return 52;
			}

			/**
			 * The real method reads the post. This double has no post.
			 *
			 * @param int    $id    Conversation post ID.
			 * @param string $title First message.
			 */
			public function title_from_first_message( int $id, string $title ): void {
				unset( $id, $title );
			}
		};
		return new Proxy( $conversations, $fetch, $thread ?? new RecordingThread() );
	}

	/**
	 * A signed-in visitor naming another visitor's unowned conversation is
	 * refused on the thread read, the select, and the turn. The turn must
	 * not open a conversation in its place.
	 */
	public function test_a_signed_in_visitor_is_refused_anothers_unowned_conversation(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 7 ) );
		$this->price_rule_says( false );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction(
			'is_wp_error',
			array(
				'return' => static fn( $thing ): bool => $thing instanceof \WP_Error,
			)
		);
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		$_COOKIE = array();
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( 99 ),
				'return' => 'linker_conversation',
			)
		);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'args'   => array( 'post_author', 99 ),
				'return' => '0',
			)
		);
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'return' => static function ( array $post ): int {
					if ( 7 !== (int) $post['post_author'] ) {
						return 0;
					}
					return 53;
				},
			)
		);
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
			WP_Mock::expectAction(
				'linker_tools_set_conversation_cookie',
				'53.' . hash_hmac( 'sha256', 'linker_conversation|53', 'test-salt' ),
				1000000,
				'/',
				'',
				false
			);
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => new \WP_Post(
					(object) array(
						'ID'         => 53,
						'post_title' => 'Genie',
					)
				),
			)
		);
		WP_Mock::userFunction( 'wp_update_post', array( 'return' => 53 ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );

		$posted        = null;
		$conversations = new class() extends Conversations {
			/**
			 * The fixed expiry second.
			 */
			protected function cookie_expire(): int {
				return 1000000;
			}
		};
		$proxy         = new Proxy(
			$conversations,
			static function ( string $url, array $body ) use ( &$posted ): string {
				$posted = array( $url, $body );
				return "event: done\ndata: {}\n\n";
			},
			new RecordingThread()
		);

		$thread = $proxy->conversation();
		$this->assertSame( 0, $thread->get_data()['conversation_id'] );
		$this->assertSame( array(), $thread->get_data()['messages'] );

		$select = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/conversations' );
		$select->set_param( 'id', 99 );
		$refused = $proxy->select_conversation( $select );
		$this->assertInstanceOf( WP_Error::class, $refused );
		$this->assertSame( 404, $refused->get_error_data()['status'] );

		$turn = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
		$turn->set_param(
			'messages',
			array(
				array(
					'role'    => 'user',
					'content' => 'Read their thread',
				),
			)
		);
		$blocked = $proxy->turn( $turn );
		$this->assertInstanceOf( WP_REST_Response::class, $blocked );
		$this->assertSame( 53, $blocked->get_data()['conversation_id'] );
		$this->assertNotSame( 99, $blocked->get_data()['conversation_id'] );
		$this->assertIsArray( $posted );
		$this->assertSame( '53', $posted[1]['conversation_id'] );
		$this->assertConditionsMet();
	}

	/**
	 * An answered turn is kept: the thread the browser sent, and the answer.
	 */
	public function test_turn_records_the_thread_and_the_answer(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		$thread  = new RecordingThread();
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
		$request->set_param(
			'messages',
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverters fit?',
				),
			)
		);

		$this->proxy( static fn(): string => "event: meta\ndata: {}\n\n", $thread )
		->turn( $request );

		$this->assertNotNull( $thread->recorded );
		$this->assertSame( 51, $thread->recorded['conversation'] );
		$this->assertSame(
			array(
				array(
					'role'    => 'user',
					'content' => 'Which inverters fit?',
				),
			),
			$thread->recorded['messages']
		);
		$this->assertSame( "event: meta\ndata: {}\n\n", $thread->recorded['stream'] );
		$this->assertConditionsMet();
	}

	/**
	 * An upstream failure is not a turn: nothing is written.
	 */
	public function test_a_failed_turn_records_nothing(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://127.0.0.1:8890' ) );
		$thread  = new RecordingThread();
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
		$request->set_param( 'messages', array() );

		$this->proxy( static fn() => new WP_Error( 'boom', 'nope' ), $thread )->turn( $request );

		$this->assertNull( $thread->recorded );
		$this->assertConditionsMet();
	}

	/**
	 * The conversation route hands the stored thread back.
	 */
	public function test_conversation_returns_the_stored_thread(): void {
		$this->wp_functions();
		$thread         = new RecordingThread();
		$thread->stored = array(
			'messages' => array(
				array(
					'role'    => 'user',
					'content' => 'Hello',
				),
			),
			'stream'   => 'event: done\ndata: {}\n\n',
		);
		// One contact request was sent after the first answer (#243).
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 51, ContactRequest::NOTE, false ),
				'return' => array(
					array(
						'messages' => 1,
						'email'    => 'maria@example.test',
						'receipt'  => true,
					),
				),
			)
		);
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn( $value ) => str_contains( (string) $value, '@' ) ) );
		$response = $this->proxy( null, $thread )->conversation();
		$data     = $response->get_data();
		$this->assertSame( 51, $data['conversation_id'] );
		$this->assertSame( $thread->stored['messages'], $data['messages'] );
		$this->assertSame( $thread->stored['stream'], $data['stream'] );
		$this->assertSame(
			array(
				array(
					'after'   => 1,
					'email'   => 'maria@example.test',
					'receipt' => true,
				),
			),
			$data['contacts']
		);
		// The answer depends on the visitor's cookie: it is never cacheable.
		$this->assertStringContainsString(
			'no-store',
			(string) $response->get_headers()['Cache-Control']
		);
			$this->assertConditionsMet();
	}

	/**
	 * The history route lists the visitor's conversations and names the
	 * current one. It does not open a conversation.
	 */
	public function test_conversations_lists_without_opening_one(): void {
		$this->wp_functions();

		$data = $this->proxy()->conversations()->get_data();

		$this->assertSame( 51, $data['current_id'] );
		$this->assertSame( 'Which inverter fits?', $data['conversations'][0]['title'] );
		$this->assertConditionsMet();
	}

	/**
	 * Selecting a conversation the visitor owns returns that id. An id
	 * they may not use is a 404, not a new conversation.
	 */
	public function test_selecting_a_conversation_refuses_one_the_visitor_may_not_use(): void {
		$this->wp_functions();
		$proxy = $this->proxy();

			$owned = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/conversations' );
			$owned->set_param( 'id', 51 );
			$selected = $proxy->select_conversation( $owned );
			$this->assertInstanceOf( WP_REST_Response::class, $selected );
			$this->assertSame( 51, $selected->get_data()['conversation_id'] );

		$foreign = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/conversations' );
		$foreign->set_param( 'id', 99 );
		$error = $proxy->select_conversation( $foreign );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 404, $error->get_error_data()['status'] );
		$this->assertConditionsMet();
	}

	/**
	 * A selection without an id opens a new conversation.
	 */
	public function test_selecting_without_an_id_opens_a_conversation(): void {
		$this->wp_functions();
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/conversations' );

			$opened = $this->proxy()->select_conversation( $request );
			$this->assertInstanceOf( WP_REST_Response::class, $opened );
			$data = $opened->get_data();

		$this->assertSame( 52, $data['conversation_id'] );
		$this->assertConditionsMet();
	}

	/**
	 * After select, this request's thread read is the new conversation.
	 * The cookie header alone would still name the previous one.
	 */
	public function test_select_is_the_conversation_the_same_request_reads(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 7 ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction(
			'is_wp_error',
			array(
				'return' => static fn( $thing ): bool => $thing instanceof \WP_Error,
			)
		);
		WP_Mock::userFunction(
			'absint',
			array(
				'return' => static fn( $value ): int => max( 0, (int) $value ),
			)
		);
			WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
			$_COOKIE = array(
				'linker_conversation' => '51.' . hash_hmac( 'sha256', 'linker_conversation|51', 'test-salt' ),
			);
			WP_Mock::userFunction(
				'get_post_type',
				array(
					'return' => static fn( int $id ): string => in_array( $id, array( 51, 52 ), true ) ? 'linker_conversation' : 'post',
				)
			);
		WP_Mock::userFunction(
			'get_post_field',
			array(
				'return' => static fn( string $field, int $id ): string => in_array( $id, array( 51, 52 ), true ) ? '7' : '8',
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
				'return' => static fn( int $id ): \WP_Post => new \WP_Post(
					(object) array(
						'ID'                => $id,
						'post_title'        => 'Conversation ' . $id,
						'post_modified_gmt' => '2026-10-12 08:00:00',
					)
				),
			)
		);
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
			WP_Mock::expectAction(
				'linker_tools_set_conversation_cookie',
				'52.' . hash_hmac( 'sha256', 'linker_conversation|52', 'test-salt' ),
				1000000,
				'/',
				'',
				false
			);

		$conversations = new class() extends Conversations {
			/**
			 * The fixed expiry second.
			 */
			protected function cookie_expire(): int {
				return 1000000;
			}
		};
			$proxy     = new Proxy( $conversations, null, new RecordingThread() );
			$request   = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/conversations' );
			$request->set_param( 'id', 52 );

			$selected = $proxy->select_conversation( $request );

			$this->assertInstanceOf( WP_REST_Response::class, $selected );
			$this->assertSame( 52, $selected->get_data()['conversation_id'] );
			$this->assertContains( 52, array_column( $selected->get_data()['conversations'], 'id' ) );
			$this->assertSame( 52, $conversations->existing_id() );
			WP_Mock::userFunction( 'get_post_meta', array( 'return' => array() ) );
			$this->assertSame( 52, $proxy->conversation()->get_data()['conversation_id'] );
			$this->assertConditionsMet();
	}
}
