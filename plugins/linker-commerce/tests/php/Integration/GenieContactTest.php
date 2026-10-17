<?php
/**
 * Integration test: "Let Linker contact me" from the contact card's route to
 * the Outbox queue.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Genie\ContactEmail;
use Linker\Commerce\Genie\Module;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Settings\Options;
use Linker\Tools\Genie\ContactGuard;
use Linker\Tools\Genie\ContactRequest;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\RateLimit;
use Linker\Tools\Genie\Thread;
use WP_REST_Request;
use WP_REST_Response;

/**
 * The instance's linker-tools route (ContactRequest) and this plugin's team
 * mail (Genie\ContactEmail) together, as the site runs them (#243,
 * docs/specs/13-genie.md goal 6, A5 and A6). The routing and the content are
 * read from the Outbox queue (AGENTS.md §5, test mail rule): the minute quota
 * is full, so each mail is stored as a queue row instead of being sent.
 *
 * @coversNothing
 */
final class GenieContactTest extends IntegrationTestCase {

	/**
	 * The default internal recipient (Options::DEFAULT_NOTIFY_TO).
	 */
	private const INTERNAL = 'sales@sunriverinverter.com';

	/**
	 * The conversation of the test.
	 *
	 * @var int
	 */
	private int $conversation = 0;

	/**
	 * The test's connection: a TEST-NET address (RFC 5737), its own counters.
	 *
	 * @var string
	 */
	private string $address = '';

