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
use Mockery;
use WC_Product;
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
	 * The product the product-page tests below read.
	 */
	private const PDP = 6530;

	/**
	 * The product mock the current test's reads answer with.
	 *
	 * @var WC_Product|null
	 */
	private ?WC_Product $pdp_product = null;

	/**
	 * The legacy ACF JSON the current test's reads answer with.
	 *
	 * @var array<string, mixed>
	 */
	private array $pdp_acf = array();

	/**
	 * The product's WooCommerce gallery field as the current test's reads
	 * answer it (the comma-separated editor list).
	 *
	 * @var string
	 */
	private string $pdp_gallery = '6504,6505';

	/**
	 * The URL of an attachment in the fixture: it names the id, so a test can
	 * tell which picture a shortcode printed.
	 *
	 * @param int $id The attachment.
	 */
	private function pdp_image_url( int $id ): string {
		return 'http://linker.test/uploads/image-' . $id . '.png';
	}

	/**
	 * Translation and escaping return their input; permalink helpers are the
	 * WordPress ones the shortcode calls, reduced to path joining.
	 */
	public function setUp(): void {
		parent::setUp();
		// English products: each answers for itself (CommerceState::is_rfq_only asks the language layer).
		$this->english_products( array( 6530 => 6530 ) );
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
				// Both forms the tree calls: add_query_arg( array $args, ?string $url )
				// and WordPress's add_query_arg( string $key, $value, ?string $url )
				// (ProductView's sign-in URL).
				'return' => static function ( $first, $second = null, $third = null ): string {
					$args     = \is_array( $first ) ? $first : array( (string) $first => $second );
					// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.MissingUnslash, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the fixture sets this value.
					$base_url = ( \is_array( $first ) ? $second : $third ) ?? (string) ( $_SERVER['REQUEST_URI'] ?? 'http://linker.test/' );
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
	 * @param WP_Term|null                       $term        The queried category, null on the shop.
	 * @param array<int, WP_Term>                $top         The top-level categories.
	 * @param array<int, array<int, WP_Term>>    $children    Children by parent term id.
	 * @param array<int, int>                    $product_ids The archive's products, in the order get_posts() answers them.
	 * @param array<string, array<int, WP_Term>> $by_slug   The terms the rail's display map looks up by English slug; they answer get_term() by id too, so the English anchors of a translated lookup resolve.
	 * @param callable(int, string): int|null    $twin        The twin the language layer links for a term id and the language a lookup asks for ('' for the language on display); null while the fixture runs without a language layer, where every lookup answers 0 — the definition of a stubbed pll_* function outlives the test that made it, so the rail's reads have to be answered here either way.
	 */
	private function mock_catalog_query( ?WP_Term $term, array $top = array(), array $children = array(), array $product_ids = array(), array $by_slug = array(), ?callable $twin = null ): void {
		WP_Mock::userFunction(
			'pll_get_term',
			array(
				// Without a twin every lookup answers 0, the way a site whose
				// terms carry no language layer answers.
				'return' => static fn ( int $id, string $language = '' ): int => null === $twin ? 0 : $twin( $id, $language ),
			)
		);
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
				'return' => static function ( array $args ) use ( $top, $children, $by_slug ) {
					if ( isset( $args['slug'] ) && isset( $by_slug[ $args['slug'] ] ) ) {
						return $by_slug[ $args['slug'] ];
					}
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
		foreach ( array_merge( $top, ...array_values( $children ), ...array_values( $by_slug ) ) as $term_row ) {
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
	 * storefront.css:212; the rail-head is the flex row the live filtered
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
	 * The rail's Category section expands the branch the visitor is in with
	 * exactly the three rows the live all-in-one page prints under Commercial
	 * Storage, in that page's order: the Inverters row the display map adds
	 * (the term itself is flat, RAIL_GROUP_ROWS), then the two children the
	 * term tree holds, the current one marked. Other branches stay flat, and
	 * the section's own top-level Inverters row keeps serving
	 * /product-category/inverters/.
	 */
	public function test_category_section_expands_the_branch_with_the_live_rows(): void {
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
		$ems       = $this->term( 454, 'EMS & Monitoring', 'ems-monitoring' );
		$this->mock_catalog_query(
			$aio,
			array( $inverters, $storage, $ems ),
			array(
				451 => array( $aio, $battery ),
			),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		// The group's three rows, in the live page's order, between the group's
		// own row and the next top-level category.
		$this->assertStringContainsString(
			'Commercial Storage</span></a>'
			. '<a class="family-link family-link--child" href="http://linker.test/product-category/inverters/"><span>Inverters</span></a>'
			. '<a class="family-link family-link--child is-current" href="http://linker.test/product-category/all-in-one-systems/" aria-current="page"><span>All-in-One Systems</span></a>'
			. '<a class="family-link family-link--child" href="http://linker.test/product-category/battery-systems/"><span>Battery Systems</span></a>'
			. '<a class="family-link" href="http://linker.test/product-category/ems-monitoring/"><span>EMS & Monitoring</span></a>',
			$rail
		);
		// Three rows, no more: the branch carries no other category.
		$this->assertSame( 3, substr_count( $rail, 'family-link--child' ) );
		// Inverters is where the live page prints it twice: the section's own
		// row, and the group's.
		$this->assertSame( 2, substr_count( $rail, '<span>Inverters</span>' ) );
	}

	/**
	 * The shop page enters no branch: every top-level category is a flat row,
	 * and the Commercial Storage display row stays out of it.
	 */
	public function test_the_shop_section_stays_flat(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$inverters = $this->term( 449, 'Inverters', 'inverters' );
		$this->mock_catalog_query(
			null,
			array( $storage, $inverters ),
			array(),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringNotContainsString( 'family-link--child', $rail );
		$this->assertSame( 1, substr_count( $rail, '<span>Inverters</span>' ) );
	}

	/**
	 * The Inverters page keeps the Commercial Storage branch closed, the row
	 * itself marked current — the live Inverters rail is flat there too, the
	 * row the display map adds is not a child of the group.
	 */
	public function test_the_inverters_page_keeps_the_group_closed(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$inverters = $this->term( 449, 'Inverters', 'inverters' );
		$ems       = $this->term( 454, 'EMS & Monitoring', 'ems-monitoring' );
		$this->mock_catalog_query(
			$inverters,
			array( $inverters, $storage, $ems ),
			array(),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		// The group's row sits between its neighbours, with nothing under it.
		$this->assertStringContainsString( 'Commercial Storage</span></a><a class="family-link" href="http://linker.test/product-category/ems-monitoring/"><span>EMS & Monitoring</span></a>', $rail );
		$this->assertStringNotContainsString( 'family-link--child', $rail );
	}

	/**
	 * The Accessories branch carries its own two children alone — the live
	 * accessories page's composition, no row from the Commercial Storage map.
	 */
	public function test_the_accessories_branch_carries_its_own_two_children(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$inverters = $this->term( 449, 'Inverters', 'inverters' );
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$accessory = $this->term( 456, 'Accessories', 'accessories' );
		$meters    = $this->term( 457, 'Meters & Current Transformers', 'meters-current-transformers', 456 );
		$backup    = $this->term( 458, 'Backup Power', 'backup-power', 456 );
		$this->mock_catalog_query(
			$accessory,
			array( $inverters, $storage, $accessory ),
			array( 456 => array( $meters, $backup ) ),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString( 'Accessories</span></a><a class="family-link family-link--child" href="http://linker.test/product-category/meters-current-transformers/"><span>Meters & Current Transformers</span></a><a class="family-link family-link--child" href="http://linker.test/product-category/backup-power/"><span>Backup Power</span></a>', $rail );
		$this->assertSame( 2, substr_count( $rail, 'family-link--child' ) );
	}

	/**
	 * The group's added row is the term's own twin in the language on
	 * display: the live Gewerbespeicher rail prints Wechselrichter above its
	 * two German children (the German capture of 2026-10-13).
	 */
	public function test_rail_group_row_is_the_german_twin_on_the_german_page(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$wechs     = $this->term( 581, 'Wechselrichter', 'wechselrichter' );
		$gewerbe   = $this->term( 587, 'Gewerbespeicher', 'gewerbespeicher' );
		$systeme   = $this->term( 599, 'All-in-One-Systeme', 'all-in-one-systeme', 587 );
		$batterien = $this->term( 601, 'Batteriesysteme', 'batteriesysteme', 587 );
		$en_group  = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$en_inv    = $this->term( 449, 'Inverters', 'inverters' );
		$this->mock_catalog_query(
			$systeme,
			array( $wechs, $gewerbe ),
			array( 587 => array( $systeme, $batterien ) ),
			array(),
			array(
				'inverters'          => array( $en_inv ),
				'commercial-storage' => array( $en_group ),
			),
			// The links the language layer carries: the German group answers
			// its English anchor, and the English Inverters term answers the
			// German page's Wechselrichter.
			static function ( int $id, string $language = '' ): int {
				if ( 587 === $id && 'en' === $language ) {
					return 451;
				}
				return 449 === $id ? 581 : 0;
			}
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertStringContainsString(
			'Gewerbespeicher</span></a>'
			. '<a class="family-link family-link--child" href="http://linker.test/product-category/wechselrichter/"><span>Wechselrichter</span></a>'
			. '<a class="family-link family-link--child is-current" href="http://linker.test/product-category/all-in-one-systeme/" aria-current="page"><span>All-in-One-Systeme</span></a>'
			. '<a class="family-link family-link--child" href="http://linker.test/product-category/batteriesysteme/"><span>Batteriesysteme</span></a>',
			$rail
		);
		$this->assertSame( 3, substr_count( $rail, 'family-link--child' ) );
	}

	/**
	 * A row the tree has since made a child keeps its single row: the map is
	 * a display addition, not a second copy of a child.
	 */
	public function test_rail_group_row_is_left_out_when_the_tree_makes_it_a_child(): void {
		$this->mock_selection_facts(
			array(
				31 => array(
					'brand'       => 'saj',
					'application' => 'commercial',
					'phase'       => 3,
					'kw'          => 50.0,
				),
			)
		);
		$storage   = $this->term( 451, 'Commercial Storage', 'commercial-storage' );
		$inverters = $this->term( 449, 'Inverters', 'inverters', 451 );
		$aio       = $this->term( 452, 'All-in-One Systems', 'all-in-one-systems', 451 );
		$this->mock_catalog_query(
			$aio,
			array( $storage ),
			array(
				451 => array( $inverters, $aio ),
			),
			array(),
			array( 'inverters' => array( $inverters ) )
		);
		$_GET = array();

		$rail = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_filters();

		$this->assertSame( 2, substr_count( $rail, 'family-link--child' ) );
		$this->assertSame( 1, substr_count( $rail, '<span>Inverters</span>' ) );
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

	/**
	 * The product page shortcodes over one product, with the WordPress and
	 * WooCommerce reads its view makes stubbed. Everything the page's data
	 * assembly asks for beyond the product's own fields is empty: the tests
	 * below read the availability dot, the feature band and the FAQ side
	 * panel, not the catalogue data around them.
	 *
	 * @param bool                 $in_stock Whether WooCommerce calls the product in stock.
	 * @param array<string, mixed> $acf      The product's legacy ACF JSON branches.
	 */
	private function pdp( bool $in_stock, array $acf = array() ): ProductShortcodes {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( self::PDP );
		$product->allows( 'get_name' )->andReturn( 'GoodWe GW60K-STS-G10' );
		$product->allows( 'get_sku' )->andReturn( 'DLK-GOODWE-GW60KSTSG10' );
		$product->allows( 'get_image_id' )->andReturn( 6503 );
		$product->allows( 'get_gallery_image_ids' )->andReturn( array( 6504, 6505 ) );
		$product->allows( 'get_short_description' )->andReturn( '<p>The intro.</p>' );
		$product->allows( 'get_description' )->andReturn( '' );
		$product->allows( 'get_price_html' )->andReturn( '<span>€ 100</span>' );
		$product->allows( 'get_permalink' )->andReturn( 'http://linker.test/product/goodwe-gw60k-sts-g10/' );
		$product->allows( 'get_attributes' )->andReturn( array() );
		$product->allows( 'get_parent_id' )->andReturn( 0 );
		$product->allows( 'is_in_stock' )->andReturn( $in_stock );

		// WP_Mock keeps the first responder of a function, and this helper may
		// run twice in one test (an in-stock product, then one that is not):
		// the reads go through the properties, so the second call re-mocks the
		// data and not the function.
		$this->pdp_product = $product;
		$this->pdp_acf     = $acf;

		WP_Mock::userFunction( 'wc_get_product', array( 'return' => fn ( int $id ) => self::PDP === $id ? $this->pdp_product : false ) );
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => self::PDP ) );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => fn ( int $id, string $key ) => match ( $key ) {
					'_tv_legacy_acf_json'       => (string) json_encode( $this->pdp_acf ),
					'_product_image_gallery'    => $this->pdp_gallery,
					default                     => '',
				},
			)
		);
		WP_Mock::userFunction(
			'wp_get_post_terms',
			array(
				'return' => fn ( int $id, string $taxonomy ) => 'pa_model' === $taxonomy
					? array(
						(object) array(
							'slug' => 'goodwe-gw60k-sts-g10',
							'name' => 'GW60K-STS-G10',
						),
					)
					: array(
						(object) array(
							'slug' => 'goodwe',
							'name' => 'GoodWe',
						),
					),
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => 'GoodWe GW60K-STS-G10' ) );
		WP_Mock::userFunction( 'get_term_link', array( 'return' => 'http://linker.test/product-category/inverters/' ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'return' => static fn ( string $page ): string => 'myaccount' === $page
					? 'http://linker.test/my-account/'
					: 'http://linker.test/products/',
			)
		);
		WP_Mock::userFunction( 'wc_get_checkout_url', array( 'return' => 'http://linker.test/proforma-request/' ) );
		WP_Mock::userFunction( 'wc_attribute_label', array( 'return' => static fn ( string $name ): string => $name ) );
		// The availability line's delivery note reads the product's own
		// shipping meta through Materials::logistics (no mode and no weight in
		// this fixture, so the note states the Proforma fallback).
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'wc_string_to_bool', array( 'return' => static fn ( $value ) => in_array( $value, array( 'yes', 'true', '1' ), true ) ) );
		WP_Mock::userFunction( 'wc_price', array( 'return' => static fn ( float $amount ): string => '€' . number_format( $amount, 2 ) ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn ( $value ) => strip_tags( (string) $value ) ) );
		// Materials::gallery_ids's WordPress half and the image tags the two
		// shortcodes print (the URL names its attachment, so a test can tell
		// which picture the markup took).
		WP_Mock::userFunction( 'wp_get_attachment_image_url', array( 'return' => fn ( int $id ): string => $this->pdp_image_url( $id ) ) );
		WP_Mock::userFunction( 'wp_attachment_is_image', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_get_attachment_image_src', array( 'return' => fn ( int $id ): array => array( $this->pdp_image_url( $id ), 1024, 768, false ) ) );
		WP_Mock::userFunction( 'wp_get_attachment_image_srcset', array( 'return' => '' ) );
		WP_Mock::userFunction( 'wp_get_attachment_image_sizes', array( 'return' => '(max-width: 1024px) 100vw, 1024px' ) );

		// The selection facts' own stubs come after the pair above, so the
		// readers registered here are the ones that answer.
		$this->mock_selection_facts(
			array(
				self::PDP => array(
					'brand'       => 'goodwe',
					'application' => 'commercial',
					'phase'       => 3,
				),
			)
		);

		return new ProductShortcodes( new ProductFilters(), new ProductView() );
	}

	/**
	 * The availability dot follows the product's own stock state: the base
	 * class for a product in stock, `is-wait` for one that is not (the live
	 * page's own two states; the shortcode printed `is-wait` on every product
	 * until 2026-10-16, so the dot could never leave its warn colour). The
	 * wording stays WooCommerce's own state text.
	 */
	public function test_the_availability_dot_follows_the_stock_state(): void {
		unset( $GLOBALS['product'] );
		$in_stock = $this->pdp( true )->pdp_availability();

		$this->assertStringContainsString( '<span class="pdp-dot"></span>', $in_stock );
		$this->assertStringContainsString( 'In stock', $in_stock );
		$this->assertStringNotContainsString( 'is-wait', $in_stock );

		$out_of_stock = $this->pdp( false )->pdp_availability();

		$this->assertStringContainsString( '<span class="pdp-dot is-wait"></span>', $out_of_stock );
		$this->assertStringContainsString( 'Currently unavailable', $out_of_stock );
	}

	/**
	 * The nameplate entry is gone: no button, no attribute, no document
	 * listener (owner ruling 2026-10-13: the nameplate chip is not
	 * delivered, so no event may promise it).
	 */
	public function test_the_project_choices_carry_the_three_stages_alone(): void {
		unset( $GLOBALS['product'] );
		$html = $this->pdp( true )->pdp_project_choices();

		$this->assertSame( 3, substr_count( $html, 'data-project-message=' ) );
		$this->assertStringContainsString( 'New system', $html );
		$this->assertStringNotContainsString( 'nameplate', $html );
		$this->assertStringNotContainsString( 'data-linker-assistant-open', $html );
	}

	/**
	 * The feature band's kicker names the product's series (`product_series`
	 * of the product's own ACF JSON, the field the catalogue cards read),
	 * and a product without one gets no kicker line.
	 */
	public function test_the_feature_band_takes_the_products_series_as_its_kicker(): void {
		unset( $GLOBALS['product'] );
		$html = $this->pdp(
			true,
			array(
				'product_series' => 'STS Series',
				'feature_cards'  => array(
					array(
						'feature_title' => 'Transfer in ≤ 4 ms.',
						'feature_body'  => 'On/off-grid transfer time is ≤ 4 ms.',
						'feature_image' => 4818,
					),
				),
			)
		)->pdp_features();

		$this->assertStringContainsString( '<p class="pdp-kicker">STS Series</p>', $html );
		$this->assertStringContainsString( 'Transfer in ≤ 4 ms.', $html );

		$without = $this->pdp(
			true,
			array(
				'feature_cards' => array(
					array(
						'feature_title' => 'Transfer in ≤ 4 ms.',
						'feature_body'  => 'On/off-grid transfer time is ≤ 4 ms.',
						'feature_image' => 4818,
					),
				),
			)
		)->pdp_features();

		$this->assertStringNotContainsString( 'pdp-kicker', $without );
	}

	/**
	 * The FAQ side panel repeats no picture from the gallery above it: it
	 * takes the gallery's last id (the featured image and the first gallery
	 * picture are the pair the page's top shows), and a product whose gallery
	 * holds nothing beyond the featured picture gets no panel.
	 */
	public function test_the_faq_side_panel_takes_the_gallerys_last_picture(): void {
		unset( $GLOBALS['product'] );

		// The fixture's own gallery: 6503 is the featured image, 6504 and 6505
		// the editor's list (the real product's data). The panel takes the
		// last id, so it repeats neither the main picture nor the second one.
		$html = $this->pdp( true )->pdp_faq_side();

		$this->assertStringContainsString( '<div class="pdp-faq-side">', $html );
		$this->assertStringContainsString( 'image-6505.png', $html );
		$this->assertStringNotContainsString( 'image-6503.png', $html );
		$this->assertStringNotContainsString( 'image-6504.png', $html );

		// A product whose gallery holds the featured picture alone: no panel,
		// and the block stays one column.
		$this->pdp_gallery = '';
		$this->assertSame( '', $this->pdp( true )->pdp_faq_side() );
	}
}
