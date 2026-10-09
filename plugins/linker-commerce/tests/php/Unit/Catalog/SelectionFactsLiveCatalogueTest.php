<?php
/**
 * Tests of the selection facts against the live products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Catalog;

use Linker\Commerce\Catalog\SelectionFacts;
use Linker\Commerce\Catalog\SelectionFactSet;
use Linker\Commerce\Tests\Support\LiveCatalogue;
use Linker\Commerce\Tests\Support\MocksProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * SelectionFacts on the 89 published inverters and batteries of de-linker.com
 * (tests/fixtures/live-products-2026-10-09.json). The expected values are the
 * research CSV (tests/fixtures/live-catalogue-facts.csv, the table of
 * docs/research/2026-10-09/old-repo-live-catalogue-facts.md) converted by hand;
 * test_the_table_follows_the_csv() binds them to the CSV, and the comments and
 * NOT_AC_POWER / SYSTEM_NOT_MODULE mark where the contract reads a figure
 * differently from the CSV.
 *
 * @covers \Linker\Commerce\Catalog\SelectionFacts
 * @covers \Linker\Commerce\Catalog\SelectionFactSet
 * @covers \Linker\Commerce\Catalog\Units
 */
final class SelectionFactsLiveCatalogueTest extends TestCase {

	use MocksProducts;

	private const U = SelectionFactSet::UNKNOWN;

