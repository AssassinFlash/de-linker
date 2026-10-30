<?php
/**
 * Customer emails keep their language in the body, the subject and the links.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail;
use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Proforma\Emails\ProformaIssuedEmail;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\Emails\ApprovedEmail;
use WC_Order;

/**
 * Ticket #263, M9: a German customer email triggered from the admin or from
 * the mail queue keeps the German body and its German links. The switch used
 * to change WordPress's locale only, while every WooCommerce page link was
 * resolved in Polylang's current language — English on an admin request.
 *
 * The fixture covers the three trigger contexts the ticket names: a front-end
 * inquiry, a staff action in wp-admin and a scheduled queue retry. It also
 * covers the review note of #243: two languages in one process must not leak
 * into each other.
 *
 * The tests write their own German page twins when the instance has none (CI's
 * bare smoke instance), and use the live snapshot's twins when it has them.
 *
 * @coversNothing
 */
final class LanguageLinksInMailTest extends IntegrationTestCase {
	/** Real classification and native consumers.
	 *
	 * @var NormalMailAuthorizationFixture
	 */
	private NormalMailAuthorizationFixture $authorization;

	/**
	 * Captured outgoing mail calls, in send order.
	 *
	 * @var list<array{to: string, recipients: list<string>, subject: string, body: string}>
	 */
	private array $sent = array();

	/**
	 * Mail settings this class puts aside for its duration.
	 *
	 * @var array<string, mixed>
	 */
	private array $settings = array();

	/**
	 * Loads WooCommerce's mailer and puts aside the saved email settings, so
	 * the default subjects and enabled state are the fixture's.
	 */
	protected function setUp(): void {
		parent::setUp();
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$this->authorization = NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
		WC()->mailer();
		foreach ( array( ApprovedEmail::ID, InquiryReceivedEmail::ID, ProformaIssuedEmail::ID ) as $id ) {
			$name                    = 'woocommerce_' . $id . '_settings';
			$this->settings[ $name ] = get_option( $name );
			delete_option( $name );
		}
		$this->later(
			function (): void {
				foreach ( $this->settings as $name => $value ) {
					if ( false === $value ) {
						delete_option( $name );
					} else {
						update_option( $name, $value );
					}
				}
			}
		);
		$this->collect();
	}

	/**
	 * Staff approve an account in wp-admin: the German customer gets a German
	 * subject, German sentences and German page links.
	 */
	public function test_admin_approval_mail_links_follow_the_customer_language(): void {
		$this->ensure_languages();

		$english = $this->customer();
		update_user_meta( $english->get_id(), 'locale', 'en_US' );
		$german = $this->customer();
		update_user_meta( $german->get_id(), 'locale', 'de_DE_formal' );

		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		delete_option( Throttle::OPTION );
		$this->as_user( 1 );
		$email = new ApprovedEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' );
		$this->later(
			static function () use ( $email ): void {
				remove_action( \Linker\Commerce\Registration\Approval::CHANGED_ACTION . '_notification', array( $email, 'trigger' ), 10 );
			}
		);
		$email->trigger( $english->get_id(), Approval::PENDING, Approval::APPROVED, '' );
		$email->trigger( $german->get_id(), Approval::PENDING, Approval::APPROVED, '' );

		$messages = $this->to_address( (string) $english->get_billing_email() );
		$this->assertCount( 1, $messages, 'One English approval mail.' );
		$this->assertStringContainsString( 'Your Linker partner account is approved.', $messages[0]['body'] );
		$this->assertStringContainsString( 'href="' . $this->english_page_url( 'shop' ) . '"', $messages[0]['body'] );
		$this->assertStringContainsString( 'href="' . $this->english_page_url( 'myaccount' ) . '"', $messages[0]['body'] );

		$messages = $this->to_address( (string) $german->get_billing_email() );
		$this->assertCount( 1, $messages, 'One German approval mail.' );
		$this->assertSame( 'Ihr Partner-Konto ist freigegeben', $messages[0]['subject'], 'The subject follows the customer.' );
		$this->assertStringContainsString( 'Ihr Partner-Konto bei Linker ist freigegeben.', $messages[0]['body'] );
		$this->assertStringContainsString( 'href="' . $this->german_page_url( 'shop' ) . '"', $messages[0]['body'], 'The shop link is German.' );
		$this->assertStringContainsString( 'href="' . $this->german_page_url( 'myaccount' ) . '"', $messages[0]['body'], 'The account link is German.' );
		$this->assertStringNotContainsString( 'href="' . $this->english_page_url( 'shop' ) . '"', $messages[0]['body'], 'No English shop link in a German body.' );
		$this->assertStringNotContainsString( 'href="' . $this->english_page_url( 'myaccount' ) . '"', $messages[0]['body'], 'No English account link in a German body.' );
	}

