<?php
/**
 * Integration test: "Let Linker contact me" from the contact card's route to
 * the Outbox queue.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Tests\Fixtures\GenieVerificationFixture;
use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;

use Linker\Commerce\Genie\Module;
use Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail;
use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Settings\Options;
use Linker\Tools\Genie\ContactRequest;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\RateLimit;
use Linker\Tools\Genie\Thread;
use WC_Order;
use WP_REST_Request;
use WP_REST_Response;

/**
 * The instance's linker-tools route (ContactRequest) and this plugin's door for
 * messages (#246: Inquiry\Sender::message() — the record, the team mail with
 * the Genie hand-off, the customer's receipt under the receipt cap) together,
 * as the site runs them (#243, docs/specs/13-genie.md goal 6, A5 and A6). The
 * routing and the content are read from the Outbox queue (AGENTS.md §5, test
 * mail rule): the minute quota is full, so each mail is stored as a queue row
 * instead of being sent.
 *
 * @coversNothing
 */
final class GenieContactTest extends IntegrationTestCase {

	/** Typed local service with native consumers.
	 *
	 * @var NormalMailAuthorizationFixture
	 */
	private NormalMailAuthorizationFixture $authorization;

	/**
	 * The default internal recipient (Options::DEFAULT_NOTIFY_TO).
	 */
	private const INTERNAL = 'sales@sunriverinverter.com';

	/**
	 * The limiters this test takes places of: the contact door's, and #246's
	 * receipts (ReceiptLimit). Their rows are put back as they were.
	 */
	private const LIMITS = array(
		// Linker\Tools\Genie\RateLimit::PREFIX . 'genie_contact': written out,
		// because the unit run (no WordPress, no linker-tools) loads this class.
		'linker_tools_limit_genie_contact',
		\Linker\Commerce\Inquiry\RateLimit::PREFIX . 'public_receipts',
	);

	/**
	 * The conversation of the test.
	 *
	 * @var int
	 */
	private int $conversation = 0;

