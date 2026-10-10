<?php
/**
 * Tests for the VAT ID as a billing field.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\BillingVatField;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Customer;
use WC_Order;
use WP_Mock;

/**
 * Tests for BillingVatField.
 *
 * @covers \Linker\Commerce\Registration\BillingVatField
 */
final class BillingVatFieldTest extends TestCase {

	/**
	 * User meta of the customer.
	 *
	 * @var array<string, mixed>
	 */
	private array $meta = array();

	/**
	 * Translation returns its source; user meta lives in $meta.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'get_user_meta', array( 'return' => fn ( int $id, string $key ) => $this->meta[ $key ] ?? '' ) );
	}

	/**
	 * The field follows the company field on the request page and the company page.
	 */
	public function test_billing_fields(): void {
		$fields = ( new BillingVatField( new VatProfile( new ViesClient() ) ) )->billing_fields( array( 'billing_company' => array( 'priority' => 30 ) ) );

		$this->assertSame( 31, $fields[ VatProfile::VAT_META ]['priority'] );
		$this->assertFalse( $fields[ VatProfile::VAT_META ]['required'] );
	}

	/**
	 * Staff see and edit the VAT ID on the inquiry, and the verdict under the address.
	 */
	public function test_admin(): void {
		$field = new BillingVatField( new VatProfile( new ViesClient() ) );
		$this->assertTrue( $field->admin_billing_fields( array() )['vat_id']['show'] );

		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_meta' )->with( VatProfile::ORDER_STATUS )->andReturn( VatProfile::INVALID );
		ob_start();
		$field->admin_order_verdict( $order );
		$this->assertSame( '<p class="linker-vat-status"><strong>VAT check:</strong> Not valid according to VIES – review</p>', ob_get_clean() );
	}

	/**
	 * The user profile shows the VAT ID with the billing fields and the business type and verdict in a section of their own.
	 */
	public function test_profile_fields(): void {
		$sections = ( new BillingVatField( new VatProfile( new ViesClient() ) ) )->profile_fields( array( 'billing' => array( 'fields' => array() ) ) );

		$this->assertArrayHasKey( VatProfile::VAT_META, $sections['billing']['fields'] );
		$this->assertSame( array( CustomerRole::META, VatProfile::STATUS_META ), array_keys( $sections['linker']['fields'] ) );
	}

	/**
	 * Saving the billing address checks a changed VAT ID again; the shipping address does not.
	 */
	public function test_after_address_saved(): void {
		$this->meta = array(
			VatProfile::VAT_META    => '',
			VatProfile::STATUS_META => VatProfile::VALID,
			VatProfile::DETAIL_META => '',
			VatProfile::NUMBER_META => 'DE143454214',
		);
		WP_Mock::userFunction( 'update_user_meta', array( 'times' => 4 ) );
		WP_Mock::expectAction( VatProfile::CHANGED_ACTION, 5, VatProfile::VALID, VatProfile::NONE );
		$field = new BillingVatField( new VatProfile( new ViesClient() ) );

		$field->after_address_saved( 5, 'shipping' );
		$field->after_address_saved( 5, 'billing' );

		$this->assertConditionsMet();
	}

	/**
	 * A sent inquiry checks the VAT ID given on the request page and keeps the verdict.
	 */
	public function test_on_inquiry(): void {
		$this->meta = array(
			VatProfile::STATUS_META => VatProfile::VALID,
			VatProfile::DETAIL_META => '',
			VatProfile::NUMBER_META => 'DE143454214',
		);
		$order      = Mockery::mock( WC_Order::class );
		$order->allows( 'get_customer_id' )->andReturn( 5 );
		$order->allows( 'get_meta' )->with( '_' . VatProfile::VAT_META )->andReturn( 'DE 143454214' );
		$order->expects( 'update_meta_data' )->with( VatProfile::ORDER_STATUS, VatProfile::VALID );

		( new BillingVatField( new VatProfile( new ViesClient() ) ) )->on_inquiry( $order );

		$this->assertConditionsMet();
	}

	/**
	 * The stored VAT ID has no spaces, dots or hyphens.
	 */
	public function test_normalize(): void {
		$customer = Mockery::mock( WC_Customer::class );
		$customer->allows( 'get_meta' )->with( VatProfile::VAT_META )->andReturn( 'de 143.454-214' );
		$customer->expects( 'update_meta_data' )->with( VatProfile::VAT_META, 'DE143454214' );

		( new BillingVatField( new VatProfile( new ViesClient() ) ) )->normalize( $customer );

		$this->assertConditionsMet();
	}
}
