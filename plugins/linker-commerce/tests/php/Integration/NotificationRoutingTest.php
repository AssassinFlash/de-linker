<?php
/**
 * Integration test: who receives the internal notifications, and which
 * address customers see.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Abilities\HandoffTeam;
use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\Handler;
use Linker\Commerce\Digest\Module as DigestModule;
use Linker\Commerce\Digest\Scheduler;
use Linker\Commerce\Genie\Module as GenieModule;
use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Emails\VatReviewEmail;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Settings\SettingsTab;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use WC_Admin_Settings;

/**
 * Owner ruling 2026-10-17 (AGENTS.md §2): every internal notification goes to
 * sales@sunriverinverter.com with the blind copies of the settings, never to
 * sales@de-linker.com; every address customers see stays sales@de-linker.com.
 * The routing is read from the Outbox queue (AGENTS.md §5, test mail rule):
 * the minute quota is full, so each call is stored as a queue row instead of
 * being sent, and the row is the routing the sender named.
 *
 * @coversNothing
 */
final class NotificationRoutingTest extends IntegrationTestCase {

	/**
	 * The default recipient of internal notifications (Options::DEFAULT_NOTIFY_TO).
	 */
	private const INTERNAL = 'sales@sunriverinverter.com';

	/**
	 * The team mailbox customers see (Options::DEFAULT_TEAM_TO).
	 */
	private const PUBLIC = 'sales@de-linker.com';

	/**
	 * Settings as live has them, the stopgap switches off, the quota full.
	 */
	protected function setUp(): void {
		parent::setUp();
		// The email classes extend WC_Email, which WooCommerce loads with its mailer.
		WC()->mailer();
		$saved = array();
		foreach ( array( Options::TEAM_TO, Options::NOTIFY_TO, Options::NOTIFY_FROM, Options::NOTIFY_BCC, Options::PROFORMA_PREFIX, 'woocommerce_email_from_name', 'woocommerce_email_from_address', Monitor::GENIE_URL_OPTION, Monitor::ENGINE_URL_OPTION ) as $name ) {
			$saved[ $name ] = get_option( $name );
		}
		foreach ( array( NewCustomerEmail::ID, VatReviewEmail::ID, NewInquiryEmail::ID, 'linker_digest' ) as $id ) {
			$saved[ 'woocommerce_' . $id . '_settings' ] = get_option( 'woocommerce_' . $id . '_settings' );
		}
		$this->later(
			static function () use ( $saved ): void {
				foreach ( $saved as $name => $value ) {
					if ( false === $value ) {
						delete_option( $name );
					} else {
						update_option( $name, $value );
					}
				}
			}
		);
		// Both team settings unset, as on live; the blind copy stands in for
		// the copy address the owner keeps once it is shown to arrive.
		delete_option( Options::TEAM_TO );
		delete_option( Options::NOTIFY_TO );
		delete_option( Options::NOTIFY_FROM );
		update_option( 'woocommerce_email_from_name', 'Linker' );
		update_option( 'woocommerce_email_from_address', self::PUBLIC );
		update_option( Options::NOTIFY_BCC, 'copy-' . self::tag() . '@example.test' );
		foreach ( array_keys( $saved ) as $name ) {
			if ( str_starts_with( $name, 'woocommerce_linker_' ) ) {
				delete_option( $name );
			}
		}
		// Fill the minute quota so every call is stored instead of sent at
		// once (MailChainTest does the same): a sent call never becomes a row.
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
	}

	/**
	 * Woo's native settings save stores the internal sender.
	 */
	public function test_native_settings_save_keeps_the_sender(): void {
		$this->save_setting( Options::NOTIFY_FROM, 'alerts@example.test' );
		$this->assertSame( 'alerts@example.test', get_option( Options::NOTIFY_FROM ) );
		$this->assertSame( 'alerts@example.test', ( new Options() )->notify_sender()->email );
	}

	/**
	 * Woo's native settings save trims only the prefix's edge hyphens.
	 */
	public function test_native_settings_save_trims_the_proforma_prefix(): void {
		$this->save_setting( Options::PROFORMA_PREFIX, '--DLK-PF--' );
		$this->assertSame( 'DLK-PF', get_option( Options::PROFORMA_PREFIX ) );
	}

