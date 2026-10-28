<?php
/**
 * Tests for the catalogue filter's request reading.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Term;
use Mockery;

/**
 * The facets the request states: the search box's `q` beside the rail's
 * facets, the unsafe input sanitised away (#16 replica port).
 *
 * @covers \Linker\Commerce\Storefront\ProductFilters::requested
 */
final class ProductFiltersTest extends TestCase {

	/**
	 * The grid keeps native taxonomy conditions and intersects visibility, even for an OR root.
	 *
	 * @dataProvider native_taxonomy_relations
	 * @param string $relation The native query's top-level relation.
	 */
	public function test_archive_keeps_the_complete_native_taxonomy_query( string $relation ): void {
		$native                  = array(
			'relation' => $relation,
			array(
				'taxonomy' => 'pa_brand',
				'field'    => 'slug',
				'terms'    => array( 'goodwe' ),
			),
			array(
				'relation' => 'OR',
				array(
					'taxonomy' => 'product_cat',
					'field'    => 'slug',
					'terms'    => array( 'nonexistent' ),
				),
				array(
					'taxonomy' => 'pa_phase',
					'field'    => 'slug',
					'terms'    => array( 'three-phase' ),
				),
			),
			array(
				'taxonomy' => 'language',
				'field'    => 'term_taxonomy_id',
				'terms'    => array( 7 ),
			),
		);
		$term                    = new WP_Term(
			(object) array(
				'term_id'  => 191,
				'taxonomy' => 'product_brand',
				'slug'     => 'goodwe',
			)
		);
		$previous_query          = $GLOBALS['wp_the_query'] ?? null;
		$main_query              = Mockery::mock( \WP_Query::class );
		$tax_query               = Mockery::mock( \WP_Tax_Query::class );
		$tax_query->queries      = $native;
		$main_query->tax_query   = $tax_query;
		$GLOBALS['wp_the_query'] = $main_query;
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'yes' ) );
		WP_Mock::userFunction(
			'wc_get_product_visibility_term_ids',
			array(
				'return' => array(
					'outofstock'           => 98,
					'exclude-from-catalog' => 99,
				),
			)
		);
		WP_Mock::userFunction( 'get_posts' )->once()->andReturnUsing(
			static function ( array $args ) use ( $native ): array {
				self::assertSame( 'AND', $args['tax_query']['relation'] );
				self::assertSame( $native, $args['tax_query'][0] );
				self::assertSame( array( 98 ), $args['tax_query'][1]['terms'] );
				self::assertSame( array( 99 ), $args['tax_query'][2]['terms'] );
				return array();
			}
		);
		try {
			self::assertSame( array(), ( new ProductFilters() )->archive_product_ids() );
		} finally {
			$GLOBALS['wp_the_query'] = $previous_query;
		}
	}

	/**
	 * Native root relations to retain inside the visibility intersection.
	 *
	 * @return array<string, array{string}>
	 */
	public static function native_taxonomy_relations(): array {
		return array(
			'and' => array( 'AND' ),
			'or'  => array( 'OR' ),
		);
	}

	/** Brand routes use the same native attribute as cards and brand filters. */
	public function test_brand_archive_reads_attribute_members_and_keeps_visibility_guards(): void {
		$term = new WP_Term(
			(object) array(
				'term_id'  => 191,
				'taxonomy' => 'product_brand',
				'slug'     => 'goodwe',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'yes' ) );
		WP_Mock::userFunction(
			'wc_get_product_visibility_term_ids',
			array(
				'return' => array(
					'outofstock'           => 98,
					'exclude-from-catalog' => 99,
				),
			)
		);
		WP_Mock::userFunction( 'get_posts' )->once()->andReturnUsing(
			static function ( array $args ): array {
				self::assertSame( 'publish', $args['post_status'] );
				self::assertSame(
					array(
						'taxonomy' => 'pa_brand',
						'field'    => 'slug',
						'terms'    => 'goodwe',
					),
					$args['tax_query'][0]
				);
				self::assertSame( array( 98 ), $args['tax_query'][1]['terms'] );
				self::assertSame( 'NOT IN', $args['tax_query'][1]['operator'] );
				self::assertSame( array( 99 ), $args['tax_query'][2]['terms'] );
				self::assertSame( 'NOT IN', $args['tax_query'][2]['operator'] );
				return array();
			}
		);
		self::assertSame( array(), ( new ProductFilters() )->archive_product_ids() );
		self::assertSame( 'product_brand', $term->taxonomy );
	}

	/**
	 * The archive uses the attribute slug even when no matching attribute term exists.
	 *
	 * @dataProvider brand_archive_slugs
	 * @param string $slug The requested brand slug.
	 */
	public function test_native_brand_query_uses_attribute_without_changing_route_identity( string $slug ): void {
		$_GET = array();
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_object_taxonomies', array( 'return' => array( 'product_brand', 'pa_brand', 'product_cat' ) ) );
		$term  = new WP_Term(
			(object) array(
				'term_id'  => 191,
				'taxonomy' => 'product_brand',
				'slug'     => $slug,
			)
		);
		$query = Mockery::mock( \WP_Query::class );
		$query->allows( 'is_main_query' )->andReturn( true );
		$query->allows( 'is_post_type_archive' )->with( 'product' )->andReturn( false );
		$query->allows( 'is_tax' )->with( array( 'product_brand', 'pa_brand', 'product_cat' ) )->andReturn( true );
		$query->allows( 'is_tax' )->with( 'product_brand' )->andReturn( true );
		$query->shouldReceive( 'get_queried_object' )->once()->andReturn( $term );
		$query->allows( 'get' )->with( 'taxonomy' )->andReturn( 'product_brand' );
		$query->shouldReceive( 'set' )->once()->with( 'product_brand', '' );
		$query->shouldReceive( 'set' )->once()->with( 'taxonomy', '' );
		$query->shouldReceive( 'set' )->once()->with( 'term', '' );
		$query->shouldReceive( 'set' )->once()->with( 'pa_brand', $slug );
		( new ProductFilters() )->filter( $query );
		self::assertSame( 'product_brand', $term->taxonomy );
		self::assertSame( 191, $term->term_id );
	}

	/**
	 * An existing slug and a slug without a corresponding attribute term.
	 *
	 * @return array<string, array{string}>
	 */
	public static function brand_archive_slugs(): array {
		return array(
			'existing' => array( 'goodwe' ),
			'no_twin'  => array( 'linker-no-attribute-fixture' ),
		);
	}

	/** Category and attribute archives retain their own native taxonomy query. */
	public function test_non_brand_native_archive_is_not_rewritten(): void {
		$_GET = array();
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_object_taxonomies', array( 'return' => array( 'product_brand', 'pa_brand', 'product_cat' ) ) );
		$query = Mockery::mock( \WP_Query::class );
		$query->allows( 'is_main_query' )->andReturn( true );
		$query->allows( 'is_post_type_archive' )->with( 'product' )->andReturn( false );
		$query->allows( 'is_tax' )->with( array( 'product_brand', 'pa_brand', 'product_cat' ) )->andReturn( true );
		$query->allows( 'is_tax' )->with( 'product_brand' )->andReturn( false );
		$query->shouldNotReceive( 'set' );
		$query->shouldNotReceive( 'get_queried_object' );
		( new ProductFilters() )->filter( $query );
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Inspect only this synthetic GET fixture.
		self::assertSame( array(), $_GET );
	}

	/** Nonscalar public query values cannot reach string casts or sort arithmetic. */
	public function test_array_values_are_not_selection_values(): void {
		$_GET    = array(
			'application' => array( 'commercial' ),
			'brand'       => array( 'goodwe' ),
			'phase'       => array( '3' ),
			'power'       => array( 'mid' ),
			'kw_min'      => array( '5' ),
			'kw_max'      => array( '20' ),
			'kwh_min'     => array( '5' ),
			'kwh_max'     => array( '30' ),
			'q'           => array( 'SAJ' ),
			'sort'        => array( 'name' ),
		);
		$filters = new ProductFilters();
		self::assertSame( array(), $filters->requested() );
		self::assertSame( 'recommended', $filters->requested_sort() );
	}

	/**
	 * The search term rides with the other facets.
	 */
	public function test_requested_reads_the_search_term(): void {
		$_GET = array(
			'q'       => 'GW5.1-BAT',
			'brand'   => 'goodwe',
			'kw_min'  => '5,5',
			'ignored' => 'x',
		);

		$selected = ( new ProductFilters() )->requested();

		$this->assertSame( 'GW5.1-BAT', $selected['q'] ?? null );
		$this->assertSame( 'goodwe', $selected['brand'] ?? null );
		$this->assertSame( 5.5, $selected['kw_min'] ?? null );
		$this->assertArrayNotHasKey( 'ignored', $selected );
	}

	/**
	 * The search box is not a filter: the applied count reads the category
	 * (one on a category archive, none on the shop) and the facets, never
	 * the term (the live bar's own arithmetic: "Filters · 0" on /products/,
	 * "· 1" on a category, "· 2" on a category with brand=goodwe).
	 *
	 * @covers \Linker\Commerce\Storefront\ProductFilters::applied_count
	 */
	public function test_applied_count_counts_the_category_and_the_facets(): void {
		$filters = new ProductFilters();

		$this->assertSame( 0, $filters->applied_count( false, array() ) );
		$this->assertSame( 1, $filters->applied_count( true, array() ) );
		$this->assertSame( 1, $filters->applied_count( false, array( 'brand' => 'goodwe' ) ) );
		$this->assertSame( 2, $filters->applied_count( true, array( 'brand' => 'goodwe' ) ) );
		$this->assertSame(
			1,
			$filters->applied_count(
				false,
				array(
					'q'     => 'GW5',
					'brand' => 'goodwe',
				)
			)
		);
	}

	/**
	 * "Name A-Z" orders by the product title, case-insensitively, in plain
	 * character order — the live shop's own order under sort=name (its first
	 * cards read GW10K-EHA…, GW10K-ETA…, GW125/261…, GW20K-ETA…: "125"
	 * before "20K", not natural-number order; measured 2026-10-12).
	 *
	 * @covers \Linker\Commerce\Storefront\ProductFilters::ordered
	 */
	public function test_name_sort_orders_by_title_in_plain_character_order(): void {
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'return' => static fn ( int $id ): string => match ( $id ) {
					7 => 'GoodWe ESA GW20K-ETA-G20 (20 kW three-phase power module)',
					3 => 'GoodWe ESA GW10K-EHA-G20 (10 kW single-phase power module)',
					5 => 'GoodWe ESA GW125/261-ESA-LCN-G10 (125 kW / 261 kWh all-in-one storage cabinet)',
					4 => 'GoodWe GW60K-STS-G10',
					default => '',
				},
			)
		);

		$ordered = ( new ProductFilters() )->ordered( array( 7, 4, 3, 5 ), 'name' );

		$this->assertSame( array( 3, 5, 7, 4 ), $ordered );
	}

	/**
	 * A facet section lists only when two of the view's own values answer:
	 * the live rail hides Application and Phase on the all-in-one archive
	 * (every product in one value) and shows them on the shop.
	 *
	 * @covers \Linker\Commerce\Storefront\ProductFilters::facet_counts
	 */
	public function test_a_facet_needs_two_answered_values_to_list(): void {
		$this->mock_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
				32 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 30.0,
				),
			)
		);

		$facets = ( new ProductFilters() )->facet_counts( array( 31, 32 ) );

		$this->assertArrayNotHasKey( 'application', $facets );
		$this->assertArrayNotHasKey( 'phase', $facets );
		$this->assertArrayHasKey( 'brand', $facets );
		// The power buckets stay listed, the empty one disabled, as the live
		// rail shows them.
		$this->assertSame( 0, $facets['power']['low']['count'] );
		$this->assertSame( 1, $facets['power']['top']['count'] );
	}

	/**
	 * The counts converge under an active filter: each facet is counted over
	 * the products the OTHER facets keep (the live rail under brand=goodwe
	 * reads the Phase rows off the goodwe subset and keeps a value nothing
	 * answers listed, disabled, at 0 — measured 2026-10-12).
	 *
	 * @covers \Linker\Commerce\Storefront\ProductFilters::facet_counts
	 */
	public function test_facet_counts_converge_to_the_other_facets_selection(): void {
		$this->mock_facts(
			array(
				41 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 20.0,
				),
				42 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 30.0,
				),
				43 => array(
					'brand'       => 'saj',
					'application' => 'home',
					'phase'       => 1,
					'kw'          => 5.0,
				),
				44 => array(
					'brand'       => 'saj',
					'application' => 'home',
					'phase'       => 1,
					'kw'          => 8.0,
				),
			)
		);

		$facets = ( new ProductFilters() )->facet_counts( array( 41, 42, 43, 44 ), array( 'brand' => 'goodwe' ) );

		// The counts by each facet value's label: PHP stores the phase keys
		// '3'/'1' under their int spellings, so the values are read by label.
		$counts_by_label = static function ( array $facet ): array {
			$counts = array();
			foreach ( $facet as $option ) {
				$counts[ $option['label'] ] = $option['count'];
			}
			return $counts;
		};

		$this->assertSame(
			array(
				'3-phase' => 2,
				'1-phase' => 0,
			),
			$counts_by_label( $facets['phase'] )
		);
		// Application converges to the goodwe subset.
		$this->assertSame(
			array(
				'Home'       => 0,
				'Commercial' => 2,
			),
			$counts_by_label( $facets['application'] )
		);
		// The active facet's own rows still count the whole view.
		$this->assertSame(
			array(
				'Goodwe' => 2,
				'Saj'    => 2,
			),
			$counts_by_label( $facets['brand'] )
		);
	}

	/**
	 * The facets' facts come from the shared selection-facts mock; the count
	 * tests only add the archive-level reads the rail makes.
	 *
	 * @param array<int, array{brand: string, application: string, phase: int, kw: float}> $products Products by ID.
	 */
	private function mock_facts( array $products ): void {
		$this->mock_selection_facts( $products );
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'yes' ) );
		WP_Mock::userFunction(
			'wc_get_product_visibility_term_ids',
			array(
				'return' => array(
					'exclude-from-catalog' => 99,
					'outofstock'           => 98,
				),
			)
		);
		WP_Mock::userFunction( 'wc_get_product', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_post_time', array( 'return' => 0 ) );
	}

	/**
	 * A request without a search term carries no q key.
	 */
	public function test_requested_omits_an_empty_search_term(): void {
		$_GET = array( 'q' => '' );

		$this->assertArrayNotHasKey( 'q', ( new ProductFilters() )->requested() );
	}

	use \Linker\Commerce\Tests\Support\MocksSelectionFacts;

	/**
	 * WP_Mock needs the unslash to answer its input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'wp_unslash',
			array(
				'return' => static fn ( array $value ): array => $value,
			)
		);
		WP_Mock::userFunction(
			'sanitize_text_field',
			array(
				'return' => static fn ( string $value ): string => $value,
			)
		);
		WP_Mock::userFunction(
			'sanitize_key',
			array(
				'return' => static fn ( string $value ): string => $value,
			)
		);
	}

	/** Cleans the superglobal. */
	public function tearDown(): void {
		$_GET = array();
		parent::tearDown();
	}
}
