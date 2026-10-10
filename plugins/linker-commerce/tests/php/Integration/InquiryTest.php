<?php
/**
 * An inquiry through WooCommerce's checkout.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Inquiry\OrderLocale;
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
}
