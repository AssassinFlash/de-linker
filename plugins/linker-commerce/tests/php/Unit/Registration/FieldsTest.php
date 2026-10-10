<?php
/**
 * Tests for the registration fields.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Error;
use WP_Mock;

/**
 * Tests for Fields. Saving on a real WooCommerce customer is tested in tests/php/Integration.
 *
 * @covers \Linker\Commerce\Registration\Fields
 */
final class FieldsTest extends TestCase {

	/**
	 * WooCommerce's address fields for Germany; allowed countries DE and AT.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$countries = Mockery::mock();
		$countries->allows( 'get_address_fields' )->andReturn(
			array(
				'billing_first_name' => array(
					'label'    => 'First name',
					'required' => true,
				),
				'billing_last_name'  => array(
					'label'    => 'Last name',
					'required' => true,
				),
				'billing_company'    => array(
					'label'    => 'Company name',
					'required' => false,
				),
				'billing_country'    => array(
					'type'     => 'country',
					'label'    => 'Country / Region',
					'required' => true,
				),
				'billing_address_1'  => array(
					'label'    => 'Street address',
					'required' => true,
				),
				'billing_address_2'  => array(
					'label'    => 'Apartment',
					'required' => false,
				),
				'billing_postcode'   => array(
					'label'    => 'Postcode',
					'required' => true,
				),
				'billing_city'       => array(
					'label'    => 'Town / City',
					'required' => true,
				),
				'billing_state'      => array(
					'label'    => 'State',
					'required' => false,
				),
			)
		);
		$countries->allows( 'get_allowed_countries' )->andReturn(
			array(
				'DE' => 'Germany',
				'AT' => 'Austria',
			)
		);
		$countries->allows( 'get_base_country' )->andReturn( 'DE' );
		$woocommerce            = new \stdClass();
		$woocommerce->countries = $countries;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => $value ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
	}

	/**
	 * Clears the posted form.
	 */
	public function tearDown(): void {
		$_POST = array();
		parent::tearDown();
	}

	/**
	 * Company (required), business type, VAT ID (optional), then WooCommerce's name and address fields;
	 * address line 2 and state are left out.
	 */
	public function test_fields(): void {
		$fields = ( new Fields( new VatProfile( new ViesClient() ) ) )->fields( 'DE' );

		$this->assertSame( array( 'billing_company', CustomerRole::META, VatProfile::VAT_META, 'billing_first_name', 'billing_last_name', 'billing_country', 'billing_address_1', 'billing_postcode', 'billing_city' ), array_keys( $fields ) );
		$this->assertTrue( $fields['billing_company']['required'] );
		$this->assertFalse( $fields[ VatProfile::VAT_META ]['required'] );
		$this->assertSame( array( '', 'installer', 'epc', 'distributor' ), array_keys( $fields[ CustomerRole::META ]['options'] ) );
	}

	/**
	 * The form is filled again with what was posted; the country defaults to the store's.
	 */
	public function test_render(): void {
		$_POST    = array( 'billing_company' => 'Solarbau GmbH' );
		$rendered = array();
		WP_Mock::userFunction(
			'woocommerce_form_field',
			array(
				'return' => function ( string $key, array $field, $value ) use ( &$rendered ): void {
					$rendered[ $key ] = $value;
				},
			)
		);

		( new Fields( new VatProfile( new ViesClient() ) ) )->render();

		$this->assertSame( 'Solarbau GmbH', $rendered['billing_company'] );
		$this->assertSame( 'DE', $rendered['billing_country'] );
		$this->assertSame( '', $rendered[ VatProfile::VAT_META ] );
	}

	/**
	 * Missing required fields, an unknown business type, a country outside the list and a wrong postcode are reported.
	 */
	public function test_validate_reports_errors(): void {
		$_POST  = array(
			CustomerRole::META => 'wholesaler',
			'billing_country'  => 'FR',
			'billing_postcode' => '123',
		);
		$errors = ( new Fields( new VatProfile( new ViesClient() ) ) )->validate( new WP_Error() );

		foreach ( array( 'billing_company', 'billing_first_name', 'billing_last_name', 'billing_address_1', 'billing_city', CustomerRole::META, 'billing_country' ) as $key ) {
			$this->assertContains( $key, $errors->get_error_codes(), $key );
		}
	}

	/**
	 * A complete registration passes, and without a validated registration save() does nothing.
	 */
	public function test_complete_registration_passes(): void {
		$_POST  = array(
			'billing_company'    => 'Solarbau GmbH',
			CustomerRole::META   => 'installer',
			VatProfile::VAT_META => 'DE 143 454 214',
			'billing_first_name' => 'Maria',
			'billing_last_name'  => 'Beispiel',
			'billing_country'    => 'DE',
			'billing_address_1'  => 'Teststraße 1',
			'billing_postcode'   => '39179',
			'billing_city'       => 'Barleben',
		);
		$fields = new Fields( new VatProfile( new ViesClient() ) );

		$this->assertFalse( $fields->validate( new WP_Error() )->has_errors() );
		( new Fields( new VatProfile( new ViesClient() ) ) )->save( 7 );
		$this->assertConditionsMet();
	}
}
