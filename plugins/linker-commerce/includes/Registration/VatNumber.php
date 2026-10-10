<?php
/**
 * A VAT identification number.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * A VAT ID as VIES takes it: a two-letter country code and the number. Input
 * such as "de 123.456.789" becomes DE + 123456789.
 */
final class VatNumber {

	/**
	 * Country codes VIES checks: the EU member states (Greece as EL) and
	 * Northern Ireland (XI). Source: VIES REST API /check-status, read via Apify
	 * on 2026-10-09.
	 */
	public const VIES_COUNTRIES = array( 'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'EL', 'ES', 'FI', 'FR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK', 'XI' );

	/**
	 * Sets up the number.
	 *
	 * @param string $country Two-letter country code.
	 * @param string $number  The number without the country code.
	 */
	public function __construct(
		public readonly string $country,
		public readonly string $number
	) {}

	/**
	 * Input with spaces, dots and hyphens removed, upper case.
	 *
	 * @param string $input What the customer typed.
	 */
	public static function normalize( string $input ): string {
		return strtoupper( (string) preg_replace( '/[\s.\-]+/', '', $input ) );
	}

	/**
	 * The number in the form VIES accepts (country [A-Z]{2}, number
	 * [0-9A-Za-z+*.]{2,12}: VIES checkVatService.wsdl, read via Apify on
	 * 2026-10-09), or null.
	 *
	 * @param string $input What the customer typed.
	 */
	public static function parse( string $input ): ?self {
		$value = self::normalize( $input );
		if ( 1 !== preg_match( '/^([A-Z]{2})([0-9A-Z+*]{2,12})$/', $value, $parts ) ) {
			return null;
		}
		return new self( $parts[1], $parts[2] );
	}

	/**
	 * Whether VIES can check the number.
	 */
	public function is_checkable(): bool {
		return in_array( $this->country, self::VIES_COUNTRIES, true );
	}

	/**
	 * Country code and number together.
	 */
	public function __toString(): string {
		return $this->country . $this->number;
	}
}