	/**
	 * Settings as live has them, the minute quota full, a connection of its own.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->use_empty_mail_queue();
		require_once dirname( __DIR__, 2 ) . '/fixtures/GenieVerificationFixture.php';
		GenieVerificationFixture::install( $this->later( ... ) );
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$this->authorization = NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
		if ( ! class_exists( ContactRequest::class ) ) {
			$this->markTestSkipped( 'linker-tools is not active on this instance.' );
		}
		WC()->mailer();
		$saved = array();
		foreach ( array( Options::NOTIFY_TO, Options::NOTIFY_FROM, Options::NOTIFY_BCC, 'woocommerce_' . NewInquiryEmail::ID . '_settings', 'woocommerce_' . InquiryReceivedEmail::ID . '_settings' ) as $name ) {
			$saved[ $name ] = get_option( $name );
		}
		$counters = self::counters();
		$started  = gmdate( 'Y-m-d H:i:s', time() - 1 );
		// Every test starts with fresh limits; the instance's own counts come back afterwards.
		self::clear_limits();
		$address = '192.0.2.' . wp_rand( 1, 254 );
		// phpcs:disable WordPress.Security.ValidatedSanitizedInput -- kept as they are, to be put back as they were.
		$cookie  = $_COOKIE[ Conversations::COOKIE ] ?? null;
		$browser = $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? null;
		$server  = $_SERVER['REMOTE_ADDR'] ?? null;
		// phpcs:enable
		$this->later(
			function () use ( $saved, $counters, $cookie, $browser, $server, $started ): void {
				// The records this test's requests made (#246's contact records).
				foreach ( self::records( $started ) as $record ) {
					$record->delete( true );
				}
				foreach ( $saved as $name => $value ) {
					false === $value ? delete_option( $name ) : update_option( $name, $value );
				}
				// The contact limits' rows as they were: the site's day counter
				// counts on, this test's connection leaves none.
				global $wpdb;
				self::clear_limits();
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
		delete_option( 'woocommerce_' . NewInquiryEmail::ID . '_settings' );
		delete_option( 'woocommerce_' . InquiryReceivedEmail::ID . '_settings' );
		update_option( Options::NOTIFY_BCC, 'copy-' . self::tag() . '@example.test' );
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
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
	 * Both plugins name one filter: linker-tools asks what this plugin answers.
	 */
	public function test_both_plugins_name_the_same_filter(): void {
		$this->assertSame( ContactRequest::CONTACT_FILTER, Module::CONTACT_FILTER );
		$this->assertNotFalse( has_filter( Module::CONTACT_FILTER ) );
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
				'email'  => $guest,
				...self::fields(),
				'reason' => 'asked',
				'locale' => 'de',
				'page'   => array(
					'type'  => 'product',
					'url'   => home_url( '/de/produkt/saj-h2-10k-t3/' ),
					'title' => 'SAJ H2-10K-T3',
				),
			)
		);

		$this->assertSame( 200, $response->get_status(), (string) ( $response->get_data()['code'] ?? '' ) );
		$this->assertSame(
			array(
				'sent'    => true,
				'email'   => $guest,
				'receipt' => null,
			),
			$response->get_data()
		);
		// One record: #246's contact message, the hand-off on it.
		$record = $this->record( $guest );
		$this->assertSame( 'linker_contact', $record->get_created_via() );
		$this->assertSame( 'contact', $record->get_meta( '_linker_inquiry_source' ) );
		$this->assertSame( 'Can I talk to a person?', $record->get_customer_note() );
		$this->assertSame( $this->conversation, $record->get_meta( Module::HANDOFF_META )['conversation']['id'] );
		// The team mail (#246's, to the internal recipient) and the receipt.
		$this->authorization->drain();
		$rows = $this->jobs_after( $marker );
		$this->assertCount( 2, $rows, 'the team mail and the receipt' );
		$team = $this->row_to( $rows, self::INTERNAL );
		$row  = $team;
		$this->assertSame( 'New inquiry #' . $record->get_order_number() . ' from ' . $guest, $row['subject'] );
		$this->assertContains( 'Bcc: ' . get_option( Options::NOTIFY_BCC ), $row['headers'] );
		$this->assertContains( 'From: Linker <' . self::INTERNAL . '>', $row['headers'] );
		$this->assertNotEmpty( array_filter( $row['headers'], static fn ( string $line ): bool => str_starts_with( $line, 'Reply-to:' ) && str_contains( $line, $guest ) ) );
		$receipt = $this->row_to( $rows, $guest );
		$this->assertStringContainsString( '#' . $record->get_order_number(), $receipt['subject'] );
		// The record carries the page's language, which #246's receipt is written in.
		$this->assertSame( 'de_DE_formal', $record->get_meta( \Linker\Commerce\Inquiry\OrderLocale::META ) );
		$body = html_entity_decode( $row['body'] );
		// The whole conversation, in the admin.
		$this->assertStringContainsString( admin_url( 'admin.php?page=linker-genie-quality&conversation=' . $this->conversation ), $body );
		$this->assertStringContainsString( 'Open the conversation', $body );
		// #246's team mail names the door: Genie, not the contact form.
		$this->assertStringContainsString( 'Through Genie', $body );
		$this->assertStringNotContainsString( 'Contact form', $body );
		// Why, and the summary, latest first.
		$this->assertStringContainsString( 'Asked to talk to a person', $body );
		$this->assertMatchesRegularExpression( '/Can I talk to a person\?.*Which battery fits the SAJ H2-10K-T3\?/s', $body );
		// The page.
		$this->assertStringContainsString( home_url( '/de/produkt/saj-h2-10k-t3/' ), $body );
		$this->assertStringContainsString( 'SAJ H2-10K-T3', $body );
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
		$this->assertSame( $record->get_id(), $notes[0]['order'] );
		$this->assertNull( $notes[0]['receipt'] );
	}



	/**
	 * A guest who did not give the consent the site's public doors ask for is
	 * refused, and nothing is recorded or sent.
	 */
	public function test_a_guest_without_consent_is_refused(): void {
		$this->thread( 'Can I talk to a person?' );
		$guest  = 'linker-it-' . self::tag() . '@example.test';
		$marker = self::newest_mail_job();
		$fields = self::fields();
		unset( $fields['consent'] );
		$response = $this->send( array( 'email' => $guest ) + $fields );
		$this->assertSame( 400, $response->get_status() );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
		$this->assertSame( array(), wc_get_orders( array( 'billing_email' => $guest ) ) );
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

		$this->assertSame( 200, $response->get_status(), (string) ( $response->get_data()['code'] ?? '' ) );
		$record = $this->record( $customer->get_billing_email() );
		$this->assertSame( $customer->get_id(), $record->get_customer_id() );
		$this->authorization->drain();
		$rows = $this->jobs_after( $marker );
		$this->assertCount( 2, $rows, 'the team mail and the receipt' );
		$team = $this->row_to( $rows, self::INTERNAL );
		$this->assertNotEmpty( array_filter( $team['headers'], static fn ( string $line ): bool => str_starts_with( $line, 'Reply-to:' ) && str_contains( $line, $customer->get_billing_email() ) ) );
		$body = html_entity_decode( $team['body'] );
		$this->assertStringContainsString( 'Seemed frustrated or wanted a person', $body );
		$this->assertStringContainsString( 'No products in the solution draft.', $body );
		$this->row_to( $rows, $customer->get_billing_email() );
	}

	/**
	 * A filled honeypot is answered like a delivery and sends nothing.
	 */
	public function test_a_filled_honeypot_sends_nothing(): void {
		$this->thread( 'Can I talk to a person?' );
		$marker   = self::newest_mail_job();
		$response = $this->send(
			array(
				...self::fields(),
				'email'   => 'bot@example.test',
				'website' => 'https://spam.example',
			)
		);
		$this->assertSame( 200, $response->get_status(), (string) ( $response->get_data()['code'] ?? '' ) );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
		$this->assertSame( array(), get_post_meta( $this->conversation, ContactRequest::NOTE, false ) );
	}

	/** An anonymous transfer without a widget response cannot send mail or create an inquiry. */
	public function test_transfer_requires_the_native_widget_response(): void {
		$this->thread( 'Can the team help me choose a battery?' );
		$marker   = self::newest_mail_job();
		$response = $this->send(
			array(
				'email'   => 'linker-it-' . self::tag() . '@example.test',
				'consent' => '1',
			)
		);
		$this->assertSame( 400, $response->get_status() );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
	}

	/** A second tab that still shows the earlier turn cannot send the later conversation. */
	public function test_earlier_card_asks_customer_to_retry_after_a_new_turn(): void {
		$this->thread( 'Can I talk to a person?' );
		$state = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/contact' ) )->get_data();
		$this->thread( 'Can I talk to a person?', 'I need storage for another site.' );
		$latest = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/contact' ) )->get_data();
		$this->assertNotSame( $state['source'], $latest['source'] );
		$marker = self::newest_mail_job();
		$result = $this->send(
			array(
				'email'  => 'linker-it-' . self::tag() . '@example.test',
				'source' => $state['source'],
			) + self::fields()
		);
		$this->assertSame( 409, $result->get_status() );
		$this->assertSame( 'linker_genie_contact_retry', $result->get_data()['code'] );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
	}

	/**
	 * The same request twice, with nothing said in between, reaches the team
	 * once; the card is told it is already with the team.
	 */
	public function test_the_same_request_twice_is_sent_once(): void {
		$this->thread( 'Can I talk to a person?' );
		$params = array(
			'email' => 'linker-it-' . self::tag() . '@example.test',
			...self::fields(),
		);
		$marker = self::newest_mail_job();
		$first  = $this->send( $params );
		delete_post_meta( $this->conversation, ContactRequest::NOTE );
		$params['cf-turnstile-response'] = ''; // The first submission already redeemed its single-use token.
		$second                          = $this->send( $params );
		$this->assertSame( array( 200, 200 ), array( $first->get_status(), $second->get_status() ) );
		// Once: one team mail and one receipt.
		$this->authorization->drain();
		$this->assertCount( 2, $this->jobs_after( $marker ) );
		$this->deliver_fixed_receipt( $this->record( $params['email'] ) );
		$after = $this->send( $params );
		$this->assertTrue( $after->get_data()['receipt'] );
		$this->assertCount( 1, $this->jobs_after( $marker ), 'Only the original team notification remains queued.' );
		$state = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/contact' ) );
		$this->assertSame(
			array(
				'email'   => $params['email'],
				'receipt' => true,
			),
			$state->get_data()['sent']
		);
	}

	/** A lost acknowledgement can be recovered after another tab opens a newer turn. */
	public function test_recover_original_contact_after_a_new_turn(): void {
		$this->thread( 'Can I talk to a person?' );
		$state  = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/contact' ) )->get_data();
		$params = array(
			'email'  => 'linker-it-' . self::tag() . '@example.test',
			'source' => $state['source'],
		) + self::fields();
		$first  = $this->send( $params );
		$this->assertSame( 200, $first->get_status(), (string) ( $first->get_data()['code'] ?? '' ) );
		$original = $this->record( $params['email'] );
		$this->thread( 'Can I talk to a person?', 'Tell me about storage.' );
		delete_post_meta( $this->conversation, ContactRequest::NOTE );
		$params['cf-turnstile-response'] = '';
		$recovered                       = $this->send( $params );
		$this->assertSame( 200, $recovered->get_status(), (string) ( $recovered->get_data()['code'] ?? '' ) );
		$notes = get_post_meta( $this->conversation, ContactRequest::NOTE, false );
		$this->assertCount( 1, $notes );
		$this->assertSame( $original->get_id(), $notes[0]['order'] );
		$this->assertSame( $state['source'], $notes[0]['source'] );
		$this->assertSame( 1, $notes[0]['messages'] );
	}

	/**
	 * The reason's label is the staff's, in the site's language, whatever page
	 * the customer asked from (review round 1 of #243: one place for the labels).
	 */
	public function test_the_reason_reaches_the_team_in_the_site_language(): void {
		$this->thread( 'Ich möchte mit einem Mitarbeiter sprechen' );
		$marker = self::newest_mail_job();
		$this->assertTrue( switch_to_locale( 'de_DE_formal' ) );
		try {
			$this->assertSame( 'Wollte mit einem Menschen sprechen', ContactRequest::reason_label( 'asked' ) );
			$response = $this->send(
				array(
					'email'  => 'linker-it-' . self::tag() . '@example.test',
					'locale' => 'de',
				) + self::fields()
			);
		} finally {
			restore_previous_locale();
		}
		$this->assertSame( 200, $response->get_status(), (string) ( $response->get_data()['code'] ?? '' ) );
		$this->authorization->drain();
		$team = $this->row_to( $this->jobs_after( $marker ), self::INTERNAL );
		$this->assertStringContainsString( 'Asked to talk to a person', html_entity_decode( $team['body'] ) );
		$this->assertSame( 'Asked to talk to a person', get_post_meta( $this->conversation, ContactRequest::NOTE, false )[0]['label'] );
	}

	/**
	 * The sent card is part of the conversation (review round 1 of #243):
	 * the stored thread names it after the answer that showed it, so later
	 * turns and a reload show it in the history.
	 */
	public function test_the_sent_card_stays_in_the_conversation(): void {
		$this->thread( 'Which battery fits the SAJ H2-10K-T3?', 'Can I talk to a person?' );
		$guest = 'linker-it-' . self::tag() . '@example.test';
		$this->assertSame( 200, $this->send( array( 'email' => $guest ) + self::fields() )->get_status() );
		$stored = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/conversation' ) )->get_data();
		// Three stored messages: the card followed the answer at index 3.
		$this->assertSame(
			array(
				array(
					'after'   => 3,
					'email'   => $guest,
					'receipt' => null,
				),
			),
			$stored['contacts']
		);
		$this->authorization->drain();
		$this->deliver_fixed_receipt( $this->record( $guest ) );
		$fresh = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/conversation' ) )->get_data();
		$this->assertTrue( $fresh['contacts'][0]['receipt'], 'Fresh history reads the delivered receipt.' );
		$current = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/contact' ) )->get_data();
		$this->assertTrue( $current['sent']['receipt'] );
	}



	/**
	 * The one queue row to an address.
	 *
	 * @param list<array{subject: string, to: list<string>, headers: list<string>, body: string}> $rows    Queue rows.
	 * @param string                                                                              $address The recipient.
	 * @return array{subject: string, to: list<string>, headers: list<string>, body: string}
	 */
	private function row_to( array $rows, string $address ): array {
		$found = array_values( array_filter( $rows, static fn ( array $row ): bool => array( $address ) === $row['to'] ) );
		$this->assertCount( 1, $found, "one row to {$address}" );
		return $found[0];
	}

	/**
	 * The one contact record of an address.
	 *
	 * @param string $email Billing email.
	 */
	private function record( string $email ): WC_Order {
		$records = wc_get_orders(
			array(
				'billing_email' => $email,
				'limit'         => -1,
			)
		);
		$this->assertIsArray( $records );
		$this->assertCount( 1, $records );
		$this->assertInstanceOf( WC_Order::class, $records[0] );
		return $records[0];
	}

	/**
	 * The contact records made since a moment (GMT).
	 *
	 * @param string $since GMT date and time.
	 * @return list<WC_Order>
	 */
	private static function records( string $since ): array {
		$found = wc_get_orders(
			array(
				'created_via'  => 'linker_contact',
				'date_created' => '>=' . strtotime( $since . ' UTC' ),
				'limit'        => -1,
			)
		);
		return array_values( array_filter( is_array( $found ) ? $found : array(), static fn ( WC_Order $order ): bool => is_array( $order->get_meta( Module::HANDOFF_META ) ) ) );
	}

	/** Native anonymous form fields with Cloudflare's official integration-test response.
	 *
	 * @return array<string,string>
	 */
	private static function fields(): array {
		return array(
			'website'               => '',
			'cf-turnstile-response' => 'XXXX.DUMMY.TOKEN.XXXX',
			'consent'               => '1',
		);
	}

	/**
	 * Deletes the rows of LIMITS.
	 */
	private static function clear_limits(): void {
		global $wpdb;
		foreach ( self::LIMITS as $limit ) {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows (RateLimit::take()).
			$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( $limit ) . '%' ) );
		}
	}

	/**
	 * The contact limits' rows as they are now (RateLimit::PREFIX).
	 *
	 * @return array<string, string> Value by option name.
	 */
	private static function counters(): array {
		global $wpdb;
		$found = array();
		foreach ( self::LIMITS as $limit ) {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the limiter's own rows, never loaded through the options API.
			$rows = $wpdb->get_results( $wpdb->prepare( "SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( $limit ) . '%' ), ARRAY_A );
			foreach ( (array) $rows as $row ) {
				$found[ (string) $row['option_name'] ] = (string) $row['option_value'];
			}
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
		$stream = "event: block\ndata: " . wp_json_encode(
			array(
				'type' => 'text',
				'text' => 'An answer.',
			)
		) . "\n\nevent: done\ndata: {}\n\n";
		$this->assertTrue( ( new Thread() )->record( $this->conversation, $messages, $stream ) );
	}

	/**
	 * POSTs the contact card's request through the REST server.
	 *
	 * @param array<string, mixed> $params Body.
	 */
	private function send( array $params ): WP_REST_Response {
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/contact' );
		$source  = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/contact' ) );
		$params += array( 'source' => $source->get_data()['source'] ?? '' );
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
