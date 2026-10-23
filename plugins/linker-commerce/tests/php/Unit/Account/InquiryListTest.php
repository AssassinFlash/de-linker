<?php
/**
 * Tests for the customer's inquiries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\InquiryList;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WC_Order_Item_Product;
use WP_Mock;

/**
 * Tests for InquiryList.
 *
 * @covers \Linker\Commerce\Account\InquiryList
 */
final class InquiryListTest extends TestCase {

	/**
	 * Translation and escaping return their input; links are built plainly.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( $key, $value, $url = '' ) => is_array( $key ) ? $value . '?' . http_build_query( $key ) : $url . '?' . $key . '=' . $value ) );
		WP_Mock::userFunction( 'wc_get_cart_url', array( 'return' => 'https://example.test/cart/' ) );
		WP_Mock::userFunction( 'wp_nonce_url', array( 'return' => static fn ( string $url, string $action ): string => $url . '&_wpnonce=' . $action ) );
	}

	/**
	 * An inquiry.
	 *
	 * @param string $number Proforma number.
	 * @param bool   $again  Whether its status allows "request again".
	 * @param string $status Stored status slug.
	 * @return WC_Order&\Mockery\MockInterface
	 */
	private function inquiry( string $number, bool $again, string $status = 'completed' ) {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_view_order_url' )->andReturn( 'https://example.test/my-account/inquiry/20/' );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( $number );
		$order->allows( 'has_status' )->andReturnUsing(
			static function ( $asked ) use ( $again, $status ): bool {
				// The "request again" check passes the status list; the Proforma
				// check passes one status. $again is the test's switch for the list.
				if ( is_array( $asked ) ) {
					return $again && in_array( $status, $asked, true );
				}
				return $asked === $status;
			}
		);
		return $order;
	}

	/**
	 * Number, date, status, amount, actions.
	 */
	public function test_columns(): void {
		$this->assertSame( array( 'Inquiry', 'Date', 'Status', 'Amount', 'Actions' ), array_values( ( new InquiryList() )->columns() ) );
	}

	/**
	 * View, the Proforma once issued, and "Request again" in the list; WooCommerce's pay and cancel buttons are gone.
	 * The inquiry page (WooCommerce's own button) and the confirmation offer no "Request again" of ours.
	 */
	public function test_actions(): void {
		$this->filter_returns( 'woocommerce_valid_order_statuses_for_order_again', array( 'completed', 'inquiry-received', 'proforma-issued', 'cancelled' ), array( array( 'completed' ) ) );
		$endpoint = '';
		WP_Mock::userFunction(
			'is_wc_endpoint_url',
			array(
				'return' => static function ( string $asked ) use ( &$endpoint ): bool {
					return $asked === $endpoint;
				},
			)
		);
		$list     = new InquiryList();
		$woo_list = array(
			'pay'    => array(
				'url'  => 'https://example.test/pay/',
				'name' => 'Pay',
			),
			'cancel' => array(
				'url'  => 'https://example.test/cancel/',
				'name' => 'Cancel',
			),
		);
		$actions  = $list->actions( $woo_list, $this->inquiry( 'PI-2026-0001', true ) );

		$this->assertSame( array( 'view', 'proforma', 'request-again' ), array_keys( $actions ) );
		$this->assertSame( 'https://example.test/?linker-document=proforma&id=20', $actions['proforma']['url'] );
		$this->assertSame( 'https://example.test/cart/?order_again=20&_wpnonce=woocommerce-order_again', $actions['request-again']['url'] );
		$this->assertSame( 'Request again', $actions['request-again']['name'] );

		// A stored number offers the download even when the status list would not. An empty number does not, in any status.
		$issued = $list->actions( $woo_list, $this->inquiry( 'PI-2026-0008', false, Statuses::PROFORMA ) );
		$this->assertSame( array( 'view', 'proforma' ), array_keys( $issued ) );
		$this->assertSame( 'https://example.test/?linker-document=proforma&id=20', $issued['proforma']['url'] );
		$this->assertSame( 'Proforma invoice (PDF)', $issued['proforma']['name'] );
			$this->assertSame( array( 'view' ), array_keys( $list->actions( $woo_list, $this->inquiry( '', false, Statuses::PROFORMA ) ) ) );
			$this->assertSame( array( 'view' ), array_keys( $list->actions( $woo_list, $this->inquiry( '', false, Statuses::RECEIVED ) ) ) );

			// Completed keeps the download. The number is what the customer reads, not the status word.
			$completed = $list->actions( $woo_list, $this->inquiry( 'DLK-PF-2026-0003', false, 'completed' ) );
			$this->assertSame( array( 'view', 'proforma' ), array_keys( $completed ) );
			$this->assertSame( 'https://example.test/?linker-document=proforma&id=20', $completed['proforma']['url'] );
			$this->assertSame( 'Proforma invoice (PDF)', $completed['proforma']['name'] );

		foreach ( array( 'view-order', 'order-received' ) as $endpoint ) {
			$this->assertSame( array( 'view', 'proforma' ), array_keys( $list->actions( $woo_list, $this->inquiry( 'PI-2026-0001', true ) ) ), $endpoint );
		}
	}

	/** A withdrawn product never supplies a new download link to historical inquiries. */
	public function test_withdrawn_product_has_no_current_datasheet_link(): void {
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => 'product' ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => 'draft' ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'times' => 0 ) );
		$item = Mockery::mock( WC_Order_Item_Product::class );
		$item->allows( 'get_product_id' )->andReturn( 4107 );
		$order = Mockery::mock( WC_Order::class );
		$list  = new InquiryList();
		ob_start();
		$list->datasheet_link( 1, $item, $order, true );
		$list->datasheet_link( 1, $item, $order );
		$this->assertSame( '', ob_get_clean() );
	}
}
