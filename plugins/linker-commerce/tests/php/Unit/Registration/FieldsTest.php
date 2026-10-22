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
use Linker\Commerce\Registration\RoleField;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Registration\Website;
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
	 * WooCommerce's address fields for Germany and the country table.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static fn ( string $url, int $component = -1 ) => parse_url( $url, $component ),
			)
		);
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
				'billing_postcode'   => array(
					'label'    => 'Postcode',
					'required' => true,
				),
				'billing_city'       => array(
					'label'    => 'Town / City',
					'required' => true,
				),
			)
		);
		$countries->allows( 'get_countries' )->andReturn(
			array(
				'AT' => 'Austria',
				'CH' => 'Switzerland',
				'DE' => 'Germany',
				'FR' => 'France',
			)
		);
		$countries->allows( 'get_continents' )->andReturn(
			array(
				'EU' => array(
					'countries' => array( 'DE', 'AT', 'FR' ),
				),
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
	 * Company, business type, country, website or VAT ID, then the customer's
	 * name; the address is collected by the Proforma request page, not here.
	 */
	public function test_fields(): void {
		$fields = ( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->fields( 'DE' );

		$this->assertSame(
			array( 'billing_company', CustomerRole::META, 'billing_country', Website::META, VatProfile::VAT_META, 'billing_first_name', 'billing_last_name' ),
			array_keys( $fields )
		);
		$this->assertTrue( $fields['billing_company']['required'] );
		$this->assertSame( RoleField::TYPE, $fields[ CustomerRole::META ]['type'], 'RoleField renders the options so each input stays a clickable native control (#351).' );
		$this->assertTrue( $fields[ CustomerRole::META ]['required'] );
		$this->assertSame( array( 'installer', 'epc', 'distributor' ), array_keys( $fields[ CustomerRole::META ]['options'] ) );
		$this->assertSame( 'linker_country', $fields['billing_country']['type'] );
		$this->assertSame( array( 'DE', 'AT', 'FR', 'CH' ), array_keys( $fields['billing_country']['options'] ) );
		$this->assertSame( 'text', $fields[ Website::META ]['type'], 'A bare host is an accepted value, so the browser must not apply the type=url rule.' );
		$this->assertSame( array( 'inputmode' => 'url' ), $fields[ Website::META ]['custom_attributes'] );
		$this->assertFalse( $fields[ Website::META ]['required'] );
		$this->assertFalse( $fields[ VatProfile::VAT_META ]['required'] );
		$this->assertArrayNotHasKey( 'billing_address_1', $fields );
		$this->assertArrayNotHasKey( 'billing_postcode', $fields );
		$this->assertArrayNotHasKey( 'billing_city', $fields );
	}

	/**
	 * The form is filled again with what was posted; the country defaults to
	 * Germany.
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

		( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->render();

		$this->assertSame( 'Solarbau GmbH', $rendered['billing_company'] );
		$this->assertSame( 'DE', $rendered['billing_country'] );
		$this->assertSame( '', $rendered[ Website::META ] );
		$this->assertSame( '', $rendered[ VatProfile::VAT_META ] );
	}

	/**
	 * Missing company, business type, country and names are reported; the
	 * address rules of the old form are gone.
	 */
	public function test_validate_reports_the_required_fields(): void {
		$_POST  = array(
			CustomerRole::META => 'wholesaler',
			'billing_country'  => 'FR',
		);
		$errors = ( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->validate( new WP_Error() );

		foreach ( array( 'billing_company', 'billing_first_name', 'billing_last_name', CustomerRole::META ) as $key ) {
			$this->assertContains( $key, $errors->get_error_codes(), $key );
		}
		$this->assertNotContains( 'billing_address_1', $errors->get_error_codes() );
		$this->assertNotContains( 'billing_postcode', $errors->get_error_codes() );
		$this->assertNotContains( 'billing_city', $errors->get_error_codes() );
	}

	/**
	 * Website or VAT ID: one of the two is required, and a written website must
	 * be an address.
	 */
	public function test_validate_needs_a_website_or_a_vat_id(): void {
		$_POST  = array(
			'billing_company'    => 'Solarbau GmbH',
			CustomerRole::META   => 'installer',
			'billing_country'    => 'DE',
			'billing_first_name' => 'Maria',
			'billing_last_name'  => 'Beispiel',
		);
		$fields = new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) );
		$errors = $fields->validate( new WP_Error() );
		$this->assertContains( 'linker_website_or_vat', $errors->get_error_codes() );

		$_POST[ VatProfile::VAT_META ] = 'DE 143 454 214';
		$this->assertFalse( ( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->validate( new WP_Error() )->has_errors() );

		$_POST[ Website::META ] = 'not a site';
		$this->assertContains( Website::META, ( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->validate( new WP_Error() )->get_error_codes() );

		$_POST[ Website::META ] = 'example.com';
		$this->assertFalse( ( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->validate( new WP_Error() )->has_errors() );
	}

	/**
	 * A country outside WooCommerce's table is refused.
	 */
	public function test_validate_refuses_an_unknown_country(): void {
		$_POST  = array(
			'billing_company'    => 'Solarbau GmbH',
			CustomerRole::META   => 'installer',
			'billing_country'    => 'XX',
			'billing_first_name' => 'Maria',
			'billing_last_name'  => 'Beispiel',
			Website::META        => 'example.com',
		);
		$errors = ( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->validate( new WP_Error() );

		$this->assertContains( 'billing_country', $errors->get_error_codes() );
	}

	/**
	 * A complete registration passes, and without a validated registration save() does nothing.
	 */
	public function test_complete_registration_passes(): void {
		$_POST  = array(
			'billing_company'    => 'Solarbau GmbH',
			CustomerRole::META   => 'installer',
			'billing_country'    => 'DE',
			Website::META        => 'example.com',
			VatProfile::VAT_META => 'DE 143 454 214',
			'billing_first_name' => 'Maria',
			'billing_last_name'  => 'Beispiel',
		);
		$fields = new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) );

		$this->assertFalse( $fields->validate( new WP_Error() )->has_errors() );
		( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->save( 7 );
		$this->assertConditionsMet();
	}

	/**
	 * A refused form opens step 1 when one of its company fields failed and
	 * step 2 when only the sign-in step is left on the page.
	 */
	public function test_the_active_step_follows_the_errors(): void {
		$_POST = array(
			'billing_company'    => '',
			CustomerRole::META   => 'installer',
			'billing_country'    => 'DE',
			Website::META        => 'example.com',
			'billing_first_name' => 'Maria',
			'billing_last_name'  => 'Beispiel',
		);
		( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->validate( new WP_Error() );
		$this->assertSame( 1, Fields::active_step() );

		$_POST['billing_company'] = 'Solarbau GmbH';
		unset( $_POST[ Website::META ] );
		$_POST[ VatProfile::VAT_META ] = 'DE 143 454 214';
		// The step-1 fields are complete now; the page stays on step 2.
		$_POST['register'] = 'Register';
		( new Fields( new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() ) ) )->validate( new WP_Error() );
		$this->assertSame( 2, Fields::active_step() );
	}
}
