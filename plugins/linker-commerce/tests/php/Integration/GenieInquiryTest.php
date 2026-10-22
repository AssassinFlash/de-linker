<?php
/**
 * Integration test: the Genie inquiry confirmation card (#250) from its route to
 * the Outbox queue.
 *
 * The card is drafted by the conversation and sent through #246's one writer
 * (Inquiry\Sender::request()) — the same Woo record, Proforma gateway, statuses,
 * team mail and receipt the request page makes. Only the card's POST sends; a
 * state read creates nothing (A8). The routing and the content are read from the
 * Outbox queue (AGENTS.md §5, test mail rule): the minute quota is full, so each
 * mail is stored as a queue row instead of being sent.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Genie\Module;
use Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail;
use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\ReceiptLimit;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Settings\Options;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\FormGuard;
use Linker\Tools\Genie\InquiryRequest;
use Linker\Tools\Genie\InquirySummary;
use Linker\Tools\Genie\RateLimit;
use Linker\Tools\Genie\Thread;
use WC_Order;
use WC_Order_Item_Product;
use WC_Product_Simple;
use WP_REST_Request;
use WP_REST_Response;

/**
 * The card's route, from the draft it states to the record it makes.
 *
 * @coversNothing
 */
final class GenieInquiryTest extends IntegrationTestCase {

	/**
	 * The default internal recipient (Options::DEFAULT_NOTIFY_TO).
	 */
	private const INTERNAL = 'sales@sunriverinverter.com';

	/**
	 * The limiters this test takes places of: the card's, and #246's receipts.
	 */
	private const LIMITS = array(
		// Linker\Tools\Genie\RateLimit::PREFIX . 'genie_inquiry': written out,
		// because the unit run (no WordPress, no linker-tools) loads this class.
		'linker_tools_limit_genie_inquiry',
		\Linker\Commerce\Inquiry\RateLimit::PREFIX . 'public_receipts',
	);

	/**
	 * The conversation of the test.
	 *
	 * @var int
	 */
	private int $conversation = 0;

	/**
	 * The summary the conversation filter answers with in this test.
	 *
	 * @var array<string, mixed>
	 */
	private array $summary = array();