	/**
	 * Settings as live has them, the minute quota full, a connection of its own.
	 */
	protected function setUp(): void {
		parent::setUp();
		if ( ! class_exists( ContactRequest::class ) ) {
			$this->markTestSkipped( 'linker-tools is not active on this instance.' );
		}
		WC()->mailer();
		$saved = array();
		foreach ( array( Options::NOTIFY_TO, Options::NOTIFY_FROM, Options::NOTIFY_BCC, 'woocommerce_' . ContactEmail::ID . '_settings' ) as $name ) {
			$saved[ $name ] = get_option( $name );
		}
		$counters      = self::counters();
		$address       = '192.0.2.' . wp_rand( 1, 254 );
		$this->address = $address;
		// phpcs:disable WordPress.Security.ValidatedSanitizedInput -- kept as they are, to be put back as they were.
		$cookie  = $_COOKIE[ Conversations::COOKIE ] ?? null;
		$browser = $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? null;
		$server  = $_SERVER['REMOTE_ADDR'] ?? null;
		// phpcs:enable
		$this->later(
			function () use ( $saved, $counters, $cookie, $browser, $server ): void {
				foreach ( $saved as $name => $value ) {
					false === $value ? delete_option( $name ) : update_option( $name, $value );
				}
				// The contact limits' rows as they were: the site's day counter
				// counts on, this test's connection leaves none.
				global $wpdb;
				// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows (RateLimit::take()).
				$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( RateLimit::PREFIX . 'genie_contact' ) . '%' ) );
				foreach ( $counters as $name => $value ) {
					// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- puts back the rows counters() read.
					$wpdb->query( $wpdb->prepare( "INSERT INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, %s, 'off')", $name, $value ) );
				}
				if ( $this->conversation > 0 ) {
					wp_delete_post( $this->conversation, true );
				}
				foreach ( array(
					Conversations::COOKIE         => $cookie,
					Conversations::BROWSER_COOKIE => $browser,
				) as $name => $value ) {
					if ( null === $value ) {
						unset( $_COOKIE[ $name ] );
					} else {
						$_COOKIE[ $name ] = $value;
					}
				}
				if ( null === $server ) {
					unset( $_SERVER['REMOTE_ADDR'] );
				} else {
					$_SERVER['REMOTE_ADDR'] = $server;
				}
				if ( function_exists( 'WC' ) && null !== WC()->cart ) {
					WC()->cart->empty_cart();
				}
			}
		);
		delete_option( Options::NOTIFY_TO );
		delete_option( Options::NOTIFY_FROM );
		delete_option( 'woocommerce_' . ContactEmail::ID . '_settings' );
		update_option( Options::NOTIFY_BCC, 'copy-' . self::tag() . '@example.test' );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$_SERVER['REMOTE_ADDR'] = $address;
		unset( $_COOKIE[ Conversations::COOKIE ], $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		$this->as_user( 0 );
		// The cookie lives in $_COOKIE (Conversations::set_cookie()); a header
		// cannot be sent from the command line once PHPUnit has printed.
		global $wp_filter;
		$listeners = array();
		foreach ( array( Conversations::COOKIE_ACTION, Conversations::BROWSER_ACTION ) as $hook ) {
			$listeners[ $hook ] = $wp_filter[ $hook ] ?? null;
			remove_all_actions( $hook );
		}
		$this->later(
			static function () use ( $listeners ): void {
				global $wp_filter;
				foreach ( $listeners as $hook => $listener ) {
					if ( null !== $listener ) {
						$wp_filter[ $hook ] = $listener; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- puts back what setUp() took away.
					}
				}
			}
		);
	}

	/**
	 * Both plugins name one action: linker-tools fires what this plugin listens to.
	 */
	public function test_both_plugins_name_the_same_action(): void {
		$this->assertSame( ContactRequest::ACTION, Module::ACTION );
		$this->assertNotFalse( has_action( Module::ACTION ) );
	}

	/**
	 * A guest's request reaches the internal recipient with the whole hand-off:
	 * the link to the conversation, the summary, the page and the solution
	 * draft (A6), and nothing goes to the address the guest typed.
	 */
	public function test_a_guest_request_reaches_the_team_with_the_whole_hand_off(): void {
		$product = $this->product( '1000' );
		$product->set_sku( 'LINKER-IT-' . strtoupper( self::tag() ) );
		$product->save();
		$this->thread( 'Which battery fits the SAJ H2-10K-T3?', 'Can I talk to a person?' );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), 2 ) );
		$guest  = 'linker-it-' . self::tag() . '@example.test';
		$marker = self::newest_mail_job();

		$response = $this->send(
			array(
				'email'   => $guest,
				'started' => ( new ContactGuard() )->started( time() - 10 ),
				'reason'  => 'asked',
				'locale'  => 'de',
				'page'    => array(
					'type'  => 'product',
					'url'   => home_url( '/de/produkt/saj-h2-10k-t3/' ),
					'title' => 'SAJ H2-10K-T3',
				),
			)
		);

		$this->assertSame( 200, $response->get_status() );
		$this->assertSame(
			array(
				'sent'  => true,
				'email' => $guest,
			),
			$response->get_data()
		);
		$rows = $this->jobs_after( $marker );
		$this->assertCount( 1, $rows, 'one team mail, no mail to the guest' );
		$row = $rows[0];
		$this->assertSame( 'Contact request from ' . $guest . ' via Genie', $row['subject'] );
		$this->assertSame( array( self::INTERNAL ), $row['to'] );
		$this->assertContains( 'Bcc: ' . get_option( Options::NOTIFY_BCC ), $row['headers'] );
		$this->assertContains( 'From: Linker <' . self::INTERNAL . '>', $row['headers'] );
		$this->assertContains( 'Reply-to: ' . $guest, $row['headers'] );
		$body = html_entity_decode( $row['body'] );
		// The whole conversation, in the admin.
		$this->assertStringContainsString( admin_url( 'admin.php?page=linker-genie-quality&conversation=' . $this->conversation ), $body );
		$this->assertStringContainsString( 'Open the conversation', $body );
		// Why, and the summary, latest first.
		$this->assertStringContainsString( 'Asked to talk to a person', $body );
		$this->assertMatchesRegularExpression( '/Can I talk to a person\?.*Which battery fits the SAJ H2-10K-T3\?/s', $body );
		// The page.
		$this->assertStringContainsString( home_url( '/de/produkt/saj-h2-10k-t3/' ), $body );
		$this->assertStringContainsString( 'SAJ H2-10K-T3', $body );
		$this->assertStringContainsString( '>DE<', $body );
		// The solution draft, line by line.
		$this->assertStringContainsString( $product->get_name(), $body );
		$this->assertStringContainsString( $product->get_sku(), $body );
		$this->assertMatchesRegularExpression( '/' . preg_quote( $product->get_sku(), '/' ) . '<\/td>\s*<td[^>]*>2<\/td>/', $body );
		$this->assertStringContainsString( 'within one business day', $body );
		// The note on the conversation.
		$notes = get_post_meta( $this->conversation, ContactRequest::NOTE, false );
		$this->assertCount( 1, $notes );
		$this->assertSame( $guest, $notes[0]['email'] );
		$this->assertSame( 'asked', $notes[0]['reason'] );
	}

	/**
	 * A signed-in customer sends without an address: the account's is used,
	 * and the card is told so before it shows (A5).
	 */
	public function test_a_signed_in_customer_is_not_asked_for_an_address(): void {
		$customer = $this->customer();
		$this->as_user( $customer->get_id() );
		$this->thread( 'This is not what I asked.' );
		$state = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/contact' ) );
		$this->assertSame( $customer->get_billing_email(), $state->get_data()['email'] );
		// A refusal names the mailbox customers see, never the internal one.
		$this->assertSame( ( new Options() )->team_mailbox(), $state->get_data()['mailbox'] );
		$this->assertNotSame( self::INTERNAL, $state->get_data()['mailbox'] );
		$marker = self::newest_mail_job();

		$response = $this->send( array( 'reason' => 'dissatisfied' ) );

		$this->assertSame( 200, $response->get_status() );
		$rows = $this->jobs_after( $marker );
		$this->assertCount( 1, $rows );
		$this->assertSame( array( self::INTERNAL ), $rows[0]['to'] );
		$this->assertContains( 'Reply-to: Maria Beispiel <' . $customer->get_billing_email() . '>', $rows[0]['headers'] );
		$body = html_entity_decode( $rows[0]['body'] );
		$this->assertStringContainsString( 'Seemed frustrated or wanted a person', $body );
		$this->assertStringContainsString( 'Open the customer', $body );
		$this->assertStringContainsString( 'No products in the solution draft.', $body );
	}

	/**
	 * A filled honeypot is answered like a delivery and sends nothing.
	 */
	public function test_a_filled_honeypot_sends_nothing(): void {
		$this->thread( 'Can I talk to a person?' );
		$marker   = self::newest_mail_job();
		$response = $this->send(
			array(
				'email'   => 'bot@example.test',
				'website' => 'https://spam.example',
				'started' => ( new ContactGuard() )->started( time() - 10 ),
			)
		);
		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
		$this->assertSame( array(), get_post_meta( $this->conversation, ContactRequest::NOTE, false ) );
	}

	/**
	 * A start time this site did not sign, or a request sooner than the
	 * floor, is refused and sends nothing.
	 *
	 * @testWith ["forged"]
	 *           ["early"]
	 *
	 * @param string $kind Which start time.
	 */
	public function test_a_request_without_a_valid_start_time_is_refused( string $kind ): void {
		$this->thread( 'Can I talk to a person?' );
		$marker   = self::newest_mail_job();
		$response = $this->send(
			array(
				'email'   => 'linker-it-' . self::tag() . '@example.test',
				'started' => 'forged' === $kind ? ( time() - 10 ) . '.forged' : ( new ContactGuard() )->started(),
			)
		);
		$this->assertSame( 400, $response->get_status() );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
	}

	/**
	 * One connection gets LIMIT requests an hour; the next is refused, not queued.
	 */
	public function test_the_connection_limit_refuses_the_next_request(): void {
		$marker = self::newest_mail_job();
		for ( $i = 1; $i <= ContactGuard::LIMIT + 1; $i++ ) {
			$this->thread( "Question {$i}: can someone call me back?" );
			$response = $this->send(
				array(
					'email'   => "linker-it-{$i}-" . self::tag() . '@example.test',
					'started' => ( new ContactGuard() )->started( time() - 10 ),
				)
			);
			$this->assertSame( $i <= ContactGuard::LIMIT ? 200 : 429, $response->get_status(), "request {$i}" );
			wp_delete_post( $this->conversation, true );
			$this->conversation = 0;
			unset( $_COOKIE[ Conversations::COOKIE ], $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		}
		$this->assertCount( ContactGuard::LIMIT, $this->jobs_after( $marker ) );
	}

	/**
	 * When the site's day is full, the request is refused and nothing is queued.
	 */
	public function test_the_daily_cap_refuses_and_queues_nothing(): void {
		$day = new RateLimit( 'genie_contact_day', ContactGuard::DAILY, DAY_IN_SECONDS );
		while ( $day->take( '' ) ) {
			// Fill the site's day; setUp() puts its count back afterwards.
			continue;
		}
		$this->thread( 'Can I talk to a person?' );
		$marker   = self::newest_mail_job();
		$response = $this->send(
			array(
				'email'   => 'linker-it-' . self::tag() . '@example.test',
				'started' => ( new ContactGuard() )->started( time() - 10 ),
			)
		);
		$this->assertSame( 429, $response->get_status() );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
	}

	/**
	 * The same request twice, with nothing said in between, reaches the team
	 * once; the card is told it is already with the team.
	 */
	public function test_the_same_request_twice_is_sent_once(): void {
		$this->thread( 'Can I talk to a person?' );
		$params = array(
			'email'   => 'linker-it-' . self::tag() . '@example.test',
			'started' => ( new ContactGuard() )->started( time() - 10 ),
		);
		$marker = self::newest_mail_job();
		$first  = $this->send( $params );
		$second = $this->send( $params );
		$this->assertSame( array( 200, 200 ), array( $first->get_status(), $second->get_status() ) );
		$this->assertCount( 1, $this->jobs_after( $marker ) );
		$state = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/contact' ) );
		$this->assertSame( array( 'email' => $params['email'] ), $state->get_data()['sent'] );
	}

	/**
	 * Requests at the same moment cannot share the last place: ten processes
	 * take one connection's places at once, and exactly LIMIT get one.
	 */
	public function test_the_connection_limit_holds_under_concurrent_requests(): void {
		$address   = $this->address;
		$root      = (string) getenv( 'LINKER_WP_ROOT' );
		$script    = sprintf(
			'define("WP_USE_THEMES", false); $_SERVER["HTTP_HOST"]="localhost"; $_SERVER["REQUEST_URI"]="/"; require %s; echo "" === ( new Linker\Tools\Genie\ContactGuard() )->take( %s ) ? "taken" : "full";',
			var_export( $root . '/wp-load.php', true ), // phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_var_export -- builds the child's PHP source.
			var_export( $address, true ) // phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_var_export -- builds the child's PHP source.
		);
		$ini       = php_ini_loaded_file();
		$processes = array();
		for ( $i = 0; $i < 10; $i++ ) {
			$command = array( PHP_BINARY );
			if ( is_string( $ini ) ) {
				array_push( $command, '-c', $ini );
			}
			array_push( $command, '-r', $script );
			// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- the concurrency is the point of the test.
			$process = proc_open( $command, array( 1 => array( 'pipe', 'w' ) ), $pipes );
			$this->assertIsResource( $process );
			$processes[] = array( $process, $pipes[1] );
		}
		$answers = array();
		foreach ( $processes as [ $process, $out ] ) {
			$answers[] = trim( (string) stream_get_contents( $out ) );
			fclose( $out ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- a process pipe.
			proc_close( $process );
		}
		// Each process took one place of the site's day too: setUp() puts the count back.
		$this->assertSame( ContactGuard::LIMIT, count( array_keys( $answers, 'taken', true ) ), implode( ',', $answers ) );
		$this->assertSame( 10 - ContactGuard::LIMIT, count( array_keys( $answers, 'full', true ) ) );
	}

	/**
	 * The contact limits' rows as they are now (RateLimit::PREFIX).
	 *
	 * @return array<string, string> Value by option name.
	 */
	private static function counters(): array {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows, never loaded through the options API.
		$rows  = $wpdb->get_results( $wpdb->prepare( "SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( RateLimit::PREFIX . 'genie_contact' ) . '%' ), ARRAY_A );
		$found = array();
		foreach ( (array) $rows as $row ) {
			$found[ (string) $row['option_name'] ] = (string) $row['option_value'];
		}
		return $found;
	}

	/**
	 * A conversation of this visitor with the customer messages given and an
	 * answer between them, as the proxy stores an answered turn.
	 *
	 * @param string ...$customer The customer's messages, oldest first.
	 */
	private function thread( string ...$customer ): void {
		if ( $this->conversation < 1 ) {
			$this->conversation = ( new Conversations() )->open();
			$this->assertGreaterThan( 0, $this->conversation );
		}
		$messages = array();
		foreach ( $customer as $text ) {
			if ( array() !== $messages ) {
				$messages[] = array(
					'role'    => 'assistant',
					'content' => 'An answer.',
				);
			}
			$messages[] = array(
				'role'    => 'user',
				'content' => $text,
			);
		}
		( new Thread() )->record( $this->conversation, $messages, '' );
	}

	/**
	 * POSTs the contact card's request through the REST server.
	 *
	 * @param array<string, mixed> $params Body.
	 */
	private function send( array $params ): WP_REST_Response {
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/contact' );
		foreach ( $params as $name => $value ) {
			$request->set_param( $name, $value );
		}
		$response = rest_do_request( $request );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		return $response;
	}

	/**
	 * The queue rows written after $marker (isolate_mail() removes them afterwards).
	 *
	 * @param int $marker The newest row id before the test.
	 * @return list<array{subject: string, to: list<string>, headers: list<string>, body: string}>
	 */
	private function jobs_after( int $marker ): array {
		$rows = array();
		foreach ( self::mail_jobs_after( $marker ) as $id ) {
			$data   = json_decode( (string) get_post_meta( $id, '_linker_mail_message', true ), true );
			$data   = is_array( $data ) ? $data : array();
			$rows[] = array(
				'subject' => (string) ( $data['subject'] ?? '' ),
				'to'      => array_values( array_map( 'strval', (array) ( $data['to'] ?? array() ) ) ),
				'headers' => array_values( array_map( 'strval', (array) ( $data['headers'] ?? array() ) ) ),
				'body'    => (string) ( $data['body'] ?? '' ),
			);
		}
		return $rows;
	}
}
