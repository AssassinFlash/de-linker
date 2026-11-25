<?php
/**
 * Tests for the catalogue search.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\ProductSearch;
use Linker\Commerce\Products\SelectionFactSet;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Tests for ProductSearch: the one rule behind the search box and the
 * archive's `q` filter. The rule on real products is ProductSearchRestTest
 * in tests/php/Integration.
 *
 * @covers \Linker\Commerce\Products\ProductSearch
 */
final class ProductSearchTest extends TestCase {

	/** The default catalogue uses its own Woo SKU. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
	}


	/**
	 * Separators and case do not decide what a model or item number is.
	 */
	public function test_normalize_folds_separators_and_case(): void {
		$this->assertSame( 'gw60kstsg10', ProductSearch::normalize( 'GW60K-STS-G10' ) );
		$this->assertSame( 'gw60kstsg10', ProductSearch::normalize( ' gw60k sts g10 ' ) );
		$this->assertSame( 'ch2299k', ProductSearch::normalize( 'CH2-29.9K' ) );
	}

	/**
	 * A product matches by its name and by its item number.
	 */
	public function test_matches_name_or_sku(): void {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 11 );
		$product->allows( 'get_name' )->andReturn( 'GoodWe GW60K-STS-G10' );
		$product->allows( 'get_sku' )->andReturn( 'DLK-GOODWE-GW60KSTSG10' );

		$this->assertTrue( ProductSearch::matches( $product, ProductSearch::normalize( 'gw60k-sts' ) ) );
		$this->assertTrue( ProductSearch::matches( $product, ProductSearch::normalize( 'DLK-GOODWE' ) ) );
		$this->assertFalse( ProductSearch::matches( $product, ProductSearch::normalize( 'saJ-h2' ) ) );
		$this->assertFalse( ProductSearch::matches( $product, '' ) );
	}

	/** Model fragments and a verified power rating can appear in either order. */
	public function test_power_and_model_use_the_catalogue_rating(): void {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_name' )->andReturn( 'GoodWe GW60K-STS-G10' );
		WP_Mock::userFunction( 'wp_parse_list', array( 'return' => static fn( string $words ): array => explode( ' ', trim( $words ) ) ) );
		$product->allows( 'get_id' )->andReturn( 6530 );
		$product->allows( 'get_sku' )->andReturn( 'DLK-GOODWE-GW60KSTSG10' );
		$facts = new SelectionFactSet( 'accessories', 'home', 3, 60.0, 'unknown', 'unknown', 'unknown' );
		$this->assertTrue( ProductSearch::matches( $product, '60kW STS', $facts ) );
		$this->assertTrue( ProductSearch::matches( $product, 'STS 60 kW', $facts ) );
		$this->assertFalse( ProductSearch::matches( $product, '6 kW STS', $facts ) );
		$this->assertFalse( ProductSearch::matches( $product, '60 kW SAJ', $facts ) );
	}

	/**
	 * The hits are the visible range's, in shop order, at most $limit
	 * of them; a query shorter than two characters names nothing.
	 */
	public function test_matching_ids_walks_the_visible_products(): void {
		WP_Mock::userFunction(
			'wc_get_product_visibility_term_ids',
			array(
				'return' => array(
					'exclude-from-search'  => 7,
					'exclude-from-catalog' => 6,
				),
			)
		);
		WP_Mock::userFunction(
			'get_posts',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'      => 'product',
						'post_status'    => 'publish',
						'posts_per_page' => -1,
						'fields'         => 'ids',
						'orderby'        => 'menu_order title',
						'order'          => 'ASC',
						// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- the expectation names the query the search runs.
						'tax_query'      => array(
							array(
								'taxonomy' => 'product_visibility',
								'field'    => 'term_taxonomy_id',
								'terms'    => array( 7, 6 ),
								'operator' => 'NOT IN',
							),
						),
					),
				),
				'return' => array( 11, 12, 13 ),
			)
		);
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => static function ( int $id ): WC_Product {
					$product = Mockery::mock( WC_Product::class );
					$product->allows( 'get_id' )->andReturn( $id );
					$product->allows( 'get_name' )->andReturn( 'GoodWe GW5.1 Battery ' . $id );
					$product->allows( 'get_sku' )->andReturn( 'DLK-GOODWE-' . $id );
					return $product;
				},
			)
		);

		$search = new ProductSearch();
		$this->assertSame( array( 11, 12 ), $search->matching_ids( 'DLK-GOODWE', 2 ) );
		$this->assertSame( array(), $search->matching_ids( 'g', 8 ), 'One character is no query.' );
		$this->assertSame( array(), $search->matching_ids( '---', 8 ), 'A query without letters or digits is no query.' );
	}

	/**
	 * The limits: never more than the route allows, never fewer than one.
	 */
	public function test_limit_is_clamped(): void {
		WP_Mock::userFunction( 'wc_get_product_visibility_term_ids', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( 11, 12, 13 ) ) );
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => static function ( int $id ): WC_Product {
					$product = Mockery::mock( WC_Product::class );
					$product->allows( 'get_id' )->andReturn( $id );
					$product->allows( 'get_name' )->andReturn( 'Inverter ' . $id );
					$product->allows( 'get_sku' )->andReturn( '' );
					return $product;
				},
			)
		);

		$search = new ProductSearch();
		$this->assertCount( 1, $search->matching_ids( 'inverter', 0 ) );
		$this->assertCount( 3, $search->matching_ids( 'inverter', 99 ) );
	}
}
