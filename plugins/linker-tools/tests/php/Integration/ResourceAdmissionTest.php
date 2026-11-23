<?php
/**
 * Actual WP journal/native callback fixtures; no upstream service or mail.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Isolated local-only private-mode fixtures restore every value.

namespace Linker\Tools\Tests\Integration;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Tools\Genie\Attachments;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\PublicationGuard;
use Linker\Tools\Genie\Thread;
use Linker\Tools\Protection\Replies;
use Linker\Tools\Protection\ResourcePolicy;
use Linker\Tools\Protection\Resources;
use PHPUnit\Framework\TestCase;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Resource admission in a real WordPress database.
 *
 * @coversNothing
 */
final class ResourceAdmissionTest extends TestCase {
	/**
	 * Saved local journal.
	 *
	 * @var mixed
	 */
	private mixed $old;
	/**
	 * Saved private environment, no credentials.
	 *
	 * @var array<string,string|false>
	 */
	private array $environment = array();
	/**
	 * Native cookies.
	 *
	 * @var array<string,mixed>
	 */
	private array $cookies = array();

	/**
	 * Local synthetic conversations removed after each fixture.
	 *
	 * @var list<int>
	 */
	private array $created_conversations = array();

	/** Synthetic private live-version HTTP fixture, removed after each case.
	 *
	 * @var \Closure
	 */
	private \Closure $live_version;

	/** Mutable synthetic running version for restart fixtures.
	 *
	 * @var string
	 */
	private string $running_version = '';


