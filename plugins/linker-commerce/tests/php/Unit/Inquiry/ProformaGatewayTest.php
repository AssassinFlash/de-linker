<?php
/**
 * Tests for the Proforma gateway.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\ProformaGateway;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Tests for ProformaGateway.
 *
 * @covers \Linker\Commerce\Inquiry\ProformaGateway
 */
final class ProformaGatewayTest extends TestCase {

	/**
	 * The gateway has no fields, is always on and is named in the visitor's language.
	 */
	public function test_setup_and_texts(): void {
		WP_Mock::passthruFunction( '__' );
		$this->filter_returns( 'woocommerce_gateway_title', 'Proforma invoice', array( 'Proforma invoice', 'linker_proforma' ) );
		$this->filter_returns( 'woocommerce_gateway_description', 'We check your inquiry and send you a Proforma invoice.', array( 'We check your inquiry and send you a Proforma invoice.', 'linker_proforma' ) );
		$gateway = new ProformaGateway();

		$this->assertSame( 'linker_proforma', $gateway->id );
		$this->assertFalse( $gateway->has_fields );
		$this->assertSame( 'yes', $gateway->enabled );
		$this->assertFalse( $gateway->needs_setup() );
		$this->assertSame( 'Proforma invoice', $gateway->get_title() );
		$this->assertSame( 'We check your inquiry and send you a Proforma invoice.', $gateway->get_description() );
		$this->assertSame( 'Proforma invoice', $gateway->get_method_title() );
		$this->assertStringContainsString( 'without payment', $gateway->get_method_description() );
	}

	/**
	 * Sending marks the inquiry as received, empties the solution draft and opens the confirmation.
	 */
	public function test_process_payment_receives_the_inquiry(): void {
		$order = Mockery::mock( WC_Order::class );
		$order->expects( 'update_status' )->with( Statuses::RECEIVED );
		WP_Mock::userFunction(
			'wc_get_order',
			array(
				'args'   => array( 20 ),
				'return' => $order,
			)
		);
		$cart = Mockery::mock();
		$cart->expects( 'empty_cart' );
		$woocommerce       = new \stdClass();
		$woocommerce->cart = $cart;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );

		$this->assertSame(
			array(
				'result'   => 'success',
				'redirect' => 'https://example.test/proforma-request/inquiry-received/',
			),
			( new ProformaGateway() )->process_payment( 20 )
		);
	}

	/**
	 * Without an order nothing happens.
	 */
	public function test_process_payment_without_order(): void {
		WP_Mock::userFunction( 'wc_get_order', array( 'return' => false ) );

		$this->assertSame( 'failure', ( new ProformaGateway() )->process_payment( 20 )['result'] );
	}
}