	/**
	 * Per product: device_class, application, phase, ac_power_kw, pv_input_kw,
	 * usable_kwh, nominal_kwh, kwh_range (min, max).
	 */
	private const EXPECTED = array(
		// Inverters, 59 products.
		1179 => array( 'inverters', 'commercial', 3, 25.0, 45.0, self::U, self::U, null ),
		1181 => array( 'inverters', 'commercial', 3, 29.999, 45.0, self::U, self::U, null ),
		1182 => array( 'inverters', 'home', 3, 10.0, 15.0, self::U, self::U, null ),
		1183 => array( 'inverters', 'home', 3, 6.0, 9.0, self::U, self::U, null ),
		1184 => array( 'inverters', 'home', 3, 8.0, 12.0, self::U, self::U, null ),
		1185 => array( 'inverters', 'home', 3, 12.0, 15.0, self::U, self::U, null ),
		1186 => array( 'inverters', 'home', 3, 6.0, 12.0, self::U, self::U, null ),
		1187 => array( 'inverters', 'home', 3, 8.0, 12.0, self::U, self::U, null ),
		1946 => array( 'inverters', 'commercial', 3, 80.0, 160.0, self::U, self::U, null ),
		1947 => array( 'inverters', 'commercial', 3, 99.99, 200.0, self::U, self::U, null ),
		1948 => array( 'inverters', 'commercial', 3, 100.0, 200.0, self::U, self::U, null ),
		2063 => array( 'inverters', 'home', 3, 15.0, 30.0, self::U, self::U, null ),
		2064 => array( 'inverters', 'home', 3, 20.0, 40.0, self::U, self::U, null ),
		2198 => array( 'inverters', 'home', 3, 5.0, 10.0, self::U, self::U, null ),
		2199 => array( 'inverters', 'home', 3, 10.0, 15.0, self::U, self::U, null ),
		3555 => array( 'inverters', 'home', 3, 10.0, 20.0, self::U, self::U, null ),
		// GoodWe ESA ETA (3556, 3583–3585, 6512–6518): the CSV's nominal is the range system_energy_kwh_range 5-108.
		3556 => array( 'inverters', 'home', 3, 10.0, 20.0, self::U, self::U, array( 5.0, 108.0 ) ),
		3574 => array( 'inverters', 'home', 3, 6.0, 12.0, self::U, self::U, null ),
		3575 => array( 'inverters', 'home', 3, 8.0, 16.0, self::U, self::U, null ),
		3576 => array( 'inverters', 'home', 3, 12.0, 24.0, self::U, self::U, null ),
		3577 => array( 'inverters', 'home', 1, 6.0, 12.0, self::U, self::U, null ),
		3578 => array( 'inverters', 'home', 1, 8.0, 16.0, self::U, self::U, null ),
		3579 => array( 'inverters', 'home', 1, 10.0, 20.0, self::U, self::U, null ),
		3580 => array( 'inverters', 'home', 1, 12.0, 24.0, self::U, self::U, null ),
		3583 => array( 'inverters', 'home', 3, 8.0, 16.0, self::U, self::U, array( 5.0, 108.0 ) ),
		3584 => array( 'inverters', 'home', 3, 12.0, 24.0, self::U, self::U, array( 5.0, 108.0 ) ),
		3585 => array( 'inverters', 'home', 3, 15.0, 30.0, self::U, self::U, array( 5.0, 108.0 ) ),
		3595 => array( 'inverters', 'commercial', 3, 125.0, 250.0, self::U, self::U, null ),
		4107 => array( 'inverters', 'home', 3, 10.0, 20.0, self::U, self::U, null ),
		4108 => array( 'inverters', 'home', 3, 12.0, 24.0, self::U, self::U, null ),
		4109 => array( 'inverters', 'home', 3, 5.0, 7.5, self::U, self::U, null ),
		// 6480–6488 lack pa_application and pa_phase on the live site; 6482 has no phase figure either.
		6480 => array( 'inverters', self::U, 3, 5.0, 10.0, self::U, self::U, null ),
		6481 => array( 'inverters', self::U, 3, 15.0, 24.0, self::U, self::U, null ),
		6482 => array( 'inverters', self::U, self::U, 15.0, 24.0, self::U, self::U, null ),
		6483 => array( 'inverters', self::U, 1, 3.0, 9.0, self::U, self::U, null ),
		6484 => array( 'inverters', self::U, 1, 3.68, 9.68, self::U, self::U, null ),
		6485 => array( 'inverters', self::U, 1, 4.6, 10.6, self::U, self::U, null ),
		6486 => array( 'inverters', self::U, 1, 5.0, 11.0, self::U, self::U, null ),
		6487 => array( 'inverters', self::U, 1, 5.75, 11.0, self::U, self::U, null ),
		6488 => array( 'inverters', self::U, 1, 6.0, 12.0, self::U, self::U, null ),
		6506 => array( 'inverters', 'commercial', 3, 75.0, 150.0, self::U, self::U, null ),
		6507 => array( 'inverters', 'commercial', 3, 80.0, 160.0, self::U, self::U, null ),
		6508 => array( 'inverters', 'commercial', 3, 99.99, 200.0, self::U, self::U, null ),
		6509 => array( 'inverters', 'commercial', 3, 100.0, 200.0, self::U, self::U, null ),
		6510 => array( 'inverters', 'commercial', 3, 110.0, 220.0, self::U, self::U, null ),
		6511 => array( 'inverters', 'commercial', 3, 124.99, 250.0, self::U, self::U, null ),
		6512 => array( 'inverters', 'home', 3, 5.0, 10.0, self::U, self::U, array( 5.0, 108.0 ) ),
		6513 => array( 'inverters', 'home', 3, 6.0, 12.0, self::U, self::U, array( 5.0, 108.0 ) ),
		6514 => array( 'inverters', 'home', 3, 9.999, 20.0, self::U, self::U, array( 5.0, 108.0 ) ),
		6515 => array( 'inverters', 'home', 3, 20.0, 40.0, self::U, self::U, array( 5.0, 108.0 ) ),
		6516 => array( 'inverters', 'home', 3, 25.0, 50.0, self::U, self::U, array( 5.0, 108.0 ) ),
		6517 => array( 'inverters', 'home', 3, 29.999, 60.0, self::U, self::U, array( 5.0, 108.0 ) ),
		6518 => array( 'inverters', 'home', 3, 30.0, 60.0, self::U, self::U, array( 5.0, 108.0 ) ),
		6523 => array( 'inverters', 'home', 1, 3.0, 6.0, self::U, self::U, null ),
		6524 => array( 'inverters', 'home', 1, 3.6, 7.2, self::U, self::U, null ),
		6525 => array( 'inverters', 'home', 1, 5.0, 10.0, self::U, self::U, null ),
		6526 => array( 'inverters', 'home', 1, 6.0, 12.0, self::U, self::U, null ),
		6527 => array( 'inverters', 'home', 1, 8.0, 16.0, self::U, self::U, null ),
		6528 => array( 'inverters', 'home', 1, 10.0, 20.0, self::U, self::U, null ),
		// All-in-one systems, 5 products.
		// 1959–1961: battery_rated_energy is a range, so it is kwh_range and the scalar stays unknown.
		1959 => array( 'all-in-one-systems', 'commercial', 3, 29.9, 59.8, self::U, self::U, array( 57.3, 100.3 ) ),
		1960 => array( 'all-in-one-systems', 'commercial', 3, 30.0, 60.0, self::U, self::U, array( 57.3, 100.3 ) ),
		1961 => array( 'all-in-one-systems', 'commercial', 3, 50.0, 100.0, self::U, self::U, array( 57.3, 100.3 ) ),
		2003 => array( 'all-in-one-systems', 'commercial', self::U, 125.0, self::U, self::U, 260.0, null ),
		6321 => array( 'all-in-one-systems', 'commercial', 3, 125.0, self::U, 261.25, 261.25, null ),
		// Battery systems, 9 products.
		// 1954–1958: the CSV takes module_energy_kwh_nominal (one module, 10.24 / 52.24 kWh); the product's own
		// figure is system_nominal_energy_kwh (1954, 1955) or rated_energy_kwh (1956–1958).
		// Battery systems' power figures are charge/discharge power, not an AC output: no AC power key, unknown.
		1954 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, 60.0, 61.4, null ),
		1955 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, 110.0, 112.6, null ),
		1956 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, self::U, 208.9, null ),
		1957 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, self::U, 208.9, null ),
		1958 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, self::U, 261.2, null ),
		// 4103–4106: usable energy under the key usable_energy, as the CSV reads it.
		4103 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, 51.5, 57.3, null ),
		4104 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, 64.4, 71.6, null ),
		4105 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, 77.3, 85.9, null ),
		4106 => array( 'battery-systems', 'commercial', self::U, self::U, self::U, 90.2, 100.3, null ),
		// Home storage, 16 products.
		// SAJ B2 batteries: the CSV's power is rated_power_w, the battery's charge/discharge power, not an AC key.
		// kwh_range is system_energy_kwh_range, which the CSV shows only where no scalar exists (2092).
		1832 => array( 'home-storage', 'home', self::U, self::U, self::U, 4.5, 5.0, array( 5.0, 25.0 ) ),
		2067 => array( 'home-storage', 'home', self::U, self::U, self::U, 9.0, 10.0, array( 5.0, 25.0 ) ),
		2068 => array( 'home-storage', 'home', self::U, self::U, self::U, 13.5, 15.0, array( 5.0, 25.0 ) ),
		2069 => array( 'home-storage', 'home', self::U, self::U, self::U, 18.0, 20.0, array( 5.0, 25.0 ) ),
		2070 => array( 'home-storage', 'home', self::U, self::U, self::U, 22.5, 25.0, array( 5.0, 25.0 ) ),
		2090 => array( 'home-storage', 'home', self::U, self::U, self::U, 4.5, 5.0, array( 5.0, 25.0 ) ),
		2092 => array( 'home-storage', 'home', self::U, self::U, self::U, self::U, self::U, array( 5.0, 25.0 ) ),
		2093 => array( 'home-storage', 'home', self::U, self::U, self::U, 4.8, 5.0, null ),
		3581 => array( 'home-storage', 'home', self::U, self::U, self::U, self::U, 5.02, array( 5.02, 30.12 ) ),
		3582 => array( 'home-storage', 'home', self::U, self::U, self::U, 7.76, 8.03, null ),
		3611 => array( 'home-storage', 'home', self::U, self::U, self::U, 5.8, 6.0, array( 5.0, 108.0 ) ),
		3612 => array( 'home-storage', 'home', self::U, self::U, self::U, 8.7, 9.0, array( 5.0, 108.0 ) ),
		6519 => array( 'home-storage', 'home', self::U, self::U, self::U, 5.0, 5.12, array( 5.0, 108.0 ) ),
		6520 => array( 'home-storage', 'home', self::U, self::U, self::U, 8.0, 8.32, array( 5.0, 108.0 ) ),
		6521 => array( 'home-storage', 'home', self::U, self::U, self::U, 5.0, 5.12, array( 5.0, 108.0 ) ),
		6522 => array( 'home-storage', 'home', self::U, self::U, self::U, 8.0, 8.32, array( 5.0, 108.0 ) ),
	);

	/**
	 * Battery systems whose CSV power is a charge/discharge power, not an AC
	 * output; the contract reads only AC power keys, so EXPECTED says unknown.
	 */
	private const NOT_AC_POWER = array(
		1832 => 'rated_power_w',
		2067 => 'rated_power_w',
		2068 => 'rated_power_w',
		2069 => 'rated_power_w',
		2070 => 'rated_power_w',
		1954 => 'max_charge_discharge_power_kw',
		1955 => 'max_charge_discharge_power_kw',
		1956 => 'max_charging_discharging_power_kw',
		1957 => 'max_input_output_power_kw',
		1958 => 'max_input_output_power_kw',
		4103 => 'rated_power',
		4104 => 'rated_power',
		4105 => 'rated_power',
		4106 => 'rated_power',
	);

	/**
	 * Battery systems whose CSV nominal energy is one module's; EXPECTED holds
	 * the product's own figure, which is larger.
	 */
	private const SYSTEM_NOT_MODULE = array( 1954, 1955, 1956, 1957, 1958 );

	/**
	 * The research's "residential three-phase hybrid inverters" (home and three-phase, 28).
	 */
	private const HOME_THREE_PHASE = array( 1182, 1183, 1184, 1185, 1186, 1187, 2063, 2064, 2198, 2199, 3555, 3556, 3574, 3575, 3576, 3583, 3584, 3585, 4107, 4108, 4109, 6512, 6513, 6514, 6515, 6516, 6517, 6518 );

	/**
	 * Each live product's facts match the hand conversion of the CSV.
	 *
	 * @dataProvider expected_facts
	 *
	 * @param int                  $id       Product ID.
	 * @param array<string, mixed> $expected Facts as SelectionFactSet::to_array() returns them.
	 */
	public function test_each_live_product( int $id, array $expected ): void {
		$this->mock_live_products( array( $id ) );

		$this->assertSame( $expected, SelectionFacts::for_product( $id )->to_array() );
	}

	/**
	 * Cases of test_each_live_product(), one per product of the fixture.
	 *
	 * @return array<string, array{int, array<string, mixed>}>
	 */
	public function expected_facts(): array {
		$cases = array();
		foreach ( LiveCatalogue::published() as $id => $product ) {
			$cases[ "{$id} {$product['name']}" ] = array( $id, self::facts( self::EXPECTED[ $id ] ) );
		}

		return $cases;
	}

	/**
	 * The table has a row for every product of the fixture and for nothing else.
	 */
	public function test_the_table_covers_the_fixture(): void {
		$expected = array_keys( self::EXPECTED );
		sort( $expected );

		$this->assertSame( $expected, array_keys( LiveCatalogue::published() ) );
		$this->assertCount( 89, $expected );
	}

	/**
	 * Every column of EXPECTED that the CSV holds equals the CSV converted by
	 * hand, except where NOT_AC_POWER and SYSTEM_NOT_MODULE say why not; a range
	 * in the CSV is EXPECTED's kwh_range.
	 *
	 * @dataProvider csv_rows
	 *
	 * @param int                   $id  Product ID.
	 * @param array<string, string> $csv The product's CSV row.
	 */
	public function test_the_table_follows_the_csv( int $id, array $csv ): void {
		list( $device_class, $application, $phase, $ac_power_kw, $pv_input_kw, $usable_kwh, $nominal_kwh, $kwh_range ) = self::EXPECTED[ $id ];

		$this->assertSame( $csv['category'], $device_class );
		$this->assertSame( '' === $csv['pa_application'] ? self::U : strtolower( $csv['pa_application'] ), $application );
		$this->assertSame( self::csv_phase( '' === $csv['pa_phase'] ? $csv['fig_phase'] : $csv['pa_phase'] ), $phase );
		if ( isset( self::NOT_AC_POWER[ $id ] ) ) {
			$this->assertSame( '_tv_b2b_figures.' . self::NOT_AC_POWER[ $id ], $csv['ac_power_src'] );
			$this->assertSame( self::U, $ac_power_kw );
		} else {
			$this->assertSame( self::csv_number( $csv['ac_power'] ), $ac_power_kw );
		}
		$this->assertSame( self::csv_number( $csv['max_pv_input'] ), $pv_input_kw );
		$this->assertSame( self::csv_number( $csv['usable_kwh'] ), $usable_kwh );
		$range = self::csv_range( $csv['nominal_kwh'] );
		if ( null !== $range ) {
			$this->assertSame( self::U, $nominal_kwh );
			$this->assertSame( $range, $kwh_range );
		} elseif ( in_array( $id, self::SYSTEM_NOT_MODULE, true ) ) {
			$this->assertSame( '_tv_b2b_figures.module_energy_kwh_nominal', $csv['nominal_src'] );
			$this->assertGreaterThan( self::csv_number( $csv['nominal_kwh'] ), $nominal_kwh );
		} else {
			$this->assertSame( self::csv_number( $csv['nominal_kwh'] ), $nominal_kwh );
		}
	}

	/**
	 * Cases of test_the_table_follows_the_csv(), one per CSV row.
	 *
	 * @return array<string, array{int, array<string, string>}>
	 */
	public function csv_rows(): array {
		$cases = array();
		foreach ( LiveCatalogue::research_csv() as $id => $row ) {
			$cases[ "{$id} {$row['name']}" ] = array( $id, $row );
		}

		return $cases;
	}

	/**
	 * The CSV has a row for every product of the table.
	 */
	public function test_the_csv_covers_the_table(): void {
		$ids = array_keys( LiveCatalogue::research_csv() );
		sort( $ids );

		$this->assertSame( array_keys( LiveCatalogue::published() ), $ids );
	}

	/**
	 * The six GoodWe ETR inverters are commercial three-phase, 80–125 kW AC and 160–250 kW PV.
	 */
	public function test_etr_inverters(): void {
		$etr = array(
			6507 => array( 80.0, 160.0 ),
			6508 => array( 99.99, 200.0 ),
			6509 => array( 100.0, 200.0 ),
			6510 => array( 110.0, 220.0 ),
			6511 => array( 124.99, 250.0 ),
			3595 => array( 125.0, 250.0 ),
		);
		$this->mock_live_products( array_keys( $etr ) );

		foreach ( $etr as $id => list( $ac_kw, $pv_kw ) ) {
			$facts = SelectionFacts::for_product( $id );
			$this->assertSame( array( 'inverters', 'commercial', 3, $ac_kw, $pv_kw ), array( $facts->device_class, $facts->application, $facts->phase, $facts->ac_power_kw, $facts->pv_input_kw ), (string) $id );
		}
	}

	/**
	 * The six GoodWe ESA battery modules state no phase.
	 */
	public function test_esa_battery_modules_have_no_phase(): void {
		$modules = array( 3611, 3612, 6519, 6520, 6521, 6522 );
		$this->mock_live_products( $modules );

		foreach ( $modules as $id ) {
			$this->assertSame( self::U, SelectionFacts::for_product( $id )->phase, (string) $id );
		}
	}

	/**
	 * On the live data the home three-phase inverters are the research's 28.
	 */
	public function test_home_three_phase_inverters(): void {
		$this->assertSame( self::HOME_THREE_PHASE, $this->home_three_phase_inverters( false ) );
	}

	/**
	 * After tools/migrate/7-facts.json, the EcoFlow inverters 6480–6482 and the
	 * SAJ H2-25K-T3 (1179) and H2-30K-T3-DE (1181) join them.
	 */
	public function test_home_three_phase_inverters_after_the_migration(): void {
		$expected = array_merge( self::HOME_THREE_PHASE, array( 1179, 1181, 6480, 6481, 6482 ) );
		sort( $expected );

		$this->assertSame( $expected, $this->home_three_phase_inverters( true ) );
	}

	/**
	 * After the migration every EcoFlow OCEAN 2 inverter has its application and
	 * phase, and the SAJ CHS2-29.9K-T4-X has its datasheet power.
	 */
	public function test_migrated_facts(): void {
		$expected = array(
			6480 => array( 'home', 3, 5.0, 10.0 ),
			6481 => array( 'home', 3, 15.0, 24.0 ),
			6482 => array( 'home', 3, 15.0, 24.0 ),
			6483 => array( 'home', 1, 3.0, 9.0 ),
			6484 => array( 'home', 1, 3.68, 9.68 ),
			6485 => array( 'home', 1, 4.6, 10.6 ),
			6486 => array( 'home', 1, 5.0, 11.0 ),
			6487 => array( 'home', 1, 5.75, 11.0 ),
			6488 => array( 'home', 1, 6.0, 12.0 ),
			1959 => array( 'commercial', 3, 29.999, 59.998 ),
		);
		$this->mock_live_products( array_keys( $expected ), true );

		foreach ( $expected as $id => $facts ) {
			$set = SelectionFacts::for_product( $id );
			$this->assertSame( $facts, array( $set->application, $set->phase, $set->ac_power_kw, $set->pv_input_kw ), (string) $id );
		}
	}

	/**
	 * The draft PowerCube-X2 (4124) states 24.9 kWh, the seven-module X2 row of
	 * the 2022 Pylontech brochure (pylontech_optim_us.pdf p.30), not this
	 * five-module product.
	 */
	public function test_draft_4124_before_the_migration(): void {
		$this->mock_live_products( array( 4124 ) );

		$this->assertSame( 24.9, SelectionFacts::for_product( 4124 )->nominal_kwh );
	}

	/**
	 * After the migration it has its datasheet's 3.552 kWh × 5 modules.
	 */
	public function test_draft_4124_after_the_migration(): void {
		$this->mock_live_products( array( 4124 ), true );

		$this->assertSame( 17.76, SelectionFacts::for_product( 4124 )->nominal_kwh );
	}

	/**
	 * What every live product's facts hold fits SelectionFactSet::schema(),
	 * the schema the REST route documents.
	 */
	public function test_every_live_fact_set_fits_the_schema(): void {
		WP_Mock::passthruFunction( '__' );
		$schema   = SelectionFactSet::schema();
		$products = LiveCatalogue::published( true );
		$this->mock_live_products( array_keys( $products ), true );

		foreach ( array_keys( $products ) as $id ) {
			$facts = SelectionFacts::for_product( $id )->to_array();
			$this->assertSame( array(), array_diff( $schema['required'], array_keys( $facts ) ), (string) $id );
			$this->assertSame( array(), array_diff( array_keys( $facts ), array_keys( $schema['properties'] ) ), (string) $id );
			$this->assertContains( $facts['device_class'], $schema['properties']['device_class']['enum'], (string) $id );
			$this->assertContains( $facts['application'], $schema['properties']['application']['enum'], (string) $id );
			$this->assertContains( $facts['phase'], array( 1, 3, self::U ), (string) $id );
		}
	}

	/**
	 * A CSV phase cell as a phase fact, read by hand from the cells the CSV has.
	 *
	 * @param string $cell pa_phase, or the figure text when pa_phase is empty.
	 * @return int|string
	 */
	private static function csv_phase( string $cell ): int|string {
		$phases = array(
			'Three-phase'     => 3,
			'Three Phase'     => 3,
			'3L+N+PE'         => 3,
			'3+N+PE, 380/400' => 3,
			'Single-phase'    => 1,
		);

		return $phases[ $cell ] ?? self::U;
	}

	/**
	 * A CSV cell "<value> <unit>" in kW or kWh; an empty cell is unknown.
	 *
	 * @param string $cell CSV cell.
	 * @return float|string
	 */
	private static function csv_number( string $cell ): float|string {
		if ( '' === $cell ) {
			return self::U;
		}
		list( $value, $unit ) = explode( ' ', $cell );
		$divisors             = array(
			'W'   => 1000,
			'Wp'  => 1000,
			'kW'  => 1,
			'kWh' => 1,
		);

		return (float) $value / $divisors[ $unit ];
	}

	/**
	 * A CSV energy cell that is a range or a list of options, as [min, max].
	 *
	 * @param string $cell CSV cell.
	 * @return array{float, float}|null
	 */
	private static function csv_range( string $cell ): ?array {
		$numbers = preg_split( '/\s*[–\-\/]\s*/u', explode( ' kWh', $cell )[0] );
		if ( false === $numbers || count( $numbers ) < 2 ) {
			return null;
		}
		$numbers = array_map( 'floatval', $numbers );

		return array( min( $numbers ), max( $numbers ) );
	}

	/**
	 * IDs of the inverters whose facts are home and three-phase, ascending.
	 *
	 * @param bool $migrated Whether tools/migrate/7-facts.json is applied.
	 * @return int[]
	 */
	private function home_three_phase_inverters( bool $migrated ): array {
		$products = LiveCatalogue::published( $migrated );
		$this->mock_live_products( array_keys( $products ), $migrated );

		$ids = array();
		foreach ( array_keys( $products ) as $id ) {
			$facts = SelectionFacts::for_product( $id );
			if ( 'inverters' === $facts->device_class && 'home' === $facts->application && 3 === $facts->phase ) {
				$ids[] = $id;
			}
		}
		sort( $ids );

		return $ids;
	}

	/**
	 * Mocks the given fixture products.
	 *
	 * @param int[] $ids      Product IDs.
	 * @param bool  $migrated Whether tools/migrate/7-facts.json is applied.
	 */
	private function mock_live_products( array $ids, bool $migrated = false ): void {
		$products = LiveCatalogue::products( $migrated );
		foreach ( $ids as $id ) {
			$product = $products[ $id ];
			$this->mock_product( $id, $product['categories'], $product['attributes']['pa_application'] ?? array(), $product['attributes']['pa_phase'] ?? array(), $product['figures'] );
		}
	}

	/**
	 * A row of EXPECTED as SelectionFactSet::to_array() returns it.
	 *
	 * @param array{string, string, int|string, float|string, float|string, float|string, float|string, array{float, float}|null} $row Expected row.
	 * @return array<string, mixed>
	 */
	private static function facts( array $row ): array {
		$facts = array_combine( array( 'device_class', 'application', 'phase', 'ac_power_kw', 'pv_input_kw', 'usable_kwh', 'nominal_kwh' ), array_slice( $row, 0, 7 ) );
		if ( null !== $row[7] ) {
			$facts['kwh_range'] = array(
				'min' => $row[7][0],
				'max' => $row[7][1],
			);
		}

		return $facts;
	}
}
