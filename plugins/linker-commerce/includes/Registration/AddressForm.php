<?php
/**
 * The company address form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * A German address has no state: WooCommerce's German address format has none
 * ({postcode} {city}), and WooCommerce already hides the field for Austria.
 * So the form asks no state for Germany, and the shop's own address counts
 * without its state (stored as DE:DE-ST, Saxony-Anhalt). WooCommerce derives a
 * new customer's address from the shop's: with the state, every customer would
 * start in Saxony-Anhalt, and every German customer elsewhere would count as
 * outside the shop's location, with "estimated for Germany" beside the VAT.
 */
final class AddressForm {

	/**
	 * The shop's location without a German state; runs on option_woocommerce_default_country.
	 *
	 * @param mixed $location Stored "Country" or "Country:State".
	 * @return mixed
	 */
	public function base_location( $location ) {
		return is_string( $location ) && str_starts_with( $location, 'DE:' ) ? 'DE' : $location;
	}

	/**
	 * No state field for German addresses; runs on woocommerce_get_country_locale.
	 *
	 * @param array<string, array<string, array<string, mixed>>> $locale Address field rules by country.
	 * @return array<string, array<string, array<string, mixed>>>
	 */
	public function country_locale( array $locale ): array {
		$locale['DE']['state']['required'] = false;
		$locale['DE']['state']['hidden']   = true;
		return $locale;
	}
}
