<?php
/**
 * Tests for the comparison assembly.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Comparison;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Tests for Comparison: the one assembly Genie's ability and the comparison
 * page both read.
 *
 * @covers \Linker\Commerce\Products\Comparison
 */
final class ComparisonTest extends TestCase {

	/**
	 * Fixture products: category term, application, phase, and the figures and
	 * technical table the readings take.
	 *
	 * @var array<int, array<string, mixed>>
	 */
	private const PRODUCTS = array(
		4107 => array(
			'name'     => 'Inverter 4107',
			'category' => 'inverters',
			'phase'    => 'three-phase',
			'figures'  => array(
				'ac_output_kw_nominal' => array(
					'value' => '10',
					'unit'  => 'kW',
				),
			),
			'specs'    => array(
				array(
					'title'     => '',
					'spec_rows' => array(
						array(
							'spec_label'        => 'Rated AC power',
							'spec_value'        => '10.0',
							'spec_unit'         => 'kW',
							'spec_is_highlight' => true,
						),
					),
				),
			),
		),
		1832 => array(
			'name'     => 'Battery 1832',
			'category' => 'home-storage',
			'figures'  => array(
				'system_nominal_energy_kwh' => array(
					'value' => '5.12',
					'unit'  => 'kWh',
				),
			),
			'specs'    => array(
				array(
					'title'     => '',
					'spec_rows' => array(
						array(
							'spec_label' => 'Ingress protection',
							'spec_value' => 'IP66',
							'spec_unit'  => '',
						),
					),
				),
			),
		),
	);

	/**
	 * Translation and escaping return their argument.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_cache_supports', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_cache_flush_runtime', array( 'return' => true ) );
		// English products: each answers for itself (CommerceState::is_rfq_only asks the language layer).
		$this->english_products(
			array(
				4107 => 4107,
				1832 => 1832,
			)
		);
		$this->plain_text();
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => 0,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction( 'get_ancestors', array( 'return' => array() ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_the_post_thumbnail_url', array( 'return' => '' ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => static fn ( int $id ): string => self::PRODUCTS[ $id ]['name'] ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => static fn ( int $id ): string => 'https://de-linker.test/product/' . $id . '/' ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => static fn ( int $id ): string => isset( self::PRODUCTS[ $id ] ) ? 'product' : '' ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => 'publish' ) );
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'return' => static function ( int $id, string $taxonomy ) {
					$product = self::PRODUCTS[ $id ];
					if ( 'product_cat' === $taxonomy ) {
						return array(
							(object) array(
								'term_id' => 10,
								'slug'    => $product['category'],
								'name'    => $product['category'],
							),
						);
					}
					$slugs = array();
					foreach ( (array) ( $product[ substr( $taxonomy, 3 ) ] ?? array() ) as $slug ) {
						$slugs[] = $slug;
					}
					return array() === $slugs ? false : array(
						(object) array(
							'term_id' => 20,
							'slug'    => $slugs[0],
							'name'    => $slugs[0],
						),
					);
				},
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ) {
					$product = self::PRODUCTS[ $id ];
					return match ( $key ) {
						'_tv_b2b_figures'    => (string) json_encode( $product['figures'] ),
						'_tv_legacy_acf_json' => (string) json_encode( array( 'spec_groups' => $product['specs'] ) ),
						default              => '',
					};
				},
			)
		);
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => static function ( int $id ) {
					if ( ! isset( self::PRODUCTS[ $id ] ) ) {
						return false;
					}
					$product = Mockery::mock( WC_Product::class );
					$product->allows( 'get_id' )->andReturn( $id );
					$product->allows( 'get_parent_id' )->andReturn( 0 );
					$product->allows( 'get_sku' )->andReturn( 'SKU-' . $id );
					$product->allows( 'get_price_html' )->andReturn( '<span>€ 100</span>' );
					$product->allows( 'is_in_stock' )->andReturn( true );
					return $product;
				},
			)
		);
	}

	/**
	 * The columns keep the order they were asked for, and an ID that is not a
	 * published product drops out.
	 */
	public function test_columns_keep_the_order_and_drop_unknown_ids(): void {
		$comparison = ( new \Linker\Commerce\Products\Comparison( facts_reader: static fn( int $id ): \Linker\Commerce\Products\SelectionFactSet => \Linker\Commerce\Products\SelectionFacts::for_product( $id ) ) )->of( array( 1832, 999, 4107 ) );

		$this->assertSame( array( 1832, 4107 ), array_column( $comparison['products'], 'product_id' ) );
		$this->assertSame( 'SKU-1832', $comparison['products'][0]['sku'] );
		$this->assertSame( 'Battery 1832', $comparison['products'][0]['title'] );
	}

