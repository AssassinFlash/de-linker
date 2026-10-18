<?php
/**
 * An inquiry through WooCommerce's checkout.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\Statuses;
use WC_Order_Item_Product;

/**
 * A customer's solution draft becomes an inquiry: the Proforma gateway is the
 * only one, the inquiry is "received", stock stays, and lines without a price
 * remember why.
 *
 * @coversNothing
 */
final class InquiryTest extends IntegrationTestCase {

	/**
	 * Sending an inquiry with a priced and an unpriced product.
	 */
	public function test_sending(): void {
		$priced   = $this->product( '1680' );
		$unpriced = $this->product( '' );
		$customer = $this->customer();

		$order = $this->send_inquiry(
			$customer,
			array(
				array( $priced, 2 ),
				array( $unpriced, 1 ),
			)
		);

		$this->assertSame( array( 'linker_proforma' ), array_keys( WC()->payment_gateways()->get_available_payment_gateways() ) );
		$this->assertSame( Statuses::RECEIVED, $order->get_status() );
		$this->assertSame( '', $order->get_payment_method_title() );
		$this->assertSame( determine_locale(), $order->get_meta( OrderLocale::META ) );
		$reasons = array();
		foreach ( $order->get_items() as $item ) {
			$this->assertInstanceOf( WC_Order_Item_Product::class, $item );
			$reasons[ $item->get_product_id() ] = $item->get_meta( PriceDisplay::ITEM_REASON_META );
		}
		$this->assertSame(
			array(
				$priced->get_id()   => '',
				$unpriced->get_id() => 'unpriced',
			),
			$reasons
		);
		$stocked = wc_get_product( $priced->get_id() );
		$this->assertInstanceOf( \WC_Product::class, $stocked );
		$this->assertSame( 10, $stocked->get_stock_quantity(), 'An inquiry reserves no stock.' );
		$this->assertTrue( WC()->cart->is_empty() );
	}

	/**
	 * The inquiry stores the conversation summary the team reads (#244).
	 */
	public function test_an_inquiry_carries_the_conversations_summary(): void {
		$product  = $this->product( '1000' );
		$customer = $this->customer();
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->customer = new WC_Customer( $customer->get_id(), true );
		WC()->cart->empty_cart();
		$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), 2 ) );
		WC()->cart->calculate_totals();

		$summary = array(
			'summary'    => 'Two inverters for a south-facing roof.',
			'quantities' => array(
				array(
					'product_id' => $product->get_id(),
					'quantity'   => 2,
				),
			),
			'conditions' => array( 'Three-phase connection' ),
			'note'       => 'We need them this quarter.',
			'source'     => 'model',
			'reason'     => null,
		);
		$filter  = static fn () => $summary;
		add_filter( 'linker_genie_inquiry_summary', $filter );
		$this->later( static fn () => remove_filter( 'linker_genie_inquiry_summary', $filter ) );

		$submission = Submission::from_post(
			array(
				'name'    => 'Maria Weber',
				'email'   => 'maria@example.test',
				'company' => 'Weber Solar',
				'message' => 'Please send a Proforma invoice.',
				'consent' => '1',
			),
			false
		);
		$this->assertInstanceOf( Submission::class, $submission );

		$order = ( new Sender() )->request( $submission );
		$this->assertInstanceOf( \WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);

		$this->assertSame( $summary, $order->get_meta( Sender::SUMMARY_META ) );
		$this->assertSame( Statuses::RECEIVED, $order->get_status() );
	}
}
