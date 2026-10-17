<?php
/**
 * The approval states against a real WooCommerce: prices, the Store API, the
 * gateway, the login gate, the three emails and the reversibility.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Account\PendingGate;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Inquiry\ProformaGateway;
use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\AccountsAdmin;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use WC_Customer;
use WP_Error;
use WP_User;
use WP_REST_Request;

/**
 * The fixture matrix of ticket 73: four states times the gated surfaces, the
 * three actions times their emails, the reason that rides along, and states
 * that go back.
 *
 * @coversNothing
 */
final class ApprovalTest extends IntegrationTestCase {

	/**
	 * The password of the fixture customer, for the sign-in.
	 */
	private const PASSWORD = 'linker-integration-test-password';

	/**
	 * The subjects of the three customer emails, English first, German second
	 * (the customer's own language; the .po terms: Nettopreis,
	 * Partner-Konto, Lösungsentwurf).
	 */
	private const APPROVED_SUBJECTS   = array( 'Your partner account is approved', 'Ihr Partner-Konto ist freigegeben' );
	private const RESTRICTED_SUBJECTS = array( 'Your partner account access is limited', 'Der Zugriff Ihres Partner-Kontos ist derzeit eingeschränkt' );
	private const REJECTED_SUBJECTS   = array( 'Your partner account was not approved', 'Ihr Partner-Konto wurde nicht freigegeben' );

	/**
	 * Captured outgoing mail: recipient, subject, body.
	 *
	 * @var list<array{to: string, recipients: list<string>, subject: string, body: string}>
	 */
	private array $sent = array();

	/**
	 * The collector registered on pre_wp_mail, once a test captured mail: it
	 * reads the address of the moment, so capturing for a second customer must
	 * not register a second one — the mail would be recorded twice.
	 *
	 * @var callable|null
	 */
	private $collector = null;

	/**
	 * The email address mail is captured for; set by capture_mail().
	 *
	 * @var string
	 */
	private string $address = '';

	/**
	 * The four states over the gated surfaces: a pending and a restricted
	 * account read the site like a guest, an approved one sees prices, a
	 * rejected one cannot even sign in.
	 */
	public function test_states_times_gating(): void {
		$product = $this->product( '1680' );
		$state   = new CommerceState();

		// A guest, for the baseline.
		$this->as_user( 0 );
		$this->assertSame( '', $this->price( $product->get_id() ) );
		$this->assertNull( $this->store_api_prices( $product->get_id() ) );

		$customer = $this->customer();
		wp_set_password( self::PASSWORD, $customer->get_id() );

		foreach ( array( Approval::PENDING, Approval::RESTRICTED ) as $status ) {
			$this->set_state( $customer, $status, Approval::RESTRICTED === $status ? 'Net prices are for businesses.' : '' );
			$this->as_user( $customer->get_id() );
			$this->assertSame( '', $this->price( $product->get_id() ), "{$status} sees no price" );
			$this->assertNull( $this->store_api_prices( $product->get_id() ), "{$status} gets null Store API prices" );
			// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WooCommerce's own filter, applied as the request page applies it.
			$this->assertSame(
				array(),
				apply_filters( 'woocommerce_available_payment_gateways', $this->gateways() ), // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WooCommerce's own filter, applied as the request page applies it.
				"{$status} may not send an inquiry"
			);
		}

		$this->set_state( $customer, Approval::APPROVED );
		$this->as_user( $customer->get_id() );
		$this->assertSame( '1680', $this->price( $product->get_id() ), 'Approved sees the price' );
		$this->assertSame( '168000', $this->store_api_prices( $product->get_id() )['price'] ?? null, 'Approved gets the Store API price' );
		$this->assertSame(
			array( ProformaGateway::ID ),
			array_keys( apply_filters( 'woocommerce_available_payment_gateways', $this->gateways() ) ), // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WooCommerce's own filter, applied as the request page applies it.
			'Approved sends through the Proforma gateway alone'
		);

		// A rejection ends in a blocked sign-in, shown on the login form.
		$this->set_state( $customer, Approval::REJECTED, 'We could not verify the business.' );
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own hook, observed as the real login path.
		$sign_in = wp_signon(
			array(
				'user_login'    => $customer->get_username(),
				'user_password' => self::PASSWORD,
				'remember'      => false,
			)
		);
		$this->assertInstanceOf( WP_Error::class, $sign_in );
		$this->assertSame( 'linker_approval_rejected', $sign_in->get_error_code() );
		$this->assertStringContainsString( 'sales@de-linker.com', $sign_in->get_error_message() );
	}

