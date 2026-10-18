<?php
/**
 * Tests for the registration country select's markup.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\CountryField;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * WooCommerce's `woocommerce_form_field_{type}` hook renders the grouped,
 * searchable country select. The groups keep the owner's order (#224).
 *
 * @covers \Linker\Commerce\Registration\CountryField
 */
final class CountryFieldTest extends TestCase {

	/**
	 * Woo's country table and the EU continent.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$countries = Mockery::mock();
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
		WP_Mock::userFunction(
			'selected',
			array(
				'return' => static fn ( $selected, $current ) => (string) $selected === (string) $current ? " selected='selected'" : '',
			)
		);
	}

	/**
	 * The field's data, as WooCommerce passes it to the type filter.
	 *
	 * @return array<string, mixed>
	 */
	private function args(): array {
		return array(
			'id'                => 'billing_country',
			'label'             => 'Country / Region',
			'required'          => true,
			'class'             => array( 'form-row-wide', 'validate-required' ),
			'input_class'       => array(),
			'label_class'       => array( 'required_field' ),
			'custom_attributes' => array(
				'autocomplete'  => 'country',
				'aria-required' => 'true',
			),
		);
	}

	/**
	 * Germany is selected, the EU group comes first with Germany leading it,
	 * and the rest follows; the select carries the marker the script uses.
	 */
	public function test_the_country_select_is_grouped_and_germany_leds(): void {
		$html = ( new CountryField() )->render( '', 'billing_country', $this->args(), 'DE' );

		$this->assertStringContainsString( '<select name="billing_country" id="billing_country"', $html );
		$this->assertStringContainsString( 'linker-country-select', $html );
		$this->assertStringContainsString( 'aria-required="true"', $html );
		$this->assertStringContainsString( 'required_field', $html );
		$this->assertStringContainsString( '<optgroup label="Europe">', $html );
		$this->assertStringContainsString( '<optgroup label="Other countries">', $html );
		$this->assertLessThan( strpos( $html, '<optgroup label="Other countries">' ), strpos( $html, '<optgroup label="Europe">' ) );
		$this->assertMatchesRegularExpression( '/<option value="DE" selected=\'selected\'>Germany<\/option>/', $html );
		$this->assertLessThan( strpos( $html, '<option value="AT"' ), strpos( $html, '<option value="DE"' ) );
		$this->assertLessThan( strpos( $html, '<option value="CH"' ), strpos( $html, '<option value="FR"' ) );
	}

	/**
	 * Only the registration's country field is ours; any other field keeps
	 * WooCommerce's own answer.
	 */
	public function test_another_field_is_left_untouched(): void {
		$this->assertSame( '<p>native</p>', ( new CountryField() )->render( '<p>native</p>', 'shipping_country', $this->args(), 'DE' ) );
	}
}