	/**
	 * An inverter and a battery: both families of dimension rows, and never a
	 * single mixed "power" row.
	 */
	public function test_the_rows_carry_both_families_and_never_a_mixed_power_row(): void {
		$comparison = ( new \Linker\Commerce\Products\Comparison( facts_reader: static fn( int $id ): \Linker\Commerce\Products\SelectionFactSet => \Linker\Commerce\Products\SelectionFacts::for_product( $id ) ) )->of( array( 4107, 1832 ) );
		$fields     = array_column( $comparison['rows'], 'field' );

		$this->assertSame(
			array( 'application', 'phase', 'ac_power_kw', 'pv_input_kw', 'usable_kwh', 'nominal_kwh', 'kwh_range' ),
			$fields
		);
		$power = $comparison['rows'][2];
		$this->assertSame( 'Rated AC power (kW)', $power['label'] );
		$this->assertSame( 10.0, $power['values'][4107] );
		$this->assertSame( 'unknown', $power['values'][1832], 'a battery does not state inverter output' );
	}

	/**
	 * The dimension labels follow the request language, and the page's rows
	 * are the same set the ability documents.
	 */
	public function test_the_labels_follow_the_language(): void {
		$german = ( new \Linker\Commerce\Products\Comparison( facts_reader: static fn( int $id ): \Linker\Commerce\Products\SelectionFactSet => \Linker\Commerce\Products\SelectionFacts::for_product( $id ) ) )->of( array( 4107 ), 'de' );

		$this->assertSame( 'Anwendung', $german['rows'][0]['label'] );
		$this->assertSame( 'Bemessungsleistung AC (kW)', $german['rows'][2]['label'] );
	}

	/**
	 * The technical rows are the union of the selected products' own tables:
	 * one row per label, the value under the product that states it.
	 */
	public function test_the_technical_rows_are_the_union_of_the_tables(): void {
		$comparison = ( new \Linker\Commerce\Products\Comparison( facts_reader: static fn( int $id ): \Linker\Commerce\Products\SelectionFactSet => \Linker\Commerce\Products\SelectionFacts::for_product( $id ) ) )->of( array( 4107, 1832 ) );
		$specs      = array_column( $comparison['specs'], null, 'label' );

		$this->assertSame( array( 'Rated AC power', 'Ingress protection' ), array_keys( $specs ) );
		$this->assertSame( '10.0 kW', $specs['Rated AC power']['values'][4107] );
		$this->assertArrayNotHasKey( 1832, $specs['Rated AC power']['values'] );
		$this->assertSame( 'IP66', $specs['Ingress protection']['values'][1832] );
	}

	/**
	 * The address's selection: numbers only, duplicates and non-numbers out,
	 * in order and never more than a comparison holds.
	 */
	public function test_parse_ids_caps_and_cleans_the_address(): void {
		$this->assertSame(
			array(
				'ids'    => array( 4, 7 ),
				'capped' => false,
			),
			Comparison::parse_ids( '4, 7, 4' )
		);
		$this->assertSame(
			array(
				'ids'    => array( 1, 2, 3, 4 ),
				'capped' => true,
			),
			Comparison::parse_ids( '1,2,3,4,5' )
		);
		$this->assertSame(
			array(
				'ids'    => array(),
				'capped' => false,
			),
			Comparison::parse_ids( 'abc,-3,0,1e3' )
		);
	}
}