	/**
	 * Settings as live has them, the minute quota full, this visitor's own cookies.
	 */
	protected function setUp(): void {
		parent::setUp();
		if ( ! class_exists( InquiryRequest::class ) ) {
			$this->markTestSkipped( 'linker-tools is not active on this instance.' );
		}
		WC()->mailer();
		$saved = array();
		foreach ( array( Options::NOTIFY_TO, Options::NOTIFY_FROM, Options::NOTIFY_BCC, 'woocommerce_' . NewInquiryEmail::ID . '_settings', 'woocommerce_' . InquiryReceivedEmail::ID . '_settings', \Linker\Tools\Genie\Proxy::OPTION ) as $name ) {
			$saved[ $name ] = get_option( $name );
		}
		$counters = self::counters();
		$started  = gmdate( 'Y-m-d H:i:s', time() - 1 );
		// phpcs:disable WordPress.Security.ValidatedSanitizedInput -- kept as they are, to be put back as they were.
		$cookie  = $_COOKIE[ Conversations::COOKIE ] ?? null;
		$browser = $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? null;
		// phpcs:enable
		$summary = &$this->summary;
		$this->later(
			function () use ( $saved, $counters, $cookie, $browser, $started ): void {
				// The inquiries this test's requests made.
				$made = wc_get_orders(
					array(
						'limit'        => -1,
						'created_via'  => 'checkout',
						'date_created' => '>=' . strtotime( $started . ' UTC' ),
					)
				);
				foreach ( is_array( $made ) ? $made : array() as $order ) {
					if ( 'proforma' === $order->get_meta( '_linker_inquiry_source' ) ) {
						$order->delete( true );
					}
				}
				foreach ( $saved as $name => $value ) {
					false === $value ? delete_option( $name ) : update_option( $name, $value );
				}
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
				if ( function_exists( 'WC' ) && null !== WC()->cart ) {
					WC()->cart->empty_cart();
				}
			}
		);
		delete_option( Options::NOTIFY_TO );
		delete_option( Options::NOTIFY_FROM );
		delete_option( 'woocommerce_' . NewInquiryEmail::ID . '_settings' );
		delete_option( 'woocommerce_' . InquiryReceivedEmail::ID . '_settings' );
		// #244's summary is answered by the test, never by the service: the
		// card and the record carry exactly this array.
		delete_option( \Linker\Tools\Genie\Proxy::OPTION );
		update_option( Options::NOTIFY_BCC, 'copy-' . self::tag() . '@example.test' );
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		unset( $_COOKIE[ Conversations::COOKIE ], $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		self::clear_limits();
		$this->as_user( 0 );
		$this->summary = array(
			'summary'    => 'Two inverters and a battery for a rooftop project.',
			'quantities' => array(),
			'conditions' => array( 'Three-phase connection' ),
			'note'       => 'We need them this quarter.',
			'source'     => 'model',
			'reason'     => null,
		);
		$filter        = static function () use ( &$summary ): array {
			return $summary;
		};
		add_filter( InquirySummary::FILTER, $filter );
		$this->later(
			static function () use ( $filter ): void {
				remove_filter( InquirySummary::FILTER, $filter );
			}
		);
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
		$this->assertSame( InquiryRequest::SEND_FILTER, Module::INQUIRY_FILTER );
		$this->assertSame( InquiryRequest::PAGE_FILTER, Module::INQUIRY_PAGE_FILTER );
		$this->assertNotFalse( has_filter( Module::INQUIRY_FILTER ) );
		$this->assertNotFalse( has_filter( Module::INQUIRY_PAGE_FILTER ) );
	}

	/**
	 * A guest sends the card: the record is #246's inquiry, line by line what
	 * the card showed, with the summary the card carried, and the team and the
	 * customer get their mails.
	 */
	public function test_a_guest_sends_the_card_and_the_inquiry_matches_it(): void {
		$product = $this->product( '1000' );
		$product->set_sku( 'LINKER-CARD-' . strtoupper( self::tag() ) );
		$product->save();
		$this->thread( 'Which inverter fits a three-phase rooftop?', 'Please send an inquiry.' );
		$this->cart( array( array( $product, 2 ) ) );
		$this->summary['quantities'] = array(
			array(
				'product_id' => $product->get_id(),
				'quantity'   => 2,
			),
		);
		$guest                       = 'linker-it-' . self::tag() . '@example.test';
		$marker                      = self::newest_mail_job();
		$state                       = $this->state();

		// The card shows every line it will send, and the draft's own price line.
		$this->assertCount( 1, $state['lines'] );
		$this->assertSame( $product->get_id(), $state['lines'][0]['product_id'] );
		$this->assertSame( 2, $state['lines'][0]['quantity'] );
		$this->assertSame( $product->get_name(), $state['lines'][0]['name'] );
		$this->assertSame( ( new \WC_Product( $product->get_id() ) )->get_price_html(), $state['lines'][0]['price_html'] );
		$this->assertSame( $this->summary['note'], $state['message'] );
		$this->assertSame( $this->summary['summary'], $state['summary'] );
		$this->assertTrue( $state['ready'] );
		$this->assertNull( $state['account'] );
		$this->assertNotEmpty( $state['page_url'] );

		$response = $this->send(
			array(
				'name'           => 'Maria Weber',
				'email'          => $guest,
				'company'        => 'Weber Solar',
				'message'        => $this->summary['note'],
				'attach_summary' => '1',
				'lines'          => $state['lines_digest'],
				'locale'         => 'en',
				'page'           => array(
					'type'  => 'draft',
					'url'   => home_url( '/inquiry/' ),
					'title' => 'Send an inquiry',
				),
			) + self::fields()
		);

		$this->assertSame( 200, $response->get_status() );
		$data = $response->get_data();
		$this->assertTrue( $data['sent'] );
		$this->assertSame( $guest, $data['email'] );
		$this->assertSame( $guest, $data['inquiry']['email'] );
		$this->assertSame( Statuses::RECEIVED, $data['inquiry']['status'] );
		$this->assertTrue( $data['inquiry']['receipt'] );
		$this->assertNotEmpty( $data['inquiry']['number'] );
		$this->assertNotEmpty( $data['inquiry']['url'] );

		// The same Woo pipeline as the request page: checkout's record, the
		// Proforma gateway, the inquiry's source and status.
		$record = $this->record( $guest );
		$this->assertSame( $data['inquiry']['order'], $record->get_id() );
		$this->assertSame( 'linker_proforma', $record->get_payment_method() );
		$this->assertSame( 'proforma', $record->get_meta( '_linker_inquiry_source' ) );
		$this->assertSame( Statuses::RECEIVED, $record->get_status() );
		$this->assertSame( $this->summary['note'], $record->get_customer_note() );
		$this->assertSame( 'Weber Solar', $record->get_billing_company() );
		$items = array_values( $record->get_items() );
		$this->assertCount( 1, $items );
		$this->assertInstanceOf( WC_Order_Item_Product::class, $items[0] );
		$this->assertSame( $product->get_id(), $items[0]->get_product_id() );
		$this->assertSame( 2, $items[0]->get_quantity() );
		$this->assertTrue( WC()->cart->is_empty(), 'the solution draft is the inquiry it became' );

		// The summary the card showed is the one the team reads (#244).
		$this->assertSame( $this->summary, $record->get_meta( Sender::SUMMARY_META ) );

		// The team mail and the receipt, looked up in the queue (test mail rule).
		$rows = $this->jobs_after( $marker );
		$this->assertCount( 2, $rows, 'the team mail and the receipt' );
		$team = $this->row_to( $rows, self::INTERNAL );
		$this->assertSame( 'New inquiry #' . $record->get_order_number() . ' from Weber Solar', $team['subject'] );
		$this->assertContains( 'Bcc: ' . get_option( Options::NOTIFY_BCC ), $team['headers'] );
		$body = html_entity_decode( $team['body'] );
		$this->assertStringContainsString( $product->get_name(), $body );
		$this->assertStringContainsString( $product->get_sku(), $body );
		$this->assertStringContainsString( 'Conversation with Genie', $body );
		$this->assertStringContainsString( $this->summary['summary'], $body );
		$this->assertStringContainsString( $this->summary['note'], $body );
		$this->row_to( $rows, $guest );

		// The sent card is part of the conversation, and the record is the state.
		$notes = get_post_meta( $this->conversation, InquiryRequest::NOTE, false );
		$this->assertCount( 1, $notes );
		$this->assertSame( $record->get_id(), $notes[0]['order'] );
		$this->assertTrue( $notes[0]['summary'] );
		$after = $this->state();
		$this->assertSame( $record->get_order_number(), $after['sent']['number'] );
		$this->assertSame( Statuses::RECEIVED, $after['sent']['status'] );
		$stored = rest_do_request( new WP_REST_Request( 'GET', '/linker-ai/v1/genie/conversation' ) )->get_data();
		$this->assertSame(
			array(
				array(
					'after'   => 3,
					'order'   => $record->get_id(),
					'number'  => $record->get_order_number(),
					'status'  => Statuses::RECEIVED,
					'receipt' => true,
					'email'   => $guest,
					'url'     => $record->get_checkout_order_received_url(),
				),
			),
			$stored['inquiries']
		);
	}

	/**
	 * The card's switch off: the inquiry carries no summary and the team mail
	 * has no summary section.
	 */
	public function test_the_customer_can_turn_the_summary_off(): void {
		$product = $this->product( '1000' );
		$this->thread( 'Please send an inquiry.' );
		$this->cart( array( array( $product, 1 ) ) );
		$guest  = 'linker-it-' . self::tag() . '@example.test';
		$marker = self::newest_mail_job();
		$state  = $this->state();

		$response = $this->send(
			array(
				'name'           => 'Maria Weber',
				'email'          => $guest,
				'company'        => '',
				'message'        => 'Please send a Proforma invoice.',
				'attach_summary' => '0',
				'lines'          => $state['lines_digest'],
				'locale'         => 'en',
			) + self::fields()
		);
		$this->assertSame( 200, $response->get_status() );
		$record = $this->record( $guest );
		$this->assertSame( '', $record->get_meta( Sender::SUMMARY_META ) );
		$body = html_entity_decode( $this->row_to( $this->jobs_after( $marker ), self::INTERNAL )['body'] );
		$this->assertStringNotContainsString( 'Conversation with Genie', $body );
	}

	/**
	 * The guest form's required details: no name, no address or no consent
	 * means no record and no mail.
	 */
	public function test_a_guest_must_give_name_address_and_consent(): void {
		$product = $this->product( '1000' );
		$this->thread( 'Please send an inquiry.' );
		$this->cart( array( array( $product, 1 ) ) );
		$state  = $this->state();
		$marker = self::newest_mail_job();
		foreach ( array( 'name', 'email', 'consent' ) as $missing ) {
			$fields             = array(
				'name'           => 'Maria Weber',
				'email'          => 'linker-it-' . self::tag() . '@example.test',
				'attach_summary' => '1',
				'lines'          => $state['lines_digest'],
			) + self::fields();
			$fields[ $missing ] = '';
			$response           = $this->send( $fields );
			$this->assertSame( 400, $response->get_status(), "without {$missing}" );
		}
		$this->assertSame( array(), $this->jobs_after( $marker ) );
		$this->assertSame( array(), $this->orders() );
	}

	/**
	 * The card's lines must still be the solution draft's: a draft that moved
	 * after the card showed it is refused, and sending again with the new lines
	 * works.
	 */
	public function test_a_draft_that_changed_after_the_card_is_refused(): void {
		$first  = $this->product( '1000' );
		$second = $this->product( '2000' );
		$this->thread( 'Please send an inquiry.' );
		$this->cart( array( array( $first, 1 ) ) );
		$state = $this->state();
		$guest = 'linker-it-' . self::tag() . '@example.test';
		$this->assertNotFalse( WC()->cart->add_to_cart( $second->get_id(), 3 ) );
		$marker = self::newest_mail_job();

		$refused = $this->send(
			array(
				'name'           => 'Maria Weber',
				'email'          => $guest,
				'message'        => 'Please send a Proforma invoice.',
				'attach_summary' => '1',
				'lines'          => $state['lines_digest'],
			) + self::fields()
		);
		$this->assertSame( 409, $refused->get_status() );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
		$this->assertSame( array(), $this->orders() );

		$again = $this->state();
		$this->assertCount( 2, $again['lines'] );
		$response = $this->send(
			array(
				'name'           => 'Maria Weber',
				'email'          => $guest,
				'message'        => 'Please send a Proforma invoice.',
				'attach_summary' => '1',
				'lines'          => $again['lines_digest'],
			) + self::fields()
		);
		$this->assertSame( 200, $response->get_status() );
		$record = $this->record( $guest );
		$items  = array_values( $record->get_items() );
		$this->assertCount( 2, $items );
		$this->assertInstanceOf( WC_Order_Item_Product::class, $items[1] );
		$this->assertSame( 3, $items[1]->get_quantity() );
	}

	/**
	 * A price that moved after the card was shown refuses the send: the card
	 * confirmed the line it displayed, not a later one (research §5.1 point 4).
	 */
	public function test_a_price_change_after_the_card_is_refused(): void {
		// A partner account sees the net price: the price line is part of what
		// the card confirmed. A guest's line is the login sentence, which a price
		// change does not move.
		$customer = $this->customer();
		$this->as_user( $customer->get_id() );
		$product = $this->product( '1000' );
		$this->thread( 'Please send an inquiry.' );
		$this->cart( array( array( $product, 1 ) ) );
		$state = $this->state();

		$changed = wc_get_product( $product->get_id() );
		$this->assertInstanceOf( \WC_Product::class, $changed );
		$changed->set_regular_price( '1250' );
		$changed->save();
		// The next request loads the cart from the session again; in this process
		// the cart's product object still holds the old price.
		WC()->cart->empty_cart();
		$this->assertNotFalse( WC()->cart->add_to_cart( $changed->get_id(), 1 ) );
		WC()->cart->calculate_totals();
		$marker = self::newest_mail_job();

		$refused = $this->send(
			array(
				'message'        => 'Please send a Proforma invoice.',
				'attach_summary' => '1',
				'lines'          => $state['lines_digest'],
			) + self::fields()
		);
		$this->assertSame( 409, $refused->get_status() );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
		$this->assertSame( array(), $this->orders() );
	}

	/**
	 * A bot's honeypot and a forged start time are refused before anything is
	 * written; a state read never writes at all (A8: no card, no inquiry).
	 */
	public function test_no_request_without_a_valid_click_writes_anything(): void {
		$product = $this->product( '1000' );
		$this->thread( 'Please send an inquiry.' );
		$this->cart( array( array( $product, 1 ) ) );
		$state  = $this->state();
		$marker = self::newest_mail_job();

		// Reading the card and a model's sentence in the thread create nothing.
		$this->state();
		$this->assertSame( array(), $this->orders() );

		$bot = $this->send(
			array(
				'name'           => 'Bot',
				'email'          => 'bot@example.test',
				'message'        => 'I have sent your inquiry.',
				'attach_summary' => '1',
				'lines'          => $state['lines_digest'],
				'consent'        => '1',
				'website'        => 'https://spam.example',
				'started'        => (string) ( time() - 10 ),
				'started_nonce'  => 'forged',
			)
		);
		$this->assertSame( 200, $bot->get_status() );
		$this->assertSame( array(), $this->orders() );

		$forged = $this->send(
			array(
				'name'           => 'Maria Weber',
				'email'          => 'linker-it-' . self::tag() . '@example.test',
				'message'        => 'Please send a Proforma invoice.',
				'attach_summary' => '1',
				'lines'          => $state['lines_digest'],
				'consent'        => '1',
				'website'        => '',
				'started'        => (string) ( time() - 10 ),
				'started_nonce'  => 'forged',
			)
		);
		$this->assertSame( 400, $forged->get_status() );
		$this->assertSame( array(), $this->orders() );
		$this->assertSame( array(), $this->jobs_after( $marker ) );
	}

	/**
	 * A signed-in customer's details come from the account, and the record
	 * belongs to it.
	 */
	public function test_a_signed_in_customer_sends_with_account_details(): void {
		$customer = $this->customer();
		$this->as_user( $customer->get_id() );
		$product = $this->product( '1000' );
		$this->thread( 'Please send an inquiry.' );
		$this->cart( array( array( $product, 2 ) ) );
		$state = $this->state( 'de' );
		$this->assertSame( $customer->get_billing_email(), $state['account']['email'] );
		$marker = self::newest_mail_job();

		$response = $this->send(
			array(
				'message'        => 'Two units for our project.',
				'attach_summary' => '1',
				'lines'          => $state['lines_digest'],
				'locale'         => 'de',
				'page'           => array(
					'type'  => 'account',
					'url'   => home_url( '/de/mein-konto/' ),
					'title' => 'Mein Konto',
				),
			)
		);

		$this->assertSame( 200, $response->get_status() );
		$record = $this->record( $customer->get_billing_email() );
		$this->assertSame( $customer->get_id(), $record->get_customer_id() );
		$this->assertSame( $customer->get_billing_company(), $record->get_billing_company() );
		$this->assertSame( 'de_DE_formal', $record->get_meta( OrderLocale::META ) );
		$this->assertCount( 2, $this->jobs_after( $marker ) );
	}

	/**
	 * Sending the same card twice, with nothing said in between, makes one
	 * record; the record created once is what the card then reads.
	 */
	public function test_the_same_send_twice_makes_one_inquiry(): void {
		$product = $this->product( '1000' );
		$this->thread( 'Please send an inquiry.' );
		$this->cart( array( array( $product, 1 ) ) );
		$state  = $this->state();
		$guest  = 'linker-it-' . self::tag() . '@example.test';
		$marker = self::newest_mail_job();
		$params = array(
			'name'           => 'Maria Weber',
			'email'          => $guest,
			'message'        => 'Please send a Proforma invoice.',
			'attach_summary' => '1',
			'lines'          => $state['lines_digest'],
		) + self::fields();
		$first  = $this->send( $params );
		$second = $this->send( $params );
		$this->assertSame( array( 200, 200 ), array( $first->get_status(), $second->get_status() ) );
		$this->assertSame( $first->get_data()['inquiry'], $second->get_data()['inquiry'] );
		$this->assertCount( 2, $this->jobs_after( $marker ), 'one team mail and one receipt' );
		$this->assertCount( 1, $this->orders() );
	}

	/**
	 * An empty solution draft and an empty message cannot send: the card's
	 * state says so and names the request page. A message alone can.
	 */
	public function test_an_empty_draft_leads_to_the_request_page(): void {
		$this->summary['note'] = '';
		$this->thread( 'Hello' );
		$state = $this->state();
		$this->assertSame( array(), $state['lines'] );
		$this->assertFalse( $state['ready'] );
		$marker = self::newest_mail_job();
		$empty  = $this->send(
			array(
				'name'           => 'Maria Weber',
				'email'          => 'linker-it-' . self::tag() . '@example.test',
				'message'        => '',
				'attach_summary' => '',
				'lines'          => $state['lines_digest'],
			) + self::fields()
		);
		$this->assertSame( 409, $empty->get_status() );
		$this->assertSame( array(), $this->orders() );

		$response = $this->send(
			array(
				'name'           => 'Maria Weber',
				'email'          => 'linker-it-' . self::tag() . '@example.test',
				'message'        => 'We need a three-phase system. Please advise.',
				'attach_summary' => '',
				'lines'          => $state['lines_digest'],
			) + self::fields()
		);
		$this->assertSame( 200, $response->get_status() );
		$this->assertCount( 2, $this->jobs_after( $marker ), 'a message alone is an inquiry' );
	}

	/**
	 * Over the site's receipt cap the inquiry still reaches the team; the
	 * receipt alone is held back, and the card is told.
	 */
	public function test_over_the_receipt_cap_the_card_reports_no_receipt(): void {
		$receipts = new \Linker\Commerce\Inquiry\RateLimit( 'public_receipts', ReceiptLimit::DAILY_CAP, DAY_IN_SECONDS );
		while ( $receipts->take( '' ) ) {
			continue;
		}
		$product = $this->product( '1000' );
		$this->thread( 'Please send an inquiry.' );
		$this->cart( array( array( $product, 1 ) ) );
		$state    = $this->state();
		$marker   = self::newest_mail_job();
		$guest    = 'linker-it-' . self::tag() . '@example.test';
		$response = $this->send(
			array(
				'name'           => 'Maria Weber',
				'email'          => $guest,
				'message'        => 'Please send a Proforma invoice.',
				'attach_summary' => '1',
				'lines'          => $state['lines_digest'],
			) + self::fields()
		);
		$this->assertSame( 200, $response->get_status() );
		$this->assertFalse( $response->get_data()['inquiry']['receipt'] );
		$rows = $this->jobs_after( $marker );
		$this->assertCount( 1, $rows, 'the team mail only' );
		$this->assertSame( array( self::INTERNAL ), $rows[0]['to'] );
		$this->assertSame( 'daily_cap', $this->record( $guest )->get_meta( ReceiptLimit::SKIPPED_META ) );
		$this->assertFalse( $this->state()['sent']['receipt'] );
	}

	/**
	 * The card's state, read through the REST server.
	 *
	 * @param string $locale The card's language.
	 * @return array<string, mixed>
	 */
	private function state( string $locale = 'en' ): array {
		$request = new WP_REST_Request( 'GET', '/linker-ai/v1/genie/inquiry' );
		$request->set_param( 'locale', $locale );
		$response = rest_do_request( $request );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( 200, $response->get_status() );
		return $response->get_data();
	}

	/**
	 * POSTs the card's send through the REST server.
	 *
	 * @param array<string, mixed> $params Body.
	 */
	private function send( array $params ): WP_REST_Response {
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/inquiry' );
		foreach ( $params as $name => $value ) {
			$request->set_param( $name, $value );
		}
		$response = rest_do_request( $request );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		return $response;
	}

	/**
	 * The inquiries this test wrote (the card's own, from checkout).
	 *
	 * @return list<WC_Order>
	 */
	private function orders(): array {
		$found  = wc_get_orders(
			array(
				'limit'       => -1,
				'created_via' => 'checkout',
			)
		);
		$orders = array();
		foreach ( is_array( $found ) ? $found : array() as $order ) {
			if ( 'proforma' === $order->get_meta( '_linker_inquiry_source' ) && 'linker-it-' === substr( (string) $order->get_billing_email(), 0, 10 ) ) {
				$orders[] = $order;
			}
		}
		return $orders;
	}

	/**
	 * The one inquiry of an address.
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
	 * The solution draft of the visitor.
	 *
	 * @param array<int, array{WC_Product_Simple, int}> $lines Products and quantities.
	 */
	private function cart( array $lines ): void {
		wc_load_cart();
		WC()->cart->empty_cart();
		foreach ( $lines as [ $product, $quantity ] ) {
			$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), $quantity ) );
		}
		WC()->cart->calculate_totals();
	}

	/**
	 * A person's guard fields: a stamp of this door from ten seconds ago.
	 *
	 * @return array{website: string, started: string, started_nonce: string, consent: string}
	 */
	private static function fields(): array {
		$stamp = ( new FormGuard( 'genie_inquiry', InquiryRequest::LIMIT, InquiryRequest::DAILY ) )->stamp( time() - 10 );
		return array(
			'website'       => '',
			'started'       => $stamp['started'],
			'started_nonce' => $stamp['nonce'],
			'consent'       => '1',
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
	 * The card limits' rows as they are now (RateLimit::PREFIX).
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
	 * The queue rows written after $marker.
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
}
