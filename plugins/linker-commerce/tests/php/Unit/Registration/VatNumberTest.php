<?php
/**
 * Tests for VAT identification numbers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\VatNumber;
use Linker\Commerce\Tests\TestCase;

/**
 * Tests for VatNumber.
 *
 * @covers \Linker\Commerce\Registration\VatNumber
 */
final class VatNumberTest extends TestCase {

	/**
	 * Spaces, dots and hyphens go; letters become upper case; the country code is split off.
	 *
	 * @testWith ["de 143.454.214", "DE", "143454214", true]
	 *           ["EL123456789", "EL", "123456789", true]
	 *           ["XI 123 4567 89", "XI", "123456789", true]
	 *           ["nl123456789B01", "NL", "123456789B01", true]
	 *           ["ATU12345678", "AT", "U12345678", true]
	 *           ["GB123456789", "GB", "123456789", false]
	 *
	 * @param string $input     As typed.
	 * @param string $country   Country code.
	 * @param string $number    Number.
	 * @param bool   $checkable Whether VIES checks it.
	 */
	public function test_parse( string $input, string $country, string $number, bool $checkable ): void {
		$vat = VatNumber::parse( $input );

		$this->assertNotNull( $vat );
		$this->assertSame( $country, $vat->country );
		$this->assertSame( $number, $vat->number );
		$this->assertSame( $checkable, $vat->is_checkable() );
		$this->assertSame( $country . $number, (string) $vat );
	}

	/**
	 * Input outside VIES's format (country [A-Z]{2}, number of 2 to 12 characters) is not a VAT number.
	 *
	 * @testWith [""]
	 *           ["DE"]
	 *           ["DE1"]
	 *           ["123456789"]
	 *           ["CHE-123.456.789 MWST"]
	 *           ["DE1234567890123"]
	 *
	 * @param string $input As typed.
	 */
	public function test_parse_rejects( string $input ): void {
		$this->assertNull( VatNumber::parse( $input ) );
	}
}
