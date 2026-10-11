<?php
/**
 * Tests for the catalogue search.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Catalog;

use Linker\Commerce\Catalog\CatalogSearch;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Tests for CatalogSearch: the one rule behind the search box and the
 * archive's `q` filter. The rule on real products is CatalogSearchRestTest
 * in tests/php/Integration.
 *
 * @covers \Linker\Commerce\Catalog\CatalogSearch
 */
final class CatalogSearchTest extends TestCase {


	/**
	 * Separators and case do not decide what a model or item number is.
	 */
	public function test_normalize_folds_separators_and_case(): void {
		$this->assertSame( 'gw60kstsg10', CatalogSearch::normalize( 'GW60K-STS-G10' ) );
		$this->assertSame( 'gw60kstsg10', CatalogSearch::normalize( ' gw60k sts g10 ' ) );
		$this->assertSame( 'ch2299k', CatalogSearch::normalize( 'CH2-29.9K' ) );
	}

	/**
	 * A product matches by its name and by its item number.
	 */
	public function test_matches_name_or_sku(): void {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_name' )->andReturn( 'GoodWe GW60K-STS-G10' );
		$product->allows( 'get_sku' )->andReturn( 'DLK-GOODWE-GW60KSTSG10' );

		$this->assertTrue( CatalogSearch::matches( $product, CatalogSearch::normalize( 'gw60k-sts' ) ) );
		$this->assertTrue( CatalogSearch::matches( $product, CatalogSearch::normalize( 'DLK-GOODWE' ) ) );
		$this->assertFalse( CatalogSearch::matches( $product, CatalogSearch::normalize( 'saJ-h2' ) ) );
		$this->assertFalse( CatalogSearch::matches( $product, '' ) );
	}

	/**
	 * The hits are the visible catalogue's, in catalogue order, at most $limit
	 * of them; a query shorter than two characters names nothing.
	 */
	public function test_matching_ids_walks_the_visible_catalogue(): void {
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
					$product->allows( 'get_name' )->andReturn( 'GoodWe GW5.1 Battery ' . $id );
					$product->allows( 'get_sku' )->andReturn( 'DLK-GOODWE-' . $id );
					return $product;
				},
			)
		);

		$search = new CatalogSearch();
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
					$product->allows( 'get_name' )->andReturn( 'Inverter ' . $id );
					$product->allows( 'get_sku' )->andReturn( '' );
					return $product;
				},
			)
		);

		$search = new CatalogSearch();
		$this->assertCount( 1, $search->matching_ids( 'inverter', 0 ) );
		$this->assertCount( 3, $search->matching_ids( 'inverter', 99 ) );
	}
}