	/**
	 * Staff issue the Proforma in wp-admin: both links in the German email
	 * stay on German pages, the download included.
	 */
	public function test_admin_proforma_mail_links_follow_the_customer_language(): void {
		$this->ensure_languages();
		$order = $this->german_inquiry();
		$order->set_status( \Linker\Commerce\Inquiry\Statuses::PROFORMA );
		$order->save();

		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		delete_option( Throttle::OPTION );
		$this->as_user( 1 );
		$email = new ProformaIssuedEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' );
		$this->later(
			static function () use ( $email ): void {
				remove_action( 'woocommerce_order_status_inquiry-received_to_proforma-issued_notification', array( $email, 'trigger' ), 10 );
			}
		);
		$email->trigger( $order->get_id(), $order );

		$messages = $this->to_address( (string) $order->get_billing_email() );
		$this->assertCount( 1, $messages, 'One German Proforma mail.' );
		$this->assertCount( 1, $this->deliveries(), 'The original native handoff makes one actual tester delivery attempt beyond its preview.' );
		$order->read_meta_data( true );
		$this->assertSame( $order->get_meta( Issuer::NUMBER_META ), $order->get_meta( ProformaIssuedEmail::ACCEPTED ) );
		$body = $messages[0]['body'];
		$this->assertStringContainsString( 'Ihre Proformarechnung', $body, 'The body is German.' );

		$this->assertSame( 1, preg_match( '~href="([^"]*linker-document=proforma[^"]*)"~', $body, $download ), 'The mail carries the download link.' );
		$this->assertStringStartsWith( $this->german_home(), html_entity_decode( $download[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ), 'The download link is on the German site.' );

		$this->assertSame( 1, preg_match( '~href="([^"]*/de/mein-konto/[^"]*)"~', $body, $inquiry ), 'The inquiry link is on the German account.' );
		$this->assertStringContainsString( '/de/mein-konto/', html_entity_decode( $inquiry[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
		$this->assertStringNotContainsString( 'href="' . $this->english_home() . '?linker-document=proforma', $body );
	}

	/**
	 * A guest inquiry from the German request form gets the German receipt,
	 * and its optional registration link opens the German account.
	 */
	public function test_front_end_inquiry_receipt_links_follow_the_recorded_language(): void {
		$this->ensure_languages();
		$order = $this->german_inquiry();

		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		delete_option( Throttle::OPTION );
		$this->as_user( 0 );
		$email = new InquiryReceivedEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' );
		$this->later(
			static function () use ( $email ): void {
				remove_action( 'woocommerce_order_status_pending_to_inquiry-received_notification', array( $email, 'trigger' ), 10 );
			}
		);
		$email->trigger( $order->get_id(), $order );
		$this->assertSame( array(), $this->to_address( (string) $order->get_billing_email() ), 'Saved inquiry waits for a bound normal verdict.' );
		$this->authorization->process( $order, true );

		$messages = $this->to_address( (string) $order->get_billing_email() );
		$this->assertCount( 1, $messages, 'One German receipt.' );
		$this->assertSame( 'Ihre Anfrage #' . $order->get_order_number() . ' ist eingegangen', $messages[0]['subject'] );
		$this->assertStringContainsString( 'Dank für Ihre Anfrage', $messages[0]['body'] );
		$this->assertSame( 1, preg_match( '~href="([^"]*/de/mein-konto/[^"]*)"~', $messages[0]['body'], $registration ), 'The registration link is German.' );
		parse_str( (string) wp_parse_url( html_entity_decode( $registration[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ), PHP_URL_QUERY ), $query );
		$this->assertSame( (string) $order->get_id(), $query['linker_inquiry'] ?? '', 'The receipt key still travels.' );
		$this->assertSame( $order->get_order_key(), $query['linker_key'] ?? '' );
	}

	/**
	 * The queue retry Action Scheduler runs later is still the German message
	 * with its German links: the rendered message is what is stored, and the
	 * retry does not re-render it in the request it runs in.
	 */
	public function test_scheduled_retry_keeps_the_german_message_and_links(): void {
		$this->ensure_languages();
		$order  = $this->german_inquiry();
		$marker = self::newest_mail_job();

		// A full minute quota makes the call a queue row instead of a send.
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$this->as_user( 0 );
		$email = new InquiryReceivedEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' );
		$this->later(
			static function () use ( $email ): void {
				remove_action( 'woocommerce_order_status_pending_to_inquiry-received_notification', array( $email, 'trigger' ), 10 );
			}
		);
		$email->trigger( $order->get_id(), $order );

		$this->assertSame( array(), self::mail_jobs_after( $marker ), 'No content job before classification.' );
		$state = $this->authorization->process( $order );
		$jobs  = array( $state['jobs']['receipt']['id'] );
		$this->assertCount( 2, self::mail_jobs_after( $marker ), 'One team notification and one German receipt are queued after the normal verdict.' );
		$stored = ( new JobStore() )->load( $jobs[0] );
		$this->assertNotNull( $stored );
		$this->assertSame( array( $order->get_billing_email() ), $stored['message']->to );

		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		delete_option( Throttle::OPTION );
		/**
		 * The queue's own retry hook, fired the way Action Scheduler fires it.
		 *
		 * @since 0.1.0
		 *
		 * @param int $job_id The queued message.
		 */
		do_action( Outbox::HOOK, $jobs[0] ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- this plugin's hook constant.

		// Test mode rewrites the delivery's recipients to the tester, so the
		// delivery is recognised by its German body, not its address.
		$delivered = array_values(
			array_filter(
				$this->deliveries(),
				static fn ( array $mail ): bool => str_contains( $mail['body'], 'Dank für Ihre Anfrage' )
			)
		);
		$this->assertCount( 1, $delivered, 'The scheduled attempt delivered once.' );
		$this->assertSame( 'Ihre Anfrage #' . $order->get_order_number() . ' ist eingegangen', $delivered[0]['subject'] );
		$this->assertStringContainsString( 'Dank für Ihre Anfrage', $delivered[0]['body'] );
		$this->assertStringContainsString( '/de/mein-konto/', $delivered[0]['body'], 'The queued message keeps its German links.' );
		$this->assertStringNotContainsString( 'href="' . $this->english_page_url( 'myaccount' ) . 'register', $delivered[0]['body'] );
	}

	/** A cached team-mail instance must follow the actual native site locale on each render. */
	public function test_cached_team_email_tracks_each_authoritative_site_locale(): void {
		$before = get_option( 'WPLANG' );
		$this->later(
			static function () use ( $before ): void {
				wp_cache_delete( 'WPLANG', 'options' );
				wp_cache_delete( 'alloptions', 'options' );
				false === $before ? delete_option( 'WPLANG' ) : update_option( 'WPLANG', $before );
			}
		);
		$order = new \WC_Order();
		$order->set_billing_email( self::TESTER );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$email = WC()->mailer()->get_emails()[ \Linker\Commerce\Inquiry\Emails\NewInquiryEmail::class ];
		self::assertInstanceOf( \Linker\Commerce\Inquiry\Emails\NewInquiryEmail::class, $email );
		foreach ( array( 'en_US', 'de_DE_formal', 'en_US' ) as $locale ) {
			wp_cache_delete( 'WPLANG', 'options' );
			wp_cache_delete( 'alloptions', 'options' );
			update_option( 'WPLANG', 'en_US' === $locale ? '' : $locale );
			global $wpdb;
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Confirm the actual fixture-owned locale, not a stale option-cache readback.
			$actual = $wpdb->get_var( $wpdb->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, 'WPLANG' ) );
			self::assertSame( 'en_US' === $locale ? '' : $locale, $actual ?? '', 'Native absence is WordPress default English.' );
			$message = $email->capture( $order );
			self::assertInstanceOf( \Linker\Commerce\Mail\Message::class, $message );
			self::assertStringStartsWith( 'en_US' === $locale ? 'New inquiry #' : 'Neue Anfrage #', $message->subject );
		}
	}

	/**
	 * The review note of #243: an English and then a German customer mail in
	 * one process. The second must not inherit the first language, and the
	 * reverse order must not leave German behind.
	 */
	public function test_two_languages_in_one_process_do_not_leak(): void {
		$this->ensure_languages();
		$english = $this->customer();
		update_user_meta( $english->get_id(), 'locale', 'en_US' );
		$german = $this->customer();
		update_user_meta( $german->get_id(), 'locale', 'de_DE_formal' );

		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		delete_option( Throttle::OPTION );
		$this->as_user( 1 );
		$email = new ApprovedEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' );
		$this->later(
			static function () use ( $email ): void {
				remove_action( \Linker\Commerce\Registration\Approval::CHANGED_ACTION . '_notification', array( $email, 'trigger' ), 10 );
			}
		);

		$email->trigger( $english->get_id(), Approval::PENDING, Approval::APPROVED, '' );
		$email->trigger( $german->get_id(), Approval::PENDING, Approval::APPROVED, '' );
		$email->trigger( $english->get_id(), Approval::PENDING, Approval::APPROVED, '' );

		$english_mail = $this->to_address( (string) $english->get_billing_email() );
		$this->assertCount( 2, $english_mail, 'Two English mails.' );
		foreach ( $english_mail as $message ) {
			$this->assertSame( 'Your partner account is approved', $message['subject'] );
			$this->assertStringContainsString( 'Your Linker partner account is approved.', $message['body'] );
			$this->assertStringContainsString( 'href="' . $this->english_page_url( 'shop' ) . '"', $message['body'] );
		}

		$german_mail = $this->to_address( (string) $german->get_billing_email() );
		$this->assertCount( 1, $german_mail, 'One German mail.' );
		$this->assertSame( 'Ihr Partner-Konto ist freigegeben', $german_mail[0]['subject'] );
		$this->assertStringContainsString( 'Ihr Partner-Konto bei Linker ist freigegeben.', $german_mail[0]['body'] );
		$this->assertStringContainsString( 'href="' . $this->german_page_url( 'shop' ) . '"', $german_mail[0]['body'] );
	}

	/** Native workers can classify English and German sources in one PHP process. */
	public function test_bound_inquiry_batch_keeps_each_recorded_language(): void {
		$this->ensure_languages();
		foreach ( array( 'en_US', 'de_DE_formal', 'en_US' ) as $locale ) {
			$order = $this->german_inquiry();
			$order->update_meta_data( '_linker_locale', $locale );
			$order->save_meta_data();
			( new InquiryReceivedEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' ) )->trigger( $order->get_id(), $order );
			$state   = $this->authorization->process( $order );
			$receipt = ( new JobStore() )->load( $state['jobs']['receipt']['id'] );
			$this->assertNotNull( $receipt );
			$subject = 'de_DE_formal' === $locale ? 'Ihre Anfrage #' . $order->get_order_number() . ' ist eingegangen' : 'Your inquiry #' . $order->get_order_number() . ' has been received';
			$this->assertSame( $subject, $receipt['message']->subject );
			$this->assertStringContainsString( 'de_DE_formal' === $locale ? 'Dank für Ihre Anfrage' : 'Thank you for your inquiry', $receipt['message']->body );
		}
	}

	/**
	 * Records every wp_mail() call. The queue's own delivery passes the
	 * recipients as a list; the chain's first call passes the recipient as a
	 * string (the same distinction ApprovalTest reads).
	 */
	private function collect(): void {
		$collector = function ( $pre, array $atts ) {
			$to           = $atts['to'] ?? '';
			$this->sent[] = array(
				'to'         => is_string( $to ) ? $to : '',
				'recipients' => is_array( $to ) ? array_values( array_filter( $to, 'is_string' ) ) : array(),
				'subject'    => (string) ( $atts['subject'] ?? '' ),
				'body'       => (string) ( $atts['message'] ?? '' ),
			);
			return $pre;
		};
		add_filter( 'pre_wp_mail', $collector, 5, 2 );
		$this->later(
			static function () use ( $collector ): void {
				remove_filter( 'pre_wp_mail', $collector, 5 );
			}
		);
	}

	/**
	 * The calls the chain handed over for an address (the first leg).
	 *
	 * @phpstan-impure Captured mail changes after native background consumers.
	 * @param string $address Recipient address.
	 * @return list<array{to: string, recipients: list<string>, subject: string, body: string}>
	 */
	private function to_address( string $address ): array {
		return array_values(
			array_filter(
				$this->sent,
				static fn ( array $mail ): bool => $mail['to'] === $address
			)
		);
	}

	/**
	 * The deliveries the queue made (the calls with a recipient list; the
	 * chain's first leg passes one address as a string).
	 *
	 * @return list<array{to: string, recipients: list<string>, subject: string, body: string}>
	 */
	private function deliveries(): array {
		return array_values(
			array_filter(
				$this->sent,
				static fn ( array $mail ): bool => array() !== $mail['recipients']
			)
		);
	}

	/**
	 * A guest inquiry recorded in German, as the German request form records it.
	 */
	private function german_inquiry(): WC_Order {
		$order = new WC_Order();
		$order->set_billing_email( 'linker-language-' . self::tag() . '@example.test' );
		$order->update_meta_data( '_linker_locale', 'de_DE_formal' );
		$order->update_meta_data( Issuer::NUMBER_META, 'DLK-PF-' . wp_date( 'Y' ) . '-0001' );
		$order->update_meta_data( Issuer::ISSUED_META, (string) time() );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$stored = wc_get_order( $order->get_id() );
				if ( $stored instanceof WC_Order ) {
					$stored->delete( true );
				}
			}
		);
		return $order;
	}

	/**
	 * The English page a WooCommerce option names, as the site serves it.
	 *
	 * @param string $page `shop` or `myaccount`.
	 */
	private function english_page_url( string $page ): string {
		$id = (int) get_option( 'woocommerce_' . $page . '_page_id' );
		return (string) get_permalink( $id );
	}

	/**
	 * The German twin of the page a WooCommerce option names.
	 *
	 * @param string $page `shop` or `myaccount`.
	 */
	private function german_page_url( string $page ): string {
		$id   = (int) get_option( 'woocommerce_' . $page . '_page_id' );
		$twin = (int) pll_get_post( $id, 'de' );
		$this->assertGreaterThan( 0, $twin, "The {$page} page has a German twin." );
		$link = get_permalink( $twin );
		$this->assertIsString( $link );
		return $link;
	}

	/**
	 * The German home URL: the site root under Polylang's /de/ directory.
	 * Written from the site root rather than pll_home_url(), whose static
	 * front page answers the front page's own /de/<page>/ link.
	 */
	private function german_home(): string {
		return trailingslashit( home_url( '/de/' ) );
	}

	/**
	 * The English home URL without its trailing slash.
	 */
	private function english_home(): string {
		return trailingslashit( home_url( '/' ) );
	}

	/**
	 * Makes sure Polylang runs both languages and the pages the mails link to
	 * have German twins. The live snapshot has both; CI's bare instance gets
	 * them created here and removed afterwards.
	 */
	private function ensure_languages(): void {
		if ( ! function_exists( 'pll_languages_list' ) ) {
			$this->markTestSkipped( 'Polylang is not active on this instance.' );
		}
		if ( ! in_array( 'de', pll_languages_list(), true ) ) {
			wp_set_current_user( 1 );
			foreach ( ( new \Linker\I18n\Setup() )->apply() as $line ) {
				$this->assertStringStartsNotWith( 'error:', $line, $line );
			}
		}
		foreach ( array( 'shop', 'myaccount' ) as $page ) {
			$id = (int) get_option( 'woocommerce_' . $page . '_page_id' );
			$this->assertGreaterThan( 0, $id, "The instance has a {$page} page." );
			if ( false === pll_get_post_language( $id ) ) {
				pll_set_post_language( $id, 'en' );
			}
			$this->german_twin( $id, 'shop' === $page ? 'produkte' : 'mein-konto', 'shop' === $page ? 'Produkte' : 'Mein Konto' );
		}
		wp_cache_flush();
	}

	/**
	 * The page's German twin, created and paired when the instance has none.
	 *
	 * @param int    $english_id English page.
	 * @param string $slug       German slug.
	 * @param string $title      German title.
	 */
	private function german_twin( int $english_id, string $slug, string $title ): int {
		$twin = (int) pll_get_post( $english_id, 'de' );
		if ( $twin > 0 ) {
			return $twin;
		}
		$twin = (int) wp_insert_post(
			array(
				'post_type'   => 'page',
				'post_status' => 'publish',
				'post_title'  => $title,
				'post_name'   => $slug,
			)
		);
		$this->assertGreaterThan( 0, $twin, 'The German twin page was created.' );
		pll_set_post_language( $twin, 'de' );
		pll_save_post_translations(
			array(
				'en' => $english_id,
				'de' => $twin,
			)
		);
		$this->forget_cached_permalinks();
		$this->later(
			static function () use ( $twin, $english_id ): void {
				wp_delete_post( $twin, true );
				pll_save_post_translations( array( 'en' => $english_id ) );
			}
		);
		return $twin;
	}

	/**
	 * Polylang's request-local link cache may hold the page URL from before the
	 * new twin received its language.
	 */
	private function forget_cached_permalinks(): void {
		$polylang = PLL();
		$links    = $polylang->filters_links;
		if ( ! isset( $links->cache ) || ! is_object( $links->cache ) || ! method_exists( $links->cache, 'clean' ) ) {
			return;
		}
		$links->cache->clean();
	}
}
