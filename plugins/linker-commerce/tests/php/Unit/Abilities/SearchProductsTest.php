<?php
/**
 * Tests for linker/search-products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\SearchProducts;
use Linker\Commerce\Tests\Support\LiveProducts;
use Linker\Commerce\Tests\Support\MocksLiveProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Qualification, sorting and the R1 residential three-phase 10 kWp set.
 *
 * @covers \Linker\Commerce\Abilities\SearchProducts
 * @covers \Linker\Commerce\Abilities\ProductCommerce
 * @covers \Linker\Commerce\Abilities\ProductText
 */
final class SearchProductsTest extends TestCase {

	use MocksLiveProducts;

	/**
	 * The research's 28 residential three-phase hybrid inverters
	 * (docs/research/2026-10-09/old-repo-live-catalogue-facts.md).
	 */
	private const HOME_THREE_PHASE = array( 1182, 1183, 1184, 1185, 1186, 1187, 2063, 2064, 2198, 2199, 3555, 3556, 3574, 3575, 3576, 3583, 3584, 3585, 4107, 4108, 4109, 6512, 6513, 6514, 6515, 6516, 6517, 6518 );

	/**
	 * Six GoodWe ETR inverters: commercial, must not appear in R1.
	 */
	private const ETR = array( 6507, 6508, 6509, 6510, 6511, 3595 );

	/**
	 * Six GoodWe ESA battery modules: not inverters, must not appear in R1.
	 */
	private const ESA = array( 3611, 3612, 6519, 6520, 6521, 6522 );

	/**
	 * HS2-5K (4109) PV 7.5 kW and HS2-6K (1183) PV 9 kW fall below 10 kWp.
	 */
	private const BELOW_10_KWP = array( 4109, 1183 );

	/**
	 * Translation and permalinks return their source.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( 'home_url' );
		WP_Mock::passthruFunction( 'add_query_arg' );
	}

	/**
	 * The ability is read-only, anonymous, and OPTIONS can show both schemas.
	 */
	public function test_args_expose_rest_schemas(): void {
		$args = ( new SearchProducts() )->args();

		$this->assertTrue( $args['meta']['show_in_rest'] );
		$this->assertTrue( $args['meta']['annotations']['readonly'] );
		$this->assertTrue( ( new SearchProducts() )->can_execute() );
		$this->assertSame( 'object', $args['input_schema']['type'] );
		$this->assertSame( 'object', $args['output_schema']['type'] );
		$this->assertContains( 'qualified', $args['output_schema']['required'] );
		$this->assertSame( 12, $args['input_schema']['properties']['limit']['maximum'] );
	}

	/**
	 * R1: residential three-phase 10 kWp. Qualified ⊆ the 28-inverter set,
	 * minus HS2-5K/HS2-6K whose PV input is below 10 kW. No ETR, no ESA.
	 * Sort is |ac_power_kw − 10| so 10 kW machines come first.
	 */
	public function test_r1_residential_three_phase_10_kwp(): void {
		$ids = array_keys( LiveProducts::published() );
		$this->mock_live_products( $ids );
		$result    = ( new SearchProducts() )->select(
			$ids,
			array(
				'device_class' => 'inverters',
				'application'  => 'home',
				'phase'        => 3,
				'pv_kwp'       => 10,
				'future'       => array( 'battery' ),
				'lang'         => 'en',
				'limit'        => 12,
			),
			'en',
			12
		);
		$qualified = array_column( $result['qualified'], 'product_id' );
		$known     = array();
		foreach ( $result['qualified'] as $card ) {
			if ( 'home' === $card['facts']['application'] && 3 === $card['facts']['phase'] ) {
				$known[] = $card['product_id'];
			}
		}
		$allowed = array_values( array_diff( self::HOME_THREE_PHASE, self::BELOW_10_KWP ) );

		$this->assertSame( array(), array_diff( $known, $allowed ), 'known home×3φ qualified ⊆ the research\'s 28, minus PV < 10 kW' );
		$this->assertSame( array(), array_intersect( $qualified, self::ETR ), 'no ETR' );
		$this->assertSame( array(), array_intersect( $qualified, self::ESA ), 'no ESA batteries' );
		$this->assertNotContains( 4109, $qualified, 'HS2-5K pv_input 7.5 < 10' );
		$this->assertNotContains( 1183, $qualified, 'HS2-6K pv_input 9 < 10' );
		$this->assertContains( 2198, $allowed, 'HS3-5K pv_input 10 stays in the allowed set' );
		$this->assertContains( 4107, $qualified, 'H2-10K-T3 qualifies' );
		$this->assertSame( 12, count( $qualified ) );
		$this->assertContains( 4107, array_slice( $qualified, 0, 6 ), '10 kW machines sort near the top' );
		foreach ( $result['qualified'] as $card ) {
			$this->assertContains( $card['facts']['application'], array( 'home', 'unknown' ) );
			$this->assertContains( $card['facts']['phase'], array( 3, 'unknown' ) );
			$why_fields = array_column( $card['why'], 'field' );
			$this->assertContains( 'application', $why_fields );
			$this->assertContains( 'phase', $why_fields );
			$this->assertContains( 'pv_input_kw', $why_fields );
			$this->assertContains( 'battery_pairing', $why_fields );
			$this->assertFalse( $card['commerce']['price_visible'], 'guests do not see prices' );
		}
		$this->assertArrayHasKey( 'application', $result['excluded']['by_reason'] );
		$this->assertGreaterThan( 0, $result['excluded']['by_reason']['application'] );
	}