	/**
	 * New-customer notifications go to the team; replies go to the customer.
	 *
	 * @testWith ["", "sales@sunriverinverter.com"]
	 *           ["alerts@example.test", "alerts@example.test"]
	 *
	 * @param string $saved_from Saved internal sender.
	 * @param string $from       Effective sender.
	 */
	public function test_new_customer_notification_routing( string $saved_from, string $from ): void {
		update_option( Options::NOTIFY_FROM, $saved_from );
		$customer = $this->customer();
		$email    = WC()->mailer()->get_emails()[ NewCustomerEmail::class ];
		$this->assertInstanceOf( NewCustomerEmail::class, $email );
		$marker = self::newest_mail_job();
		$email->trigger( $customer->get_id() );
		$row = $this->internal_message( $marker, 'New customer: Linker Integration Test GmbH', $from );
		$this->assertContains( 'Reply-to: Maria Beispiel <' . $customer->get_billing_email() . '>', $row['headers'], NewCustomerEmail::ID );
	}

	/**
	 * VAT-review notifications preserve the customer's Reply-To.
	 *
	 * @testWith ["", "sales@sunriverinverter.com"]
	 *           ["alerts@example.test", "alerts@example.test"]
	 *
	 * @param string $saved_from Saved internal sender.
	 * @param string $from       Effective sender.
	 */
	public function test_vat_review_notification_routing( string $saved_from, string $from ): void {
		update_option( Options::NOTIFY_FROM, $saved_from );
		$customer = $this->customer();
		$email    = WC()->mailer()->get_emails()[ VatReviewEmail::class ];
		$this->assertInstanceOf( VatReviewEmail::class, $email );
		$marker = self::newest_mail_job();
		$email->trigger( $customer->get_id(), VatProfile::UNVERIFIED, VatProfile::INVALID );
		$row = $this->internal_message( $marker, 'VAT check changed: Linker Integration Test GmbH', $from );
		$this->assertContains( 'Reply-to: Maria Beispiel <' . $customer->get_billing_email() . '>', $row['headers'], VatReviewEmail::ID );
	}

	/**
	 * Inquiry notifications use the internal sender and customer Reply-To;
	 * the customer's receipt keeps the public sender.
	 *
	 * @testWith ["", "sales@sunriverinverter.com"]
	 *           ["alerts@example.test", "alerts@example.test"]
	 *
	 * @param string $saved_from Saved internal sender.
	 * @param string $from       Effective sender.
	 */
	public function test_new_inquiry_notification_routing( string $saved_from, string $from ): void {
		update_option( Options::NOTIFY_FROM, $saved_from );
		$customer = $this->customer();
		$marker   = self::newest_mail_job();
		$order    = $this->send_inquiry( $customer, array( array( $this->product( '100' ), 1 ) ) );
		$row      = $this->internal_message( $marker, 'New inquiry #' . $order->get_order_number() . ' from ', $from );
		$this->assertContains( 'Reply-to: Maria Beispiel <' . $customer->get_billing_email() . '>', $row['headers'], NewInquiryEmail::ID );
		$receipt = array_values( array_filter( $this->jobs_after( $marker ), static fn ( array $row ): bool => array( $customer->get_billing_email() ) === $row['to'] ) );
		$this->assertCount( 1, $receipt );
		$this->assertContains( 'From: Linker <' . self::PUBLIC . '>', $receipt[0]['headers'] );
		$this->assertStringNotContainsString( self::INTERNAL, implode( "\n", $receipt[0]['headers'] ) );
	}

	/**
	 * Contact notifications reply to the visitor; their receipt replies to Linker.
	 *
	 * @testWith ["", "sales@sunriverinverter.com"]
	 *           ["alerts@example.test", "alerts@example.test"]
	 *
	 * @param string $saved_from Saved internal sender.
	 * @param string $from       Effective sender.
	 */
	public function test_contact_notification_routing( string $saved_from, string $from ): void {
		update_option( Options::NOTIFY_FROM, $saved_from );
		$this->as_user( 0 );
		$stamp         = (string) ( time() - 5 );
		$contact_email = 'linker-it-' . self::tag() . '@example.test';
		$marker        = self::newest_mail_job();
		$this->assertSame(
			'sent',
			( new Handler() )->process(
				array(
					'name'                 => 'Maria Beispiel',
					'email'                => $contact_email,
					'message'              => 'A question about a storage system.',
					'consent'              => '1',
					Form::NONCE_FIELD      => wp_create_nonce( Form::NONCE_ACTION ),
					'linker_started'       => $stamp,
					'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
				)
			)
		);
		$contacts = wc_get_orders(
			array(
				'billing_email' => $contact_email,
				'limit'         => -1,
			)
		);
		$this->assertIsArray( $contacts );
		foreach ( $contacts as $contact ) {
			$this->later(
				static function () use ( $contact ): void {
					$contact->delete( true );
				}
			);
		}
		$this->assertCount( 1, $contacts );
		$emails = WC()->mailer()->get_emails();
		$this->assertArrayNotHasKey( 'Linker\\Commerce\\Contact\\Emails\\ReceiptEmail', $emails );
		$this->assertArrayNotHasKey( 'Linker\\Commerce\\Contact\\Emails\\TeamMessageEmail', $emails );
		$row = $this->internal_message( $marker, 'New inquiry #' . $contacts[0]->get_order_number() . ' from ', $from );
		$this->assertContains( 'Reply-to: Maria Beispiel <' . $contact_email . '>', $row['headers'], NewInquiryEmail::ID );
		$receipt = array_values( array_filter( $this->jobs_after( $marker ), static fn ( array $row ): bool => array( $contact_email ) === $row['to'] ) );
		$this->assertCount( 1, $receipt );
		$this->assertContains( 'From: Linker <' . self::PUBLIC . '>', $receipt[0]['headers'] );
		$this->assertContains( 'Reply-to: Linker <' . self::PUBLIC . '>', $receipt[0]['headers'] );
	}

