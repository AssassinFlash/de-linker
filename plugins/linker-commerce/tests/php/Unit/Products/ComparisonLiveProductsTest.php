<?php
/**
 * The comparison assembly on the live products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Abilities\CompareProducts;
use Linker\Commerce\Products\Comparison;
use Linker\Commerce\Tests\Support\MocksLiveProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Comparison over the live catalogue fixture (tests/fixtures/live-products-2026-10-09.json,
 * the published inverters and batteries of de-linker.com as read on
 * 2026-10-09): the real figures of the products Genie and the comparison page
 * show, and the one assembly both entries read.
 *
 * @covers \Linker\Commerce\Products\Comparison
 */
final class ComparisonLiveProductsTest extends TestCase {

	use MocksLiveProducts;

	/**
	 * Translation returns its source.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
		// Another test class earlier in the run may already have mocked
		// has_filter (WP_Mock defines the function for the rest of the
		// process), which puts SelectionFacts' twin-swap branch on the
		// path; the swap has no listener here.
		WP_Mock::userFunction(
			'has_filter',
			array(
				'return' => false,
				'times'  => '0+',
			)
		);
		// ComparisonTest in this namespace mocks pll_get_post in its setUp.
		// Once any test defines that function, function_exists stays true
		// for the process, so the live assembly has to stub the same call
		// or a full-suite run reaches ProductText::translated_id unmocked.
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => 0,
				'times'  => '0+',
			)
		);
	}

	/**
	 * An inverter and a battery of the live catalogue: the columns carry their
	 * real names and the rows their real figures — 4107 states 10 kW AC and
	 * 20 kW PV input (the fixture's own entry), 1832 is a 4.5 kWh usable /
	 * 5.0 kWh nominal home battery with the 5–25 kWh range its figures state.
	 */
	public function test_the_rows_carry_the_live_figures_of_the_products(): void {
		$this->mock_live_products( array( 4107, 1832 ) );

		$comparison = ( new Comparison( publication: $this->publication_data() ) )->of( array( 4107, 1832 ) );
		$rows       = array_column( $comparison['rows'], 'values', 'field' );

		$this->assertSame( array( 4107, 1832 ), array_column( $comparison['products'], 'product_id' ) );
		$this->assertSame( 'SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)', $comparison['products'][0]['title'] );
		$this->assertSame( 10.0, $rows['ac_power_kw'][4107] );
		$this->assertSame( 20.0, $rows['pv_input_kw'][4107] );
		$this->assertSame( 3, $rows['phase'][4107] );
		$this->assertSame( 'home', $rows['application'][4107] );
		$this->assertSame( 'unknown', $rows['usable_kwh'][1832] );
		$this->assertSame( 5.0, $rows['nominal_kwh'][1832] );
		$this->assertSame(
			array(
				'min' => 5.0,
				'max' => 25.0,
			),
			$rows['kwh_range'][1832]
		);
		$this->assertSame( 'unknown', $rows['usable_kwh'][4107] );
		$this->assertSame( 'unknown', $rows['ac_power_kw'][1832] );
	}

	/**
	 * The ability reads the same assembly: its products are the columns' four
	 * fields, its rows the rows' field/label/values — so Genie's table and the
	 * page's table cannot drift apart.
	 */
	public function test_the_ability_is_the_same_assembly(): void {
		$this->mock_live_products( array( 4107, 1832 ) );

		$comparison = ( new Comparison( publication: $this->publication_data() ) )->of( array( 4107, 1832 ) );
		$ability    = ( new CompareProducts( null, $this->publication_data() ) )->execute(
			array(
				'product_ids' => array( 4107, 1832 ),
				'lang'        => 'en',
			)
		);

		$this->assertSame( array( 'product_id', 'title', 'url', 'facts' ), array_keys( $ability['products'][0] ) );
		$this->assertSame( array_column( $comparison['rows'], 'field' ), array_column( $ability['rows'], 'field' ) );
		foreach ( $comparison['rows'] as $index => $row ) {
			$this->assertSame( $row['values'], (array) $ability['rows'][ $index ]['values'] );
			$this->assertSame( $row['label'], $ability['rows'][ $index ]['label'] );
		}
	}

	/**
	 * The German build of the same two products: the labels are German, the
	 * values and the column order are the ones asked for.
	 */
	public function test_the_german_build_keeps_the_values_and_translates_the_labels(): void {
		$this->mock_live_products( array( 1832, 4107 ) );

		$comparison = ( new Comparison( publication: $this->publication_data() ) )->of( array( 1832, 4107 ), 'de' );
		$rows       = array_column( $comparison['rows'], 'values', 'field' );
		$labels     = array_column( $comparison['rows'], 'label', 'field' );

		$this->assertSame( array( 1832, 4107 ), array_column( $comparison['products'], 'product_id' ) );
		$this->assertSame( 'Nutzbare Energie (kWh)', $labels['usable_kwh'] );
		$this->assertSame( 5.0, $rows['nominal_kwh'][1832] );
	}
}
