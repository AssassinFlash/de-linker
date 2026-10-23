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
use Linker\Commerce\Protection\Proof;
use Linker\Tools\Genie\Attachments;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Proxy;
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


	/** Isolate the journal and official dummy configuration. */
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
	 * Mint the trusted synthetic verification parent; no Cloudflare request.
	 *
	 * @param string $action Exact native scope.
	 * @param bool   $with_parent Persist successful receipt.
	 */
	private function proof( string $action, bool $with_parent = true ): string {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$id = wp_generate_uuid4();
		if ( $with_parent ) {
			$ledger = new Ledger();
			$fp     = hash( 'sha256', $id );
			$this->assertIsArray( $ledger->reserve( $id, $fp, array( new Allowance( 'fixture_verify', 'site', 1000, DAY_IN_SECONDS ) ), 90, array(), 'verification_' . $action, $identity->binding() ) );
			$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
			$this->assertIsArray( $ledger->complete( $id, $fp, 1 ) );
		}
		return ( new Proof() )->issue( 'verified', $action, $identity, $id );
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
		$request->set_header( 'X-Linker-Proof', $this->proof( $action ) );
		$request->set_body( (string) wp_json_encode( $input ) );
		return $request;
	}

	/** Missing, expired and signed-but-unbacked proofs never parse a file or run work. */
	public function test_bad_proofs_never_parse_or_dispatch(): void {
		$parser    = new class() extends Attachments {
			/**
			 * Number of heavy parse attempts.
			 *
			 * @var int
			 */
			public int $calls = 0;
			/**
			 * Count the expensive boundary without decoding.
			 *
			 * @param mixed $raw Synthetic input.
			 * @return array{}
			 */
			public function check( mixed $raw ): array {
				++$this->calls;
				return array(); }
		};
		$resources = new Resources( attachments: $parser );
		$calls     = 0;
		$handler   = array(
			'callback' => static function () use ( &$calls ): WP_REST_Response {
						++$calls;
						return new WP_REST_Response();
			},
		);
		$request   = $this->request( '/linker-ai/v1/genie/turn', array( 'attachments' => array( array( 'data' => 'invalid' ) ) ), 'genie' );
		$request->set_header( 'X-Linker-Proof', '' );
		$this->assertInstanceOf( WP_Error::class, $resources->dispatch( null, $request, '', $handler ) );
		$request->set_header( 'X-Linker-Proof', $this->proof( 'genie', false ) );
		$this->assertInstanceOf( WP_Error::class, $resources->dispatch( null, $request, '', $handler ) );
		$request->set_header( 'X-Linker-Operation', wp_generate_uuid4() );
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$request->set_header( 'X-Linker-Proof', ( new Proof( static fn(): int => time() - 301 ) )->issue( 'verified', 'genie', $identity, wp_generate_uuid4() ) );
		$this->assertInstanceOf( WP_Error::class, $resources->dispatch( null, $request, '', $handler ) );
		$this->assertSame( 0, $calls );
		$this->assertSame( 0, $parser->calls );
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
				return new WP_REST_Response(
					array(
						'conversation_id' => 123,
						'stream'          => 'synthetic',
					)
				);
			},
		);
		$first     = $resources->dispatch( null, $request, '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $first );
		$this->assertFalse( Resources::verified() );
		$this->assertNull( $resources->context( null ) );
		$request->set_header( 'X-Linker-Proof', '' );
		$second = $resources->dispatch( null, $request, '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $second );
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
			$held[ $hook ] = $wp_filter[ $hook ] ?? null;
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
		foreach ( array( 'off', 'observe' ) as $mode ) {
			putenv( 'LINKER_PUBLIC_PROTECTION_MODE=' . $mode );
			$this->assertFalse( Resources::completed_genie_operation( $id, $fingerprint ) );
		}
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' );
		$receipt = ( new Ledger() )->lookup( $id, $fingerprint );
		$this->assertIsArray( $receipt );
		if ( 'delete-reply' === $lifetime ) {
			wp_delete_post( $receipt['outcome'], true );
		} elseif ( 'expire-reply' === $lifetime ) {
			update_post_meta( $receipt['outcome'], '_linker_expires', time() - 1 );
		} elseif ( 'erase-ledger' === $lifetime ) {
			$identity = Identity::current();
			$this->assertInstanceOf( Identity::class, $identity );
			$this->assertIsArray( ( new Ledger() )->privacy( array( Allowance::owner_for( $identity->browser ) ), true ) );
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
		return array( array( 'delete-reply' ), array( 'expire-reply' ), array( 'erase-ledger' ), array( 'clear-conversation' ) );
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

	/** Reads and conversation writes never consume Genie/model-turn dimensions. */
	public function test_policy_reads_writes_and_native_budget_exhaustion(): void {
		$this->assertSame( 'draft_write', ResourcePolicy::action( '/linker-ai/v1/genie/draft', 'POST' ) );
		$this->assertSame( 'solution_save', ResourcePolicy::action( '/linker-ai/v1/genie/solution', 'POST' ) );
		$this->assertSame( '', ResourcePolicy::action( '/linker-ai/v1/genie/conversation', 'GET' ) );
		$this->assertSame( '', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'GET' ) );
		$this->assertSame( 'conversation_write', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'POST', true ) );
		$this->assertSame( 'conversation_create', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'POST' ) );
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$plan = ResourcePolicy::plan( 'genie', $identity );
		$this->assertSame( array( 'genie_day', 'genie_burst', 'genie_busy', 'genie_site_day', 'genie_site_busy' ), array_map( static fn( Allowance $a ): string => $a->name, $plan['limits'] ) );
		// Burst advances must stay within one synthetic UTC day, even near midnight.
		$now    = intdiv( time(), DAY_IN_SECONDS ) * DAY_IN_SECONDS + HOUR_IN_SECONDS;
		$ledger = new Ledger(
			static function () use ( &$now ): int {
				return $now;
			}
		);
		for ( $i = 0; $i < 30; ++$i ) {
			if ( 0 === $i % 10 ) {
				$now += 601;
			}
			$id = wp_generate_uuid4();
			$fp = hash( 'sha256', $id );
			$this->assertIsArray( $ledger->reserve( $id, $fp, $plan['limits'], 90 ) );
			$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
			$this->assertIsArray( $ledger->complete( $id, $fp ) );
		}
		$now += 601;
		$this->assertInstanceOf( WP_Error::class, $ledger->reserve( wp_generate_uuid4(), hash( 'sha256', 'next' ), $plan['limits'], 90 ) );
		$writes = ResourcePolicy::plan( 'solution_save', $identity );
		$this->assertIsArray( $ledger->reserve( wp_generate_uuid4(), hash( 'sha256', 'saved' ), $writes['limits'], 90 ), 'Saved input remains independent from model turns.' );
	}
	/** Same valid engineering input/version returns its native result once. */
	public function test_engine_input_key_order_deduplication(): void {
		$resources = new Resources();
		$first     = $this->request(
			'/linker-ai/v1/engine/design/residential',
			array(
				'plz'        => '80538',
				'annual_kwh' => 5000,
			),
			'design'
		);
		$second    = $this->request(
			'/linker-ai/v1/engine/design/residential',
			array(
				'annual_kwh' => 5000,
				'plz'        => '80538',
			),
			'design'
		);
		// These query fields are not sent to the engine and cannot buy fresh work.
		$first->set_query_params(
			array(
				'x'       => '1',
				'_locale' => 'user',
			)
		);
		$second->set_query_params(
			array(
				'x'       => '2',
				'_locale' => 'site',
			)
		);
		$calls   = 0;
		$handler = array(
			'callback' => static function () use ( &$calls ): WP_REST_Response {
				++$calls;
				return new WP_REST_Response( array( 'synthetic' => 'design' ) );
			},
		);
		$a       = $resources->dispatch( null, $first, '', $handler );
		$b       = $resources->dispatch( null, $second, '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $a );
		$this->assertInstanceOf( WP_REST_Response::class, $b );
		$this->assertSame( $a->get_data(), $b->get_data() );
		$this->assertSame( 1, $calls );
		$nested = array( 'value' => 'synthetic' );
		for ( $depth = 0; $depth < 20; ++$depth ) {
			$nested = array( 'child' => $nested );
		}
		$too_deep = $this->request( '/linker-ai/v1/engine/design/residential', $nested, 'design' );
		$refused  = $resources->dispatch( null, $too_deep, '', $handler );
		$this->assertInstanceOf( WP_Error::class, $refused );
		$this->assertSame( 400, $refused->get_error_data()['status'] );
		$this->assertSame( 1, $calls );
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=observe' );
		$this->assertNull( $resources->dispatch( null, $too_deep, '', $handler ) );
	}

	/** A single-use business proof cannot hand off twice; old floor is scoped. */
	public function test_business_seam_single_use_and_legacy_scope(): void {
		$policy = static fn( array $old, string $action, Identity $identity ): array => array( new Allowance( 'fixture_business_day', $identity->browser, 20, DAY_IN_SECONDS ) );
		add_filter( 'linker_commerce_public_business_limits', $policy, 10, 3 );
		try {
			$resources = new Resources();
			$request   = $this->request( '/linker-ai/v1/genie/contact', array( 'email' => 'synthetic@example.test' ), 'genie_contact' );
			$guard     = new \Linker\Tools\Genie\FormGuard( 'fixture_contact', 3, 20 );
			$calls     = 0;
			$handler   = array(
				'callback' => function () use ( &$calls, $guard, $resources ): WP_REST_Response {
								++$calls;
								$this->assertTrue( $guard->passes( array() ) );
								$this->assertSame( '', $guard->take() );
								$this->assertSame( 'genie_contact', $resources->context( null )['action'] );
								return new WP_REST_Response( array( 'received' => true ) );
				},
			);
			$this->assertInstanceOf( WP_REST_Response::class, $resources->dispatch( null, $request, '', $handler ) );
			$request->set_header( 'X-Linker-Operation', wp_generate_uuid4() );
			$this->assertInstanceOf( WP_Error::class, $resources->dispatch( null, $request, '', $handler ) );
			$this->assertSame( 1, $calls );
			$this->assertFalse( $guard->passes( array() ) );
			$this->assertNull( $resources->context( null ) );
		} finally {
			remove_filter( 'linker_commerce_public_business_limits', $policy, 10 );
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

	/** Recipient exhaustion refuses a guest confirmation before secrets, meta or mail. */
	public function test_conversation_receipt_gate_runs_once_inside_trusted_context(): void {
		$policy        = static fn( array $old, string $action, Identity $identity ): array => array( new Allowance( 'fixture_business_day', $identity->browser, 20, DAY_IN_SECONDS ) );
		$resources     = new Resources();
		$conversations = new \Linker\Tools\Genie\Conversations();
		$thread        = new \Linker\Tools\Genie\Thread();
		global $wp_filter;
		$held = array();
		foreach ( array( 'linker_tools_set_conversation_cookie', 'linker_tools_set_genie_browser_cookie' ) as $hook ) {
			$held[ $hook ] = $wp_filter[ $hook ] ?? null;
			remove_all_actions( $hook );
		}
		$id = $conversations->open();
		foreach ( $held as $hook => $callbacks ) {
			if ( null !== $callbacks ) {
				$wp_filter[ $hook ] = $callbacks; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Restore fixture-held native cookie writers.
			}
		}

		$thread->record(
			$id,
			array(
				array(
					'role'    => 'user',
					'content' => 'Synthetic mail question',
				),
			),
			"event: block\ndata: {\"type\":\"text\",\"text\":\"Synthetic reply\",\"refs\":[]}\n\nevent: done\ndata: {}\n\n"
		);
		$calls  = array();
		$gate   = static function ( mixed $old, string $email, string $reference, string $kind ) use ( &$calls ): string {
			$calls[] = array( $email, $reference, $kind );
			return 'target_cap';
		};
		$sent   = 0;
		$sender = static function () use ( &$sent ): bool {
			++$sent;
			return true;
		};
		add_filter( 'linker_commerce_public_business_limits', $policy, 10, 3 );
		add_filter( 'linker_commerce_public_business_context', array( $resources, 'context' ) );
		add_filter( 'linker_commerce_receipt_budget_reason', $gate, 10, 4 );
		add_filter( 'linker_tools_genie_confirm_address', $sender );
		try {
			$request  = $this->request(
				'/linker-ai/v1/genie/conversations/' . $id . '/email',
				array(
					'id'    => $id,
					'email' => 'synthetic@example.test',
				),
				'conversation_mail'
			);
			$handler  = array(
				'callback' => static function () use ( $id, $conversations, $thread ): WP_REST_Response {
								$mail = new \Linker\Tools\Genie\ConversationMail( $conversations, $thread );
								return new WP_REST_Response( $mail->send( $id, 'synthetic@example.test', 'en' ), 503 );
				},
			);
			$response = $resources->dispatch( null, $request, '', $handler );
			$this->assertInstanceOf( WP_REST_Response::class, $response );
			$this->assertSame( 'unavailable', $response->get_data()['status'] );
			$this->assertSame( '', get_post_meta( $id, \Linker\Tools\Genie\ConversationMail::PENDING, true ) );
			$this->assertSame( array( array( 'synthetic@example.test', $request->get_header( 'X-Linker-Operation' ), 'conversation_confirmation' ) ), $calls );
			$this->assertSame( 0, $sent );
			$this->assertInstanceOf( WP_REST_Response::class, $resources->dispatch( null, $request, '', $handler ) );
			$this->assertCount( 1, $calls, 'Completed replay cannot spend a second receipt unit.' );
		} finally {
			remove_filter( 'linker_commerce_public_business_limits', $policy, 10 );
			remove_filter( 'linker_commerce_public_business_context', array( $resources, 'context' ) );
			remove_filter( 'linker_commerce_receipt_budget_reason', $gate, 10 );
			remove_filter( 'linker_tools_genie_confirm_address', $sender );
			wp_delete_post( $id, true );
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
	/** Definite pure-service failure permits an explicit retry; success is canonical. */
	public function test_failed_calculation_can_recover_without_losing_success_deduplication(): void {
		$resources = new Resources();
		$request   = $this->request( '/linker-ai/v1/engine/design/residential', array( 'plz' => '80538' ), 'design' );
		$calls     = 0;
		$handler   = array(
			'callback' => static function () use ( &$calls ): WP_REST_Response {
				++$calls;
				return new WP_REST_Response( array( 'synthetic' => true ), 1 === $calls ? 503 : 200 );
			},
		);
		$failed    = $resources->dispatch( null, $request, '', $handler );
		$this->assertSame( 503, $failed->get_status() );
		$this->assertSame( 'failed', $failed->get_headers()['X-Linker-Resource-Outcome'] );
		$request->set_header( 'X-Linker-Operation', wp_generate_uuid4() );
		$this->assertSame( 200, $resources->dispatch( null, $request, '', $handler )->get_status() );
		$request->set_header( 'X-Linker-Operation', wp_generate_uuid4() );
		$this->assertSame( 200, $resources->dispatch( null, $request, '', $handler )->get_status() );
		$this->assertSame( 2, $calls );
	}
	/** Account-owned ability recomputation shares the same safe failure recovery. */
	public function test_native_saved_design_retries_definite_failure_and_reuses_success(): void {
		$user = wp_insert_user(
			array(
				'user_login' => 'g521-' . wp_generate_uuid4(),
				'user_pass'  => wp_generate_password( 32 ),
				'user_email' => wp_generate_uuid4() . '@example.test',
				'role'       => 'customer',
			)
		);
		$this->assertIsInt( $user );
		wp_set_current_user( $user );
		$url     = rtrim( (string) get_option( 'linker_engine_url', '' ), '/' ) . '/design/residential';
		$calls   = 0;
		$fixture = function ( mixed $old, array $args, string $target ) use ( $url, $user, &$calls ): mixed {
			if ( $target !== $url ) {
				return $old;
			}
			++$calls;
			$this->assertSame( Identity::account( $user ), $args['headers']['X-Linker-Resource-Subject'] );
			$this->assertSame( (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ), $args['headers']['X-Linker-Service-Token'] );
			return array(
				'response' => array( 'code' => 1 === $calls ? 503 : 200 ),
				'body'     => '{"synthetic":true}',
				'headers'  => array( 'x-linker-engine-version' => $args['headers']['X-Linker-Engine-Version'] ),
			);
		};
		add_filter( 'pre_http_request', $fixture, 0, 3 );
		try {
			$engine = new \Linker\Tools\Protection\NativeEngine();
			$first  = $engine->request( null, $url, '{"synthetic":true}' );
			$this->assertIsArray( $first );
			$this->assertSame( 503, $first[0] );
			$retry = $engine->request( null, $url, '{"synthetic":true}' );
			$this->assertIsArray( $retry );
			$this->assertSame( 200, $retry[0] );
			$cached = $engine->request( null, $url, '{"synthetic":true}' );
			$this->assertIsArray( $cached );
			$this->assertSame( 200, $cached[0] );
			$this->assertSame( 2, $calls );
		} finally {
			remove_filter( 'pre_http_request', $fixture, 0 );
			wp_set_current_user( 0 );
			require_once ABSPATH . 'wp-admin/includes/user.php';
			wp_delete_user( $user );
		}
	}
	/**
	 * WP's real case-insensitive route matcher cannot bypass resource admission.
	 */
	public function test_mixed_case_native_rest_route_refuses_before_records_or_upstream(): void {
		$before  = wp_count_posts( \Linker\Tools\Genie\Conversations::POST_TYPE );
		$http    = 0;
		$fixture = static function () use ( &$http ): WP_Error {
			++$http;
			return new WP_Error( 'synthetic_unexpected_http' );
		};
		add_filter( 'pre_http_request', $fixture, 0 );
		try {
			$request = new WP_REST_Request( 'POST', '/LINKER-AI/v1/GeNiE/TuRn' );
			$request->set_header( 'Content-Type', 'application/json' );
			$request->set_header( 'X-Linker-Operation', wp_generate_uuid4() );
			$request->set_body( '{"messages":[{"role":"user","content":"Synthetic case variation"}],"locale":"en"}' );
			$response = rest_do_request( $request );
			$this->assertSame( 400, $response->get_status(), (string) wp_json_encode( $response->get_data() ) );
			$this->assertSame( 'linker_admission_proof', $response->get_data()['code'] );
			$this->assertSame( 0, $http );
			$this->assertEquals( $before, wp_count_posts( \Linker\Tools\Genie\Conversations::POST_TYPE ) );
		} finally {
			remove_filter( 'pre_http_request', $fixture, 0 );
		}
	}
	/**
	 * Observe adds no proof/parse/ledger block to the original native callback.
	 */
	public function test_observe_keeps_native_callback_on_protection_preflight_and_storage_failure(): void {
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=observe' );
		update_option( Ledger::OPTION, 'synthetic-corrupt-shadow-store', false );
		$resources = new Resources();
		$calls     = 0;
		$handler   = array(
			'callback' => static function () use ( &$calls ): WP_REST_Response {
				++$calls;
				return new WP_REST_Response( array( 'native' => true ) );
			},
		);
		$request   = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
		$request->set_header( 'Content-Type', 'application/json' );
		$request->set_header( 'X-Linker-Operation', wp_generate_uuid4() );
		$request->set_body( '{"attachments":[{}, {}, {}, {}],"website":"synthetic-bot-field"}' );
		$this->assertInstanceOf( WP_REST_Response::class, $resources->dispatch( null, $request, '', $handler ) );
		$this->assertSame( 1, $calls );
		$this->assertFalse( Resources::verified() );
		// New protection body ceilings are also advisory; native validation stays.
		$request->set_route( '/linker-ai/v1/engine/design/residential' );
		$request->set_body( str_repeat( 'x', 6 * 1024 * 1024 + 1 ) );
		$this->assertNull( $resources->dispatch( null, $request, '', $handler ) );
	}

	/**
	 * Unavailable live version is advisory in observe; private service auth still applies.
	 */
	public function test_observe_native_saved_design_does_not_require_live_version_readback(): void {
		$user = wp_insert_user(
			array(
				'user_login' => 'g521-' . wp_generate_uuid4(),
				'user_pass'  => wp_generate_password( 32 ),
				'user_email' => wp_generate_uuid4() . '@example.test',
				'role'       => 'customer',
			)
		);
		$this->assertIsInt( $user );
		wp_set_current_user( $user );
		$url     = rtrim( (string) get_option( 'linker_engine_url', '' ), '/' ) . '/design/residential';
		$calls   = 0;
		$fixture = function ( mixed $old, array $args, string $target ) use ( $url, &$calls ): mixed {
			if ( $target !== $url ) {
				return $old;
			}
			++$calls;
			$this->assertSame( (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ), $args['headers']['X-Linker-Service-Token'] );
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => '{"synthetic":true}',
				'headers'  => array( 'x-linker-engine-version' => $args['headers']['X-Linker-Engine-Version'] ),
			);
		};
		add_filter( 'pre_http_request', $fixture, 0, 3 );
		try {
			$engine = new \Linker\Tools\Protection\NativeEngine( new \Linker\Tools\Protection\EngineVersion( static fn(): string => '' ) );
			putenv( 'LINKER_PUBLIC_PROTECTION_MODE=observe' );
			$this->assertSame( array( 200, '{"synthetic":true}' ), $engine->request( null, $url, '{"synthetic":true}' ) );
			putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' );
			$this->assertInstanceOf( WP_Error::class, $engine->request( null, $url, '{"synthetic":true}' ) );
			$this->assertSame( 1, $calls );
		} finally {
			remove_filter( 'pre_http_request', $fixture, 0 );
			wp_set_current_user( 0 );
			include_once ABSPATH . 'wp-admin/includes/user.php';
			wp_delete_user( $user );
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
	 * A real cookie/header failure cannot replace native validation in observe.
	 */
	public function test_observe_cookie_failure_keeps_native_validation_in_a_real_process(): void {
     // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Exercise PHP's real headers_sent state outside PHPUnit output buffering.
		$process = proc_open(
			array( PHP_BINARY, '-d', 'memory_limit=512M', __DIR__ . '/fixtures/resource-observe-cookie.php' ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		$this->assertIsResource( $process );
		$output = (string) stream_get_contents( $pipes[1] );
		$error  = (string) stream_get_contents( $pipes[2] );
		fclose( $pipes[1] ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- Native process pipe.
		fclose( $pipes[2] ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- Native process pipe.
		$this->assertSame( 0, proc_close( $process ), $error );
		$this->assertSame(
			array(
				'cookie_failed' => true,
				'calls'         => 1,
				'code'          => 'native_validation',
			),
			json_decode( substr( $output, strpos( $output, "\n" ) + 1 ), true ),
			$output
		);
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
	/** Native route capture wins over body/query path; irrelevant queries share one result. */
	public function test_real_engine_proxy_cannot_override_route_or_duplicate_work_with_query(): void {
		$base    = rtrim( (string) get_option( 'linker_engine_url', '' ), '/' );
		$urls    = array();
		$fixture = static function ( mixed $old, array $args, string $url ) use ( $base, &$urls ): mixed {
			if ( ! str_starts_with( $url, $base . '/' ) || str_ends_with( $url, '/resource/version' ) ) {
				return $old; }
			$urls[]  = $url;
			$input   = json_decode( $args['body'], true );
			$invalid = isset( $input['_route'] ) || isset( $input['started_nonce'] );
			return array(
				'response' => array( 'code' => $invalid ? 422 : 200 ),
				'body'     => '{"synthetic":"native-engine"}',
				'headers'  => array(
					'content-type'            => 'application/json',
					'x-linker-engine-version' => $args['headers']['X-Linker-Engine-Version'],
				),
			);
		};
		add_filter( 'pre_http_request', $fixture, 0, 3 );
		try {
			foreach ( array( 'roof/pack', 'report/pdf' ) as $index => $fake_path ) {
				$request = $this->request(
					'/linker-ai/v1/engine/design/residential',
					array(
						'plz'        => '80538',
						'annual_kwh' => 5000,
					),
					'design'
				);
				$request->set_query_params(
					array(
						'path'    => $fake_path,
						'x'       => $index,
						'_locale' => $index,
					)
				);
				$this->assertSame( 200, rest_do_request( $request )->get_status() );
			}
			$this->assertSame( array( $base . '/design/residential' ), $urls );
			// Actual upstream JSON is nested apart from adapter metadata. Fields
			// that look like transport keys still change the real engine input.
			foreach ( array( '_route', 'started_nonce' ) as $field ) {
				$request = $this->request(
					'/linker-ai/v1/engine/design/residential',
					array(
						'plz'        => '80538',
						'annual_kwh' => 5000,
						$field       => 'synthetic-extra',
					),
					'design'
				);
				$this->assertSame( 422, rest_do_request( $request )->get_status() );
			}
			$this->assertCount( 3, $urls );
			foreach ( array(
				array( 'plz' => '80538' ),
				array(
					'plz'  => '80538',
					'path' => 'design/residential',
				),
			) as $body ) {
				$request = new WP_REST_Request( 'POST', '/linker-ai/v1/engine/unknown' );
				$request->set_header( 'Content-Type', 'application/json' );
				$request->set_body( (string) wp_json_encode( $body ) );
				$request->set_query_params( array( 'path' => 'design/residential' ) );
				$response = rest_do_request( $request );
				$this->assertSame( 404, $response->get_status() );
				$this->assertSame( 'linker_engine_path', $response->get_data()['code'] );
			}
			$this->assertCount( 3, $urls, 'No query/body override reaches any additional upstream work.' );
		} finally {
			remove_filter( 'pre_http_request', $fixture, 0 );
		}
	}
	/** A nightly restart changes public/native canonical keys within the same UTC day. */
	public function test_live_engine_rotation_never_reuses_the_previous_loaded_snapshot(): void {
		$resources = new Resources();
		$calls     = 0;
		$handler   = array(
			'callback' => function () use ( &$calls ): WP_REST_Response {
						++$calls;
						$this->assertSame( $this->running_version, Resources::engine_version() );
						return new WP_REST_Response( array( 'snapshot' => $this->running_version ) );
			},
		);
		$input     = array(
			'plz'        => '80538',
			'annual_kwh' => 5000,
		);
		$first     = $resources->dispatch( null, $this->request( '/linker-ai/v1/engine/design/residential', $input, 'design' ), '', $handler );
		$old       = $this->running_version;
		$this->assertSame( $old, $first->get_data()['snapshot'] );
		$resources->dispatch( null, $this->request( '/linker-ai/v1/engine/design/residential', $input, 'design' ), '', $handler );
		$this->assertSame( 1, $calls );
		$this->running_version = hash( 'sha256', 'synthetic-nightly-engine-b' );
		$rotated               = $resources->dispatch( null, $this->request( '/linker-ai/v1/engine/design/residential', $input, 'design' ), '', $handler );
		$this->assertSame( $this->running_version, $rotated->get_data()['snapshot'] );
		$this->assertSame( 2, $calls );
		$unavailable = static function ( mixed $prior, array $args, string $url ): mixed {
			return str_ends_with( $url, '/resource/version' ) ? new WP_Error( 'synthetic-version-down' ) : $prior;
		};
		add_filter( 'pre_http_request', $unavailable, 999, 3 );
		try {
			$failed = $resources->dispatch( null, $this->request( '/linker-ai/v1/engine/design/residential', $input, 'design' ), '', $handler );
			$this->assertInstanceOf( WP_Error::class, $failed );
			$this->assertSame( 503, $failed->get_error_data()['status'] );
			$this->assertSame( 2, $calls, 'Even a known cached result requires current live readback.' );
			putenv( 'LINKER_PUBLIC_PROTECTION_MODE=observe' );
			$native = array( 'callback' => static fn(): WP_REST_Response => new WP_REST_Response( array( 'native' => true ) ) );
			$this->assertInstanceOf( WP_REST_Response::class, $resources->dispatch( null, $this->request( '/linker-ai/v1/engine/design/residential', $input, 'design' ), '', $native ) );
		} finally {
			remove_filter( 'pre_http_request', $unavailable, 999 );
			putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' );
		}
		$version               = new \Linker\Tools\Protection\EngineVersion();
		$scope                 = new \stdClass();
		$before                = $version->current( $scope );
		$this->running_version = hash( 'sha256', 'synthetic-next-live-version' );
		$this->assertSame( $before, $version->current( $scope ), 'Only this in-flight request can reuse its handshake.' );
		$this->assertSame( $this->running_version, $version->current( new \stdClass() ) );
	}

	/** Native saved designs read live version first and refuse mismatched success headers. */
	public function test_native_engine_rotation_and_wrong_worker_response_are_not_cached_as_success(): void {
		$user = wp_insert_user(
			array(
				'user_login' => 'g521-' . wp_generate_uuid4(),
				'user_pass'  => wp_generate_password( 32 ),
				'user_email' => wp_generate_uuid4() . '@example.test',
				'role'       => 'customer',
			)
		);
		$this->assertIsInt( $user );
		wp_set_current_user( $user );
		$url     = rtrim( (string) get_option( 'linker_engine_url', '' ), '/' ) . '/design/residential';
		$calls   = 0;
		$state   = new class() {
			/** Synthetic rolling-worker response fault.
			 *
			 * @var bool
			 */
			public bool $wrong = false;
		};
		$fixture = function ( mixed $old, array $args, string $target ) use ( $url, &$calls, $state ): mixed {
			if ( $target !== $url ) {
				return $old; }
			++$calls;
			$this->assertSame( $this->running_version, $args['headers']['X-Linker-Engine-Version'] );
			return array(
				'response' => array( 'code' => 200 ),
				'headers'  => array( 'x-linker-engine-version' => $state->wrong ? str_repeat( 'f', 64 ) : $this->running_version ),
				'body'     => wp_json_encode( array( 'snapshot' => $this->running_version ) ),
			);
		};
		add_filter( 'pre_http_request', $fixture, 0, 3 );
		try {
			$engine = new \Linker\Tools\Protection\NativeEngine();
			$body   = '{"plz":"80538","annual_kwh":5000}';
			$first  = $engine->request( null, $url, $body );
			$this->assertIsArray( $first );
			$this->assertSame( 200, $first[0] );
			$first = $engine->request( null, $url, $body );
			$this->assertIsArray( $first );
			$this->assertSame( 200, $first[0] );
			$this->assertSame( 1, $calls );
			$this->running_version = hash( 'sha256', 'synthetic-native-nightly-b' );
			$rotated               = $engine->request( null, $url, $body );
			$this->assertIsArray( $rotated );
			$this->assertSame( $this->running_version, json_decode( $rotated[1], true )['snapshot'] );
			$this->assertSame( 2, $calls );
			$this->running_version = hash( 'sha256', 'synthetic-restart-race-c' );
			$state->wrong          = true;
			$failed                = $engine->request( null, $url, $body );
			$this->assertIsArray( $failed );
			$this->assertSame( 503, $failed[0] );
			$state->wrong = false;
			$first        = $engine->request( null, $url, $body );
			$this->assertIsArray( $first );
			$this->assertSame( 200, $first[0] );
			$this->assertSame( 4, $calls, 'A wrong-worker success never becomes the canonical success.' );
		} finally {
			remove_filter( 'pre_http_request', $fixture, 0 );
			wp_set_current_user( 0 );
			require_once ABSPATH . 'wp-admin/includes/user.php';
			wp_delete_user( $user );
		}
	}
	/** An actual public proxy success from the wrong worker cannot poison a canonical result. */
	public function test_public_proxy_rejects_wrong_worker_success_then_recovers(): void {
		$url     = rtrim( (string) get_option( 'linker_engine_url', '' ), '/' ) . '/design/residential';
		$state   = new class() {
			/** Synthetic wrong-worker response.
			 *
			 * @var bool
			 */
			public bool $wrong = true;
		};
		$calls   = 0;
		$fixture = function ( mixed $old, array $args, string $target ) use ( $url, $state, &$calls ): mixed {
			if ( $target !== $url ) {
				return $old; }
			++$calls;
			return array(
				'response' => array( 'code' => 200 ),
				'headers'  => array( 'x-linker-engine-version' => $state->wrong ? str_repeat( 'f', 64 ) : $args['headers']['X-Linker-Engine-Version'] ),
				'body'     => '{"synthetic":"actual-worker-result"}',
			);
		};
		add_filter( 'pre_http_request', $fixture, 0, 3 );
		try {
			$input  = array(
				'plz'        => '80538',
				'annual_kwh' => 5000,
			);
			$failed = rest_do_request( $this->request( '/linker-ai/v1/engine/design/residential', $input, 'design' ) );
			$this->assertSame( 502, $failed->get_status() );
			$this->assertSame( 'linker_engine_upstream', $failed->get_data()['code'] );
			$state->wrong = false;
			$recovered    = rest_do_request( $this->request( '/linker-ai/v1/engine/design/residential', $input, 'design' ) );
			$this->assertSame( 200, $recovered->get_status() );
			$this->assertSame( 'actual-worker-result', $recovered->get_data()['synthetic'] );
			$this->assertSame( 200, rest_do_request( $this->request( '/linker-ai/v1/engine/design/residential', $input, 'design' ) )->get_status() );
			$this->assertSame( 2, $calls );
		} finally {
			remove_filter( 'pre_http_request', $fixture, 0 );
		}
	}
	/** Current writes can reuse proof; a withdrawal invalidates both receipt routes. */
	public function test_solution_save_and_draft_receipts_revalidate_current_products(): void {
		foreach ( array(
			'/linker/v1/solutions'       => 'solution_save',
			'/linker/v1/solutions/draft' => 'draft_write',
		) as $route => $action ) {
			$product = new \WC_Product_Simple();
			$product->set_name( 'Publication receipt fixture' );
			$product->set_status( 'publish' );
			$id = $product->save();
			try {
				$current = \Linker\Commerce\Products\Publication::product( $id );
				$this->assertIsArray( $current );
				$dependencies = array(
					'products'  => array(
						array(
							'product_id'       => $current['product_id'],
							'product_revision' => $current['product_revision'],
						),
					),
					'documents' => array(),
				);
				$calls        = 0;
				$handler      = array(
					'callback' => static function () use ( &$calls, $dependencies ): WP_REST_Response {
						++$calls;
						return new WP_REST_Response(
							array(
								'saved'       => true,
								'publication' => $dependencies,
							)
						);
					},
				);
				$request      = $this->request( $route, array( 'input' => array( 'plz' => '80538' ) ), $action );
				$resources    = new Resources();
				$first        = $resources->dispatch( null, $request, '', $handler );
				$this->assertInstanceOf( WP_REST_Response::class, $first );
				$this->assertSame( 200, $first->get_status() );
				$this->assertSame( 200, $resources->dispatch( null, $request, '', $handler )->get_status() );
				$this->assertSame( 1, $calls );
				$product->set_status( 'draft' );
				$product->save();
				$withdrawn = $resources->dispatch( null, $request, '', $handler );
				$this->assertInstanceOf( WP_Error::class, $withdrawn );
				$this->assertSame( 'linker_publication_changed', $withdrawn->get_error_code() );
				$this->assertSame( 409, $withdrawn->get_error_data()['status'] );
				$this->assertSame( 1, $calls );
			} finally {
				wp_delete_post( $id, true );
			}
		}
	}

	/** An already completed pre-contract write has no current publication proof. */
	public function test_pre_contract_solution_receipt_cannot_replay_as_current_success(): void {
		foreach ( array(
			'/linker/v1/solutions'       => 'solution_save',
			'/linker/v1/solutions/draft' => 'draft_write',
		) as $route => $action ) {
			$dependencies = array(
				'products'  => array(),
				'documents' => array(),
			);
			$handler      = array(
				'callback' => static fn(): WP_REST_Response => new WP_REST_Response(
					array(
						'saved'       => true,
						'publication' => $dependencies,
					)
				),
			);
			$request      = $this->request( $route, array( 'input' => array( 'plz' => '80538' ) ), $action );
			$resources    = new Resources();
			$this->assertSame( 200, $resources->dispatch( null, $request, '', $handler )->get_status() );
			$receipts = get_posts(
				array(
					'post_type'      => Replies::TYPE,
					'post_status'    => 'private',
					'posts_per_page' => 1,
					'fields'         => 'ids',
				)
			);
			$this->assertCount( 1, $receipts );
			$stored = json_decode( (string) get_post_field( 'post_content', $receipts[0] ), true );
			unset( $stored['publication'], $stored['data']['publication'] );
			wp_update_post(
				array(
					'ID'           => $receipts[0],
					'post_content' => wp_slash( (string) wp_json_encode( $stored ) ),
				)
			);
			$reply = $resources->dispatch( null, $request, '', $handler );
			$this->assertInstanceOf( WP_Error::class, $reply );
			$this->assertSame( 'linker_publication_changed', $reply->get_error_code() );
		}
	}
}
