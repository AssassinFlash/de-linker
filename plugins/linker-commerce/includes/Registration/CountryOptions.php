<?php
/**
 * The order of the registration form's country select.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WC_Countries;

/**
 * The owner's country ruling of 2026-10-17 (AGENTS.md §2): every country stays
 * open, Europe is the focus. The list is WooCommerce's own country table and
 * its `EU` continent (`i18n/continents.php`, read through WC_Countries), as the
 * field research directs (#224, docs/research/2026-10-17-registration-fields/
 * DOSSIER.md §8): Germany first, then the remaining EU countries, then the rest,
 * each group sorted by its own name.
 */
final class CountryOptions {

	/**
	 * The two select groups. Germany leads the European group.
	 *
	 * @return array{europe: array<string, string>, rest: array<string, string>}
	 */
	public static function groups(): array {
		$countries = WC()->countries->get_countries();
		$continent = WC()->countries->get_continents();
		$members   = $continent['EU']['countries'] ?? array();
		$europe    = array();
		$rest      = array();
		foreach ( $countries as $code => $name ) {
			if ( 'DE' === $code ) {
				continue;
			}
			if ( in_array( $code, $members, true ) ) {
				$europe[ $code ] = $name;
			} else {
				$rest[ $code ] = $name;
			}
		}
		uasort( $europe, array( self::class, 'by_name' ) );
		uasort( $rest, array( self::class, 'by_name' ) );
		if ( isset( $countries['DE'] ) ) {
			$europe = array( 'DE' => $countries['DE'] ) + $europe;
		}
		return array(
			'europe' => $europe,
			'rest'   => $rest,
		);
	}

	/**
	 * Every country in form order, for validation and a flat list.
	 *
	 * @return array<string, string>
	 */
	public static function all(): array {
		$groups = self::groups();
		return $groups['europe'] + $groups['rest'];
	}

	/**
	 * Germany when the table has it (the owner's default), otherwise the
	 * store's own base country.
	 */
	public static function default_country(): string {
		return isset( WC()->countries->get_countries()['DE'] ) ? 'DE' : WC()->countries->get_base_country();
	}

	/**
	 * Case-insensitive natural order of the names as WooCommerce translated them.
	 *
	 * @param string $first  First name.
	 * @param string $second Second name.
	 */
	private static function by_name( string $first, string $second ): int {
		return strnatcasecmp( $first, $second );
	}
}
