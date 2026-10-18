<?php
/**
 * Clearing a conversation and emailing it, through the REST routes.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\ConversationMail;
use Linker\Tools\Genie\FormGuard;
use Linker\Tools\Genie\RateLimit;
use Linker\Tools\Genie\Thread;
use PHPUnit\Framework\TestCase;
use WP_REST_Request;

/**
 * The two routes a visitor uses on one conversation of the list (ticket
 * #235): DELETE clears it, POST …/email sends it to the visitor's own
 * address. The email goes through the site's real mail chain as far as
 * wp_mail(); the call is recorded there and stopped before the Outbox, so
 * a run writes no mail (AGENTS.md §5, test mail).
 *
 * @coversNothing
 */
final class ConversationRoutesTest extends TestCase {

	/**
	 * A stream as the service writes it: meta, one text block, done.
	 */
	private const STREAM = "event: meta\ndata: {\"turn_id\": 7, \"grounded\": true}\n\n"
		. "event: block\ndata: {\"type\": \"text\", \"text\": \"The SAJ H2-10K-T3 is a three-phase hybrid inverter.\", \"refs\": []}\n\n"
		. "event: block\ndata: {\"type\": \"cards\", \"product_ids\": [4107]}\n\n"
		. "event: done\ndata: {}\n\n";

	/**
	 * The wp_mail() calls of the test.
	 *
	 * @var list<array<string, mixed>>
	 */
	private array $mail = array();

	/**
	 * The instance's limiter rows from before the test.
	 *
	 * @var array<int, array<string, string>>
	 */
	private array $limits = array();

	/**
	 * Hooks and cookies held while a test runs.
	 *
	 * @var array<string, mixed>
	 */
	private array $held = array();

	/**
	 * Conversations and users the tests created.
	 *
	 * @var array{posts: list<int>, users: list<int>}
	 */
	private array $created = array(
		'posts' => array(),
		'users' => array(),
	);

