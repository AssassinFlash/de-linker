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
use Linker\Commerce\Contact\Emails\TeamMessageEmail;
use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Digest\Module as DigestModule;
use Linker\Commerce\Digest\Scheduler;
use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Emails\VatReviewEmail;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;

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
		foreach ( array( Options::TEAM_TO, Options::NOTIFY_TO, Options::NOTIFY_BCC, Monitor::GENIE_URL_OPTION, Monitor::ENGINE_URL_OPTION ) as $name ) {
			$saved[ $name ] = get_option( $name );
		}
		foreach ( array( NewCustomerEmail::ID, VatReviewEmail::ID, NewInquiryEmail::ID, TeamMessageEmail::ID, 'linker_digest' ) as $id ) {
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
	 * New customer, VAT check, new inquiry, contact form message, daily
	 * digest and health alert: each is one queued message To the internal
	 * address with the blind copy, sent from the team mailbox, and none of
	 * them names sales@de-linker.com as a recipient.
	 */
	public function test_every_internal_notification_goes_to_the_internal_address_only(): void {
		$bcc    = 'Bcc: ' . get_option( Options::NOTIFY_BCC );
		$marker = self::newest_mail_job();
		$plugin = WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php';
		$emails = WC()->mailer()->get_emails();

		$new_customer = $emails[ NewCustomerEmail::class ] ?? null;
		$vat_review   = $emails[ VatReviewEmail::class ] ?? null;
		$this->assertInstanceOf( NewCustomerEmail::class, $new_customer, 'The new-customer email is registered with WooCommerce.' );
		$this->assertInstanceOf( VatReviewEmail::class, $vat_review, 'The VAT check email is registered with WooCommerce.' );

		$customer = $this->customer();
		$new_customer->trigger( $customer->get_id() );
		$vat_review->trigger( $customer->get_id(), VatProfile::UNVERIFIED, VatProfile::INVALID );
		$order = $this->send_inquiry( $customer, array( array( $this->product( '100' ), 1 ) ) );
		$this->as_user( 0 );
		$submission = Submission::from_post(
			array(
				'name'    => 'Maria Beispiel',
				'email'   => 'linker-it-' . self::tag() . '@example.test',
				'message' => 'A question about a storage system.',
				'consent' => '1',
			)
		);
		$this->assertInstanceOf( Submission::class, $submission );
		( new TeamMessageEmail( $plugin, new Options() ) )->notify( $submission );
		( new DigestModule( $plugin, new JobStore() ) )->run();
		$this->later(
			static function (): void {
				wp_clear_scheduled_hook( Scheduler::HOOK );
				( new \Linker\Commerce\Digest\Scheduler() )->ensure();
			}
		);
		// A port with no listener refuses at once: both services fail.
		update_option( Monitor::GENIE_URL_OPTION, 'http://127.0.0.1:9' );
		update_option( Monitor::ENGINE_URL_OPTION, 'http://127.0.0.1:9' );
		/** The monitor's own daily event (Monitor::HOOK), as WP-Cron delivers it.
		 *
		 * @since 0.2.0
		 */
		do_action( Monitor::HOOK ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- the monitor's own hook constant.

		$rows     = $this->jobs_after( $marker );
		$internal = array(
			'New customer: Linker Integration Test GmbH',
			'VAT check changed: Linker Integration Test GmbH',
			'New inquiry #' . $order->get_order_number() . ' from ',
			'New message from Maria Beispiel',
			'Daily digest, ',
			'The Genie service failed its health check',
			'The engine service failed its health check',
		);
		foreach ( $internal as $subject ) {
			$matching = array_values( array_filter( $rows, static fn ( array $row ): bool => str_starts_with( $row['subject'], $subject ) ) );
			$this->assertCount( 1, $matching, "One queued message: {$subject}" );
			$this->assertSame( array( self::INTERNAL ), $matching[0]['to'], "{$subject} goes to the internal address alone." );
			$this->assertContains( $bcc, $matching[0]['headers'], "{$subject} carries the blind copy of the settings." );
			$this->assertStringNotContainsString( self::PUBLIC, implode( "\n", array_filter( $matching[0]['headers'], static fn ( string $line ): bool => 0 !== stripos( $line, 'From:' ) ) ), "{$subject} names sales@de-linker.com in no recipient header." );
			$this->assertContains( 'From: Linker <' . self::PUBLIC . '>', $matching[0]['headers'], "{$subject} is sent from WooCommerce's email sender, the team mailbox." );
		}

		$receipt = array_values( array_filter( $rows, static fn ( array $row ): bool => array( $customer->get_billing_email() ) === $row['to'] ) );
		$this->assertNotSame( array(), $receipt, 'The customer got their own receipt of the inquiry.' );
		$this->assertContains( 'From: Linker <' . self::PUBLIC . '>', $receipt[0]['headers'], 'Customer mail is sent from the team mailbox.' );
		$this->assertStringNotContainsString( self::INTERNAL, implode( "\n", $receipt[0]['headers'] ), 'Customer mail never names the internal address.' );
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
