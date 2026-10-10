<?php
/**
 * Tests for the content of a Proforma invoice.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Proforma;

use DateTimeImmutable;
use DateTimeZone;
use Linker\Commerce\Proforma\Document;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WC_Order_Item_Fee;
use WC_Order_Item_Product;
use WC_Product;
use WP_Mock;

/**
 * Tests for Document.
 *
 * @covers \Linker\Commerce\Proforma\Document
 */
final class DocumentTest extends TestCase {

	/**
	 * Valid for 30 days (owner ruling 2026-10-09).
	 */
	public function test_valid_until(): void {
		$issued = new DateTimeImmutable( '2026-10-09 15:00', new DateTimeZone( 'Europe/Berlin' ) );

		$this->assertSame( 30, Document::VALID_DAYS );
		$this->assertSame( '2026-11-08', Document::valid_until( $issued )->format( 'Y-m-d' ) );
	}

	/**
	 * The document carries number, dates, seller, bank, buyer, lines with net prices, fees, tax and total.
	 */
	public function test_data(): void {
		WP_Mock::userFunction( '_x', array( 'return' => 'Y-m-d' ) );
		WP_Mock::userFunction( 'wp_date', array( 'return' => static fn ( string $format, int $time ): string => gmdate( $format, $time ) ) );
		WP_Mock::userFunction( 'wc_price', array( 'return' => static fn ( float $amount ): string => '€' . number_format( $amount, 2 ) ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		$this->options(
			array(
				Options::BANK_IBAN            => 'DE89370400440532013000',
				Options::BANK_HOLDER          => 'Linker Technology GmbH',
				'woocommerce_store_address'   => 'Steinfeldstraße 3',
				'woocommerce_store_postcode'  => '39179',
				'woocommerce_store_city'      => 'Barleben',
				'woocommerce_default_country' => 'DE:DE-ST',
			)
		);
		$countries = Mockery::mock();
		$countries->allows( 'get_formatted_address' )->andReturn( 'Teststraße 1<br/>39179 Barleben' );
		$countries->allows( 'get_countries' )->andReturn( array( 'DE' => 'Germany' ) );
		$woocommerce            = new \stdClass();
		$woocommerce->countries = $countries;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );

		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_sku' )->andReturn( 'DLK-SAJ-H210KT3' );
		$line = Mockery::mock( WC_Order_Item_Product::class );
		$line->allows( 'get_product' )->andReturn( $product );
		$line->allows( 'get_name' )->andReturn( 'SAJ H2-10K-T3' );
		$line->allows( 'get_quantity' )->andReturn( 2 );
		$line->allows( 'get_total' )->andReturn( '3360' );
		$fee = Mockery::mock( WC_Order_Item_Fee::class );
		$fee->allows( 'get_name' )->andReturn( 'Freight' );
		$fee->allows( 'get_total' )->andReturn( '150' );
		$tax                   = new \stdClass();
		$tax->label            = 'MwSt. 19%';
		$tax->formatted_amount = '€666.90';

		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_currency' )->andReturn( 'EUR' );
		$order->allows( 'get_items' )->andReturn( array( $line ) );
		$order->allows( 'get_item_subtotal' )->with( $line, false, true )->andReturn( 1680.0 );
		$order->allows( 'get_fees' )->andReturn( array( $fee ) );
		$order->allows( 'get_tax_totals' )->andReturn( array( 'DE-MWST' => $tax ) );
		$order->allows( 'get_address' )->with( 'billing' )->andReturn(
			array(
				'company'    => 'Solarbau GmbH',
				'first_name' => 'Maria',
				'address_1'  => 'Teststraße 1',
			)
		);
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_billing_company' )->andReturn( 'Solarbau GmbH' );
		$order->allows( 'get_formatted_billing_full_name' )->andReturn( 'Maria Beispiel' );
		$order->allows( 'get_meta' )->with( '_billing_vat_id' )->andReturn( 'DE143454214' );
		$order->allows( 'get_billing_email' )->andReturn( 'maria@example.test' );
		$order->allows( 'get_subtotal' )->andReturn( 3360.0 );
		$order->allows( 'get_total' )->andReturn( '4176.90' );

		$data = ( new Document( new Options() ) )->data( $order, 'PI-2026-0001', new DateTimeImmutable( '2026-10-09 12:00 UTC' ) );

		$this->assertSame( 'PI-2026-0001', $data['number'] );
		$this->assertSame( '#20', $data['inquiry'] );
		$this->assertSame( '2026-10-09', $data['issued'] );
		$this->assertSame( '2026-11-08', $data['valid_until'] );
		$this->assertSame( array( 'Steinfeldstraße 3', '39179 Barleben', 'Germany' ), $data['seller']['address'] );
		$this->assertSame( 'DE89370400440532013000', $data['bank']['iban'] );
		$this->assertSame(
			array(
				'company' => 'Solarbau GmbH',
				'name'    => 'Maria Beispiel',
				'address' => array( 'Teststraße 1', '39179 Barleben' ),
				'vat_id'  => 'DE143454214',
				'email'   => 'maria@example.test',
			),
			$data['buyer']
		);
		$this->assertSame(
			array(
				array(
					'position' => 1,
					'name'     => 'SAJ H2-10K-T3',
					'sku'      => 'DLK-SAJ-H210KT3',
					'quantity' => 2,
					'unit'     => '€1,680.00',
					'total'    => '€3,360.00',
				),
			),
			$data['lines']
		);
		$this->assertSame(
			array(
				array(
					'name'  => 'Freight',
					'total' => '€150.00',
				),
			),
			$data['fees']
		);
		$this->assertSame(
			array(
				array(
					'label'  => 'MwSt. 19%',
					'amount' => '€666.90',
				),
			),
			$data['taxes']
		);
		$this->assertSame( '€4,176.90', $data['total'] );
	}
}