	/**
	 * Skips unless the integration configuration ran the bootstrap.
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just up); the unit suite does not load WordPress.' );
		}
	}

	/**
	 * Holds the cookie writers, records and stops mail, starts as a guest.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->mail    = array();
		$this->created = array(
			'posts' => array(),
			'users' => array(),
		);
		global $wp_filter;
		foreach ( array( 'linker_tools_set_conversation_cookie', 'linker_tools_set_genie_browser_cookie' ) as $hook ) {
			$this->held[ $hook ] = $wp_filter[ $hook ] ?? null;
			remove_all_actions( $hook );
		}
		add_filter( 'wp_mail', array( $this, 'record' ), PHP_INT_MAX );
		add_filter( 'pre_wp_mail', array( $this, 'stop' ), 1 );
		$this->held['limit'] = $_SERVER['REMOTE_ADDR'] ?? null; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- held to be put back unchanged.
		// A connection of its own, so a run starts with a full allowance
		// and never spends another test's.
		$_SERVER['REMOTE_ADDR'] = '192.0.2.' . wp_rand( 1, 254 );
		$_COOKIE                = array();
		wp_set_current_user( 0 );
		// The site's daily cap is shared state: this run starts with a fresh
		// count and the instance gets its own count back afterwards.
		global $wpdb;
		$this->limits = $wpdb->get_results( $wpdb->prepare( "SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( RateLimit::PREFIX . 'genie_mail' ) . '%' ), ARRAY_A ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows.
		self::clear_limits();
	}

	/**
	 * Gives everything back and removes the fixtures.
	 */
	protected function tearDown(): void {
		global $wp_filter;
		remove_filter( 'wp_mail', array( $this, 'record' ), PHP_INT_MAX );
		remove_filter( 'pre_wp_mail', array( $this, 'stop' ), 1 );
		self::clear_limits();
		global $wpdb;
		foreach ( $this->limits as $row ) {
			$wpdb->insert( $wpdb->options, $row + array( 'autoload' => 'off' ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows, put back.
		}
		foreach ( array( 'linker_tools_set_conversation_cookie', 'linker_tools_set_genie_browser_cookie' ) as $hook ) {
			if ( null === $this->held[ $hook ] ) {
				unset( $wp_filter[ $hook ] );
			} else {
				$wp_filter[ $hook ] = $this->held[ $hook ]; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- restores the hook this test held.
			}
		}
		if ( null === $this->held['limit'] ) {
			unset( $_SERVER['REMOTE_ADDR'] );
		} else {
			$_SERVER['REMOTE_ADDR'] = $this->held['limit'];
		}
		$this->held = array();
		wp_set_current_user( 0 );
		$_COOKIE = array();
		foreach ( $this->created['posts'] as $id ) {
			wp_delete_post( $id, true );
		}
		require_once ABSPATH . 'wp-admin/includes/user.php';
		foreach ( $this->created['users'] as $user ) {
			wp_delete_user( $user );
		}
		$this->created = array(
			'posts' => array(),
			'users' => array(),
		);
		parent::tearDown();
	}

	/**
	 * Records one wp_mail() call; the `wp_mail` filter.
	 *
	 * @param array<string, mixed> $atts The call's arguments.
	 * @return array<string, mixed>
	 */
	public function record( array $atts ): array {
		$this->mail[] = $atts;
		return $atts;
	}

	/**
	 * Stops the call before the Outbox; the `pre_wp_mail` filter.
	 *
	 * @param null|bool $pre Earlier answer.
	 */
	public function stop( $pre ): bool {
		unset( $pre );
		return true;
	}

	/**
	 * DELETE clears the visitor's own conversation and answers the list
	 * without it; another browser gets a 404 and the conversation stays.
	 */
	public function test_delete_clears_only_the_visitors_own_conversation(): void {
		$keep  = $this->answered( 'linker-it-keep' );
		$clear = $this->answered( 'linker-it-clear' );
		$jar   = $_COOKIE;

		$_COOKIE = array();
		$this->assertSame( 404, $this->call( 'DELETE', $clear )->get_status(), 'Another browser cannot clear it.' );
		$this->assertInstanceOf( \WP_Post::class, get_post( $clear ) );

		$_COOKIE  = $jar;
		$response = $this->call( 'DELETE', $clear );
		$this->assertSame( 200, $response->get_status() );
		$this->assertNull( get_post( $clear ) );
		$data = $response->get_data();
		$this->assertSame( array( $keep ), array_column( $data['conversations'], 'id' ) );
		$this->assertSame( 0, $data['current_id'], 'The cleared one was current; no conversation is current now.' );
	}

	/**
	 * A guest's request sends only the confirmation: fixed words and a
	 * link to the typed address, nothing of the conversation. Opening the
	 * link sends the conversation there, with the product its answer
	 * showed; the link works once.
	 */
	public function test_a_guest_confirms_the_address_before_the_conversation_goes(): void {
		$id = $this->answered( 'Which hybrid inverter fits a home?' );

		$response = $this->call(
			'POST',
			$id,
			'/email',
			array(
				'email'  => 'tester@example.test',
				'locale' => 'en',
			) + self::guard()
		);

		$this->assertSame( 202, $response->get_status(), (string) wp_json_encode( $response->get_data() ) );
		$this->assertSame( array( 'status' => 'confirm', 'to' => 'tester@example.test' ), $response->get_data() ); // phpcs:ignore WordPress.Arrays.ArrayDeclarationSpacing.AssociativeArrayFound -- the whole answer.
		$this->assertCount( 1, $this->mail, 'Only the confirmation.' );
		$this->assertSame( array( 'tester@example.test' ), (array) $this->mail[0]['to'] );
		$this->assertSame( 'Conversation with Genie requested for this email address', $this->mail[0]['subject'] );
		$confirmation = (string) $this->mail[0]['message'];
		$this->assertStringNotContainsString( 'Which hybrid inverter fits a home?', $confirmation, 'No conversation text before the address is confirmed.' );
		$this->assertStringNotContainsString( 'three-phase hybrid inverter', $confirmation );
		$this->assertSame( 1, preg_match( '/token=(\d+\.[0-9a-f]{64})/', $confirmation, $token ), 'The link is in it.' );

		$mail = new ConversationMail( new Conversations(), new Thread() );
		$this->assertSame( 'sent', $mail->confirm( (string) ( $token[1] ?? '' ) )['status'] );
		$this->assertCount( 2, $this->mail );
		$this->assertSame( array( 'tester@example.test' ), (array) $this->mail[1]['to'] );
		$this->assertSame( 'Your conversation with Genie', $this->mail[1]['subject'] );
		$body = (string) $this->mail[1]['message'];
		$this->assertStringContainsString( 'Which hybrid inverter fits a home?', $body );
		$this->assertStringContainsString( 'The SAJ H2-10K-T3 is a three-phase hybrid inverter.', $body, 'The last answer, from its stream.' );
		$this->assertStringContainsString( esc_html( get_the_title( 4107 ) ), $body, 'The product the answer showed.' );
		$this->assertStringNotContainsString( 'Bcc', implode( "\n", (array) $this->mail[1]['headers'] ), 'Nobody else is copied.' );

		$this->assertSame( 'expired', $mail->confirm( (string) ( $token[1] ?? '' ) )['status'], 'The link works once.' );
		$this->assertCount( 2, $this->mail );
	}

	/**
	 * An expired link sends nothing; the German page's request gets the
	 * German confirmation.
	 */
	public function test_an_expired_link_sends_nothing(): void {
		$id = $this->answered( 'Welcher Hybridwechselrichter passt?' );
		$this->assertSame(
			202,
			$this->call(
				'POST',
				$id,
				'/email',
				array(
					'email'  => 'tester@example.test',
					'locale' => 'de',
				) + self::guard()
			)->get_status()
		);
		$this->assertSame( 'Gespräch mit Genie für diese E-Mail-Adresse angefordert', $this->mail[0]['subject'] );
		preg_match( '/token=(\d+\.[0-9a-f]{64})/', (string) $this->mail[0]['message'], $token );
		$pending            = get_post_meta( $id, ConversationMail::PENDING, true );
		$pending['expires'] = time() - 1;
		update_post_meta( $id, ConversationMail::PENDING, $pending );

		$result = ( new ConversationMail( new Conversations(), new Thread() ) )->confirm( (string) ( $token[1] ?? '' ) );

		$this->assertSame( array( 'status' => 'expired', 'locale' => 'de' ), $result ); // phpcs:ignore WordPress.Arrays.ArrayDeclarationSpacing.AssociativeArrayFound -- the whole answer.
		$this->assertCount( 1, $this->mail );
	}

	/**
	 * A filled honeypot, a start time a moment old, one this site did not
	 * sign, or one older than a day: answered like a request, nothing sent.
	 */
	public function test_the_bot_guard_sends_nothing(): void {
		$id = $this->answered( 'linker-it-bots' );
		foreach (
			array(
				array( 'website' => 'https://spam.example' ) + self::guard(),
				self::guard( 0 ),
				array(
					'started'       => (string) ( time() - 60 ),
					'started_nonce' => 'forged',
				),
				self::guard( FormGuard::STAMP_LIFETIME + 60 ),
				array(),
			) as $guard
		) {
			$response = $this->call( 'POST', $id, '/email', array( 'email' => 'tester@example.test' ) + $guard );
			$this->assertSame( 202, $response->get_status() );
		}
		$this->assertSame( array(), $this->mail );
		$this->assertSame( '', get_post_meta( $id, ConversationMail::PENDING, true ), 'No link was made.' );
	}

	/**
	 * A signed-in customer's conversation goes to the account's address at
	 * once, whatever address the request names.
	 */
	public function test_a_customer_gets_it_at_the_account_address(): void {
		$user = wp_insert_user(
			array(
				'user_login' => 'linker-it-' . wp_generate_password( 8, false ),
				'user_email' => 'linker-it-account@example.test',
				'user_pass'  => wp_generate_password( 24 ),
				'role'       => 'customer',
			)
		);
		$this->assertIsInt( $user );
		$this->created['users'][] = $user;
		wp_set_current_user( $user );
		$id = $this->answered( 'Where is my Proforma?' );

		$response = $this->call(
			'POST',
			$id,
			'/email',
			array(
				'email'  => 'someone-else@example.test',
				'locale' => 'en',
			)
		);

		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( 'linker-it-account@example.test', $response->get_data()['to'], 'The panel is told which address the account used.' );
		$this->assertCount( 1, $this->mail );
		$this->assertSame( array( 'linker-it-account@example.test' ), (array) $this->mail[0]['to'] );
		$this->assertSame( 'Your conversation with Genie', $this->mail[0]['subject'] );
	}

	/**
	 * What the route refuses: a bad address, someone else's conversation,
	 * one with nothing answered yet, a fourth request within the hour.
	 */
	public function test_the_route_refuses_what_it_must_not_send(): void {
		$id = $this->answered( 'linker-it-refusals' );
		$this->assertSame( 400, $this->call( 'POST', $id, '/email', array( 'email' => 'not an address' ) + self::guard() )->get_status() );

		$empty                    = ( new Conversations() )->open();
		$this->created['posts'][] = $empty;
		$this->assertSame( 409, $this->call( 'POST', $empty, '/email', array( 'email' => 'tester@example.test' ) + self::guard() )->get_status(), 'Nothing answered yet, nothing to send.' );

		$jar     = $_COOKIE;
		$_COOKIE = array();
		$this->assertSame( 404, $this->call( 'POST', $id, '/email', array( 'email' => 'tester@example.test' ) + self::guard() )->get_status() );
		$_COOKIE = $jar;

		for ( $sent = 0; $sent < ConversationMail::LIMIT; ++$sent ) {
			$this->assertSame( 202, $this->call( 'POST', $id, '/email', array( 'email' => 'tester@example.test' ) + self::guard() )->get_status() );
		}
		$refused = $this->call( 'POST', $id, '/email', array( 'email' => 'tester@example.test' ) + self::guard() );
		$this->assertSame( 429, $refused->get_status() );
		$this->assertSame( 'linker_genie_email_throttled', $refused->get_data()['code'] );
		$this->assertSame( ConversationMail::LIMIT, $refused->get_data()['data']['limit'], 'The refusal names the limit the panel shows.' );
		$this->assertCount( ConversationMail::LIMIT, $this->mail, 'Only the allowed ones reached wp_mail().' );
	}

	/**
	 * At the site's daily cap the request is refused, and nothing reaches
	 * wp_mail() (so nothing waits in the Outbox either).
	 */
	public function test_at_the_daily_cap_nothing_is_sent_or_queued(): void {
		$id   = $this->answered( 'linker-it-cap' );
		$site = new RateLimit( 'genie_mail_day', ConversationMail::DAILY_CAP, DAY_IN_SECONDS );
		for ( $taken = 0; $taken < ConversationMail::DAILY_CAP; ++$taken ) {
			$this->assertTrue( $site->take( '' ) );
		}

		$refused = $this->call( 'POST', $id, '/email', array( 'email' => 'tester@example.test' ) + self::guard() );

		$this->assertSame( 429, $refused->get_status() );
		$this->assertSame( 'linker_genie_email_capped', $refused->get_data()['code'] );
		$this->assertSame( array(), $this->mail );
	}

	/**
	 * Reopening preserves the exact Markdown/Unicode the first reply showed.
	 */
	public function test_reopening_keeps_the_complete_reply_formatting(): void {
		$id       = $this->answered( 'linker-it-formatting' );
		$text     = <<<'ANSWER'
## Auswahl

Prüfen Sie **"Phase"**.

1. Netzanschluss
2. Batterie

`C:\PV\Datenblatt`
ANSWER;
		$messages = array(
			array( 'role' => 'user', 'content' => 'First question' ), // phpcs:ignore WordPress.Arrays.ArrayDeclarationSpacing.AssociativeArrayFound -- one message per line.
			array( 'role' => 'assistant', 'content' => $text ), // phpcs:ignore WordPress.Arrays.ArrayDeclarationSpacing.AssociativeArrayFound -- one message per line.
			array( 'role' => 'user', 'content' => 'What next?' ), // phpcs:ignore WordPress.Arrays.ArrayDeclarationSpacing.AssociativeArrayFound -- one message per line.
		);
		$stream   = "event: block\ndata: " . wp_json_encode(
			array(
				'type' => 'text',
				'text' => $text,
				'refs' => array(),
			)
		)
			. "\n\nevent: done\ndata: {}\n\n";
		( new Thread() )->record( $id, $messages, $stream );
		// Exercise the same public route a reloaded workspace or dock reads.
		$response = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/conversation' ) );
		$this->assertSame( 200, $response->get_status() );
		$data = $response->get_data();
		$this->assertSame( $stream, $data['stream'] );
		$this->assertSame( $messages, $data['messages'] );
		$this->assertSame( $text, ( new Thread() )->transcript( $id )[3]['content'] );
	}

	/**
	 * Every answer keeps the products its cards showed, also after later
	 * turns, when the browser sends that answer back as text only.
	 */
	public function test_each_answer_keeps_its_products(): void {
		$id     = $this->answered( 'linker-it-first' );
		$thread = new Thread();
		$first  = 'The SAJ H2-10K-T3 is a three-phase hybrid inverter.';
		$thread->record(
			$id,
			array(
				array( 'role' => 'user', 'content' => 'linker-it-first' ), // phpcs:ignore WordPress.Arrays.ArrayDeclarationSpacing.AssociativeArrayFound -- one message per line.
				array( 'role' => 'assistant', 'content' => $first ), // phpcs:ignore WordPress.Arrays.ArrayDeclarationSpacing.AssociativeArrayFound -- one message per line.
				array( 'role' => 'user', 'content' => 'linker-it-second' ), // phpcs:ignore WordPress.Arrays.ArrayDeclarationSpacing.AssociativeArrayFound -- one message per line.
			),
			"event: block\ndata: {\"type\": \"text\", \"text\": \"No cards this time.\", \"refs\": []}\n\nevent: done\ndata: {}\n\n"
		);

		$transcript = $thread->transcript( $id );

		$this->assertSame( array( 'user', 'assistant', 'user', 'assistant' ), array_column( $transcript, 'role' ) );
		$this->assertSame( $first, $transcript[1]['content'] );
		$this->assertSame( array( 4107 ), $transcript[1]['products'], 'The first answer still names its product.' );
		$this->assertSame( 'No cards this time.', $transcript[3]['content'] );
		$this->assertSame( array(), $transcript[3]['products'] );
	}

	/**
	 * A guest's bot-guard fields as the page would have given them, signed
	 * by this site `$age` seconds ago.
	 *
	 * @param int $age Seconds since the page was made.
	 * @return array{started: string, started_nonce: string}
	 */
	private static function guard( int $age = 10 ): array {
		$stamp = ConversationMail::stamp( time() - $age );
		return array(
			'started'       => $stamp['started'],
			'started_nonce' => $stamp['nonce'],
		);
	}

	/**
	 * Removes every row of the two Genie mail limiters.
	 */
	private static function clear_limits(): void {
		global $wpdb;
		$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( RateLimit::PREFIX . 'genie_mail' ) . '%' ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows.
	}

	/**
	 * A conversation of this browser with one answered turn, current.
	 *
	 * @param string $question The customer's first message.
	 */
	private function answered( string $question ): int {
		$conversations = new Conversations();
		$id            = $conversations->open();
		$this->assertGreaterThan( 0, $id );
		$this->created['posts'][] = $id;
		$conversations->title_from_first_message( $id, $question );
		( new Thread() )->record(
			$id,
			array(
				array(
					'role'    => 'user',
					'content' => $question,
				),
			),
			self::STREAM
		);
		return $id;
	}

	/**
	 * One request to the conversation routes.
	 *
	 * @param string               $method HTTP method.
	 * @param int                  $id     Conversation post ID.
	 * @param string               $suffix Path after the id.
	 * @param array<string, mixed> $body   Parameters.
	 */
	private function call( string $method, int $id, string $suffix = '', array $body = array() ): \WP_REST_Response {
		$request = new WP_REST_Request( $method, '/linker-ai/v1/genie/conversations/' . $id . $suffix );
		foreach ( $body as $key => $value ) {
			$request->set_param( $key, $value );
		}
		return rest_ensure_response( rest_do_request( $request ) );
	}
}