	/**
	 * An account without approval cannot get an inquiry in: the draft accepts
	 * the line, as a guest's does, but no gateway is offered for the send.
	 */
	public function test_a_pending_account_cannot_send_an_inquiry(): void {
		$product  = $this->product( '1680' );
		$customer = $this->customer();
		$this->set_state( $customer, Approval::PENDING );

		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->customer = new WC_Customer( $customer->get_id(), true );
		WC()->cart->empty_cart();
		$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), 1 ), 'The draft accepts the line, as a guest\'s does' );

		$this->assertArrayNotHasKey(
			ProformaGateway::ID,
			apply_filters( 'woocommerce_available_payment_gateways', $this->gateways() ), // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WooCommerce's own filter, applied as the request page applies it.
			'WooCommerce offers the account no gateway, so the send is refused'
		);
	}

	/**
	 * The three actions, each with the customer's email: subject, language and
	 * the team's reason; then the way back.
	 */
	public function test_the_three_actions_mail_the_customer_and_revert(): void {
		delete_option( Throttle::OPTION );
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), 'locale', 'de_DE_formal' );
		$this->capture_mail( (string) $customer->get_billing_email() );

		// The fixture account is approved; the actions speak from the states
		// the team would set after a review round.
		$this->set_state( $customer, Approval::PENDING );
		$this->set_state( $customer, Approval::APPROVED );
		$this->set_state( $customer, Approval::RESTRICTED, 'Wir benötigen eine gültige Umsatzsteuer-ID.' );
		$this->set_state( $customer, Approval::REJECTED, 'Das Konto konnte nicht verifiziert werden.' );

		$captured = $this->to_address();
		$this->assertCount( 3, $captured, 'One email per action' );
		$this->assertSubject( $captured[0], self::APPROVED_SUBJECTS, 'The approved email' );
		$this->assertSubject( $captured[1], self::RESTRICTED_SUBJECTS, 'The restriction email' );
		$this->assertStringContainsString( 'Wir benötigen eine gültige Umsatzsteuer-ID.', $captured[1]['body'], 'The reason rides in the restriction email' );
		$this->assertSubject( $captured[2], self::REJECTED_SUBJECTS, 'The rejection email' );
		$this->assertStringContainsString( 'Das Konto konnte nicht verifiziert werden.', $captured[2]['body'], 'The reason rides in the rejection email' );

		// Back to approved: the account reads the site fully again, and the
		// way back also tells the customer.
		$this->set_state( $customer, Approval::APPROVED );
		$captured = $this->to_address();
		$this->assertCount( 4, $captured, 'One email per action, including the way back' );
		$this->assertSubject( $captured[3], self::APPROVED_SUBJECTS, 'The way back' );
		$this->as_user( $customer->get_id() );
		$this->assertTrue( ( new CommerceState() )->visitor_sees_prices() );
		$this->assertSame( Approval::APPROVED, ( new Approval() )->status( $customer->get_id() ) );
		$this->assertSame( '', ( new Approval() )->reason( $customer->get_id() ), 'The approval carries no reason' );
	}

	/** The former users-list operation is now a deep link to the shared card. */
	public function test_the_user_list_links_to_review_without_a_legacy_write_hook(): void {
		$customer = $this->customer();
		$this->as_user( 1 );
		$admin = new \Linker\Commerce\Registration\ApprovalAdmin( new Approval() );
		$user  = get_userdata( $customer->get_id() );
		$this->assertInstanceOf( WP_User::class, $user );
		$link = $admin->row_action( array(), $user )[ Approval::STATUS_META ];
		$this->assertStringContainsString( esc_url( AccountsAdmin::url( $customer->get_id() ) ), $link );
		$this->assertFalse( has_action( 'admin_post_linker_approval' ) );
		$this->assertFalse( has_action( 'admin_post_update' ) );
	}

	/**
	 * The three customer emails speak the sentences the copy review finalized
	 * (docs/acceptance/2026-10-11/73/copy-review.md, §4–§6), each in the
	 * customer's own language: a German customer reads German bodies, an
	 * English one English bodies. The .eml renders in the acceptance directory
	 * are the same check on the instance's captured mail.
	 */
	public function test_the_customer_emails_speak_the_finalized_copy(): void {
		$approved = $this->approval_mail_body( 'de_DE_formal', Approval::APPROVED );
		$this->assertStringContainsString( 'Ihr Partner-Konto bei Linker ist freigegeben.', $approved );
		$this->assertStringContainsString(
			'Die Nettopreise werden jetzt zu jedem Produkt angezeigt. Legen Sie die benötigten Systeme in Ihren Lösungsentwurf und fordern Sie die Proformarechnung an, wenn er fertig ist.',
			$approved
		);
		$this->assertStringContainsString( 'Zu den Produkten', $approved, 'The link reuses the existing term.' );
		$this->assertStringNotContainsString( 'Net prices are now shown', $approved, 'No English sentence in a German body.' );

		$restricted = $this->approval_mail_body( 'de_DE_formal', Approval::RESTRICTED, 'Net prices are for businesses.' );
		$this->assertStringContainsString( 'Ihr Partner-Konto ist vorerst eingeschränkt.', $restricted );
		$this->assertStringContainsString(
			'Sie können die Produkte weiterhin ansehen und uns jederzeit unter sales@de-linker.com erreichen. Nettopreise und Proforma-Anfrage sind pausiert, solange das Konto eingeschränkt ist.',
			$restricted
		);
		$this->assertStringContainsString( 'Unser Grund:', $restricted );
		$this->assertStringContainsString( 'Schreiben Sie uns, und wir sehen uns Ihr Konto erneut an.', $restricted );

		$rejected = $this->approval_mail_body( 'de_DE_formal', Approval::REJECTED, 'Das Konto konnte nicht verifiziert werden.' );
		$this->assertStringContainsString( 'Wir können Ihr Partner-Konto bei Linker nicht freigeben. Die Anmeldung bleibt deshalb geschlossen.', $rejected );
		$this->assertStringContainsString( 'Unser Grund:', $rejected );
		$this->assertStringContainsString( 'Bei Fragen schreiben Sie an sales@de-linker.com.', $rejected );

		$approved_en = $this->approval_mail_body( 'en_US', Approval::APPROVED );
		$this->assertStringContainsString( 'Your Linker partner account is approved.', $approved_en );
		$this->assertStringContainsString(
			'Net prices are now shown with every product. Add the systems you need to your solution draft, and request the Proforma when the draft is ready.',
			$approved_en
		);

		$restricted_en = $this->approval_mail_body( 'en_US', Approval::RESTRICTED, 'Net prices are for businesses.' );
		$this->assertStringContainsString( 'Your partner account has been limited for now.', $restricted_en );
		$this->assertStringContainsString(
			'You can keep browsing the products, and you can reach us any time at sales@de-linker.com. Net prices and the Proforma request are paused while the account is limited.',
			$restricted_en
		);
		$this->assertStringContainsString( 'Our reason:', $restricted_en );
		$this->assertStringContainsString( 'Write to us and we will look at your account again.', $restricted_en );

		$rejected_en = $this->approval_mail_body( 'en_US', Approval::REJECTED, 'We could not verify the business.' );
		$this->assertStringContainsString( 'We cannot approve your Linker partner account. Signing in therefore stays closed.', $rejected_en );
		$this->assertStringContainsString( 'If you have questions, write to sales@de-linker.com.', $rejected_en );
	}

	/**
	 * Test mode (Mail\TestMode, AGENTS.md §5): with the switch on, one message
	 * per action reaches the single test address — no customer mailbox — while
	 * the mail chain still hands the message over for the customer's address.
	 */
	public function test_test_mode_delivers_to_one_address_only(): void {
		delete_option( Throttle::OPTION );
		$test_mode = new TestMode();
		$before    = $test_mode->address();
		$this->assertTrue( $test_mode->enable() );
		$this->later(
			static function () use ( $test_mode, $before ): void {
				'' === $before ? $test_mode->disable() : $test_mode->enable( $before );
			}
		);

		$customer = $this->customer();
		update_user_meta( $customer->get_id(), 'locale', 'en_US' );
		$this->capture_mail( (string) $customer->get_billing_email() );
		$this->set_state( $customer, Approval::PENDING );
		$this->set_state( $customer, Approval::APPROVED );

		// The chain handed one message over for the customer, and the send
		// reached the one test address (the delivery the switch rewrites).
		$this->assertCount( 1, $this->to_address(), 'The message was handed over for the customer.' );
		$delivered = $this->delivered();
		$this->assertCount( 1, $delivered, 'One delivery.' );
		$this->assertSame( array( TestMode::DEFAULT_TO ), $delivered[0]['recipients'], 'The delivery went to the one test address.' );
		$this->assertStringContainsString( 'Your Linker partner account is approved.', $delivered[0]['body'] );
	}

	/**
	 * A registration through the real form fields starts pending, and the
	 * customer's language is recorded for the later emails.
	 */
	public function test_a_registration_starts_pending(): void {
		$_POST   = array(
			'billing_company'    => 'Solarbau Beispiel GmbH',
			CustomerRole::META   => 'installer',
			VatProfile::VAT_META => '',
			'billing_first_name' => 'Maria',
			'billing_last_name'  => 'Beispiel',
			'billing_country'    => 'DE',
			'billing_address_1'  => 'Teststraße 1',
			'billing_postcode'   => '39179',
			'billing_city'       => 'Barleben',
		);
		$created = wc_create_new_customer( 'linker-it-' . self::tag() . '@example.test', 'linker-it-' . self::tag(), 'x' );
		$this->assertIsInt( $created );
		$id = $created;
		$this->later(
			static function () use ( $id ): void {
				require_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
			}
		);

		$fields = new Fields( new VatProfile( new ViesClient() ) );
		$this->assertFalse( $fields->validate( new \WP_Error() )->has_errors() );
		$fields->save( $id );

			$this->assertSame( Approval::PENDING, ( new Approval() )->status( $id ), 'The account waits for the team' );
			$this->assertNotSame( '', get_user_meta( $id, 'locale', true ), 'The customer\'s language is recorded' );
			$this->assertTrue( ( new Approval() )->is_subject( $id ) );
			$this->assertFalse( ( new Approval() )->sees_prices( $id ) );
	}

		/**
		 * A pending sign-in is held on the review page, including a direct request
		 * for the inquiries and the documents. Approving opens those pages again.
		 * A restricted account keeps the workplace and reads its own gate, with
		 * the reason, on the Proforma request. A rejection cannot sign in, and
		 * the reason is in the email.
		 */
	public function test_a_pending_sign_in_is_held_until_approval(): void {
		delete_option( Throttle::OPTION );
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), 'locale', 'en_US' );
		$this->capture_mail( (string) $customer->get_billing_email() );

		$this->set_state( $customer, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		$gate = new PendingGate( new Approval(), new LoginGate( new Approval() ) );
		$this->assertTrue( $gate->holds(), 'A pending sign-in is held.' );
		$this->assertFalse( ( new CommerceState() )->visitor_sees_prices(), 'Pending sees no prices.' );
		$this->assertArrayNotHasKey(
			ProformaGateway::ID,
			apply_filters( 'woocommerce_available_payment_gateways', $this->gateways() ), // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WooCommerce's own filter, applied as the request page applies it.
			'Pending may not send an inquiry.'
		);
		ob_start();
		$gate->render();
		$review = (string) ob_get_clean();
		$this->assertStringContainsString( 'Your account is under review', $review, 'The review page is what a pending sign-in reads.' );

		$this->set_state( $customer, Approval::APPROVED );
		$this->as_user( $customer->get_id() );
		$this->assertFalse( $gate->holds(), 'Approved is no longer held.' );
		$this->assertTrue( ( new CommerceState() )->visitor_sees_prices(), 'Approved sees prices.' );
		$this->assertArrayHasKey(
			ProformaGateway::ID,
			apply_filters( 'woocommerce_available_payment_gateways', $this->gateways() ), // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WooCommerce's own filter, applied as the request page applies it.
			'Approved may send an inquiry.'
		);

		$this->set_state( $customer, Approval::RESTRICTED, 'Net prices are for businesses.' );
		$this->as_user( $customer->get_id() );
		$this->assertFalse( $gate->holds(), 'Restricted keeps the workplace.' );
		$this->assertFalse( ( new CommerceState() )->visitor_sees_prices(), 'Restricted sees no prices.' );
		$this->assertStringContainsString( 'Net prices are for businesses.', ( new LoginGate( new Approval() ) )->html() );

		$this->set_state( $customer, Approval::REJECTED, 'We could not verify the business.' );
		wp_set_password( self::PASSWORD, $customer->get_id() );
		$sign_in = wp_signon(
			array(
				'user_login'    => $customer->get_username(),
				'user_password' => self::PASSWORD,
				'remember'      => false,
			)
		);
		$this->assertInstanceOf( WP_Error::class, $sign_in );
		$this->assertSame( 'linker_approval_rejected', $sign_in->get_error_code() );
		$captured = $this->to_address();
		$this->assertNotEmpty( $captured, 'The rejection mailed the customer.' );
		$this->assertStringContainsString( 'We could not verify the business.', $captured[ count( $captured ) - 1 ]['body'] );
	}

	/**
	 * The product's price as the visitor's pages read it.
	 *
	 * @param int $product_id Product.
	 */
	private function price( int $product_id ): string {
		$product = wc_get_product( $product_id );
		$this->assertInstanceOf( \WC_Product::class, $product );
		return (string) $product->get_price();
	}

	/**
	 * The prices block of a product in WooCommerce's Store API.
	 *
	 * @param int $product_id Product.
	 * @return array<string, mixed>|null
	 */
	private function store_api_prices( int $product_id ): ?array {
		$response = rest_do_request( new WP_REST_Request( 'GET', '/wc/store/v1/products/' . $product_id ) );
		$this->assertSame( 200, $response->get_status() );
		$data = $response->get_data();
		$this->assertIsArray( $data );
		return null === $data['prices'] ? null : (array) $data['prices'];
	}

	/**
	 * The gateways WooCommerce knows, before the availability filter.
	 *
	 * @return array<string, mixed>
	 */
	private function gateways(): array {
		return WC()->payment_gateways()->payment_gateways();
	}

		/**
		 * Applies one action as the admin-post handler does.
		 *
		 * @param WC_Customer $customer The account.
		 * @param string      $status   The state to set.
		 * @param string      $reason   The reason, required for restrict and reject.
		 */
	private function set_state( WC_Customer $customer, string $status, string $reason = '' ): void {
		wp_set_current_user( 1 );
		$this->assertTrue( ( new Approval() )->set( $customer->get_id(), $status, $reason ), "The {$status} action was written" );
	}

	/**
	 * Records every wp_mail() call while a test runs; a queue retry of an
	 * earlier test's message may land in the same window, so the assertions
	 * read only the mail of this test's own address.
	 *
	 * A call made by the chain carries its recipient as the string WordPress
	 * was handed; the outbox's own call — the delivery that actually reaches
	 * the mailer — passes the recipients as a list, so the two are told apart.
	 *
	 * @param string $address The address to capture for.
	 */
	private function capture_mail( string $address ): void {
		$this->sent    = array();
		$this->address = $address;
		if ( null !== $this->collector ) {
			return;
		}
		$this->collector = function ( $pre, array $atts ) {
			$to           = $atts['to'] ?? '';
			$this->sent[] = array(
				'to'         => ( is_string( $to ) ? $to : '' ),
				'recipients' => is_array( $to ) ? array_values( array_filter( $to, 'is_string' ) ) : array(),
				'subject'    => (string) ( $atts['subject'] ?? '' ),
				'body'       => (string) ( $atts['message'] ?? '' ),
			);
			return $pre;
		};
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- WordPress's own hook, observed as the real mail path.
		add_action( 'pre_wp_mail', $this->collector, 5, 2 );
		$this->later(
			function (): void {
				if ( null !== $this->collector ) {
					remove_action( 'pre_wp_mail', $this->collector, 5 );
				}
			}
		);
	}

	/**
	 * The captured mail of this test's own address, in send order.
	 *
	 * @return list<array{to: string, recipients: list<string>, subject: string, body: string}>
	 */
	private function to_address(): array {
		return array_values(
			array_filter(
				$this->sent,
				fn ( array $mail ): bool => $mail['to'] === $this->address
			)
		);
	}

	/**
	 * The deliveries of this test's captured mail: the sends the outbox made,
	 * which are the ones a mailbox receives.
	 *
	 * @return list<array{to: string, recipients: list<string>, subject: string, body: string}>
	 */
	private function delivered(): array {
		return array_values(
			array_filter(
				$this->sent,
				static fn ( array $mail ): bool => array() !== $mail['recipients']
			)
		);
	}

	/**
	 * The body of the one email an approval action sends a fresh customer, in
	 * the language that customer reads. A pending account has no email of its
	 * own, so the action is the only mail of the call.
	 *
	 * @param string $locale Customer's language.
	 * @param string $status The state to set.
	 * @param string $reason The team's reason, required for restrict and reject.
	 */
	private function approval_mail_body( string $locale, string $status, string $reason = '' ): string {
		delete_option( Throttle::OPTION );
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), 'locale', $locale );
		$this->capture_mail( (string) $customer->get_billing_email() );
		$this->set_state( $customer, Approval::PENDING );
		$this->set_state( $customer, $status, $reason );

		$captured = $this->to_address();
		$this->assertCount( 1, $captured, "One email for the {$status} action: " . implode( ' | ', array_column( $captured, 'subject' ) ) );
		return $captured[0]['body'];
	}

	/**
	 * The mail speaks the state's subject, in English or — as on the instance,
	 * where the captured .eml carries it — in the customer's German.
	 *
	 * @param array{to: string, recipients: list<string>, subject: string, body: string} $mail The mail.
	 * @param string[]                                                                   $subjects The state's subjects.
	 * @param string                                                                     $which    What the mail is, for the message.
	 */
	private function assertSubject( array $mail, array $subjects, string $which ): void {
		$this->assertContains(
			$mail['subject'],
			$subjects,
			"{$which} speaks none of its subjects: {$mail['subject']}"
		);
	}
}
