<?php
/**
 * Tests for the catalogue shortcodes' language links.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Tests\Support\MocksSelectionFacts;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;
use WP_Term;

/**
 * The language half is the translated permalink of the queried object plus
 * the request path past that object's permalink. The current language's half
 * is the address the visitor is on.
 *
 * @covers \Linker\Commerce\Presentation\ProductShortcodes
 */
final class ProductShortcodesTest extends TestCase {

	use MocksSelectionFacts;

	/**
	 * Translation and escaping return their input; permalink helpers are the
	 * WordPress ones the shortcode calls, reduced to path joining.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'home_url',
			array(
				'return' => static fn( string $path = '/' ): string => 'http://linker.test' . ( '' === $path || '/' === $path ? '/' : $path ),
			)
		);
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static function ( string $url, int $component = -1 ) {
					$parsed = -1 === $component ? parse_url( $url ) : parse_url( $url, $component );
					return false === $parsed ? null : $parsed;
				},
			)
		);
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static function ( array $args, ?string $url = null ): string {
					// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.MissingUnslash, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the fixture sets this value.
					$base_url = $url ?? (string) ( $_SERVER['REQUEST_URI'] ?? 'http://linker.test/' );
					$parts    = parse_url( $base_url );
					$query    = array();
					if ( is_array( $parts ) && isset( $parts['query'] ) ) {
						parse_str( $parts['query'], $query );
					}
					foreach ( $args as $key => $value ) {
						$query[ $key ] = $value;
					}
					$base = strtok( $base_url, '?' );
					return array() === $query ? (string) $base : $base . '?' . http_build_query( $query );
				},
			)
		);
		WP_Mock::userFunction(
			'remove_query_arg',
			array(
				'return' => static function ( $keys, ?string $url = null ): string {
					// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.MissingUnslash, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the fixture sets this value.
					$base_url = $url ?? (string) ( $_SERVER['REQUEST_URI'] ?? 'http://linker.test/' );
					$parts    = parse_url( $base_url );
					if ( ! is_array( $parts ) || ! isset( $parts['query'] ) ) {
						return $base_url;
					}
					parse_str( $parts['query'], $query );
					foreach ( (array) $keys as $key ) {
						unset( $query[ $key ] );
					}
					$base = strtok( $base_url, '?' );
					return array() === $query ? (string) $base : $base . '?' . http_build_query( $query );
				},
			)
		);
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'user_trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction( 'untrailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn( $thing ): bool => $thing instanceof \WP_Error ) );
	}

	/**
	 * An account endpoint, its value and a nested endpoint stay on the translated account permalink.
	 *
	 * @dataProvider account_paths
	 * @param string $request  The visitor's path.
	 * @param string $expected The German half.
	 */
	public function test_account_path_is_appended_to_the_translated_account_permalink( string $request, string $expected ): void {
		$this->page(
			1037,
			'http://linker.test/my-account/',
			array(
				'de' => 6869,
			)
		);
		$this->permalink( 6869, 'http://linker.test/de/mein-konto/' );
		$_SERVER['REQUEST_URI'] = $request;
		$_GET                   = array();

		$this->assertSame( $expected, $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test' . $request, $this->url( 'en' ) );
	}

	/**
	 * The account paths the language half has to keep whole.
	 *
	 * @return array<string, array{string, string}>
	 */
	public function account_paths(): array {
		return array(
			'endpoint'        => array( '/my-account/inquiries/', 'http://linker.test/de/mein-konto/inquiries/' ),
			'endpoint value'  => array( '/my-account/inquiry/1600/', 'http://linker.test/de/mein-konto/inquiry/1600/' ),
			'paging'          => array( '/my-account/inquiries/2/', 'http://linker.test/de/mein-konto/inquiries/2/' ),
			'nested endpoint' => array( '/my-account/company/billing/', 'http://linker.test/de/mein-konto/company/billing/' ),
		);
	}

	/**
	 * A confirmation stays on the translated request page, endpoint and value included.
	 */
	public function test_confirmation_stays_on_the_translated_request_page(): void {
		$this->page(
			1036,
			'http://linker.test/proforma-request/',
			array(
				'de' => 6867,
			)
		);
		$this->permalink( 6867, 'http://linker.test/de/proforma-anfrage/' );
		$_SERVER['REQUEST_URI'] = '/proforma-request/inquiry-received/7021/?key=k';
		$_GET                   = array( 'key' => 'k' );

		// Woo needs the order key on the confirmation page — without it the
		// thank-you page renders without the order's details.
		$this->assertSame( 'http://linker.test/de/proforma-anfrage/inquiry-received/7021/?key=k', $this->url( 'de' ) );
		$this->assertStringNotContainsString( 'mein-konto', $this->url( 'de' ) );
	}

	/**
	 * A category page keeps paging; the query keys the visitor set travel with the link.
	 */
	public function test_category_paging_and_the_visitor_query_are_kept(): void {
		$term = new WP_Term(
			(object) array(
				'term_id'  => 44,
				'slug'     => 'inverters',
				'taxonomy' => 'product_cat',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ) );
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( $term ),
				'return' => 'http://linker.test/product-category/inverters/',
			)
		);
		WP_Mock::userFunction(
			'pll_get_term',
			array(
				'args'   => array( 44, 'de' ),
				'return' => 88,
			)
		);
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( 88 ),
				'return' => 'http://linker.test/de/produkt-kategorie/wechselrichter/',
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		$_SERVER['REQUEST_URI'] = '/product-category/inverters/page/2/?step=roof';
		$_GET                   = array( 'step' => 'roof' );

		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => 'http://linker.test/product-category/inverters/page/2/?step=roof',
			)
		);

		$this->assertSame( 'http://linker.test/de/produkt-kategorie/wechselrichter/page/2/?step=roof', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/product-category/inverters/page/2/?step=roof', $this->url( 'en' ) );
	}

	/**
	 * A search is not a queried page: the switcher's URL keeps the search query.
	 */
	public function test_search_keeps_the_switcher_url_and_the_query(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_the_languages',
			array(
				'return' => array(
					'de' => array( 'url' => 'http://linker.test/de/?s=inverter' ),
				),
			)
		);
		WP_Mock::userFunction( 'pll_get_requested_url', array( 'return' => 'http://linker.test/?s=inverter' ) );
		$_SERVER['REQUEST_URI'] = '/?s=inverter';
		$_GET                   = array( 's' => 'inverter' );

		$this->assertSame( 'http://linker.test/de/?s=inverter', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/?s=inverter', $this->url( 'en' ) );
	}

	/**
	 * Without a queried object the switcher's URL is the answer, query included.
	 * The current language's half is the request, cache-bust key included.
	 */
	public function test_a_page_without_a_queried_object_keeps_the_switcher_url(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_the_languages',
			array(
				'return' => array(
					'de' => array( 'url' => 'http://linker.test/de/loesungskonfigurator/?step=roof' ),
				),
			)
		);
		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => 'http://linker.test/solution-configurator/?step=roof&cbq=1',
			)
		);
		$_SERVER['REQUEST_URI'] = '/solution-configurator/?step=roof&cbq=1';
		$_GET                   = array(
			'step' => 'roof',
			'cbq'  => '1',
		);

		$this->assertSame( 'http://linker.test/de/loesungskonfigurator/?step=roof', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/solution-configurator/?step=roof', $this->url( 'en' ) );
	}

	/**
	 * The fixture's request path, without its query.
	 */
	private function request_path(): string {
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_unslash( $_SERVER['REQUEST_URI'] ) : '/'; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the fixture sets this value.
		return (string) strtok( $uri, '?' );
	}

	/**
	 * The catalogue query's common reads: the queried object (or none), the
	 * shop address, the category terms' reads and the helper shortcodes.
	 *
	 * @param WP_Term|null                    $term        The queried category, null on the shop.
	 * @param array<int, WP_Term>             $top         The top-level categories.
	 * @param array<int, array<int, WP_Term>> $children    Children by parent term id.
	 * @param array<int, int>                 $product_ids The archive's products, in the order get_posts() answers them.
	 */
	private function mock_catalog_query( ?WP_Term $term, array $top = array(), array $children = array(), array $product_ids = array() ): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn( string $value ): string => $value ) );
		// The rail's tool card links the configurator page; the fixture has
		// none (get_page_by_path answers nothing).
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => null ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'return' => 'http://linker.test/products/',
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static fn ( string $option ) => 'default_product_cat' === $option ? 15 : 'no',
			)
		);
		WP_Mock::userFunction( 'do_shortcode', array( 'return' => '' ) );
		WP_Mock::userFunction(
			'get_terms',
			array(
				'return' => static function ( array $args ) use ( $top, $children ) {
					if ( isset( $args['parent'] ) && isset( $children[ $args['parent'] ] ) ) {
						return $children[ $args['parent'] ];
					}
					if ( isset( $args['parent'] ) && 0 === $args['parent'] ) {
						return $top;
					}
					return array();
				},
			)
		);
		$terms_by_id = array();
		if ( null !== $term ) {
			$terms_by_id[ (int) $term->term_id ] = $term;
		}
		foreach ( array_merge( $top, ...array_values( $children ) ) as $term_row ) {
			$terms_by_id[ (int) $term_row->term_id ] = $term_row;
			WP_Mock::userFunction(
				'get_term_link',
				array(
					'args'   => array( $term_row ),
					'return' => 'http://linker.test/product-category/' . $term_row->slug . '/',
				)
			);
		}
		// The crumb and the rail's branch walk read the remembered terms by
		// id; anything else answers nothing, which ends a parent chain.
		WP_Mock::userFunction(
			'get_term',
			array(
				'return' => static fn ( int $id ): ?WP_Term => $terms_by_id[ $id ] ?? null,
			)
		);
		if ( null !== $term ) {
			WP_Mock::userFunction(
				'get_term_link',
				array(
					'args'   => array( $term ),
					'return' => 'http://linker.test/product-category/' . $term->slug . '/',
				)
			);
		}
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
		WP_Mock::userFunction( 'get_posts', array( 'return' => $product_ids ) );
		WP_Mock::userFunction( 'get_post_time', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => '' ) );
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'setup_postdata' );
		WP_Mock::userFunction( 'wp_reset_postdata' );
	}

	/**
	 * A term row.
	 *
	 * @param int    $id     Term id.
	 * @param string $name   Name.
	 * @param string $slug   Slug.
	 * @param int    $parent_id Parent term id.
	 */
	private function term( int $id, string $name, string $slug, int $parent_id = 0 ): WP_Term {
		return new WP_Term(
			(object) array(
				'term_id'  => $id,
				'name'     => $name,
				'slug'     => $slug,
				'taxonomy' => 'product_cat',
				'parent'   => $parent_id,
			)
		);
	}

	/**
	 * The nested category's crumb walks the term's parent chain: the live
	 * all-in-one page reads HOME / PRODUCTS / COMMERCIAL STORAGE /
	 * ALL-IN-ONE SYSTEMS, the parent linked, the category itself bold
	 * (measured 2026-10-12; recheck 2026-10-14 found the deployed crumb
	 * missing the parent segment).
	 */
	public function test_head_breadcrumb_walks_the_parent_chain(): void {
		$parent = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$child  = $this->term( 452, 'All-in-One Systems', 'all-in-one-systems', 451 );
		// No language layer: the crumb reads the terms' own names.
		WP_Mock::userFunction( 'pll_get_term', array( 'return' => 0 ) );
		$this->mock_catalog_query( $child, array( $parent ) );
		$_GET = array();

		$head = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_head();

		$this->assertStringContainsString( 'HOME</a> / <a href="http://linker.test/products/">PRODUCTS</a> / <a href="http://linker.test/product-category/commercial-storage/">COMMERCIAL STORAGE</a> / <b>ALL-IN-ONE SYSTEMS</b>', $head );
	}

	/**
	 * The head's tool row carries the AI entry only: the batch item-number
	 * and nameplate chips stay out (owner re-confirmed 2026-10-13, spec 13
	 * section C), and no chip may borrow another surface's words.
	 */
	public function test_head_tool_row_carries_the_ai_entry_alone(): void {
		$this->mock_catalog_query( null );
		$_GET = array();

		$head = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_head();

		$this->assertStringContainsString( 'class="wb-acts"', $head );
		$this->assertStringNotContainsString( 'Batch item numbers', $head );
		$this->assertStringNotContainsString( 'Identify a device from a nameplate photo', $head );
		$this->assertStringNotContainsString( 'data-linker-bom-open', $head );
	}

	/**
	 * The rail's hidden summary carries the applied count ("Filters (1)" on
	 * a category with no facet selected — the category is the one filter),
	 * and the Reset link sits in the rail-head row, the one the stylesheet
	 * shows (`#linker-products .rail-summary` is display:none,
	 * storefront.css:192; the rail-head is the flex row the live filtered
	 * rail shows its "Filters … Reset" on).
	 */
	public function test_filters_summary_shows_the_count_without_a_facet_and_reset_with_one(): void {
		$this->mock_selection_facts(
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
		$category = $this->term( 452, 'All-in-One Systems', 'all-in-one-systems', 451 );
		$this->mock_catalog_query( $category, array( $this->term( 451, 'Commercial Storage', 'commercial-storage' ) ) );

		$shortcodes = new ProductShortcodes( new ProductFilters(), new ProductView() );
		$_GET       = array();
		$summary    = $shortcodes->products_filters();
		$this->assertStringContainsString( 'Filters (1)</span><span class="rail-summary-mark"', $summary );
		// Without a facet there is no Reset anywhere on the rail.
		$this->assertStringNotContainsString( 'rail-reset', $summary );

		$_GET = array( 'brand' => 'goodwe' );
		$rail = $shortcodes->products_filters();
		// The Reset sits in the visible rail-head row, after its label.
		$this->assertStringContainsString( '<div class="rail-head"><span class="rail-head-label">Filters</span><a class="rail-reset" href="http://linker.test/product-category/all-in-one-systems/">Reset</a></div>', $rail );
	}

	/**
	 * The rail's Power section is the view's own: a shelf whose products carry
	 * no AC power figure renders no Power fold at all — the live rail of the
	 * powerless shelves (meters, EMS) reads Category → Brand → its tool card
	 * and stops (the 2026-10-14 shelf captures), and the 2026-10-14 recheck
	 * found the deployed rail listing four empty Power rows there. The empty
	 * tiers of a shelf that does carry power stay, disabled, and are asserted
	 * on the shop fixture below.
	 */
	public function test_rail_omits_power_when_no_product_carries_it(): void {
		$this->mock_selection_facts(
			array(
				71 => array(
					'brand'       => 'chint',
					'application' => 'commercial',
					'phase'       => 3,
				),
				72 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
				),
			)
		);
		$this->mock_catalog_query( null, array(), array(), array( 71, 72 ) );
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString( '<summary class="filter-title">Brand</summary>', $rail );
		$this->assertStringNotContainsString( 'Power', $rail );
	}

	/**
	 * A shelf that carries power lists the fold with its empty tiers disabled
	 * — the live accessories rail prints "15 to 30 kW"/"Over 30 kW" as rows
	 * and leaves the two it has nothing in greyed (the 2026-10-14 shelf
	 * captures). The empty tiers are not links.
	 */
	public function test_rail_lists_power_with_its_empty_tiers_disabled(): void {
		$this->mock_selection_facts(
			array(
				81 => array(
					'brand'       => 'chint',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 25.0,
				),
				82 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$this->mock_catalog_query( null, array(), array(), array( 81, 82 ) );
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString( '<summary class="filter-title">Power</summary>', $rail );
		// One product in "15 to 30 kW" and one in "Over 30 kW": the two empty
		// tiers still list, and they are not links.
		$this->assertStringContainsString( '<span class="filter-option is-disabled" aria-disabled="true">', $rail );
		$this->assertStringContainsString( '>15 to 30 kW</span></span><span class="filter-count">1</span></a>', $rail );
	}

	/**
	 * The grid's family rows follow the request's sort. The rows are grouped
	 * from filtered_product_ids() in its order and a family's first product
	 * leads its card, so sort=name opens the grid with the alphabetically
	 * first title — the live shop's own lead under
	 * /products/?brand=goodwe&sort=name. The 2026-10-14 recheck found the
	 * deployed grid keeping the Recommended lead (GW60K-STS-G10) because the
	 * sort reached only the main query's post__in, which the grid does not
	 * read.
	 */
	public function test_family_grid_rows_follow_the_requested_sort(): void {
		$this->mock_selection_facts(
			array(
				4 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 60.0,
				),
				7 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 20.0,
				),
				3 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 1,
					'kw'          => 10.0,
				),
				5 => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 125.0,
				),
			)
		);
		// The grid's own reads, bespoke: the shared archive fixture answers an
		// empty product list and stubs the row loop, and this test needs both
		// the products and the leads the loop hands the cards.
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		// No language layer: the family data is read off the products as they are.
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => '' ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'http://linker.test/products/' ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'no' ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( 7, 4, 3, 5 ) ) );
		// The archive's own "Recommended" order is newest first, and this
		// fixture's newest product is its title-last one: the two orders
		// differ, so the row leads below can only come out sorted if the
		// request's sort really reaches the grid.
		WP_Mock::userFunction(
			'get_post_time',
			array(
				'return' => static fn ( string $format, bool $gmt, int $id ): int => match ( $id ) {
					4 => 300,
					7 => 200,
					3 => 100,
					5 => 50,
					default => 0,
				},
			)
		);
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
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'return' => static fn ( int $id ): string => match ( $id ) {
					7 => 'GoodWe ESA GW20K-ETA-G20',
					4 => 'GoodWe GW60K-STS-G10',
					3 => 'GoodWe ESA GW10K-EHA-G20',
					5 => 'GoodWe ESA GW125/261-ESA-LCN-G10',
					default => '',
				},
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static fn ( int $id ): WP_Post => new WP_Post( (object) array( 'ID' => $id ) ),
			)
		);
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => 0 ) );
		// Each row hands its lead to the card fragment; the order of those
		// calls is the order of the grid's cards.
		$leads = array();
		WP_Mock::userFunction(
			'setup_postdata',
			array(
				'return' => static function ( $post ) use ( &$leads ): bool {
					$leads[] = (int) $post->ID;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_reset_postdata' );
		$_GET = array(
			'brand' => 'goodwe',
			'sort'  => 'name',
		);

		( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_families();

		// No family data in the fixture: each product is its own family, so the
		// row leads are the sorted list itself, the ESA card first.
		$this->assertSame( array( 3, 5, 7, 4 ), $leads );
	}

	/**
	 * The rail's Category section nests the children of the branch the
	 * visitor is in (the live all-in-one page renders the two siblings under
	 * Commercial Storage, the current one marked), other branches flat.
	 */
	public function test_category_section_nests_the_current_branch_children(): void {
		$this->mock_selection_facts(
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
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$inverters = $this->term( 449, 'Inverters', 'inverters' );
		$aio       = $this->term( 452, 'All-in-One Systems', 'all-in-one-systems', 451 );
		$battery   = $this->term( 453, 'Battery Systems', 'battery-systems', 451 );
		$this->mock_catalog_query(
			$aio,
			array( $storage, $inverters ),
			array(
				451 => array( $aio, $battery ),
			)
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString( 'family-link family-link--child is-current" href="http://linker.test/product-category/all-in-one-systems/" aria-current="page"><span>All-in-One Systems</span></a>', $rail );
		$this->assertStringContainsString( 'family-link family-link--child" href="http://linker.test/product-category/battery-systems/">', $rail );
		// Commercial Storage itself sits right before its expanded children.
		$this->assertStringContainsString( 'Commercial Storage</span></a><a class="family-link family-link--child is-current"', $rail );
	}

	/**
	 * The mobile actions bar reads the applied count the live bar reads (1
	 * on a category) and carries the two tool entries beside the AI chip.
	 */
	public function test_actions_bar_carries_the_count_and_the_tool_entries(): void {
		$this->mock_catalog_query( $this->term( 456, 'Accessories', 'accessories' ) );
		$_GET = array();

		$bar = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_actions();

		$this->assertStringContainsString( 'id="product-filter-open"', $bar );
		$this->assertStringContainsString( 'data-linker-applied-filter-count>1</span>', $bar );
		$this->assertStringNotContainsString( 'Batch import', $bar );
		$this->assertStringNotContainsString( 'Nameplate photo', $bar );
	}

	/**
	 * The applied-filter chips: one pill per selected facet that removes it,
	 * one per set range bound, and the "Clear all" link; no selection, no
	 * chips.
	 */
	public function test_chips_strip_renders_a_chip_per_facet_and_clear_all(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $this->term( 449, 'Inverters', 'inverters' ) ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'return' => 'http://linker.test/products/',
			)
		);
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'return' => 'http://linker.test/product-category/inverters/',
			)
		);
		WP_Mock::userFunction(
			'get_terms',
			array(
				'return' => array(
					(object) array(
						'slug' => 'goodwe',
						'name' => 'GoodWe',
					),
				),
			)
		);
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn( string $value ): string => $value ) );
		$shortcodes = new ProductShortcodes( new ProductFilters(), new ProductView() );
		$_GET       = array();

		$this->assertSame( '', $shortcodes->products_chips() );

		$_GET                   = array(
			'brand'  => 'goodwe',
			'kw_min' => '5',
			'kw_max' => '20',
			'cbq'    => '1791',
		);
		$_SERVER['REQUEST_URI'] = '/product-category/inverters/?brand=goodwe&kw_min=5&kw_max=20&cbq=1791';

		$chips = $shortcodes->products_chips();

		// The chips keep the live page's relative addresses (the one-argument
		// query helpers read the request) and drop the facet they remove.
		$this->assertStringContainsString( 'href="/product-category/inverters/?kw_min=5', $chips );
		$this->assertStringContainsString( '>GoodWe <span aria-hidden="true">&times;</span></a>', $chips );
		$this->assertStringContainsString( 'href="/product-category/inverters/?brand=goodwe', $chips );
		$this->assertStringContainsString( 'AC power 5&ndash;20 kW <span aria-hidden="true">&times;</span></a>', $chips );
		$this->assertStringContainsString( 'class="wbclear" href="http://linker.test/product-category/inverters/" rel="nofollow">Clear all</a>', $chips );
		$this->assertStringNotContainsString( 'product-page', $chips );
	}

	/**
	 * The family card's title is the data's series label unless that label
	 * is the brand's own name: the live pages print "ESA Series" for the ESA
	 * family but the full model names for the SAJ CHS2 records whose series
	 * field holds "SAJ" (their brand).
	 *
	 * @covers \Linker\Commerce\Presentation\ProductShortcodes::series_title
	 */
	public function test_series_title_falls_back_to_the_model_when_the_series_is_the_brand(): void {
		$this->assertSame( 'ESA Series', ProductShortcodes::series_title( 'ESA Series', 'GoodWe', 'GoodWe ESA GW10K-ETA-G20' ) );
		$this->assertSame( 'GoodWe BAT-C', ProductShortcodes::series_title( 'GoodWe BAT-C', 'GoodWe', 'GoodWe GW261.2-BAT-LCD-G10' ) );
		$this->assertSame( 'SAJ CHS2-50K-T6-X', ProductShortcodes::series_title( 'SAJ', 'SAJ', 'SAJ CHS2-50K-T6-X' ) );
		$this->assertSame( 'SAJ CHS2-50K-T6-X', ProductShortcodes::series_title( '', 'SAJ', 'SAJ CHS2-50K-T6-X' ) );
	}

	/**
	 * The queried page, its German twin and that twin's permalink.
	 *
	 * @param int                $id           Queried page id.
	 * @param string             $permalink    Its permalink.
	 * @param array<string, int> $translations Language => translated id.
	 */
	private function page( int $id, string $permalink, array $translations ): void {
		$page = new WP_Post(
			(object) array(
				'ID'        => $id,
				'post_type' => 'page',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $page ) );
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $page ),
				'return' => $permalink,
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => function () {
					return 'http://linker.test' . $this->request_path();
				},
			)
		);
		foreach ( $translations as $language => $translated ) {
			WP_Mock::userFunction(
				'pll_get_post',
				array(
					'args'   => array( $id, $language ),
					'return' => $translated,
				)
			);
		}
	}

	/**
	 * A translated page's permalink.
	 *
	 * @param int    $id   Translated page id.
	 * @param string $link Its permalink.
	 */
	private function permalink( int $id, string $link ): void {
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $id ),
				'return' => $link,
			)
		);
	}

	/**
	 * The language half for `$lang`.
	 *
	 * @param string $lang Language code.
	 */
	private function url( string $lang ): string {
		$shortcodes = new ProductShortcodes( new ProductFilters(), new ProductView() );
		$method     = new \ReflectionMethod( ProductShortcodes::class, 'language_url' );
		return $method->invoke( $shortcodes, $lang );
	}
}
