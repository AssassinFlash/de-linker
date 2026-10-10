<?php
/**
 * Tests for the company address form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\AddressForm;
use Linker\Commerce\Tests\TestCase;

/**
 * Tests for AddressForm.
 *
 * @covers \Linker\Commerce\Registration\AddressForm
 */
final class AddressFormTest extends TestCase {

	/**
	 * The shop's German location counts without its state; other locations and an unset option stay.
	 */
	public function test_base_location(): void {
		$form = new AddressForm();

		$this->assertSame( 'DE', $form->base_location( 'DE:DE-ST' ) );
		$this->assertSame( 'DE', $form->base_location( 'DE' ) );
		$this->assertSame( 'US:CA', $form->base_location( 'US:CA' ) );
		$this->assertFalse( $form->base_location( false ) );
	}

	/**
	 * A German address asks no state; WooCommerce's other rules for Germany and other countries stay.
	 */
	public function test_country_locale(): void {
		$locale = ( new AddressForm() )->country_locale(
			array(
				'DE' => array(
					'postcode' => array( 'priority' => 65 ),
					'state'    => array( 'required' => false ),
				),
				'IT' => array( 'state' => array( 'required' => true ) ),
			)
		);

		$this->assertSame(
			array(
				'postcode' => array( 'priority' => 65 ),
				'state'    => array(
					'required' => false,
					'hidden'   => true,
				),
			),
			$locale['DE']
		);
		$this->assertSame( array( 'state' => array( 'required' => true ) ), $locale['IT'] );
	}
}
