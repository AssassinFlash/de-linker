<?php
/**
 * Public inquiries through the shared submission entry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\PublicGuard;
use Linker\Commerce\Mail\Throttle;
use WC_Order;

/**
 * Shared entry, account states, and queue routes on a real instance.
 *
 * @coversNothing
 */
final class OpenInquiryTest extends IntegrationTestCase {

	/** Retired Woo checkout transports cannot bypass the shared public inquiry sender. */
	public function test_alternate_checkout_transports_cannot_create_an_inquiry(): void {
		$this->as_user( 0 );
		$marker = self::newest_mail_job();
		$errors = new \WP_Error();
		do_action( 'woocommerce_after_checkout_validation', array(), $errors ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Woo's validation boundary.
		$this->assertTrue( $errors->has_errors() );
		foreach ( array( 'GET', 'POST' ) as $method ) {
			$response = rest_do_request( new \WP_REST_Request( $method, '/wc/store/v1/checkout' ) );
			$this->assertSame( 403, $response->get_status() );
			$this->assertSame( 'linker_inquiry_form_required', $response->get_data()['code'] );
		}
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/** The public product button must reach the draft rather than require sign-in. */
	public function test_guest_product_action_adds_to_the_draft_without_opening_prices(): void {
		$this->as_user( 0 );
		$product = $this->product( '125' );
		$fields  = ( new \Linker\Commerce\Storefront\ProductView() )->fields( $product->get_id() );
		$this->assertSame( 'Add to solution draft', $fields['cta_label'] );
		$this->assertStringContainsString( 'add-to-cart=' . $product->get_id(), $fields['cta_url'] );
		$this->assertStringNotContainsString( '125', $fields['price']['html'] );
	}

	/**
	 * The actual LC request pages expand the form and localize the browser title.
	 *
	 * @dataProvider request_languages
	 * @param string $path Request page.
	 * @param string $title Localized title.
	 * @param string $message Message field label.
	 */
	public function test_public_request_page_in_both_languages( string $path, string $title, string $message ): void {
		$query    = array(
			'post_type'     => 'linker_conversation',
			'post_status'   => 'private',
			'numberposts'   => -1,
			'fields'        => 'ids',
			'cache_results' => false,
		);
		$existing = get_posts( $query );
		$response = wp_remote_get( home_url( $path ) );
		$created  = array_diff( get_posts( $query ), $existing );
		$this->later(
			static function () use ( $created ): void {
				foreach ( $created as $id ) {
					wp_delete_post( $id, true );
				}
			}
		);
		$this->assertSame( array(), $created, 'Reading the inquiry form must not create a Genie conversation.' );
		$this->assertIsArray( $response );
		$this->assertSame( 200, wp_remote_retrieve_response_code( $response ) );
		$html = wp_remote_retrieve_body( $response );
		$this->assertStringContainsString( '<title>' . $title . ' | Linker</title>', $html );
		$this->assertSame( 1, preg_match( '/<form class="linker-inquiry-form".*?<\/form>/s', $html, $matches ) );
		$form = $matches[0] ?? '';
		$this->assertStringContainsString( $message, $form );
		$this->assertStringContainsString( 'action="' . admin_url( 'admin-post.php' ) . '"', $form );
		$this->assertStringNotContainsString( '[linker_', $form );
		$this->assertStringNotContainsString( 'name="billing_country"', $form );
		$this->assertStringNotContainsString( 'name="billing_address_1"', $form );
	}

	/**
	 * The two public request URLs and independently written labels.
	 *
	 * @return array<string, array{string, string, string}>
	 */
	public static function request_languages(): array {
		return array(
			'en' => array( '/proforma-request/', 'Send an inquiry', 'Message (optional)' ),
			'de' => array( '/de/proforma-anfrage/', 'Anfrage senden', 'Nachricht (optional)' ),
		);
	}

	/** Blank guest fields must be real empty values rather than unevaluated template tags. */
	public function test_guest_form_renders_empty_fields_and_real_transport_attributes(): void {
		$this->as_user( 0 );
		wc_load_cart();
		$tags = $GLOBALS['shortcode_tags'];
		$this->later(
			static function () use ( $tags ): void {
				$GLOBALS['shortcode_tags'] = $tags;
			}
		);
		( new \Linker\Commerce\Inquiry\Form() )->register();
		$html = do_shortcode( '[linker_inquiry_form]' );
		$this->assertStringNotContainsString( '[linker_inquiry_', $html );
		$this->assertStringContainsString( 'id="inquiry-name" name="name"', $html );
		// Woo posts to the draft route and redirects to this form through its native referer.
		$this->assertStringContainsString( '<form method="post" action="' . wc_get_cart_url() . '">', $html );
		$this->assertStringContainsString( 'value="" required', $html );
		$this->assertStringContainsString( 'action="' . admin_url( 'admin-post.php' ) . '"', $html );
		$fields = WC()->session->get( 'linker_inquiry_fields' );
		$this->later(
			static function () use ( $fields ): void {
				WC()->session->set( 'linker_inquiry_fields', $fields );
			}
		);
		$literal = '[linker_inquiry_text key=title]';
		WC()->session->set( 'linker_inquiry_fields', array( 'message' => $literal ) );
		$this->assertStringContainsString( '>' . esc_attr( $literal ) . '</textarea>', do_shortcode( '[linker_inquiry_form]' ) );
		$this->assertNull( WC()->session->get( 'linker_inquiry_fields' ), 'The next render consumes the guest PII.' );
		$this->assertStringNotContainsString( esc_attr( $literal ), do_shortcode( '[linker_inquiry_form]' ), 'PII is never refilled a second time.' );
	}

	/** Retained validation feedback follows the language when the customer switches pages. */
	public function test_retained_error_changes_language_with_the_request_page(): void {
		wc_load_cart();
		$error  = WC()->session->get( 'linker_inquiry_error' );
		$locale = WC()->session->get( 'linker_inquiry_error_locale' );
		$this->later(
			static function () use ( $error, $locale ): void {
				WC()->session->set( 'linker_inquiry_error', $error );
				WC()->session->set( 'linker_inquiry_error_locale', $locale );
			}
		);
		WC()->session->set( 'linker_inquiry_error', 'Please add a product or write a message.' );
		WC()->session->set( 'linker_inquiry_error_locale', 'en_US' );
		$language = new \Linker\Commerce\Mail\LocaleSwitch();
		$language->to( 'de_DE_formal' );
		try {
			$this->assertStringContainsString( 'Bitte prüfen Sie Ihre Angaben und senden Sie das Formular erneut.', ( new \Linker\Commerce\Inquiry\Form() )->render() );
			$this->assertNull( WC()->session->get( 'linker_inquiry_error' ) );
		} finally {
			$language->back();
		}
	}

	/** A German form's validation does not send the customer back with English text. */
	public function test_german_form_validation_is_german(): void {
		$error = ( new \Linker\Commerce\Inquiry\Handler() )->process( array( 'lang' => 'de' ) );
		$this->assertInstanceOf( \WP_Error::class, $error );
		$this->assertSame( 'Bitte prüfen Sie Ihre Angaben und senden Sie das Formular erneut.', $error->get_error_message() );
	}


	/**
	 * The shared browser adapter honors its language field without global POST state.
	 */
	public function test_german_message_without_products_uses_the_german_receipt_and_url(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$stamp = (string) ( time() - 5 );
		$order = ( new \Linker\Commerce\Inquiry\Handler() )->process(
			array(
				'name'                 => 'Maria Weber',
				'email'                => 'guest@example.test',
				'message'              => 'Bitte kontaktieren Sie mich.',
				'consent'              => '1',
				'lang'                 => 'de',
				'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
				'linker_started'       => $stamp,
				'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			)
		);
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( 'de_DE_formal', $order->get_meta( '_linker_locale' ) );
		$this->assertStringContainsString( '/de/proforma-anfrage/', $order->get_checkout_order_received_url() );
		$this->assertSame( 0, $order->get_item_count() );
		$this->assertSame( array(), $order->get_order_item_totals(), 'A message alone has no monetary total.' );
	}

	/** Admin-post is an admin request; the stored product line must still use the form's language. */
	public function test_german_product_inquiry_keeps_canonical_product_and_translated_line(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$english = $this->product( '125' );
		$german  = $this->product( '125' );
		$german->set_name( 'Testprodukt für eine Anfrage' );
		$german->save();
		pll_set_post_language( $english->get_id(), 'en' );
		pll_set_post_language( $german->get_id(), 'de' );
		pll_save_post_translations(
			array(
				'en' => $english->get_id(),
				'de' => $german->get_id(),
			)
		);
		WC()->cart->add_to_cart( $english->get_id(), 2 );
		$details = Submission::from_post(
			array(
				'name'    => 'Maria Test',
				'email'   => 'guest@example.test',
				'consent' => '1',
				'lang'    => 'de',
			),
			false
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->request( $details );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$item = current( $order->get_items() );
		$this->assertInstanceOf( \WC_Order_Item_Product::class, $item );
		$this->assertSame( $english->get_id(), $item->get_product_id() );
		$this->assertSame( 'Testprodukt für eine Anfrage', $item->get_name() );
	}

	/**
	 * All invalid public attempts stop before records or notifications exist.
	 */
	public function test_bots_and_invalid_details_cannot_create_an_inquiry_or_mail(): void {
		$this->as_user( 0 );
		$marker = self::newest_mail_job();
		$stamp  = (string) ( time() - 5 );
		$post   = array(
			'name'                 => 'Maria Weber',
			'email'                => 'bot-' . self::tag() . '@example.test',
			'message'              => 'A question.',
			'consent'              => '1',
			'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		$now    = (string) time();
		foreach ( array(
			array( 'website' => 'spam' ),
			array(
				'linker_started'       => $now,
				'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $now ),
			),
			array( 'linker_started_nonce' => 'forged' ),
			array( 'linker_inquiry_nonce' => 'forged' ),
			array( 'name' => '' ),
			array( 'email' => 'invalid' ),
			array( 'consent' => '' ),
		) as $invalid ) {
			$this->assertInstanceOf( \WP_Error::class, ( new \Linker\Commerce\Inquiry\Handler() )->process( array_replace( $post, $invalid ) ) );
		}
		$this->assertSame(
			array(),
			wc_get_orders(
				array(
					'billing_email' => $post['email'],
					'return'        => 'ids',
				)
			)
		);
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/**
	 * The receipt key is needed to attach an inquiry to an optional new account.
	 */
	public function test_account_link_claim_requires_both_the_key_and_the_same_email(): void {
		$customer = $this->customer();
		$order    = new WC_Order();
		$order->set_billing_email( $customer->get_billing_email() );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$order->set_customer_id( 0 );
		$order->save();
		$saved = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Saving test request state.
		$this->later(
			static function () use ( $saved ): void {
				$_GET = $saved;
			}
		);
		$_GET = array(
			'linker_inquiry' => $order->get_id(),
			'linker_key'     => 'forged',
		);
		$link = new \Linker\Commerce\Inquiry\AccountLink();
		$link->claim( $customer->get_id() );
		$this->assertSame( '', $link::email() );
		$loaded = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $loaded );
		$this->assertSame( 0, $loaded->get_customer_id() );
		$_GET['linker_key'] = $order->get_order_key();
		$this->assertSame( $customer->get_billing_email(), $link::email() );
		$link->claim( $customer->get_id() );
		$loaded = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $loaded );
		$this->assertSame( $customer->get_id(), $loaded->get_customer_id() );
	}

	/**
	 * A guest can send products without an account or an address.
	 */
	public function test_guest_sends_the_solution_draft_and_receives_a_receipt(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$product = $this->product( '125' );
		WC()->cart->add_to_cart( $product->get_id(), 2 );
		WC()->cart->calculate_totals();
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$details = Submission::from_post(
			array(
				'name'    => 'Maria Weber',
				'email'   => 'guest@example.test',
				'consent' => '1',
			),
			false
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->request( $details );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( 'inquiry-received', $order->get_status() );
		$this->assertSame( 0, $order->get_customer_id() );
		$this->assertSame( 'guest@example.test', $order->get_billing_email() );
		$this->assertSame( '', $order->get_billing_country() );
		$this->assertSame( 2, $order->get_item_count() );
		$this->assertSame( array(), $order->get_order_item_totals(), 'Unpriced inquiries must not present zero as a quoted total.' );
		$product = wc_get_product( $product->get_id() );
		$this->assertInstanceOf( \WC_Product::class, $product );
		$this->assertSame( '10', (string) $product->get_stock_quantity() );
	}
	/**
	 * Bots must be stopped before a record or email can be created.
	 */
	public function test_public_guard_requires_a_signed_time_and_an_empty_honeypot(): void {
		$stamp  = (string) ( time() - 5 );
		$post   = array(
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			'website'              => '',
		);
		$fields = ( new PublicGuard() )->fields();
		$this->assertStringContainsString( 'name="website"', $fields, 'Both doors receive the trap from the shared guard.' );
		$this->assertStringContainsString( 'aria-label="Website"', $fields );
		$this->assertTrue( ( new PublicGuard() )->allows( $post ) );
		$this->assertFalse( ( new PublicGuard() )->allows( array_replace( $post, array( 'website' => 'spam' ) ) ) );
		$this->assertFalse( ( new PublicGuard() )->allows( array_replace( $post, array( 'linker_started' => (string) time() ) ) ) );
		$this->assertFalse( ( new PublicGuard() )->allows( array_replace( $post, array( 'linker_started_nonce' => 'forged' ) ) ) );
	}
	/**
	 * Contact submissions must be visible in the same native inquiry list.
	 */
	public function test_contact_message_creates_one_inquiry_without_consuming_the_draft(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$product = $this->product( '100' );
		WC()->cart->add_to_cart( $product->get_id(), 1 );
		$stamp = (string) ( time() - 5 );
		$email = 'contact-' . self::tag() . '@example.test';
		$post  = array(
			'name'                 => 'Maria Weber',
			'email'                => $email,
			'message'              => 'A contact question.',
			'consent'              => '1',
			'linker_contact_nonce' => wp_create_nonce( 'linker_contact_form' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		WC()->mailer();
		$address                = $_SERVER['REMOTE_ADDR'] ?? null; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Preserve the exact test runner value for restoration.
		$_SERVER['REMOTE_ADDR'] = '127.246.0.1';
		$limit_key              = 'linker_contact_' . md5( '127.246.0.1' );
		$recent                 = get_transient( $limit_key );
		delete_transient( $limit_key );
		$this->later(
			static function () use ( $limit_key, $recent, $address ): void {
				delete_transient( $limit_key );
				if ( false !== $recent ) {
					set_transient( $limit_key, $recent, HOUR_IN_SECONDS );
				} if ( null === $address ) {
					unset( $_SERVER['REMOTE_ADDR'] );
				} else {
					$_SERVER['REMOTE_ADDR'] = $address;
				}
			}
		);
		$handler = new \Linker\Commerce\Contact\Handler();
		$this->assertSame( 'sent', $handler->process( $post ) );
		$orders = wc_get_orders(
			array(
				'billing_email' => $email,
				'limit'         => -1,
			)
		);
		$this->assertIsArray( $orders );
		foreach ( $orders as $order ) {
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
		}
		$this->assertCount( 1, $orders );
		$this->assertSame( 'inquiry-received', $orders[0]->get_status() );
		$this->assertSame( 0, $orders[0]->get_item_count() );
		$this->assertSame( 'A contact question.', $orders[0]->get_customer_note() );
		$this->assertSame( 1, WC()->cart->get_cart_contents_count() );
	}
	/**
	 * Approval controls price visibility, never whether an inquiry may be sent.
	 *
	 * @dataProvider account_states
	 * @param        string $status Account status.
	 */
	public function test_every_account_state_sends_with_its_saved_details( string $status ): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), 'billing_vat_id', 'DE123456789' );
		update_user_meta( $customer->get_id(), 'linker_vat_status', 'valid' );
		update_user_meta( $customer->get_id(), 'linker_vat_checked_number', 'DE123456789' );
		update_user_meta( $customer->get_id(), \Linker\Commerce\Registration\Approval::STATUS_META, $status );
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$product = $this->product( '125' );
		WC()->cart->add_to_cart( $product->get_id(), 2 );
		$stamp  = (string) ( time() - 5 );
		$post   = array(
			'name'                 => 'Maria Beispiel',
			'email'                => $customer->get_billing_email(),
			'consent'              => '1',
			'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		$result = ( new \Linker\Commerce\Inquiry\Handler() )->process( $post );
		$this->assertInstanceOf( WC_Order::class, $result );
		$this->later(
			static function () use ( $result ): void {
				$result->delete( true );
			}
		);
		$this->assertSame( 'inquiry-received', $result->get_status() );
		$this->assertSame( $customer->get_id(), $result->get_customer_id() );
		$this->assertSame( 'Teststraße 1', $result->get_billing_address_1() );
		$this->assertSame( 'DE123456789', $result->get_meta( '_billing_vat_id' ) );
		$this->assertSame( 'valid', get_user_meta( $customer->get_id(), 'linker_vat_status', true ) );
		$this->assertSame( 2, $result->get_item_count() );
		foreach ( $result->get_items() as $line ) {
			$this->assertInstanceOf( \WC_Order_Item_Product::class, $line );
			$this->assertSame( 'approved' === $status ? '' : ( 'pending' === $status ? 'approval' : 'unavailable' ), $line->get_meta( '_linker_price_reason' ) );
		}
	}

	/**
	 * Billing edits apply only to this inquiry, including clearing or changing VAT.
	 *
	 * @testWith ["", "none"]
	 *           ["CHE123456789", "unverified"]
	 * @param string $vat Inquiry-specific VAT.
	 * @param string $verdict Expected inquiry verdict.
	 */
	public function test_account_billing_fields_prefill_and_send_the_edited_address( string $vat, string $verdict ): void {
		$customer = $this->customer();
		$customer->update_meta_data( 'billing_vat_id', 'DE123456789' );
		$customer->save();
		update_user_meta( $customer->get_id(), 'linker_vat_checked_number', 'DE123456789' );
		update_user_meta( $customer->get_id(), 'linker_vat_status', 'valid' );
		$account_vat = array();
		foreach ( array( 'billing_vat_id', 'linker_vat_status', 'linker_vat_detail', 'linker_vat_checked_number', 'linker_vat_checked_at' ) as $key ) {
			$account_vat[ $key ] = get_user_meta( $customer->get_id(), $key, true );
		}
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();
		$fields = \Linker\Commerce\Inquiry\BillingFields::render();
		$this->assertStringContainsString( 'name="billing_address_1"', $fields );
		$this->assertStringContainsString( 'value="Teststraße 1"', $fields );
		$this->assertStringContainsString( 'name="billing_vat_id"', $fields );
		$this->assertStringContainsString( 'value="DE123456789"', $fields );
		$stamp  = (string) ( time() - 5 );
		$result = ( new \Linker\Commerce\Inquiry\Handler() )->process(
			array(
				'name'                 => 'Maria Beispiel',
				'email'                => $customer->get_billing_email(),
				'message'              => 'Please send a Proforma for this address.',
				'consent'              => '1',
				'billing_address_1'    => 'Teststraße 246',
				'billing_vat_id'       => $vat,
				'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
				'linker_started'       => $stamp,
				'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			)
		);
		$this->assertInstanceOf( WC_Order::class, $result );
		$this->later(
			static function () use ( $result ): void {
				$result->delete( true );
			}
		);
		$this->assertSame( 'Teststraße 246', $result->get_billing_address_1() );
		$this->assertSame( $vat, $result->get_meta( '_billing_vat_id' ) );
		$this->assertSame( $verdict, $result->get_meta( '_linker_vat_status' ) );
		foreach ( $account_vat as $key => $saved ) {
			$this->assertSame( $saved, get_user_meta( $customer->get_id(), $key, true ), 'Inquiry edits preserve account VAT metadata: ' . $key );
		}
		$this->as_user( 0 );
		$this->assertSame( '', \Linker\Commerce\Inquiry\BillingFields::render(), 'Guests are never asked for billing fields.' );
		$this->assertSame( array(), \Linker\Commerce\Inquiry\BillingFields::values( array( 'billing_country' => 'DE' ) ), 'Guest billing input is ignored.' );
	}

	/** Restricted accounts read the reason above a usable form in both languages. */
	public function test_restricted_reason_does_not_close_the_request_form(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), \Linker\Commerce\Registration\Approval::STATUS_META, 'restricted' );
		update_user_meta( $customer->get_id(), \Linker\Commerce\Registration\Approval::REASON_META, 'Please add your company VAT ID.' );
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		$tags = $GLOBALS['shortcode_tags'];
		$this->later(
			static function () use ( $tags ): void {
				$GLOBALS['shortcode_tags'] = $tags;
			}
		);
		( new \Linker\Commerce\Inquiry\Form() )->register();
		$language = new \Linker\Commerce\Mail\LocaleSwitch();
		foreach ( array(
			'en_US'        => 'You can send inquiries.',
			'de_DE_formal' => 'Sie können Anfragen senden.',
		) as $locale => $notice ) {
			$language->to( $locale );
			try {
				$html = do_shortcode( '[linker_inquiry_form]' );
				$this->assertStringContainsString( $notice, $html );
				$this->assertStringContainsString( 'Please add your company VAT ID.', $html );
				$this->assertLessThan( strpos( $html, '<form ' ), strpos( $html, 'Please add your company VAT ID.' ) );
				$this->assertStringContainsString( 'type="submit"', $html );
				$this->assertStringNotContainsString( 'paused', $html );
			} finally {
				$language->back();
			}
		}
	}

	/**
	 * Account states from the owner ruling.
	 *
	 * @return array<string, array{string}>
	 */
	public static function account_states(): array {
		return array(
			'pending'    => array( 'pending' ),
			'restricted' => array( 'restricted' ),
			'approved'   => array( 'approved' ),
		);
	}

	/**
	 * The actual sender queues one team notification and one receipt.
	 */
	public function test_sender_routes_the_team_mail_and_receipt_through_outbox(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$saved = array();
		foreach ( array( 'linker_commerce_notify_to', 'linker_commerce_team_bcc', 'woocommerce_linker_new_inquiry_settings', 'woocommerce_linker_inquiry_received_settings' ) as $option ) {
			$saved[ $option ] = get_option( $option );
			delete_option( $option );
		}
		$this->later(
			static function () use ( $saved ): void {
				foreach ( $saved as $option => $value ) {
					if ( false === $value ) {
						delete_option( $option );
					} else {
						update_option( $option, $value );
					}
				}
			}
		);
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$marker  = self::newest_mail_job();
		$details = Submission::from_post(
			array(
				'name'    => 'Maria Weber',
				'email'   => 'guest@example.test',
				'message' => 'Please help with my project.',
				'consent' => '1',
			)
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->message( $details );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$rows = array_map( static fn ( int $id ) => json_decode( (string) get_post_meta( $id, '_linker_mail_message', true ), true ), self::mail_jobs_after( $marker ) );
		$this->assertCount( 2, $rows );
		$recipients = array_column( $rows, 'to' );
		$this->assertContains( array( 'sales@sunriverinverter.com' ), $recipients );
		$this->assertContains( array( 'guest@example.test' ), $recipients );
		$this->assertNotContains( array( 'sales@de-linker.com' ), $recipients );
	}
}
