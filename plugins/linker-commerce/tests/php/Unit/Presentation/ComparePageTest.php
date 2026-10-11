<?php
/**
 * Tests for the comparison page's table and chip.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\ComparePage;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;
use WP_Post;

/**
 * Tests for ComparePage: the fragment the LC template renders, the address it
 * keeps, and the chip that leads to it.
 *
 * @covers \Linker\Commerce\Presentation\ComparePage
 */
final class ComparePageTest extends TestCase {

	/**
	 * The products of the fixture: categories and figures, and the technical
	 * table of one of them.
	 *
	 * @var array<int, array<string, mixed>>
	 */
	private const PRODUCTS = array(
		4107 => array(
			'name'     => 'Inverter 4107',
			'category' => 'inverters',
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
							'spec_label' => 'Rated AC power',
							'spec_value' => '10.0',
							'spec_unit'  => 'kW',
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
			'specs'    => array(),
		),
	);

	/**
	 * The page's address as the tests serve it.
	 */
	private const PAGE_URL = 'https://de-linker.test/compare-products/';

	/**
	 * The language the mocked language layer answers; a test that reads the
	 * German page sets it.
	 */
	private string $language = 'en';

	/**
	 * Translation and escaping, and the WordPress reads of the fixture products.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn ( string $value ): string => rtrim( $value, '/' ) . '/' ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://de-linker.test/' ) );
		WP_Mock::userFunction(
			'pll_current_language',
			array(
				'times'  => '0+',
				'return' => function (): string {
					return $this->language;
				},
			)
		);
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'return' => static function ( string $slug ): WP_Post {
					return new WP_Post(
						(object) array(
							'ID'        => 5385,
							'post_name' => $slug,
							'post_type' => 'page',
						)
					);
				},
			)
		);
		WP_Mock::userFunction( 'get_permalink', array( 'return' => self::PAGE_URL ) );
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
		WP_Mock::userFunction( 'get_post_type', array( 'return' => static fn ( int $id ): string => isset( self::PRODUCTS[ $id ] ) ? 'product' : '' ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => 'publish' ) );
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'return' => static function ( int $id, string $taxonomy ) {
					if ( 'product_cat' !== $taxonomy ) {
						return false;
					}
					return array(
						(object) array(
							'term_id' => 10,
							'slug'    => self::PRODUCTS[ $id ]['category'],
							'name'    => self::PRODUCTS[ $id ]['category'],
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
						'_tv_b2b_figures'     => (string) json_encode( $product['figures'] ),
						'_tv_legacy_acf_json' => (string) json_encode( array( 'spec_groups' => $product['specs'] ) ),
						default               => '',
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
	 * The table: one column per product with its item number, its price and its
	 * availability, the size rows, and the technical rows of its own table.
	 */
	public function test_the_table_has_one_column_per_product(): void {
		$_GET['ids'] = '4107,1832';

		$html = ( new ComparePage() )->table();

		$this->assertStringContainsString( 'data-compare-ids="4107,1832"', $html );
		$this->assertStringContainsString( 'Inverter 4107', $html );
		$this->assertStringContainsString( 'Battery 1832', $html );
		$this->assertStringContainsString( 'SKU-4107', $html );
		$this->assertStringContainsString( 'Net price after partner sign-in', $html );
		$this->assertStringContainsString( 'In stock', $html );
		$this->assertStringContainsString( 'Rated AC power (kW)', $html );
		$this->assertStringContainsString( '10.0 kW', $html );
		$this->assertStringContainsString( 'Remove', $html );
		unset( $_GET['ids'] );
	}

	/**
	 * Nothing selected: the empty state, and no table at all.
	 */
	public function test_an_empty_selection_shows_the_empty_state(): void {
		$html = ( new ComparePage() )->table();

		$this->assertStringContainsString( 'Choose products to compare their specifications.', $html );
		$this->assertStringNotContainsString( '<table', $html );
	}

	/**
	 * An address that asked for more than four products says so, and keeps the
	 * first four in the order they were asked for.
	 */
	public function test_a_capped_address_says_only_the_first_products_are_shown(): void {
		$_GET['ids']    = '1,2,3,4,5';
		$_GET['capped'] = '1';

		$page  = new ComparePage();
		$table = $page->table();

		$this->assertStringContainsString( 'Only the first 4 products are shown.', $table );
		$this->assertSame( array( 1, 2, 3, 4 ), $page->selection()['ids'] );
		unset( $_GET['ids'], $_GET['capped'] );
	}

	/**
	 * The rows follow the page's language: the German page labels the
	 * dimensions in German, the same words the product page's key numbers and
	 * Genie's table use.
	 */
	public function test_the_rows_follow_the_page_language(): void {
		$_GET['ids']     = '4107,1832';
		$this->language = 'de';

		$german = ( new ComparePage() )->table();

		$this->assertStringContainsString( 'Bemessungsleistung AC (kW)', $german );
		$this->assertStringContainsString( 'Anwendung', $german );
		$this->assertStringNotContainsString( 'Rated AC power (kW)', $german );
		unset( $_GET['ids'] );
	}

	/**
	 * A product the data does not establish reads as an em dash, not as the
	 * word the fact contract uses internally.
	 */
	public function test_an_unknown_value_reads_as_a_dash(): void {
		$_GET['ids'] = '4107,1832';

		$html = ( new ComparePage() )->table();

		$this->assertStringNotContainsString( '>unknown<', $html );
		$this->assertStringContainsString( '—', $html );
		unset( $_GET['ids'] );
	}

	/**
	 * The page's address carries the selection; without one it is the page.
	 */
	public function test_the_page_address_carries_the_selection(): void {
		$page = new ComparePage();

		$this->assertSame( self::PAGE_URL, $page->page_url() );
		$this->assertSame( self::PAGE_URL . '?ids=7,9', $page->page_url( array( 7, 9 ) ) );
		$this->assertSame( self::PAGE_URL . '?ids=7&capped=1', $page->page_url( array( 7 ), true ) );
	}

	/**
	 * The chip is hidden until the tab has a selection, and carries its
	 * address, the maximum and the count in its own markup, so the browser
	 * needs no configuration of its own.
	 */
	public function test_the_chip_carries_its_address_and_its_maximum(): void {
		$chip = ( new ComparePage() )->chip_shortcode();

		$this->assertStringContainsString( 'data-compare-chip', $chip );
		$this->assertStringContainsString( 'data-compare-page="' . self::PAGE_URL . '"', $chip );
		$this->assertStringContainsString( 'data-compare-max="4"', $chip );
		$this->assertStringContainsString( 'data-compare-count', $chip );
		$this->assertStringContainsString( 'hidden', $chip );
	}
}
