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
use WP_Term;

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
	 * The German page's address, the twin of the page above.
	 */
	private const PAGE_URL_DE = 'https://de-linker.test/de/compare-products/';

	/**
	 * The language the mocked language layer answers; a test that reads the
	 * German page sets it.
	 *
	 * @var string
	 */
	private string $language = 'en';

	/**
	 * Whether the language-navigation fixture has product twins.
	 *
	 * @var bool
	 */
	private bool $product_twins = false;

	/**
	 * Whether this fixture compares accessories instead of power equipment.
	 *
	 * @var bool
	 */
	private bool $accessories = false;

	/**
	 * Translation and escaping, and the WordPress reads of the fixture products.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_cache_supports', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_cache_flush_runtime', array( 'return' => true ) );
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'yes' ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => fn (): string => 'https://de-linker.test/' . ( 'de' === $this->language ? 'de/mein-konto/' : 'my-account/' ) ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => 'https://example.test/my-account/register/' ) );
		// English products: each answers for itself (CommerceState::is_rfq_only asks the language layer).
		$this->english_products(
			array(
				4107 => 4107,
				1832 => 1832,
			)
		);
		$this->plain_text();
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return_arg' => 0 ) );
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
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn ( int $id ): string => match ( $id ) {
					5385    => self::PAGE_URL,
					6608    => self::PAGE_URL_DE,
					default => 'https://de-linker.test/product/' . $id . '/',
				},
			)
		);
		WP_Mock::userFunction( 'has_filter', array( 'return' => fn (): bool => $this->product_twins ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ): string => (string) json_encode( $value ) ) );
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				// The language layer's answer as the instance's Polylang gives it:
				// the post itself in its own language, its twin in the other.
				'return' => function ( int $id, string $language = '' ): int {
					if ( $this->product_twins && in_array( $id, array( 4107, 84107 ), true ) ) {
						return 'de' === $language ? 84107 : 4107;
					}
					$translations = array(
						5385 => array(
							'en' => 5385,
							'de' => 6608,
						),
						6608 => array(
							'en' => 5385,
							'de' => 6608,
						),
					);
					return $translations[ $id ][ $language ] ?? 0;
				},
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'get_terms',
			array(
				'return' => static fn ( array $args ): array => array(
					new WP_Term(
						(object) array(
							'term_id' => 'inverters' === $args['slug'] ? 10 : ( 'accessories' === $args['slug'] ? 30 : 20 ),
							'name'    => 'inverters' === $args['slug'] ? 'Inverters' : 'Home storage',
						)
					),
				),
			)
		);
		WP_Mock::userFunction( 'pll_get_term', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction(
			'get_term',
			array(
				'return' => fn ( int $id ): WP_Term => new WP_Term(
					(object) array(
						'term_id' => $id,
						'name'    => 30 === $id ? ( 'de' === $this->language ? 'Zubehör' : 'Accessories' ) : ( 10 === $id ? ( 'de' === $this->language ? 'Wechselrichter' : 'Inverters' ) : ( 'de' === $this->language ? 'Heimspeicher' : 'Home storage' ) ),
					)
				),
			)
		);
		WP_Mock::userFunction( 'get_ancestors', array( 'return' => array() ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_the_post_thumbnail_url', array( 'return' => '' ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => static fn ( int $id ): string => self::PRODUCTS[ $id ]['name'] ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => fn ( int $id ): string => isset( self::PRODUCTS[ $id ] ) || ( $this->product_twins && 84107 === $id ) ? 'product' : '' ) );
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

		$html = ( new ComparePage( $this->comparison() ) )->table();

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
		$source = new \Linker\Commerce\Abilities\PublicationData(
			static function (): array {
				throw new \RuntimeException( 'An empty comparison must not assemble the product/document manifest.' );
			}
		);
		$html   = ( new ComparePage( new \Linker\Commerce\Products\Comparison( publication: $source ) ) )->table();

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

		$page  = new ComparePage( $this->comparison() );
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
		$_GET['ids']    = '4107,1832';
		$this->language = 'de';

		$german = ( new ComparePage( $this->comparison() ) )->table();

		$this->assertStringContainsString( 'Bemessungsleistung AC (kW)', $german );
		$this->assertStringContainsString( 'Anwendung', $german );
		$this->assertStringNotContainsString( 'Rated AC power (kW)', $german );
		unset( $_GET['ids'] );
	}

	/** Accessory comparisons show the maintained localized taxonomy label. */
	public function test_accessory_category_is_a_localized_name(): void {
		$_GET['ids']       = '4107,1832';
		$this->language    = 'de';
		$this->accessories = true;
		$html              = ( new ComparePage( $this->comparison() ) )->table();
		self::assertStringContainsString( 'Zubehör', $html );
		self::assertStringNotContainsString( '>accessories<', $html );
		unset( $_GET['ids'] );
	}

	/** Native translated slugs retain ordered product twins and run the state script. */
	public function test_german_page_keeps_product_twins_and_loads_selection_script(): void {
		$this->product_twins = true;
		$this->english_products(
			array(
				84107 => 4107,
				77    => 77,
				88    => 88,
				99    => 99,
				100   => 100,
			)
		);
		$page   = new WP_Post(
			(object) array(
				'ID'        => 6608,
				'post_type' => 'page',
				'post_name' => 'produkte-vergleichen',
			)
		);
		$source = new WP_Post(
			(object) array(
				'ID'        => 5385,
				'post_type' => 'page',
				'post_name' => 'compare-products',
			)
		);
		WP_Mock::userFunction( 'is_page', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $page ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'args'   => array( 5385 ),
				'return' => $source,
			)
		);
		self::assertSame(
			array(
				'ids'    => '4107',
				'capped' => '1',
			),
			ComparePage::language_query( array( 'ids' => '4107,4107,bad,84107,77,88,99,100' ), 'de' )
		);
		self::assertSame( array( 'ids' => '4107' ), ComparePage::language_query( array( 'ids' => '84107' ), 'en' ) );
		self::assertSame(
			array(
				84107 => 4107,
				4107  => 4107,
			),
			ComparePage::identities( array( 84107 ) )
		);
		$_GET['ids'] = '84107,4107,77,88,99,100';
		self::assertSame(
			array(
				'ids'    => array( 4107, 77, 88, 99 ),
				'capped' => true,
			),
			( new ComparePage() )->selection()
		);
		unset( $_GET['ids'] );
		WP_Mock::userFunction( 'plugins_url', array( 'return' => 'https://de-linker.test/compare-selection.js' ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'times' => 1 ) );
		( new ComparePage() )->assets();
	}

	/** An unrelated page must never inherit comparison state from arbitrary query data. */
	public function test_language_query_is_scoped_to_the_comparison_page(): void {
		WP_Mock::userFunction( 'is_page', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		self::assertSame( array(), ComparePage::language_query( array( 'ids' => '4107' ), 'de' ) );
		self::assertSame( array(), ComparePage::language_query( array( 'ids' => array( '4107' ) ), 'de' ) );
	}

	/**
	 * A product the data does not establish reads as an em dash, not as the
	 * word the fact contract uses internally.
	 */
	public function test_an_unknown_value_reads_as_a_dash(): void {
		$_GET['ids'] = '4107,1832';

		$html = ( new ComparePage( $this->comparison() ) )->table();

		$this->assertStringNotContainsString( '>unknown<', $html );
		$this->assertStringContainsString( '—', $html );
		unset( $_GET['ids'] );
	}

	/**
	 * The page's address carries the selection; without one it is the page.
	 */
	public function test_the_page_address_carries_the_selection(): void {
		$page = new ComparePage( $this->comparison() );

		$this->assertSame( self::PAGE_URL, $page->page_url() );
		$this->assertSame( self::PAGE_URL . '?ids=7,9', $page->page_url( array( 7, 9 ) ) );
		$this->assertSame( self::PAGE_URL . '?ids=7&capped=1', $page->page_url( array( 7 ), true ) );
	}

	/**
	 * The page's address on a German request is the German page, selection
	 * and all: the slug resolves to the page, the language layer's twin is
	 * the address that follows.
	 */
	public function test_the_german_page_address_is_the_german_page(): void {
		$this->language = 'de';
		$page           = new ComparePage( $this->comparison() );

		$this->assertSame( self::PAGE_URL_DE, $page->page_url() );
		$this->assertSame( self::PAGE_URL_DE . '?ids=7,9', $page->page_url( array( 7, 9 ) ) );
		$this->assertSame( self::PAGE_URL_DE . '?ids=7&capped=1', $page->page_url( array( 7 ), true ) );
	}

	/**
	 * On the German page every address the fragment prints stays German: the
	 * chip leads to the German page, and so do the Remove links and the Clear
	 * link — the canonical redirect the page keeps is the same address.
	 */
	public function test_the_german_fragment_leads_to_the_german_page(): void {
		$_GET['ids']    = '4107,1832';
		$this->language = 'de';

		$page  = new ComparePage( $this->comparison() );
		$table = $page->table();
		$chip  = $page->chip_shortcode();

		$this->assertStringContainsString( 'data-compare-page="' . self::PAGE_URL_DE . '"', $chip );
		$this->assertStringContainsString( 'href="' . self::PAGE_URL_DE . '"', $table );
		$this->assertStringContainsString( 'href="' . self::PAGE_URL_DE . '?ids=1832"', $table );
		$this->assertStringContainsString( 'href="' . self::PAGE_URL_DE . '?ids=4107"', $table );
		$this->assertStringNotContainsString( self::PAGE_URL . '"', $table );
		unset( $_GET['ids'] );
	}

	/**
	 * The chip is hidden until the tab has a selection, and carries its
	 * address, the maximum and the count in its own markup, so the browser
	 * needs no configuration of its own.
	 */
	public function test_the_chip_carries_its_address_and_its_maximum(): void {
		$chip = ( new ComparePage( $this->comparison() ) )->chip_shortcode();

		$this->assertStringContainsString( 'data-compare-chip', $chip );
		$this->assertStringContainsString( 'data-compare-page="' . self::PAGE_URL . '"', $chip );
		$this->assertStringContainsString( 'data-compare-max="4"', $chip );
		$this->assertStringContainsString( 'data-compare-count', $chip );
		$this->assertStringContainsString( 'hidden', $chip );
	}

	/** Presentation fixtures inject their stated facts and an explicit source set. */
	private function comparison(): \Linker\Commerce\Products\Comparison {
		$source = new \Linker\Commerce\Abilities\PublicationData(
			static function (): array {
				$products = array();
				foreach ( array_keys( self::PRODUCTS ) as $id ) {
					$products[] = array(
						'product_id'           => $id,
						'product_revision'     => (string) $id,
						'published_locale_ids' => array( $id ),
					);
				}
				return array(
					'source_revision'        => 'fixture',
					'compatibility_revision' => 'fixture',
					'products'               => $products,
					'documents'              => array(),
				);
			}
		);
		return new \Linker\Commerce\Products\Comparison( facts_reader: fn( int $id ): \Linker\Commerce\Products\SelectionFactSet => $this->accessories ? new \Linker\Commerce\Products\SelectionFactSet( 'accessories', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown', 'unknown' ) : \Linker\Commerce\Products\SelectionFacts::for_product( $id ), publication: $source );
	}
}