	/** Isolate the journal, the session trust and official dummy configuration. */
	protected function setUp(): void {
		$this->running_version = hash( 'sha256', 'synthetic-running-engine-a' );
		$this->live_version    = function ( mixed $old, array $args, string $url ): mixed {
			if ( ! str_ends_with( $url, '/resource/version' ) ) {
				return $old; }
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode( array( 'version' => $this->running_version ) ),
			);
		};
		add_filter( 'pre_http_request', $this->live_version, -1, 3 );
		$this->old = get_option( Ledger::OPTION );
		delete_option( Ledger::OPTION );
		$this->cookies               = $_COOKIE;
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		wp_set_current_user( 0 );
		foreach ( array(
			'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
			'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
			'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
			'LINKER_TURNSTILE_HOSTNAME'     => '127.0.0.1',
		) as $key => $value ) {
			$this->environment[ $key ] = getenv( $key );
			putenv( $key . '=' . $value );
		}
	}

	/** Restore the local fixture without touching real service settings. */
	protected function tearDown(): void {
		remove_filter( 'pre_http_request', $this->live_version, -1 );
		delete_option( Ledger::OPTION );
		if ( false !== $this->old ) {
			update_option( Ledger::OPTION, $this->old, false );
		}
		foreach ( $this->environment as $key => $value ) {
			putenv( false === $value ? $key : $key . '=' . $value );
		}
		foreach ( $this->created_conversations as $conversation ) {
			wp_delete_post( $conversation, true );
		}
		$_COOKIE = $this->cookies;
		foreach ( get_posts(
			array(
				'post_type'      => Replies::TYPE,
				'post_status'    => 'any',
				'fields'         => 'ids',
				'posts_per_page' => -1,
			)
		) as $id ) {
			wp_delete_post( (int) $id, true );
		}
	}

	/**
	 * Native request, stable logical UUID, semantic JSON.
	 *
	 * @param string              $route Actual route.
	 * @param array<string,mixed> $input Synthetic fields.
	 * @param string              $action Server scope.
	 */
	private function request( string $route, array $input, string $action ): WP_REST_Request {
		$request = new WP_REST_Request( 'POST', $route );
		$request->set_header( 'Content-Type', 'application/json' );
		$request->set_header( 'X-Linker-Operation', wp_generate_uuid4() );
		$request->set_body( (string) wp_json_encode( $input ) );
		if ( 1 === preg_match( '#/conversations/(\d+)/email$#', $route, $capture ) ) {
			$request->set_url_params( array( 'id' => (int) $capture[1] ) );
		}
		return $request;
	}

	/** The same native receipt follows a guest from preparation through checked output or a recoverable refusal.
	 *
	 * @dataProvider async_outcomes
	 * @param string $outcome Terminal scenario.
	 */
	public function test_async_turn_uses_the_owned_receipt_until_completion( string $outcome ): void {
		global $wp_filter;
		$hooks = array();
		foreach ( array( Conversations::COOKIE_ACTION, Conversations::BROWSER_ACTION ) as $hook ) {
			$hooks[ $hook ] = isset( $wp_filter[ $hook ] ) ? clone $wp_filter[ $hook ] : null;
			remove_all_actions( $hook );
		}
		$old_url = get_option( Proxy::OPTION );
		update_option( Proxy::OPTION, 'http://127.0.0.1:9' );
		$job      = wp_generate_uuid4();
		$question = 'Where is the AC rating for C:\\manuals?';
		$request  = $this->request(
			'/linker-ai/v1/genie/turn/start',
			array(
				'locale'   => 'en',
				'messages' => array(
					array(
						'role'    => 'user',
						'content' => $question,
					),
				),
			),
			'genie'
		);
		$poll     = new WP_REST_Request( 'GET', '/linker-ai/v1/genie/turn/' . $job );
		$poll->set_url_params( array( 'job_id' => $job ) );
		$scope  = '';
		$starts = 0;
		$reads  = 0;
		$stream = "event: reading\ndata: {\"id\":\"att1\",\"text\":\"private extraction\"}\n\nevent: block\ndata: {\"type\":\"text\",\"text\":\"Look at the AC output.\",\"refs\":[]}\n\nevent: done\ndata: {}\n\n";
		$fetch  = function ( string $url, array $body, array $headers ) use ( $job, &$scope, &$starts, &$reads, $stream, $outcome ) {
			if ( str_ends_with( $url, '/start' ) ) {
				++$starts;
				$scope = $headers['X-Linker-Resource-Subject'];
				$this->assertNotEmpty( $body['messages'] );
				return (string) wp_json_encode(
					array(
						'status' => 'running',
						'job_id' => $job,
						'stage'  => 'understanding',
					)
				);
			}
			$this->assertStringEndsWith( $job, $url );
			$this->assertSame( $scope, $headers['X-Linker-Resource-Subject'] );
			++$reads;
			return (string) wp_json_encode(
				1 === $reads ? array(
					'status' => 'running',
					'stage'  => 'searching_documents',
				)
					: ( 'failed' === $outcome ? array(
						'status'      => 'failed',
						'http_status' => 503,
						'code'        => 'genie_job_failed',
					) : array(
						'status' => 'completed',
						'stream' => $stream,
					) )
			);
		};
		try {

			$source  = new PublicationGuard(
				null,
				static function ( array $deps ) use ( $outcome ) {
					return 'revoked' === $outcome ? array( 'valid' => false ) : \Linker\Commerce\Products\Publication::validate( $deps );
				}
			);
			$proxy   = new Proxy( new Conversations(), $fetch, token: 'synthetic', publication: $source );
			$handler = array( 'callback' => array( $proxy, 'start' ) );
			$gate    = new Resources();
			$start   = $gate->dispatch( null, $request, '', $handler );
			$this->assertInstanceOf( WP_REST_Response::class, $start );
			$this->assertSame( 202, $start->get_status(), (string) wp_json_encode( $start->get_data() ) );
			$id                            = $start->get_data()['conversation_id'];
			$this->created_conversations[] = $id;
			$this->assertSame( 'auto-draft', get_post_status( $id ) );
			$this->assertSame( $job, $start->get_data()['job_id'] );
			$pending = $proxy->conversation()->get_data()['pending_job'];
			$this->assertSame( $question, $pending['user_message'] );
			$this->assertSame( $job, $pending['job_id'] );
			$this->assertArrayNotHasKey( 'messages', $pending );
			$this->assertArrayNotHasKey( 'stream', $pending );
			$operation = $request->get_header( 'X-Linker-Operation' );
			$this->assertIsString( $operation );
			$receipt     = ( new Replies() )->operation( $operation );
			$fingerprint = (string) get_post_meta( $receipt, '_linker_input', true );
			$this->assertFalse( Resources::completed_genie_operation( $operation, $fingerprint ) );
			$this->assertSame( 202, $gate->dispatch( null, $request, '', $handler )->get_status() );
			$this->assertSame( 1, $starts );

			$owner   = $_COOKIE;
			$_COOKIE = array( Identity::COOKIE => str_repeat( 'b', 32 ) );
			$foreign = $proxy->poll( $poll );
			$this->assertInstanceOf( WP_Error::class, $foreign );
			$this->assertSame( 404, $foreign->get_error_data()['status'] );
			$this->assertSame( 0, $reads );
			$_COOKIE = $owner;
			$running = $proxy->poll( $poll );
			$this->assertInstanceOf( WP_REST_Response::class, $running );
			$this->assertSame( 'searching_documents', $running->get_data()['stage'] );
			$this->assertSame( 'searching_documents', $proxy->conversation()->get_data()['pending_job']['stage'] );
			if ( 'expired' === $outcome ) {
				$input               = \Linker\Tools\Genie\PendingTurns::current( $id );
				$input['started_at'] = time() - Proxy::TURN_BUDGET - 1;
				update_post_meta( $id, \Linker\Tools\Genie\PendingTurns::PENDING, wp_slash( $input ) );
			}
			// A second native MySQL connection holds the terminal operation while this tab polls.
			$peer = new \wpdb( constant( 'DB_USER' ), constant( 'DB_PASSWORD' ), constant( 'DB_NAME' ), constant( 'DB_HOST' ) );
			$key  = \Linker\Commerce\Inquiry\Assessment\Lock::name( 'genie-operation-' . $operation );
			$this->assertSame( '1', $peer->get_var( $peer->prepare( 'SELECT GET_LOCK(%s, 0)', $key ) ) );
			try {
				$joining = $proxy->poll( $poll );
				$this->assertInstanceOf( WP_REST_Response::class, $joining );
				$this->assertSame( 'running', $joining->get_data()['status'] );
				$this->assertSame( 1, $reads );
			} finally {
				$peer->get_var( $peer->prepare( 'SELECT RELEASE_LOCK(%s)', $key ) );
				$peer->close();
			}

			$final = $proxy->poll( $poll );
			if ( 'completed' !== $outcome ) {
				$this->assertInstanceOf( WP_Error::class, $final );
				$this->assertSame( 'revoked' === $outcome ? 409 : 503, $final->get_error_data()['status'] );
				$this->assertTrue( $final->get_error_data()['unrecorded'] );
				$this->assertNull( get_post( $id ) );
				$this->assertFalse( Resources::completed_genie_operation( $operation, $fingerprint ) );
				$this->assertSame( 0, ( new Replies() )->operation( $operation ) );
				return;
			}
			$this->assertInstanceOf( WP_REST_Response::class, $final );
			$this->assertSame( 'completed', $final->get_data()['status'] );
			$this->assertStringNotContainsString( 'private extraction', $final->get_data()['stream'] );
			$this->assertSame( 'private', get_post_status( $id ) );
			$this->assertTrue( Resources::completed_genie_operation( $operation, $fingerprint ) );
			$again = $proxy->poll( $poll );
			$this->assertInstanceOf( WP_REST_Response::class, $again );
			$this->assertSame( $final->get_data(), $again->get_data() );
			$this->assertSame( 2, $reads );
			$thread = $proxy->conversation()->get_data();
			$this->assertArrayNotHasKey( 'pending_job', $thread );
			$this->assertSame( $operation, $thread['operation_id'] );
			$this->assertCount( 1, $thread['messages'] );
			$this->assertSame( $question, $thread['messages'][0]['content'] );
		} finally {
			foreach ( $hooks as $hook => $callbacks ) {
				if ( null === $callbacks ) {
					unset( $wp_filter[ $hook ] );
				} else {
					$wp_filter[ $hook ] = $callbacks; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Restore this fixture's cookie hooks.
				}
			}
			if ( false === $old_url ) {
				delete_option( Proxy::OPTION );
			} else {
				update_option( Proxy::OPTION, $old_url );
			}
		}
	}

	/** Terminal states of a real WordPress receipt.
	 *
	 * @return array<string,array{string}>
	 */
	public static function async_outcomes(): array {
		return array(
			'checked'               => array( 'completed' ),
			'publication withdrawn' => array( 'revoked' ),
			'worker failed'         => array( 'failed' ),
			'deadline'              => array( 'expired' ),
		);
	}

	/** Reject an oversized attachment list before file parsing and private transport. */
	public function test_too_many_files_never_dispatch(): void {
		$request = $this->request( '/linker-ai/v1/genie/turn', array( 'attachments' => array_fill( 0, Attachments::MAX_FILES + 1, array() ) ), 'genie' );
		$result  = ( new Resources() )->dispatch(
			null,
			$request,
			'',
			array(
				'callback' => static function () {
					self::fail( 'Too many files reached transport.' );
				},
			)
		);
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_resource_files', $result->get_error_code() );
	}

	/** Completed retries restore the original private response without work or fresh proof. */
	public function test_completed_retry_and_callback_scope(): void {
		$request   = $this->request(
			'/linker-ai/v1/genie/turn',
			array(
				'messages' => array(
					array(
						'role'    => 'user',
						'content' => 'Synthetic inverter question',
					),
				),
			),
			'genie'
		);
		$resources = new Resources();
		$calls     = 0;
		$handler   = array(
			'callback' => function () use ( &$calls, $resources ): WP_REST_Response {
				++$calls;
				$this->assertTrue( Resources::verified() );
				$context = $resources->context( null );
				$this->assertSame( 'genie', $context['action'] );
				$this->assertMatchesRegularExpression( '/^[a-f0-9]{64}$/', $context['binding'] );
				$response = new WP_REST_Response(
					array(
						'conversation_id' => 123,
						'stream'          => 'synthetic',
					)
				);
				$publication = new PublicationGuard();
				$dependencies = $publication->dependencies();
				$this->assertIsArray( $dependencies );
				$publication->remember( $response, $dependencies );
				return $response;
			},
		);
		$first     = $resources->dispatch( null, $request, '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $first );
		$this->assertFalse( Resources::verified() );
		$this->assertNull( $resources->context( null ) );
		$second = $resources->dispatch( null, $request, '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $second, is_wp_error( $second ) ? (string) wp_json_encode( array( $second->get_error_code(), $second->get_error_data() ) ) : '' );
		$this->assertSame( $first->get_data(), $second->get_data() );
		$this->assertSame( 1, $calls );
	}

	/**
	 * The permit binds attachment/context bytes; native GET respects result lifetime.
	 *
	 * @dataProvider completion_lifetimes
	 * @param string $lifetime How the completed native result becomes unavailable.
	 */
	public function test_genie_completion_is_bound_to_semantic_input_and_native_result_lifetime( string $lifetime ): void {
		global $wp_filter;
		$held = array();
		foreach ( array( Conversations::COOKIE_ACTION, Conversations::BROWSER_ACTION ) as $hook ) {
			$held[ $hook ] = isset( $wp_filter[ $hook ] ) ? clone $wp_filter[ $hook ] : null;
			remove_all_actions( $hook );
		}
		try {
			$conversation                  = ( new Conversations() )->open();
			$this->created_conversations[] = $conversation;
		} finally {
			foreach ( $held as $hook => $callbacks ) {
				if ( null === $callbacks ) {
					unset( $wp_filter[ $hook ] );
				} else {
					$wp_filter[ $hook ] = $callbacks; } // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Restore this fixture's held cookie hooks.
			}
		}
		$stream      = "event: block\ndata: {\"type\":\"text\",\"text\":\"Native answer.\",\"refs\":[]}\n\nevent: done\ndata: {\"ok\":true}\n\n";
		$input       = array(
			'locale'   => 'en',
			'messages' => array(
				array(
					'role'    => 'user',
					'content' => 'Check test.pdf',
				),
			),
			'page'     => array(
				'type'       => 'product',
				'product_id' => 2067,
			),
		);
		$request     = $this->request( '/linker-ai/v1/genie/turn', $input, 'genie' );
		$id          = (string) $request->get_header( 'X-Linker-Operation' );
		$fingerprint = '';
		$calls       = 0;
		$resources   = new Resources();
		$handler     = array(
			'callback' => function () use ( &$calls, &$fingerprint, $id, $conversation, $stream, $input ): WP_REST_Response {
				++$calls;
				$this->assertSame( $id, Resources::genie_operation() );
				$fingerprint = Resources::genie_fingerprint();
				$this->assertMatchesRegularExpression( '/^[a-f0-9]{64}$/', $fingerprint );
				$this->assertFalse( Resources::completed_genie_operation( $id, $fingerprint ) );
				$old_url = get_option( 'linker_genie_url' );
				update_option( 'linker_genie_url', 'http://127.0.0.1:9' );
				try {
					$proxy = new Proxy( new Conversations(), static fn(): string => $stream, token: 'synthetic-local-only' );
					$turn = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
					foreach ( $input as $key => $value ) {
						$turn->set_param( $key, $value ); }
					$response = $proxy->turn( $turn );
					$this->assertInstanceOf( WP_REST_Response::class, $response );
					$this->assertSame( $conversation, $response->get_data()['conversation_id'] );
					return $response;
				} finally {
					if ( false === $old_url ) {
						delete_option( 'linker_genie_url' );
					} else {
						update_option( 'linker_genie_url', $old_url ); }
				}
			},
		);
		$this->assertInstanceOf( WP_REST_Response::class, $resources->dispatch( null, $request, '', $handler ) );
		$this->assertSame( '', Resources::genie_operation() );
		$this->assertTrue( Resources::completed_genie_operation( $id, $fingerprint ) );
		$data = ( new Proxy( new Conversations() ) )->conversation()->get_data();
		$this->assertSame( $id, $data['operation_id'] ?? '' );
		$this->assertArrayNotHasKey( 'operation_fingerprint', $data );
		$this->assertSame( $stream, $data['stream'] );

		// The same real operation survives JSON key reordering without another turn.
		$reordered = $this->request(
			'/linker-ai/v1/genie/turn',
			array(
				'page'     => $input['page'],
				'messages' => $input['messages'],
				'locale'   => $input['locale'],
			),
			'genie'
		);
		$reordered->set_header( 'X-Linker-Operation', $id );
		$replayed = $resources->dispatch( null, $reordered, '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $replayed );
		$this->assertSame( $conversation, $replayed->get_data()['conversation_id'] );
		$this->assertSame( 1, $calls );

		$jar = $_COOKIE;
		unset( $_COOKIE[ Conversations::COOKIE ], $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		$this->assertArrayNotHasKey( 'operation_id', ( new Proxy( new Conversations() ) )->conversation()->get_data(), 'UUID is not authorization for a different browser.' );
		$_COOKIE = $jar;
		foreach ( array(
			'page'        => array(
				'type'       => 'product',
				'product_id' => 2068,
			),
			'attachments' => array(
				array(
					'name' => 'test.pdf',
					'type' => 'application/pdf',
					'data' => 'ZGlmZmVyZW50',
				),
			),
		) as $key => $value ) {
			$changed = $this->request( '/linker-ai/v1/genie/turn', array_replace( $input, array( $key => $value ) ), 'genie' );
			$changed->set_header( 'X-Linker-Operation', $id );
			$reply = $resources->dispatch( null, $changed, '', $handler );
			$this->assertInstanceOf( WP_Error::class, $reply );
			$this->assertSame( 'linker_admission_payload_changed', $reply->get_error_code() );
		}
		$this->assertSame( 1, $calls );
		$this->assertTrue( Resources::completed_genie_operation( $id, $fingerprint ) );
		$outcome = ( new Replies() )->operation( $id );
		$this->assertGreaterThan( 0, $outcome );
		if ( 'delete-reply' === $lifetime ) {
			wp_delete_post( $outcome, true );
		} elseif ( 'expire-reply' === $lifetime ) {
			update_post_meta( $outcome, '_linker_expires', time() - 1 );
		} elseif ( 'erase-reply' === $lifetime ) {
			$email = 'genie-privacy@example.test';
			update_post_meta( $outcome, '_linker_recipient', Identity::recipient( $email ) );
			$this->assertTrue( ( new \Linker\Tools\Protection\ReplyPrivacy() )->erase( $email )['items_removed'] );
			$this->assertInstanceOf( WP_Error::class, $resources->dispatch( null, $request, '', $handler ) );
			$this->assertSame( 1, $calls );
		} else {
			wp_delete_post( $conversation, true );
			$this->assertSame( '', get_post_meta( $conversation, Thread::COMPLETION, true ) );
		}
		$this->assertArrayNotHasKey( 'operation_id', ( new Proxy( new Conversations() ) )->conversation()->get_data() );
	}

	/**
	 * Native erasure, expiry and clear boundaries.
	 *
	 * @return list<array{string}>
	 */
	public static function completion_lifetimes(): array {
		return array( array( 'delete-reply' ), array( 'expire-reply' ), array( 'erase-reply' ), array( 'clear-conversation' ) );
	}

	/** An exception leaves quota spent and removes trusted native context. */
	public function test_crash_has_no_replay_or_leaked_scope(): void {
		$request   = $this->request( '/linker-ai/v1/genie/turn', array(), 'genie' );
		$resources = new Resources();
		$handler   = array(
			'callback' => static function (): never {
							throw new \RuntimeException( 'synthetic crash' );
			},
		);
		try {
			$resources->dispatch( null, $request, '', $handler );
			$this->fail( 'Expected fixture crash.' );
		} catch ( \RuntimeException $error ) {
			$this->assertSame( 'synthetic crash', $error->getMessage() );
		}
		$this->assertFalse( Resources::verified() );
		$this->assertNull( $resources->context( null ) );
		$retry = $resources->dispatch( null, $request, '', $handler );
		$this->assertInstanceOf( WP_Error::class, $retry );
		$this->assertSame( 409, $retry->get_error_data()['status'] );
	}

	/** A committed action without a writable reply stays uncertain and never runs twice. */
	public function test_failed_reply_save_does_not_confirm_or_redispatch(): void {
		$request   = $this->request( '/linker-ai/v1/genie/turn', array(), 'genie' );
		$reject    = static fn ( bool $rejected, array $post ): bool => $rejected || ( Replies::TYPE === $post['post_type'] && ! empty( $post['ID'] ) && '' !== $post['post_content'] );
		$calls     = 0;
		$handler   = array(
			'callback' => static function () use ( &$calls ): WP_REST_Response {
						++$calls;
						return new WP_REST_Response( array( 'saved' => true ) );
			},
		);
		$resources = new Resources();
		add_filter( 'wp_insert_post_empty_content', $reject, 10, 2 );
		try {
			$first = $resources->dispatch( null, $request, '', $handler );
			$this->assertInstanceOf( WP_Error::class, $first );
			$this->assertSame( 409, $first->get_error_data()['status'] );
		} finally {
			remove_filter( 'wp_insert_post_empty_content', $reject );
		}
		$retry = $resources->dispatch( null, $request, '', $handler );
		$this->assertInstanceOf( WP_Error::class, $retry );
		$this->assertSame( 409, $retry->get_error_data()['status'] );
		$this->assertSame( 1, $calls );
	}

	/** A completed result from the previous release is still replayed by its owner. */
	public function test_previous_release_result_is_recovered_without_running_its_callback(): void {
		$request = $this->request( '/linker-ai/v1/genie/turn', array(), 'genie' );
		$id      = $request->get_header( 'X-Linker-Operation' );
		$this->assertIsString( $id );
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$payload = array(
			'_route'  => $request->get_route(),
			'_method' => 'POST',
		);
		$input   = \Linker\Commerce\Protection\Fingerprint::make( $identity, 'genie', $payload );
		$this->assertIsString( $input );
		$ledger   = new Ledger();
		$replies  = new Replies();
		$reply_id = $replies->open( $identity->binding() );
		$this->assertGreaterThan( 0, $reply_id );
		$this->assertIsArray( $ledger->reserve( $id, $input, array(), 90, array(), 'genie', $identity->binding(), array( Allowance::owner_for( $identity->browser ) ) ) );
		$this->assertIsArray( $ledger->dispatch( $id, $input ) );
		$this->assertSame( $reply_id, $replies->finish( $reply_id, new WP_REST_Response( array( 'previous' => true ) ) ) );
		$this->assertIsArray( $ledger->complete( $id, $input, $reply_id ) );
		$handler  = array(
			'callback' => static function (): never {
						self::fail( 'The old request must not run twice.' );
			},
		);
		$resource = new Resources();
		$response = $resource->dispatch( null, $request, '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( array( 'previous' => true ), $response->get_data() );
		$this->assertTrue( Resources::completed_genie_operation( $id, $input ) );
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'e', 32 );
		$foreign                     = $resource->dispatch( null, $request, '', $handler );
		$this->assertInstanceOf( WP_Error::class, $foreign );
		$this->assertSame( 409, $foreign->get_error_data()['status'] );
	}

	/** A blank guest editor holds no records; the first question belongs to a new conversation. */
	public function test_guest_opens_blank_with_history_and_first_question_uses_its_own_conversation(): void {
		global $wp_filter;
		$held = array();
		foreach ( array( Conversations::COOKIE_ACTION, Conversations::BROWSER_ACTION ) as $hook ) {
			$held[ $hook ] = isset( $wp_filter[ $hook ] ) ? clone $wp_filter[ $hook ] : null;
			remove_all_actions( $hook );
		}
		try {
			$store     = new Conversations();
			$proxy     = new Proxy( $store );
			$handler   = array( 'callback' => array( $proxy, 'select_conversation' ) );
			$resources = new Resources();
			$new       = $this->request( '/linker-ai/v1/genie/conversations', array(), 'conversation_create' );
			$fresh     = $resources->dispatch( null, $new, '', $handler );
			$this->assertInstanceOf( WP_REST_Response::class, $fresh );
			$this->assertSame( 0, $fresh->get_data()['conversation_id'] );
			$key = $new->get_header( 'X-Linker-Operation' );
			$this->assertIsString( $key );
			$this->assertSame( 0, ( new Replies() )->operation( $key ) );
			$old                           = $store->current_id();
			$this->created_conversations[] = $old;
			$old_group                     = sanitize_text_field( wp_unslash( $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? '' ) );
			$this->assertMatchesRegularExpression( '/^[0-9a-f]{32}$/', $old_group );
			unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
			$signed_cookie_only = $_COOKIE;
			$entry              = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/entry-context' );
			$entry->set_param( 'tab', wp_generate_uuid4() );
			$entry->set_header( 'origin', home_url() );
			$this->assertSame( 200, rest_do_request( $entry )->get_status() );
			$previous_tab = $_COOKIE;
			$from_old     = $this->request( '/linker-ai/v1/genie/conversations', array(), 'conversation_create' );
			$blank        = $resources->dispatch( null, $from_old, '', $handler );
			$this->assertInstanceOf( WP_REST_Response::class, $blank );
			$this->assertSame( 0, $blank->get_data()['conversation_id'] );
			$this->assertContains( $old, array_column( $blank->get_data()['conversations'], 'id' ) );
			// The response was lost before either of its Set-Cookie headers arrived.
			$_COOKIE = $previous_tab;
			$again   = $resources->dispatch( null, $from_old, '', $handler );
			$this->assertInstanceOf( WP_REST_Response::class, $again );
			$this->assertContains( $old, array_column( ( new Conversations() )->list_for_visitor(), 'id' ) );
			$this->assertSame( 0, ( new Conversations() )->existing_id() );
			$first_question                = ( new Conversations() )->current_id();
			$this->created_conversations[] = $first_question;
			$this->assertNotSame( $old, $first_question );
			$this->assertSame( $first_question, ( new Conversations() )->existing_id() );
			$retry = $resources->dispatch( null, $from_old, '', $handler );
			$this->assertInstanceOf( WP_REST_Response::class, $retry );
			$this->assertSame( $first_question, ( new Conversations() )->existing_id() );
			$_COOKIE = $previous_tab;
			$this->assertSame( $old, ( new Conversations() )->existing_id() );
			unset( $_COOKIE[ Conversations::COOKIE ] );
			$_COOKIE[ Conversations::BROWSER_COOKIE ] = $old_group;
			$this->assertTrue( ( new Conversations() )->may_use( $old ) );
			$_COOKIE                          = $signed_cookie_only;
			$_COOKIE[ Conversations::COOKIE ] = $old . '.' . str_repeat( '0', 64 );
			$this->assertSame( 200, rest_do_request( $entry )->get_status() );
			$this->assertFalse( ( new Conversations() )->may_use( $old ) );

			$owner = wp_create_user( 'entry-owner-' . wp_generate_uuid4(), wp_generate_password() );
			$this->assertIsInt( $owner );
			try {
				wp_update_post(
					array(
						'ID'          => $old,
						'post_author' => $owner,
					)
				);
				$_COOKIE = $signed_cookie_only;
				$marks   = get_post_meta( $old, Conversations::BROWSER_META, false );
				$this->assertSame( 200, rest_do_request( $entry )->get_status() );
				$this->assertFalse( ( new Conversations() )->may_use( $old ) );
				$this->assertSame( $marks, get_post_meta( $old, Conversations::BROWSER_META, false ) );
			} finally {
				require_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $owner );
			}
		} finally {
			foreach ( $held as $hook => $callbacks ) {
				if ( null === $callbacks ) {
					unset( $wp_filter[ $hook ] );
				} else {
					$wp_filter[ $hook ] = $callbacks; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Restore this fixture's held cookie hooks.
				}
			}
		}
	}

	/** Guest actions continue independently of traffic recorded by the previous site policy. */
	public function test_guest_solution_and_conversation_writes_are_independent_of_the_shared_site_journal(): void {
		$ledger = new Ledger();
		$id     = wp_generate_uuid4();
		$fp     = hash( 'sha256', $id );
		$old    = new Allowance( 'tool_write_site_day', 'site', 2000, DAY_IN_SECONDS, 2000 );
		$this->assertIsArray( $ledger->reserve( $id, $fp, array( $old ), 90 ) );
		$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
		$this->assertIsArray( $ledger->complete( $id, $fp ) );
		$before = get_option( Ledger::OPTION );
		foreach ( array( 'solution', 'turn' ) as $route ) {
			$calls     = 0;
			$request   = $this->request( '/linker-ai/v1/genie/' . $route, array(), $route );
			$handler   = array(
				'callback' => function () use ( &$calls ): WP_REST_Response {
					++$calls;
					$response = new WP_REST_Response( array( 'saved' => true ) );
					$guard    = new PublicationGuard();
					$dependencies = $guard->dependencies();
					$this->assertIsArray( $dependencies );
					$guard->remember( $response, $dependencies );
					return $response;
				},
			);
			$resources = new Resources();
			foreach ( array( 'send', 'retry' ) as $attempt ) {
				$result = $resources->dispatch( null, $request, '', $handler );
				$this->assertInstanceOf( WP_REST_Response::class, $result, $route . ' ' . $attempt );
				$this->assertSame( 200, $result->get_status() );
			}
			$this->assertSame( 1, $calls );
		}
		$this->assertSame( $before, get_option( Ledger::OPTION ) );
	}

	/** A filled historical site allowance cannot reject a new guest or account project. */
	public function test_guest_and_account_projects_ignore_historical_site_counts(): void {
		$user = wp_create_user( 'planner-owner-' . wp_generate_uuid4(), wp_generate_password() );
		$this->assertIsInt( $user );
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			define( 'LINKER_GENIE_SERVICE_TOKEN', 'synthetic-owned-project' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Used only by the injected native transport.
		}
		$endpoint = static fn (): string => 'https://planner.example.test';
		add_filter( 'pre_option_linker_planner_url', $endpoint );
		try {
			wp_set_current_user( $user );
			$ledger    = new Ledger();
			$allowance = new Allowance( 'planner_projects_site', 'site', 500, DAY_IN_SECONDS, 500 );
			$id        = wp_generate_uuid4();
			$fp        = hash( 'sha256', $id );
			$this->assertIsArray( $ledger->reserve( $id, $fp, array( $allowance ), 90 ) );
			$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
			$this->assertIsArray( $ledger->complete( $id, $fp ) );

			$command = array(
				'key'    => wp_generate_uuid4(),
				'title'  => 'Owned project',
				'inputs' => array(),
			);
			$body    = (string) wp_json_encode( $command );
			foreach ( array(
				0     => new \Linker\Tools\Planner\Principal( 'guest', 'owned-test-session' ),
				$user => new \Linker\Tools\Planner\Principal( 'user', \Linker\Tools\Planner\NativeIdentity::user_subject( $user ) ),
			) as $user_id => $principal ) {
				wp_set_current_user( $user_id );
				$transport = new \Linker\Tools\Planner\Transport(
					function ( string $url, array $args ) use ( $body, $principal ): array {
						$this->assertSame( 'https://planner.example.test/projects/create', $url );
						$this->assertSame( $principal->subject, $args['headers']['X-Linker-Planner-Principal-Subject'] );
						$this->assertSame( $body, $args['body'] );
						return array(
							'response' => array( 'code' => 200 ),
							'headers'  => array( 'content-type' => 'application/json' ),
							'body'     => '{"revision":1}',
						);
					}
				);
				$result    = ( new \Linker\Tools\Planner\Admission() )->send( $principal, 'projects/create', $command, $body, $transport );
				$this->assertIsArray( $result );
				$this->assertSame( '{"revision":1}', $result['body'] );
			}
		} finally {
			remove_filter( 'pre_option_linker_planner_url', $endpoint );
			wp_set_current_user( 0 );
			require_once ABSPATH . 'wp-admin/includes/user.php';
			wp_delete_user( $user );
		}
	}

	/** The same signed-in save returns its first result without consuming another usage allowance. */
	public function test_account_save_replays_the_same_result_without_a_customer_allowance(): void {
		$user = wp_create_user( 'solution-owner-' . wp_generate_uuid4(), wp_generate_password() );
		$this->assertIsInt( $user );
		try {
			wp_set_current_user( $user );
			$request   = $this->request( '/linker-ai/v1/genie/solution', array(), 'solution_save' );
			$calls     = 0;
			$handler   = array(
				'callback' => function () use ( &$calls ): WP_REST_Response {
								++$calls;
								$response = new WP_REST_Response( array( 'saved' => true ), 201 );
								$guard = new PublicationGuard();
								$dependencies = $guard->dependencies();
								$this->assertIsArray( $dependencies );
								$guard->remember( $response, $dependencies );
								return $response;
				},
			);
			$resources = new Resources();
			foreach ( array( 'save', 'retry' ) as $attempt ) {
				$result = $resources->dispatch( null, $request, '', $handler );
				$this->assertInstanceOf( WP_REST_Response::class, $result, $attempt );
				$this->assertSame( 201, $result->get_status() );
			}
			$this->assertSame( 1, $calls );
			$this->assertFalse( get_option( Ledger::OPTION ) );
		} finally {
			wp_set_current_user( 0 );
			require_once ABSPATH . 'wp-admin/includes/user.php';
			wp_delete_user( $user );
		}
	}

	/** Native form handlers own these submissions and their server-side human check. */
	public function test_forms_do_not_enter_the_tool_work_journal(): void {
		foreach ( array( 'contact', 'inquiry' ) as $entry ) {
			$request = $this->request( '/linker-ai/v1/genie/' . $entry, array(), 'genie_' . $entry );
			$this->assertNull( ( new Resources() )->dispatch( null, $request, '', array() ) );
		}
	}

	/** Native privacy erasure during work prevents late completion resurrection. */
	public function test_reply_erasure_during_work_cannot_recreate_response(): void {
		$replies = new Replies();
		$privacy = new \Linker\Tools\Protection\ReplyPrivacy();
		$one     = $replies->open( hash( 'sha256', 'one' ), 'one@example.test' );
		$other   = $replies->open( hash( 'sha256', 'other' ), 'other@example.test' );
		$this->assertGreaterThan( 0, $one );
		$this->assertTrue( $privacy->erase( 'one@example.test' )['items_removed'] );
		$this->assertSame( 0, $replies->finish( $one, new WP_REST_Response( array( 'late' => 'must not be retained' ) ) ) );
		$this->assertFalse( get_post_status( $one ) );
		$this->assertSame( $other, $replies->finish( $other, new WP_REST_Response( array( 'retained' => true ) ) ) );
		$this->assertInstanceOf( WP_Error::class, $replies->read( $other, hash( 'sha256', 'foreign' ) ) );
		$this->assertInstanceOf( WP_REST_Response::class, $replies->read( $other, hash( 'sha256', 'other' ) ) );
		$this->assertCount( 1, $privacy->export( 'other@example.test' )['data'] );
	}


	/** An overridden JSON id cannot authorize a private transcript of the URL's owner. */
	public function test_conversation_mail_ownership_is_bound_to_the_native_url_id(): void {
		$user = wp_create_user( 'resource-owner-' . wp_generate_uuid4(), wp_generate_password() );
		$this->assertIsInt( $user );
		$own                         = wp_insert_post(
			array(
				'post_type'   => Conversations::POST_TYPE,
				'post_status' => 'private',
				'post_author' => $user,
			)
		);
		$foreign                     = wp_insert_post(
			array(
				'post_type'   => Conversations::POST_TYPE,
				'post_status' => 'private',
				'post_author' => 0,
			)
		);
		$this->created_conversations = array( $own, $foreign );
		try {
			wp_set_current_user( $user );
			$request = $this->request( '/linker-ai/v1/genie/conversations/' . $foreign . '/email', array( 'id' => $own ), 'conversation_mail' );
			$result  = ( new Proxy( new Conversations() ) )->email_conversation( $request );
			$this->assertInstanceOf( WP_Error::class, $result );
			$this->assertSame( 404, $result->get_error_data()['status'] );
		} finally {
			wp_set_current_user( 0 );
			require_once ABSPATH . 'wp-admin/includes/user.php';
			wp_delete_user( $user );
		}
	}

	/** Actual PHP transport never treats an off/malformed private guard as permission. */
	public function test_private_provider_filter_requires_positive_native_debit(): void {
		$reply   = array( 'remaining' => 0 );
		$status  = 200;
		$calls   = array();
		$fixture = static function ( mixed $old, array $args, string $url ) use ( &$reply, &$status, &$calls ): mixed {
			if ( ! str_ends_with( $url, '/budget/take' ) ) {
				return $old;
			}
			$calls[] = $args;
			return array(
				'response' => array( 'code' => $status ),
				'body'     => wp_json_encode( $reply ),
			);
		};
		add_filter( 'pre_http_request', $fixture, 0, 3 );
		try {
			$budget = new \Linker\Tools\Protection\ProviderBudget();
			$this->assertTrue( $budget->take( false, 'deepseek' ) );
			$reply = array( 'remaining' => null );
			$off   = $budget->take( false, 'deepseek' );
			$this->assertInstanceOf( WP_Error::class, $off );
			$this->assertSame( 503, $off->get_error_data()['status'] );
			$status  = 429;
			$limited = $budget->take( false, 'jev' );
			$this->assertInstanceOf( WP_Error::class, $limited );
			$this->assertSame( 429, $limited->get_error_data()['status'] );
			$this->assertCount( 3, $calls );
			$ids = array_column( array_map( static fn( array $args ): array => json_decode( $args['body'], true ), $calls ), 'attempt' );
			$this->assertCount( 3, array_unique( $ids ) );
			$this->assertSame( (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ), $calls[0]['headers']['X-Linker-Service-Token'] );
			$this->assertInstanceOf( WP_Error::class, $budget->take( false, 'unsupported' ) );
			$this->assertCount( 3, $calls );
		} finally {
			remove_filter( 'pre_http_request', $fixture, 0 );
		}
	}


	/**
	 * Verified account A owns its reply even when the requested reply address is B.
	 */
	public function test_native_privacy_finds_author_or_recipient_and_erasure_prevents_late_finish(): void {
		$email = wp_generate_uuid4() . '@example.test';
		$user  = wp_insert_user(
			array(
				'user_login' => 'g521-' . wp_generate_uuid4(),
				'user_pass'  => wp_generate_password( 32 ),
				'user_email' => $email,
				'role'       => 'customer',
			)
		);
		$this->assertIsInt( $user );
		$replies = new Replies();
		$privacy = new \Linker\Tools\Protection\ReplyPrivacy();
		try {
			wp_set_current_user( $user );
			$own = $replies->open( hash( 'sha256', 'author-a' ), 'different-b@example.test' );
			wp_set_current_user( 0 );
			$recipient = $replies->open( hash( 'sha256', 'guest-for-a' ), $email );
			$unrelated = $replies->open( hash( 'sha256', 'unrelated' ), 'different-b@example.test' );
			$export    = $privacy->export( $email );
			$this->assertSame( array( 'tool-reply-' . $own, 'tool-reply-' . $recipient ), array_column( $export['data'], 'item_id' ) );
			$this->assertTrue( $privacy->erase( $email )['items_removed'] );
			$this->assertSame( 0, $replies->finish( $own, new WP_REST_Response( array( 'late' => true ) ) ) );
			$this->assertFalse( get_post_status( $recipient ) );
			$this->assertSame( $unrelated, $replies->finish( $unrelated, new WP_REST_Response( array( 'keep' => true ) ) ) );
			$this->assertCount( 1, $privacy->export( 'different-b@example.test' )['data'] );
		} finally {
			wp_set_current_user( 0 );
			include_once ABSPATH . 'wp-admin/includes/user.php';
			wp_delete_user( $user );
		}
	}

	/**
	 * Actual PHP service transport binds work to the browser/account, never a conversation.
	 */
	public function test_genie_private_turn_transport_shares_subject_across_conversations(): void {
		$headers = array();
		$fixture = static function ( mixed $old, array $args, string $url ) use ( &$headers ): mixed {
			if ( ! str_ends_with( $url, '/assistant/turn' ) ) {
				return $old;
			}
			$headers[] = $args['headers'];
			return array(
				'response' => array( 'code' => 429 ),
				'body'     => '{"code":"genie_resource_busy"}',
			);
		};
		add_filter( 'pre_http_request', $fixture, 0, 3 );
		try {
			$proxy  = new \Linker\Tools\Genie\Proxy( new \Linker\Tools\Genie\Conversations() );
			$post   = new \ReflectionMethod( $proxy, 'post' );
			$first  = $post->invoke( $proxy, 'http://127.0.0.1:9/assistant/turn', array( 'conversation_id' => 'one' ) );
			$second = $post->invoke( $proxy, 'http://127.0.0.1:9/assistant/turn', array( 'conversation_id' => 'two' ) );
			$this->assertInstanceOf( WP_Error::class, $first );
			$this->assertSame( 'linker_genie_quota', $first->get_error_code() );
			$this->assertInstanceOf( WP_Error::class, $second );
			$this->assertSame( $headers[0]['X-Linker-Resource-Subject'], $headers[1]['X-Linker-Resource-Subject'] );
			$identity = Identity::current();
			$this->assertInstanceOf( Identity::class, $identity );
			$this->assertSame( $identity->browser, $headers[0]['X-Linker-Resource-Subject'] );
			$this->assertSame( (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ), $headers[0]['X-Linker-Service-Token'] );
		} finally {
			remove_filter( 'pre_http_request', $fixture, 0 );
		}
	}



	/** Native Genie actions and their retries use Genie proof while still checking Woo. */
	public function test_native_genie_list_writes_recheck_the_current_woo_product(): void {
		wc_load_cart();
		$before_cart  = WC()->cart->get_cart_contents();
		$before_saved = WC()->session->get( \Linker\Commerce\Account\SavedSolutions::SESSION_KEY );
		$pending      = get_option( 'linker_publication_pending' );
		$actions      = array();
		$record       = static function ( int $id ) use ( &$actions ): void {
			$action = \ActionScheduler::store()->fetch_action( $id );
			if ( in_array( $action->get_hook(), array( 'linker_publication_reconcile', 'linker_i18n_translate', 'woocommerce_run_product_attribute_lookup_update_callback' ), true ) ) {
				$actions[] = $id;
			}
		};
		add_action( 'action_scheduler_stored_action', $record );
		$product = new \WC_Product_Simple();
		$product->set_name( 'Current Genie receipt fixture' );
		$product->set_status( 'publish' );
		$id = $product->save();
		try {
			$dependencies = ( new \Linker\Tools\Genie\PublicationGuard() )->dependencies();
			$this->assertIsArray( $dependencies );
			$block  = array(
				'type' => 'parts',
				'add'  => array(
					'items' => array(
						array(
							'product_id' => $id,
							'quantity'   => 1,
						),
					),
				),
			);
			$stream = ( new \Linker\Tools\Genie\DraftProof() )->stream( "event: block\ndata: " . wp_json_encode( $block ) . "\n\nevent: done\ndata: {}\n\n", $dependencies );
			$this->assertIsString( $stream );
			if ( 1 !== preg_match( '/^data: (.+)$/m', $stream, $matches ) ) {
				$this->fail( 'The live Genie fixture did not produce its signed artifact.' );
			}
			$artifact = json_decode( $matches[1], true );
			$requests = array();
			foreach ( array(
				'draft'    => 200,
				'solution' => 202,
			) as $path => $status ) {
				$request = $this->request( '/linker-ai/v1/genie/' . $path, array( 'proof' => $artifact['add']['proof'] ), 'draft' === $path ? 'draft_write' : 'solution_save' );
				$request->set_header( 'Nonce', wp_create_nonce( 'wc_store_api' ) );
				$first = rest_do_request( $request );
				$this->assertSame( $status, $first->get_status(), (string) wp_json_encode( $first->get_data() ) );
				$again = rest_do_request( $request );
				$this->assertSame( $status, $again->get_status(), (string) wp_json_encode( $again->get_data() ) );
				$requests[] = $request;
			}
			$product->set_status( 'draft' );
			$product->save();
			foreach ( $requests as $request ) {
				$this->assertSame( 409, rest_do_request( $request )->get_status(), 'A Genie consumer marker cannot bypass a current Woo withdrawal.' );
			}
		} finally {
			WC()->cart->set_cart_contents( $before_cart );
			WC()->session->set( \Linker\Commerce\Account\SavedSolutions::SESSION_KEY, $before_saved );
			wp_delete_post( $id, true );
			remove_action( 'action_scheduler_stored_action', $record );
			foreach ( $actions as $action ) {
				\ActionScheduler::store()->delete_action( $action );
			}
			if ( false === $pending ) {
				delete_option( 'linker_publication_pending' );
			} else {
				update_option( 'linker_publication_pending', $pending, false );
			}
		}
	}
}
