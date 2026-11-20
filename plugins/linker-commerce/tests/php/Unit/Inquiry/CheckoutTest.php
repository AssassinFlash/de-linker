<?php
/**
 * Tests for the Proforma request page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\Checkout;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\InquiryGateway;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use Mockery;
use WC_Order;

/**
 * Tests for Checkout.
 *
 * @covers \Linker\Commerce\Inquiry\Checkout
 */
final class CheckoutTest extends TestCase {
	/** Native success uses Woo's localized checkout address without command arguments. */
	public function test_after_add_uses_the_current_checkout_destination(): void {
		WP_Mock::userFunction(
			'wc_get_checkout_url',
			array(
				'return' => 'https://example.test/de/proforma-anfrage/',
				'times'  => 1,
			)
		);
		$this->assertSame( 'https://example.test/de/proforma-anfrage/', ( new Checkout() )->after_add_destination( false ) );
	}

	/** An existing explicit native destination remains authoritative. */
	public function test_after_add_preserves_an_existing_destination(): void {
		$this->assertSame( 'https://example.test/inquiry/', ( new Checkout() )->after_add_destination( 'https://example.test/inquiry/' ) );
	}


	/**
	 * Only the Proforma gateway is offered, even when other gateways are
	 * active; an account whose prices are not open gets none at all.
	 */
	public function test_gateways(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::APPROVED ) );
		$proforma = new \stdClass();
		$gateways = array(
			'bacs'             => new \stdClass(),
			InquiryGateway::ID => $proforma,
			'stripe'           => new \stdClass(),
		);

		$approved = new Checkout();
		$this->assertSame(
			array( InquiryGateway::ID => $proforma ),
			$approved->gateways( $gateways )
		);
		$this->assertSame( array(), $approved->gateways( array( 'bacs' => new \stdClass() ) ) );

		$this->approval_meta( array() );
		$this->assertSame( array( InquiryGateway::ID => $proforma ), ( new Checkout() )->gateways( $gateways ), 'Pending accounts may send inquiries.' );

		$this->signed_in( 0 );
		$guest = new Checkout();
		$this->assertSame(
			array( InquiryGateway::ID => $proforma ),
			$guest->gateways( $gateways ),
			'A guest reaches the checkout flow WooCommerce itself runs.'
		);
	}

	/**
	 * The stored inquiry has no payment method title.
	 */
	public function test_without_payment_method_title(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->expects( 'set_payment_method_title' )->with( '' );

		( new Checkout() )->without_payment_method_title( $order );

		$this->assertConditionsMet();
	}

	/**
	 * The reply promise (owner ruling 2026-10-09) above the button and on the confirmation.
	 */
	public function test_next_steps(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->shouldReceive( 'get_id' )->andReturn( 124 );
		$order->shouldReceive( 'get_order_number' )->andReturn( 'L-124' );
		$order->shouldReceive( 'get_customer_id' )->andReturn( 12 );
		$order->shouldReceive( 'get_meta' )->andReturn( '' );
		WP_Mock::userFunction(
			'wc_get_order',
			array(
				'args'   => array( 124 ),
				'return' => $order,
			)
		);

		$this->plain_text();
		$checkout = new Checkout();
		WP_Mock::userFunction(
			'wc_get_account_endpoint_url',
			array(
				'args'   => array( 'orders' ),
				'return' => 'http://site/my-account/inquiries/',
			)
		);

		ob_start();
		$checkout->next_steps( 124 );
		$html = (string) ob_get_clean();
		$this->assertStringContainsString( 'We reply within one business day to the email address you provided.', $html );
		$this->assertStringContainsString( 'Inquiry #L-124', $html );
		$this->assertStringContainsString( '<h1 id="linker-receipt-title">Inquiry received</h1>', $html );
		$this->assertStringContainsString( 'href="http://site/my-account/inquiries/"', $html );
		$this->assertStringContainsString( 'View inquiries', $html );
	}

	/** A receipt without a persisted order cannot announce that an inquiry arrived. */
	public function test_missing_order_emits_no_success(): void {
		ob_start();
		( new Checkout() )->next_steps();
		$this->assertSame( '', (string) ob_get_clean() );
	}

	/**
	 * A German inquiry confirms on the German request page: the English URL's
	 * page part is replaced, the endpoint and key stay.
	 */
	public function test_received_url_of_a_german_inquiry(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->shouldReceive( 'get_id' )->andReturn( 7021 );
		$order->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'de_DE_formal' );
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 36, 'de' ),
				'return' => 6925,
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'woocommerce_checkout_page_id' ),
				'return' => 36,
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 36 ),
				'return' => 'http://linker.test/proforma-request/',
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 6925 ),
				'return' => 'http://linker.test/de/proforma-anfrage/',
			)
		);

		$this->filter_returns( 'woocommerce_get_endpoint_url', 'http://linker.test/de/proforma-anfrage/inquiry-received/7021/?key=k', array( 'http://linker.test/de/proforma-anfrage/inquiry-received/7021/?key=k', 'order-received', '7021', 'http://linker.test/de/proforma-anfrage/' ) );
		$this->assertSame(
			'http://linker.test/de/proforma-anfrage/inquiry-received/7021/?key=k',
			( new Checkout() )->received_url( 'http://linker.test/proforma-request/inquiry-received/7021/?key=k', $order )
		);
	}

	/** Verifying a German guest order from its English receipt keeps that open receipt. */
	public function test_guest_email_verification_uses_the_open_receipt_language(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->shouldReceive( 'get_id' )->andReturn( 7021 );
		$order->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'de_DE_formal' );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'get_query_var',
			array(
				'args'   => array( 'order-received' ),
				'return' => '7021',
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'woocommerce_checkout_page_id' ),
				'return' => 36,
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 36, 'de' ),
				'return' => 6925,
			)
		);
		WP_Mock::userFunction( 'get_permalink', array( 'return' => static fn ( $id ) => 36 === $id ? 'http://localhost/request/' : 'http://localhost/de/anfrage/' ) );
		$url = 'http://localhost/request/inquiry-received/7021/?key=wc_order_example';
		$this->assertSame( $url, ( new Checkout() )->received_url( $url, $order ) );
	}

	/**
	 * An English inquiry keeps WooCommerce's URL, and so does one without Polylang.
	 */
	public function test_received_url_of_an_english_inquiry(): void {
		$english = Mockery::mock( WC_Order::class );
		$english->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'en_US' );
		$url = 'http://linker.test/proforma-request/inquiry-received/7021/?key=k';

		$this->assertSame( $url, ( new Checkout() )->received_url( $url, $english ) );
	}
}
