<?php
/**
 * Tests for the registration form's country order.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\CountryOptions;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Owner ruling 2026-10-17 (AGENTS.md §2) and the field research (#224): every
 * country stays open, Germany leads, the EU follows, the rest closes. Woo's own
 * country table and its `EU` continent are the data.
 *
 * @covers \Linker\Commerce\Registration\CountryOptions
 */
final class CountryOptionsTest extends TestCase {

	/**
	 * Makes WC_Countries answer with a fixture.
	 *
	 * @param array<string, string>               $names     Country code → name.
	 * @param array<string, array<string, mixed>> $continents Continent key → data.
	 * @param string                              $base      Store base country.
	 */
	private function countries( array $names, array $continents, string $base ): void {
		$countries = Mockery::mock();
		$countries->allows( 'get_countries' )->andReturn( $names );
		$countries->allows( 'get_continents' )->andReturn( $continents );
		$countries->allows( 'get_base_country' )->andReturn( $base );
		$woocommerce            = new \stdClass();
		$woocommerce->countries = $countries;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
	}

	/**
	 * Germany first, then the EU alphabetically, then every other country
	 * alphabetically; no country is lost and none is repeated.
	 */
	public function test_germany_then_europe_then_the_rest(): void {
		$this->countries(
			array(
				'AT' => 'Austria',
				'BE' => 'Belgium',
				'CH' => 'Switzerland',
				'DE' => 'Germany',
				'FR' => 'France',
				'GB' => 'United Kingdom (UK)',
				'US' => 'United States (US)',
			),
			array(
				'EU' => array(
					'name'      => 'Europe',
					'countries' => array( 'BE', 'DE', 'AT', 'FR' ),
				),
				'NA' => array(
					'name'      => 'North America',
					'countries' => array( 'US' ),
				),
			),
			'DE'
		);
		$groups = CountryOptions::groups();

		$this->assertSame( array( 'DE', 'AT', 'BE', 'FR' ), array_keys( $groups['europe'] ) );
		$this->assertSame( array( 'CH', 'GB', 'US' ), array_keys( $groups['rest'] ) );
		$this->assertSame(
			array( 'DE', 'AT', 'BE', 'FR', 'CH', 'GB', 'US' ),
			array_keys( CountryOptions::all() )
		);
		$this->assertSame( 'Germany', CountryOptions::all()['DE'] );
	}

	/**
	 * Germany is the default whenever the table has it, even when the store's
	 * base country is another one.
	 */
	public function test_the_default_country_is_germany(): void {
		$this->countries(
			array(
				'AT' => 'Austria',
				'DE' => 'Germany',
			),
			array(),
			'AT'
		);
		$this->assertSame( 'DE', CountryOptions::default_country() );
	}

	/**
	 * Without Germany the store's own base country is the default.
	 */
	public function test_without_germany_the_store_base_is_the_default(): void {
		$this->countries( array( 'AT' => 'Austria' ), array(), 'AT' );
		$this->assertSame( 'AT', CountryOptions::default_country() );
	}
}