	/**
	 * Full matches sort before a product that is only unknown on an applied filter.
	 */
	public function test_full_matches_sort_before_unknown(): void {
		$this->mock_live_products( array( 4107, 6480 ) );
		$result = ( new SearchProducts() )->select(
			array( 4107, 6480 ),
			array(
				'device_class' => 'inverters',
				'application'  => 'home',
				'phase'        => 3,
				'pv_kwp'       => 10,
				'limit'        => 12,
			),
			'en',
			12
		);
		$ids    = array_column( $result['qualified'], 'product_id' );

		$this->assertSame( array( 4107, 6480 ), $ids );
		$this->assertContains( 'application', $result['unknown_fields'] );
	}

	/**
	 * After the #7 migration, 6480 is home three-phase and sorts with the full matches.
	 */
	public function test_migrated_ecoflow_is_a_full_match(): void {
		$this->mock_live_products( array( 4107, 6480 ), true );
		$result = ( new SearchProducts() )->select(
			array( 4107, 6480 ),
			array(
				'device_class' => 'inverters',
				'application'  => 'home',
				'phase'        => 3,
				'pv_kwp'       => 10,
				'limit'        => 12,
			),
			'en',
			12
		);

		$this->assertSame( array(), $result['unknown_fields'] );
		$this->assertSame( array( 4107, 6480 ), array_column( $result['qualified'], 'product_id' ) );
	}

	/**
	 * Closer AC power to the stated kWp sorts first when both are full matches.
	 */
	public function test_sorts_by_ac_power_distance_to_pv_kwp(): void {
		$this->mock_live_products( array( 2064, 4107 ) );
		$result = ( new SearchProducts() )->select(
			array( 2064, 4107 ),
			array(
				'device_class' => 'inverters',
				'application'  => 'home',
				'phase'        => 3,
				'pv_kwp'       => 10,
				'limit'        => 12,
			),
			'en',
			12
		);

		$this->assertSame( array( 4107, 2064 ), array_column( $result['qualified'], 'product_id' ) );
	}

		/**
		 * With pairings, documented batteries are listed on an inverter, never not_released.
		 */
	public function test_with_pairings_lists_documented_batteries(): void {
		$ids = array( 4107, 1832, 2067 );
		$this->mock_live_products( $ids );
		$result = ( new SearchProducts() )->select(
			$ids,
			array(
				'device_class'  => 'inverters',
				'with_pairings' => true,
				'limit'         => 12,
			),
			'en',
			12
		);
		$h2     = $result['qualified'][0];
		$this->assertSame( 4107, $h2['product_id'] );
		$this->assertArrayHasKey( 'pairings', $h2 );
		foreach ( $h2['pairings'] as $pair ) {
			$this->assertNotSame( 'not_released', $pair['verdict'] );
		}
	}
}