	/**
	 * Genie's contact request (#243) goes to the internal recipient, replies
	 * to the address the customer left.
	 *
	 * @testWith ["", "sales@sunriverinverter.com"]
	 *           ["alerts@example.test", "alerts@example.test"]
	 *
	 * @param string $saved_from Saved internal sender.
	 * @param string $from       Effective sender.
	 */
	public function test_genie_contact_notification_routing( string $saved_from, string $from ): void {
		update_option( Options::NOTIFY_FROM, $saved_from );
		$this->as_user( 0 );
		$guest  = 'linker-it-' . self::tag() . '@example.test';
		$marker = self::newest_mail_job();
		// A contact message through Genie is #246's record, team mail and receipt.
		$sent = ( new GenieModule( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() ) )->contact(
			null,
			array(
				'conversation' => array(
					'id'       => 1,
					'url'      => admin_url( 'admin.php?page=linker-genie-quality&conversation=1' ),
					'messages' => 1,
				),
				'reason'       => 'asked',
				'reason_label' => 'Asked to talk to a person',
				'locale'       => 'en',
				'customer'     => array(
					'user_id' => 0,
					'email'   => $guest,
					'name'    => '',
				),
				'summary'      => array( 'Can I talk to a person?' ),
				'page'         => array(
					'type'  => 'home',
					'url'   => home_url( '/' ),
					'title' => 'Home',
				),
				'draft'        => array(),
			)
		);
		$this->assertIsArray( $sent );
		$order = wc_get_order( $sent['order'] );
		$this->assertInstanceOf( \WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$row = $this->internal_message( $marker, 'New inquiry #' . $order->get_order_number() . ' from ' . $guest, $from );
		$this->assertNotEmpty( array_filter( $row['headers'], static fn ( string $line ): bool => str_starts_with( $line, 'Reply-to:' ) && str_contains( $line, $guest ) ) );
		$receipt = array_values( array_filter( $this->jobs_after( $marker ), static fn ( array $row ): bool => array( $guest ) === $row['to'] ) );
		$this->assertCount( 1, $receipt );
		$this->assertContains( 'From: Linker <' . self::PUBLIC . '>', $receipt[0]['headers'] );
	}

	/**
	 * The daily digest uses the internal sender and adds no Reply-To.
	 *
	 * @testWith ["", "sales@sunriverinverter.com"]
	 *           ["alerts@example.test", "alerts@example.test"]
	 *
	 * @param string $saved_from Saved internal sender.
	 * @param string $from       Effective sender.
	 */
	public function test_digest_notification_routing( string $saved_from, string $from ): void {
		update_option( Options::NOTIFY_FROM, $saved_from );
		$marker = self::newest_mail_job();
		$this->later(
			static function (): void {
				wp_clear_scheduled_hook( Scheduler::HOOK );
				( new Scheduler() )->ensure();
			}
		);
		( new DigestModule( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new JobStore() ) )->run();
		$row = $this->internal_message( $marker, 'Daily digest, ', $from );
		$this->assert_no_reply_to( $row['headers'] );
	}

	/**
	 * Each failing service queues its own internal alert without a Reply-To.
	 *
	 * @testWith ["", "sales@sunriverinverter.com"]
	 *           ["alerts@example.test", "alerts@example.test"]
	 *
	 * @param string $saved_from Saved internal sender.
	 * @param string $from       Effective sender.
	 */
	public function test_health_notification_routing( string $saved_from, string $from ): void {
		update_option( Options::NOTIFY_FROM, $saved_from );
		update_option( Monitor::GENIE_URL_OPTION, 'http://127.0.0.1:9' );
		update_option( Monitor::ENGINE_URL_OPTION, 'http://127.0.0.1:9' );
		$marker = self::newest_mail_job();
		( new Monitor( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() ) )->run();
		foreach ( array( 'The Genie service failed its health check', 'The engine service failed its health check' ) as $subject ) {
			$row = $this->internal_message( $marker, $subject, $from );
			$this->assert_no_reply_to( $row['headers'] );
		}
	}

	/**
	 * The addresses customers see — the Proforma seller, Genie's hand-off
	 * sentence, the contact page's direct address, the product page's contact
	 * band — stay sales@de-linker.com while internal mail goes elsewhere.
	 */
	public function test_every_customer_visible_address_stays_the_team_mailbox(): void {
		$this->assertSame( self::PUBLIC, ( new Options() )->seller()['email'] );
		$this->assertSame( self::PUBLIC, ( new Options() )->contact()['email'] );

		$handoff = ( new HandoffTeam() )->execute();
		$this->assertSame( 'Our team will answer that at ' . self::PUBLIC . '.', $handoff['sentence_en'] );
		$this->assertSame( 'Unser Team beantwortet das unter ' . self::PUBLIC . '.', $handoff['sentence_de'] );
		$this->assertSame( 'mailto:' . self::PUBLIC, $handoff['mailto'] );

		// The shortcodes' own callbacks: PHPUnit loads WordPress inside a
		// function, so WordPress's top-level $shortcode_tags never becomes the
		// global add_shortcode() writes to, and do_shortcode() finds no tag.
		$renders = array(
			'[linker_contact_form]'     => ( new Form() )->render(),
			'[linker_products_contact]' => ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_contact(),
		);
		foreach ( $renders as $shortcode => $html ) {
			$this->assertStringContainsString( 'mailto:' . self::PUBLIC, $html, "{$shortcode} links the team mailbox." );
			$this->assertStringNotContainsString( self::INTERNAL, $html, "{$shortcode} never shows the internal address." );
		}
	}

	/**
	 * Saves one field through Woo's native settings API.
	 *
	 * @param string $id    Setting id.
	 * @param string $value Submitted value.
	 */
	private function save_setting( string $id, string $value ): void {
		$fields = array_values( array_filter( ( new SettingsTab( new JobStore() ) )->fields(), static fn ( array $field ): bool => $id === $field['id'] ) );
		WC_Admin_Settings::save_fields( $fields, array( $id => $value ) );
	}

	/**
	 * The queued internal message with its common recipient and sender contract.
	 *
	 * @param int    $marker  Queue marker before the trigger.
	 * @param string $subject Expected subject prefix.
	 * @param string $from    Expected sender.
	 * @return array{subject: string, to: list<string>, headers: list<string>}
	 */
	private function internal_message( int $marker, string $subject, string $from ): array {
		$matching = array_values( array_filter( $this->jobs_after( $marker ), static fn ( array $row ): bool => str_starts_with( $row['subject'], $subject ) ) );
		$this->assertCount( 1, $matching, "One queued message: {$subject}" );
		$row = $matching[0];
		$this->assertSame( array( self::INTERNAL ), $row['to'] );
		$this->assertContains( 'Bcc: ' . get_option( Options::NOTIFY_BCC ), $row['headers'] );
		$this->assertContains( 'From: Linker <' . $from . '>', $row['headers'] );
		$this->assertContains( \Linker\Commerce\Mail\Message::INTERNAL_HEADER, $row['headers'], 'Every internal producer explicitly selects its transport.' );
		$this->assertStringNotContainsString( self::PUBLIC, implode( "\n", array_filter( $row['headers'], static fn ( string $line ): bool => 0 !== stripos( $line, 'From:' ) ) ) );
		return $row;
	}

	/**
	 * Digest and health alerts do not add a Reply-To header.
	 *
	 * @param string[] $headers Queued headers.
	 */
	private function assert_no_reply_to( array $headers ): void {
		$this->assertSame( array(), array_values( array_filter( $headers, static fn ( string $line ): bool => str_starts_with( strtolower( $line ), 'reply-to:' ) ) ) );
	}

	/**
	 * The routing of every queue row written after $marker (isolate_mail()
	 * removes the rows afterwards).
	 *
	 * @param int $marker The newest row id before the test.
	 * @return list<array{subject: string, to: list<string>, headers: list<string>}>
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
			);
		}
		return $rows;
	}
}
