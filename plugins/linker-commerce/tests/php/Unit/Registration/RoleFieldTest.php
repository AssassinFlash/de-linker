<?php
/**
 * Tests for the registration business-type radios' markup.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\RoleField;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The business-type field renders through WooCommerce's
 * `woocommerce_form_field_{type}` extension point (#351): the input stays the
 * native control — nested inside its option label so the pill's whole area is
 * the input's own hit and focus target, the way the configurator's choice
 * cards nest theirs.
 *
 * @covers \Linker\Commerce\Registration\RoleField
 */
final class RoleFieldTest extends TestCase {

	/**
	 * The checked() marker of the option inputs.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'checked',
			array(
				'return' => static fn ( $checked, $current ) => (string) $checked === (string) $current ? " checked='checked'" : '',
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
			'id'                => CustomerRole::META,
			'label'             => 'Business type',
			'required'          => true,
			'class'             => array( 'form-row-wide' ),
			'input_class'       => array(),
			'label_class'       => array( 'required_field' ),
			'custom_attributes' => array( 'aria-required' => 'true' ),
		);
	}

	/**
	 * Every option is one label that contains its input before its text: the
	 * input itself is what a pointer, Playwright's actionability check and a
	 * screen reader reach, and the posted value keeps WooCommerce's checked
	 * marker.
	 */
	public function test_each_radio_input_is_nested_inside_its_option_label(): void {
		$html = ( new RoleField() )->render( '', CustomerRole::META, $this->args(), 'epc' );

		$this->assertStringContainsString( 'id="linker_customer_role_field"', $html );
		$this->assertStringContainsString( 'validate-required', $html, 'The client check of the card finds the row.' );
		foreach ( CustomerRole::options() as $key => $label ) {
			$id    = CustomerRole::META . '_' . $key;
			$regex = '/<label for="' . preg_quote( $id, '/' ) . '" class="radio[^"]*">' .
				'<input type="radio"[^>]*value="' . preg_quote( (string) $key, '/' ) . '"[^>]*name="' . CustomerRole::META . '"[^>]*aria-required="true"[^>]*id="' . preg_quote( $id, '/' ) . '"[^>]*\/>' .
				preg_quote( (string) $label, '/' ) . '<\/label>/';
			$this->assertMatchesRegularExpression( $regex, $html, $label . ' is one label that wraps its input.' );
		}
		$this->assertMatchesRegularExpression( '/value="epc"[^>]*checked=\'checked\'/', $html, 'The posted value stays checked.' );
		$this->assertDoesNotMatchRegularExpression( '/value="installer"[^>]*checked=\'checked\'/', $html );
		$this->assertDoesNotMatchRegularExpression( '/value="distributor"[^>]*checked=\'checked\'/', $html );
	}

	/**
	 * The row keeps WooCommerce's own shape around the options: the field's
	 * label names the first option, the wrapper class stays, and Woo's
	 * per-option required copies do not come back.
	 */
	public function test_the_row_keeps_woocommerce_s_own_shape(): void {
		$html = ( new RoleField() )->render( '', CustomerRole::META, $this->args(), '' );

		$this->assertMatchesRegularExpression( '/<label for="linker_customer_role_installer" class="[^"]*">Business type&nbsp;<span class="required" aria-hidden="true">\*<\/span><\/label>/', $html );
		$this->assertStringContainsString( '<span class="woocommerce-input-wrapper">', $html );
		$this->assertSame( 3, substr_count( $html, '<label for="linker_customer_role_' ) - 1, 'The three option labels, beside the field label that names the first option.' );
		$this->assertSame( 1, substr_count( $html, '<span class="required"' ), 'The required marker is the field label\'s alone; Woo\'s per-option copies stay out.' );
	}

	/**
	 * Only the registration's role field is ours; any other field keeps
	 * WooCommerce's own answer.
	 */
	public function test_another_field_is_left_untouched(): void {
		$this->assertSame( '<p>native</p>', ( new RoleField() )->render( '<p>native</p>', 'billing_company', $this->args(), '' ) );
	}
}
