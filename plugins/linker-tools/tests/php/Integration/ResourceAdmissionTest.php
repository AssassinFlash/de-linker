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

	/** Isolate the journal and official dummy configuration. */
	protected function setUp(): void {
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
		delete_option( Ledger::OPTION );
		if ( false !== $this->old ) {
			update_option( Ledger::OPTION, $this->old, false );
		}
		foreach ( $this->environment as $key => $value ) {
			putenv( false === $value ? $key : $key . '=' . $value );
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
		$this->assertSame( '', ResourcePolicy::action( '/linker-ai/v1/genie/conversation', 'GET' ) );
		$this->assertSame( '', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'GET' ) );
		$this->assertSame( 'conversation_write', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'POST', true ) );
		$this->assertSame( 'conversation_create', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'POST' ) );
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$plan = ResourcePolicy::plan( 'genie', $identity );
		$this->assertSame( array( 'genie_day', 'genie_burst', 'genie_busy', 'genie_site_day', 'genie_site_busy' ), array_map( static fn( Allowance $a ): string => $a->name, $plan['limits'] ) );
		$now    = time();
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
		$calls     = 0;
		$handler   = array(
			'callback' => static function () use ( &$calls ): WP_REST_Response {
						++$calls;
						return new WP_REST_Response( array( 'synthetic' => 'design' ) );
			},
		);
		$a         = $resources->dispatch( null, $first, '', $handler );
		$b         = $resources->dispatch( null, $second, '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $a );
		$this->assertInstanceOf( WP_REST_Response::class, $b );
		$this->assertSame( $a->get_data(), $b->get_data() );
		$this->assertSame( 1, $calls );
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
		$this->assertSame( 503, $resources->dispatch( null, $request, '', $handler )->get_status() );
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
}
