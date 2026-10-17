<?php
/**
 * Tests for the retired addresses.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Redirects;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Term;

// phpcs:disable WordPress.WP.AlternativeFunctions -- this test runs outside WordPress: files, JSON and URL parsing through PHP itself.

/**
 * Tests for Redirects: the mapping tables load, and every kind of retired
 * address goes where the map says — while a product or a shelf that is back
 * stays with WordPress.
 *
 * @covers \Linker\Tools\Redirects
 */
final class RedirectsTest extends TestCase {

	/**
	 * The site address of the test.
	 */
	private const HOME = 'https://de-linker.test';

	/**
	 * The `product` query var of the request under test (WordPress's own
	 * routing, which is what a product address is read from).
	 *
	 * @var string
	 */
	private string $product = '';

	/**
	 * The `product_cat` query var of the request under test.
	 *
	 * @var string
	 */
	private string $category = '';

	/**
	 * Where the checkout page itself answers (WooCommerce's own address).
	 *
	 * @var string
	 */
	private string $checkout = '/proforma-request/';

	/**
	 * Where the shop page itself answers (WooCommerce's own address).
	 *
	 * @var string
	 */
	private string $shop = '/products/';

	/**
	 * The product category terms that exist, by slug.
	 *
	 * @var array<string, WP_Term>
	 */
	private array $terms = array();

	/**
	 * The ids a published-product query answers with.
	 *
	 * @var list<int>
	 */
	private array $published = array();

	/**
	 * The permalink a term answers with, by term id.
	 *
	 * @var array<int, string>
	 */
	private array $links = array();

	/**
	 * Polylang's answer to the language of the request, null while Polylang
	 * does not answer.
	 *
	 * @var string|null
	 */
	private ?string $current_language = null;

	/**
	 * Polylang's default language, '' while Polylang does not answer.
	 *
	 * @var string
	 */
	private string $default_language = '';

	/**
	 * Polylang's language slugs, empty while Polylang does not answer.
	 *
	 * @var list<string>
	 */
	private array $languages = array();

	/**
	 * A term's twin id, by term id and language.
	 *
	 * @var array<int, array<string, int>>
	 */
	private array $term_twins = array();

	/**
	 * A post id for a URL, URL_to_postid's answer.
	 *
	 * @var array<string, int>
	 */
	private array $post_ids = array();

	/**
	 * A post's own address, get_permalink's answer, by post id.
	 *
	 * @var array<int, string>
	 */
	private array $permalinks = array();

	/**
	 * A post's twin id, by post id and language.
	 *
	 * @var array<int, array<string, int>>
	 */
	private array $post_twins = array();

	/**
	 * The WordPress and WooCommerce functions the plugin reads, wired to the
	 * properties above.
	 */
	private function wordpress(): void {
		WP_Mock::userFunction( 'home_url' )->andReturnUsing(
			static fn( string $path = '' ): string => self::HOME . $path
		);
		WP_Mock::userFunction( 'trailingslashit' )->andReturnUsing(
			static fn( string $value ): string => rtrim( $value, '/' ) . '/'
		);
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing(
			static fn( string $url, int $component = -1 ) => parse_url( $url, $component )
		);
		WP_Mock::userFunction( 'wc_get_permalink_structure' )->andReturn(
			array(
				'product_rewrite_slug'  => 'product',
				'category_rewrite_slug' => 'product-category',
			)
		);
		WP_Mock::userFunction( 'wc_get_page_permalink' )->andReturnUsing(
			fn(): string => self::HOME . $this->shop
		);
		WP_Mock::userFunction( 'wc_get_checkout_url' )->andReturnUsing(
			fn(): string => self::HOME . $this->checkout
		);
		WP_Mock::userFunction( 'get_query_var' )->andReturnUsing(
			fn( string $name ): string => $this->query_var( $name )
		);
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			fn(): array => $this->published
		);
		WP_Mock::userFunction( 'get_terms' )->andReturnUsing(
			function ( array $args ): array {
				$term = $this->terms[ (string) $args['slug'] ] ?? null;
				return null === $term ? array() : array( $term );
			}
		);
		WP_Mock::userFunction( 'get_term_link' )->andReturnUsing(
			fn( $term ) => $this->links[ $term instanceof WP_Term ? $term->term_id : (int) $term ] ?? new \WP_Error( 'invalid_term' )
		);
		WP_Mock::userFunction( 'wp_unslash' )->andReturnUsing(
			static fn( string $value ): string => $value
		);
		// Polylang's API, wired to the properties above; without a request
		// language it reads as Polylang not answering.
		WP_Mock::userFunction( 'pll_current_language' )->andReturnUsing(
			fn() => $this->current_language ?? false
		);
		WP_Mock::userFunction( 'pll_default_language' )->andReturnUsing(
			fn(): string => $this->default_language
		);
		WP_Mock::userFunction( 'pll_languages_list' )->andReturnUsing(
			fn(): array => $this->languages
		);
		WP_Mock::userFunction( 'pll_get_post' )->andReturnUsing(
			fn( int $post_id, string $language ): int => $this->post_twins[ $post_id ][ $language ] ?? 0
		);
		WP_Mock::userFunction( 'pll_get_term' )->andReturnUsing(
			fn( int $term_id, string $language ): int => $this->term_twins[ $term_id ][ $language ] ?? 0
		);
		WP_Mock::userFunction( 'url_to_postid' )->andReturnUsing(
			fn( string $url ): int => $this->post_ids[ $url ] ?? 0
		);
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing(
			fn( int $post_id ) => $this->permalinks[ $post_id ] ?? false
		);
	}

	/**
	 * One query var of the request under test; a product request carries the
	 * slug as `product` and resolves it to `name`, as WordPress does.
	 *
	 * @param string $name Query var name.
	 */
	private function query_var( string $name ): string {
		if ( 'product' === $name || 'name' === $name ) {
			return $this->product;
		}
		if ( 'product_cat' === $name ) {
			return $this->category;
		}
		if ( 'post_type' === $name && '' !== $this->product ) {
			return 'product';
		}

		return '';
	}

	/**
	 * A product category term, as WordPress builds one.
	 *
	 * @param int    $id   Term id.
	 * @param string $slug Term slug.
	 */
	private static function term( int $id, string $slug ): WP_Term {
		return new WP_Term(
			(object) array(
				'term_id'  => $id,
				'slug'     => $slug,
				'taxonomy' => 'product_cat',
			)
		);
	}

	/**
	 * A category target's term, so that `/product-category/<slug>/` resolves
	 * to the term's own permalink.
	 *
	 * @param int    $id   Term id.
	 * @param string $slug Term slug.
	 */
	private function shelf( int $id, string $slug ): void {
		$this->terms[ $slug ] = self::term( $id, $slug );
		$this->links[ $id ]   = self::HOME . '/product-category/' . $slug . '/';
	}

	/**
	 * Every table the plugin ships, loaded and shaped as the ticket's counts
	 * state them (the Advisor's three entries joined the retired tools with
	 * #66; six product slugs from SEOPress's deletion notices joined with
	 * #252).
	 */
	public function test_the_maps_load_with_the_ticket_counts(): void {
		$maps = Redirects::maps();
		$this->assertNotNull( $maps );
		$this->assertCount( 261, $maps['products'] );
		$this->assertCount( 31, $maps['categories'] );
		$this->assertCount( 24, $maps['pages'] );
			$this->assertCount( 5, $maps['retired_tools'] );
		$this->assertSame( array( 'checkout', 'kasse' ), $maps['checkout']['slugs'] );
		$this->assertSame( '/proforma-request/', $maps['checkout']['target'] );
	}

	/**
	 * Every map is a map of addresses: slugs without a slash for the product
	 * and category tables, paths for the page tables, targets that name an
	 * address of this site.
	 */
	public function test_every_mapping_is_an_address(): void {
		$maps = Redirects::maps();
		$this->assertNotNull( $maps );
		foreach ( array( 'products', 'categories' ) as $table ) {
			foreach ( $maps[ $table ] as $from => $to ) {
				$this->assertSame( $from, strtolower( $from ) );
				$this->assertStringNotContainsString( '/', $from );
				$this->assertStringStartsWith( '/', $to );
			}
		}
		foreach ( array( 'pages', 'retired_tools' ) as $table ) {
			foreach ( $maps[ $table ] as $from => $to ) {
				$this->assertStringStartsWith( '/', $from );
				$this->assertStringStartsWith( '/', $to );
			}
		}
	}

	/**
	 * No target is another retired address: the maps were written so that a
	 * visitor reaches a live route in one hop, and a target that is itself a
	 * key would put a second 301 in front of them.
	 */
	public function test_no_mapping_points_at_another_retired_address(): void {
		$maps = Redirects::maps();
		$this->assertNotNull( $maps );
		// A /shop/ target is the shop page's own address and never a retired
		// one: the dispatch resolves a /shop/ target to the address the retired
		// /shop/ goes to as well, so a target naming it is the same one hop.
		$products   = array_flip( $maps['products'] );
		$categories = array_flip( $maps['categories'] );
		unset( $products['/shop/'], $categories['/shop/'] );
		foreach ( array( 'pages', 'retired_tools' ) as $table ) {
			foreach ( $maps[ $table ] as $from => $to ) {
				$this->assertArrayNotHasKey( $from, $products, $from . ' is a target of a product entry' );
				$this->assertArrayNotHasKey( $from, $categories, $from . ' is a target of a category entry' );
			}
		}
		foreach ( $maps['products'] as $slug => $to ) {
			$segments = explode( '/', trim( (string) parse_url( $to, PHP_URL_PATH ), '/' ) );
			if ( 'product' === $segments[0] && isset( $segments[1] ) ) {
				$this->assertArrayNotHasKey( $segments[1], $maps['products'], $to . ' is itself a retired product address' );
			}
		}
		foreach ( $maps['categories'] as $slug => $to ) {
			$segments = explode( '/', trim( (string) parse_url( $to, PHP_URL_PATH ), '/' ) );
			if ( 'product-category' === $segments[0] ) {
				$this->assertArrayNotHasKey( (string) end( $segments ), $maps['categories'], $to . ' is itself a retired category address' );
			}
		}
	}

	/**
	 * A file that is not a map reads as no maps at all (never half a file):
	 * missing, not JSON, not an object, or an entry that is not a string.
	 */
	public function test_a_broken_data_file_reads_as_no_maps(): void {
		$file = tempnam( sys_get_temp_dir(), 'linker-redirects' );
		$this->assertIsString( $file );

		$this->assertNull( Redirects::maps_from( $file . '.missing' ) );

		file_put_contents( $file, 'not json' );
		$this->assertNull( Redirects::maps_from( $file ) );

		file_put_contents( $file, '[]' );
		$this->assertNull( Redirects::maps_from( $file ) );

		file_put_contents(
			$file,
			json_encode(
				array(
					'products'      => array( 'a' => 1 ),
					'categories'    => array(),
					'pages'         => array(),
					'retired_tools' => array(),
				)
			)
		);
		$this->assertNull( Redirects::maps_from( $file ) );

		file_put_contents(
			$file,
			json_encode(
				array(
					'products'      => array( 'a' => '/x/' ),
					'categories'    => array(),
					'pages'         => array(),
					'retired_tools' => array(),
					'checkout'      => array(
						'slugs'  => 'checkout',
						'target' => '/y/',
					),
				)
			)
		);
		$this->assertNull( Redirects::maps_from( $file ) );
		unlink( $file );
	}

	/**
	 * A withdrawn product's address goes to the shelf it was filed under.
	 */
	public function test_a_withdrawn_product_goes_to_its_shelf(): void {
		$this->wordpress();
		$this->product = 'pylontech-force-h2-system-7-1';
		$this->shelf( 11, 'home-storage' );

		$this->assertSame(
			self::HOME . '/product-category/home-storage/',
			( new Redirects() )->target( '/product/pylontech-force-h2-system-7-1/' )
		);
	}

	/**
	 * The retired slug under the legacy /produkt/ alias lands where its
	 * /product/ sibling lands. WordPress resolves the alias only while the post
	 * exists, so a retired slug arrives with no product query var at all
	 * (measured: the request parses as an attachment) — the path is what is
	 * left to read.
	 */
	public function test_the_legacy_alias_goes_to_the_shelf_of_the_products_line(): void {
		$this->wordpress();
		$this->shelf( 11, 'home-storage' );
		$_SERVER['REQUEST_URI'] = '/produkt/pylontech-force-h2-system-7-1/';

		$this->assertSame(
			self::HOME . '/product-category/home-storage/',
			( new Redirects() )->target( '/produkt/pylontech-force-h2-system-7-1/' )
		);

		unset( $_SERVER['REQUEST_URI'] );
	}

	/**
	 * The alias carries the map's entry, not the slug's own shelf: a replaced
	 * product goes to its replacement through it too.
	 */
	public function test_the_legacy_alias_carries_the_maps_entry(): void {
		$this->wordpress();
		$_SERVER['REQUEST_URI'] = '/produkt/saj-b2-5-0-hv5/';

		$this->assertSame(
			self::HOME . '/product/saj-b2-5-0-hv1/',
			( new Redirects() )->target( '/produkt/saj-b2-5-0-hv5/' )
		);

		unset( $_SERVER['REQUEST_URI'] );
	}

	/**
	 * A retired slug that sells again is served again through the alias as
	 * well: the map never shadows a published product.
	 */
	public function test_a_product_that_comes_back_is_served_again_through_the_alias(): void {
		$this->wordpress();
		$this->published        = array( 481 );
		$_SERVER['REQUEST_URI'] = '/produkt/saj-b2-5-0-hv5/';

		$this->assertNull( ( new Redirects() )->target( '/produkt/saj-b2-5-0-hv5/' ) );

		unset( $_SERVER['REQUEST_URI'] );
	}

	/**
	 * The German alias address: the language prefix is folded away before the
	 * path is read, and the target lands on the German shelf.
	 */
	public function test_a_german_alias_address_goes_to_the_german_shelf(): void {
		$this->wordpress();
		$this->shelf( 11, 'home-storage' );
		$this->links[12]            = self::HOME . '/de/produkt-kategorie/heimspeicher/';
		$this->current_language     = 'de';
		$this->default_language     = 'en';
		$this->languages            = array( 'en', 'de' );
		$this->term_twins[11]['de'] = 12;
		$_SERVER['REQUEST_URI']     = '/de/produkt/pylontech-force-h2-system-7-1/';

		$this->assertSame(
			self::HOME . '/de/produkt-kategorie/heimspeicher/',
			( new Redirects() )->target( '/de/produkt/pylontech-force-h2-system-7-1/' )
		);

		unset( $_SERVER['REQUEST_URI'] );
	}

	/**
	 * The German product address, whose slug is the English one, lands on the
	 * German shelf.
	 */
	public function test_a_german_product_address_goes_to_the_german_shelf(): void {
		$this->wordpress();
		$this->product = 'pylontech-force-h2-system-7-1';
		$this->shelf( 11, 'home-storage' );
		$this->links[12]            = self::HOME . '/de/produkt-kategorie/heimspeicher/';
		$this->current_language     = 'de';
		$this->default_language     = 'en';
		$this->languages            = array( 'en', 'de' );
		$this->term_twins[11]['de'] = 12;

		$this->assertSame(
			self::HOME . '/de/produkt-kategorie/heimspeicher/',
			( new Redirects() )->target( '/de/produkt/pylontech-force-h2-system-7-1/' )
		);
	}

	/**
	 * A withdrawn product that sells again is served again: the map never
	 * shadows a published product.
	 */
	public function test_a_product_that_comes_back_is_served_again(): void {
		$this->wordpress();
		$this->product   = 'pylontech-force-h2-system-7-1';
		$this->published = array( 481 );

		$this->assertNull( ( new Redirects() )->target( '/product/pylontech-force-h2-system-7-1/' ) );
	}

	/**
	 * A withdrawn product that was replaced goes to its replacement.
	 */
	public function test_a_replaced_product_goes_to_its_replacement(): void {
		$this->wordpress();
		$this->product = 'saj-b2-5-0-hv5';

		$this->assertSame(
			self::HOME . '/product/saj-b2-5-0-hv1/',
			( new Redirects() )->target( '/product/saj-b2-5-0-hv5/' )
		);
	}

	/**
	 * A category whose term is gone goes where its route goes now — here the
	 * shop, the shop page's own address.
	 */
	public function test_a_deleted_category_goes_to_its_shelf(): void {
		$this->wordpress();
		$this->category = 'solar-modules';

		$this->assertSame(
			self::HOME . '/products/',
			( new Redirects() )->target( '/product-category/solar-modules/' )
		);
	}

	/**
	 * A category target that names a term resolves to that term's own
	 * permalink — the nested one, for a child shelf.
	 */
	public function test_a_category_target_resolves_to_the_terms_own_permalink(): void {
		$this->wordpress();
		$this->category                    = 'ci-all-in-one';
		$this->terms['all-in-one-systems'] = self::term( 21, 'all-in-one-systems' );
		$this->links[21]                   = self::HOME . '/product-category/commercial-storage/all-in-one-systems/';

		$this->assertSame(
			self::HOME . '/product-category/commercial-storage/all-in-one-systems/',
			( new Redirects() )->target( '/product-category/ci-all-in-one/' )
		);
	}

	/**
	 * The German address of a retired shelf carries the same slug as the
	 * English one and lands on the German shelf, not on the English one.
	 */
	public function test_a_german_address_of_a_retired_shelf_goes_to_the_german_shelf(): void {
		$this->wordpress();
		$this->category                    = 'ci-hybrid';
		$this->current_language            = 'de';
		$this->default_language            = 'en';
		$this->languages                   = array( 'en', 'de' );
		$this->terms['all-in-one-systems'] = self::term( 21, 'all-in-one-systems' );
		$this->links[21]                   = self::HOME . '/product-category/commercial-storage/all-in-one-systems/';
		$this->term_twins[21]['de']        = 22;
		$this->links[22]                   = self::HOME . '/de/produkt-kategorie/gewerbespeicher/all-in-one-systeme/';

		$this->assertSame(
			self::HOME . '/de/produkt-kategorie/gewerbespeicher/all-in-one-systeme/',
			( new Redirects() )->target( '/de/produkt-kategorie/ci-hybrid/' )
		);
	}

	/**
	 * A shelf that fills again is not retired, whatever the map says: its own
	 * address answers.
	 */
	public function test_a_shelf_that_fills_again_is_not_retired(): void {
		$this->wordpress();
		$this->category               = 'res-batteries';
		$this->terms['res-batteries'] = self::term( 31, 'res-batteries' );
		$this->links[31]              = self::HOME . '/product-category/res-batteries/';
		$this->published              = array( 512 );

		$this->assertNull( ( new Redirects() )->target( '/product-category/res-batteries/' ) );
	}

	/**
	 * A retired page path goes to the page that answers it now.
	 */
	public function test_a_retired_page_goes_to_the_page_that_answers_it(): void {
		$this->wordpress();

		$this->assertSame(
			self::HOME . '/solution/residential-storage/',
			( new Redirects() )->target( '/application/residential-storage/' )
		);
		$this->assertSame(
			self::HOME . '/for-installer/',
			( new Redirects() )->target( '/for-oem-odm/' )
		);
	}

	/**
	 * A retired page keeps the query it was requested with: the German
	 * configurator address with a step on it (measured in the 2026-10-16
	 * deployment window: the 301 dropped `?step=roof` and landed the visitor
	 * on the configurator's first step).
	 */
	public function test_a_retired_page_carries_the_requests_query(): void {
		$this->wordpress();
		$this->post_ids[ self::HOME . '/solution-configurator/' ] = 41;
		$this->post_twins[41]['de']                               = 42;
		$this->permalinks[42]                                     = self::HOME . '/de/loesungskonfigurator/';
		$this->current_language                                   = 'de';
		$this->default_language                                   = 'en';
		$this->languages = array( 'en', 'de' );

		try {
			$_SERVER['QUERY_STRING'] = 'step=roof';
			$this->assertSame(
				self::HOME . '/de/loesungskonfigurator/?step=roof',
				( new Redirects() )->target( '/de/solution-configurator/' )
			);

			$_SERVER['QUERY_STRING'] = 'utm_source=newsletter';
			$this->assertSame(
				self::HOME . '/solution/residential-storage/?utm_source=newsletter',
				( new Redirects() )->target( '/application/residential-storage/' )
			);
		} finally {
			unset( $_SERVER['QUERY_STRING'] );
		}
	}

	/**
	 * The query a retired tool address finally carries: the map's own where it
	 * has one (the design canvas's roof step survives a request's query), the
	 * request's where it does not (a plain tool address moves the request's
	 * query onto the configurator).
	 */
	public function test_a_retired_tool_address_carries_the_right_query(): void {
		$this->wordpress();

		$this->assertSame(
			self::HOME . '/solution-configurator/?step=roof',
			( new Redirects() )->target( '/design-canvas/' )
		);
		$this->assertSame(
			self::HOME . '/de/loesungskonfigurator/?step=roof',
			( new Redirects() )->target( '/de/entwurfsflache/' )
		);
		$this->assertSame(
			self::HOME . '/solution-configurator/',
			( new Redirects() )->target( '/quote-configurator/' )
		);

		try {
			$_SERVER['QUERY_STRING'] = 'utm_source=newsletter';
			// The map's own query settles the target; the request's does not
			// replace it.
			$this->assertSame(
				self::HOME . '/de/loesungskonfigurator/?step=roof',
				( new Redirects() )->target( '/de/design-canvas/' )
			);
			// A target without a query of its own carries the request's.
			$this->assertSame(
				self::HOME . '/de/loesungskonfigurator/?utm_source=newsletter',
				( new Redirects() )->target( '/de/angebots-konfigurator/' )
			);
		} finally {
			unset( $_SERVER['QUERY_STRING'] );
		}
	}

	/**
	 * The self-map of the configurator's English slug: the German twin carried
	 * that slug until 2026-10-16, so a German request for it lands on the
	 * twin's own address, while the English page answers its own address (the
	 * same-address guard keeps the map from redirecting the page itself).
	 */
	public function test_the_configurator_self_map_sends_only_the_german_twin_address(): void {
		$this->wordpress();
		$this->post_ids[ self::HOME . '/solution-configurator/' ] = 41;
		$this->post_twins[41]['de']                               = 42;
		$this->permalinks[42]                                     = self::HOME . '/de/loesungskonfigurator/';
		$this->current_language                                   = 'de';
		$this->default_language                                   = 'en';
		$this->languages = array( 'en', 'de' );

		$this->assertSame(
			self::HOME . '/de/loesungskonfigurator/',
			( new Redirects() )->target( '/de/solution-configurator/' )
		);

		$this->current_language = 'en';
		$this->assertNull( ( new Redirects() )->target( '/solution-configurator/' ) );

		// The same-address guard reads the path, not the query: the page's own
		// address with a step on it is still the page itself, never a redirect
		// onto itself.
		try {
			$_SERVER['QUERY_STRING'] = 'step=roof';
			$this->assertNull( ( new Redirects() )->target( '/solution-configurator/' ) );
		} finally {
			unset( $_SERVER['QUERY_STRING'] );
		}
	}

	/**
	 * The retired checkout slug goes to the checkout page — with the rest of
	 * the path and the query string, where WooCommerce's received page and
	 * its order links live.
	 */
	public function test_the_retired_checkout_slug_goes_to_the_checkout_page(): void {
		$this->wordpress();

		$this->assertSame(
			self::HOME . '/proforma-request/',
			( new Redirects() )->target( '/checkout/' )
		);

		// WooCommerce's received page and its order links carry the order key
		// in the query string, which the redirect passes on.
		$_SERVER['QUERY_STRING'] = 'key=wc_order_abc';
		$this->assertSame(
			self::HOME . '/proforma-request/order-received/4711/?key=wc_order_abc',
			( new Redirects() )->target( '/checkout/order-received/4711/' )
		);
		unset( $_SERVER['QUERY_STRING'] );
	}

	/**
	 * While the checkout page answers the retired address itself — a site
	 * where it was never renamed — nothing redirects: the page's own path, and
	 * the addresses under it, which are the page's endpoints (WooCommerce's
	 * received page with the order id among them).
	 */
	public function test_a_checkout_page_on_the_retired_addresses_is_not_redirected(): void {
		$this->wordpress();
		$this->checkout = '/checkout/';

		$this->assertNull( ( new Redirects() )->target( '/checkout/' ) );
		$this->assertNull( ( new Redirects() )->target( '/checkout/order-received/4711/' ) );
	}

	/**
	 * A German shelf address is no product address, however its base starts:
	 * the product bases are matched as whole path segments, never as prefixes.
	 */
	public function test_a_german_shelf_address_is_not_a_product_address(): void {
		$this->wordpress();
		$this->category         = 'heimspeicher';
		$_SERVER['REQUEST_URI'] = '/de/produkt-kategorie/heimspeicher/';

		$this->assertNull( ( new Redirects() )->target( '/de/produkt-kategorie/heimspeicher/' ) );

		unset( $_SERVER['REQUEST_URI'] );
	}

	/**
	 * A German request: WooCommerce answers the German checkout page, whose
	 * prefix is the German one — the German endpoints stay too.
	 */
	public function test_a_german_checkout_pages_endpoints_are_not_redirected(): void {
		$this->wordpress();
		$this->checkout         = '/de/kasse/';
		$this->current_language = 'de';
		$this->default_language = 'en';
		$this->languages        = array( 'en', 'de' );

		$this->assertNull( ( new Redirects() )->target( '/de/kasse/order-received/4711/' ) );
	}

	/**
	 * The retired shop archive goes to the shop page's own address — the
	 * address the live site's rule sent it to, and the one the shop answers
	 * today (measured 2026-10-11: /shop/ answers /products/). The map's target
	 * is the dispatch-time one the category targets already use, so a site
	 * that keeps its shop elsewhere answers there.
	 */
	public function test_the_retired_shop_archive_goes_to_the_shop_page(): void {
		$this->wordpress();

		$this->assertSame(
			self::HOME . '/products/',
			( new Redirects() )->target( '/shop/' )
		);
	}

	/**
	 * While the shop page answers /shop/ itself — a site where the archive
	 * never moved — the address is the page: the target would be the request,
	 * and the redirect would loop for good.
	 */
	public function test_a_shop_page_on_the_retired_address_is_not_redirected(): void {
		$this->wordpress();
		$this->shop = '/shop/';

		$this->assertNull( ( new Redirects() )->target( '/shop/' ) );
	}

	/**
	 * The German shop address lands on the German page's address, not the
	 * English one.
	 */
	public function test_a_german_shop_address_lands_on_the_german_page(): void {
		$this->wordpress();
		$this->current_language                      = 'de';
		$this->default_language                      = 'en';
		$this->languages                             = array( 'en', 'de' );
		$this->post_ids[ self::HOME . '/products/' ] = 61;
		$this->post_twins[61]['de']                  = 62;
		$this->permalinks[62]                        = self::HOME . '/de/produkte/';

		$this->assertSame(
			self::HOME . '/de/produkte/',
			( new Redirects() )->target( '/de/shop/' )
		);
	}

	/**
	 * Every retired tool address of this site goes to the configurator page of
	 * its own language, with the roof step (#12 item 2; /de/design-canvas/
	 * is the old plugin's English-slug-under-/de/ alias, /de/entwurfsflache/
	 * the German page slug).
	 */
	public function test_retired_tool_addresses_go_to_the_configurators_roof_step(): void {
		$this->wordpress();

		$this->assertSame( self::HOME . '/solution-configurator/?step=roof', ( new Redirects() )->target( '/design-canvas/' ) );
		$this->assertSame( self::HOME . '/de/loesungskonfigurator/?step=roof', ( new Redirects() )->target( '/de/design-canvas/' ) );
		$this->assertSame( self::HOME . '/de/loesungskonfigurator/?step=roof', ( new Redirects() )->target( '/de/entwurfsflache/' ) );
	}

	/**
	 * The configurator's own former address goes to the page itself (it was
	 * the configurator, not a step of it); German likewise.
	 */
	public function test_the_configurators_former_address_goes_to_the_page(): void {
		$this->wordpress();

		$this->assertSame( self::HOME . '/solution-configurator/', ( new Redirects() )->target( '/quote-configurator/' ) );
		$this->assertSame( self::HOME . '/de/loesungskonfigurator/', ( new Redirects() )->target( '/de/angebots-konfigurator/' ) );
	}

	/**
	 * The configurator's own former addresses go to the page: the slug moved
	 * from /linker-planner/ (the German twin /de/linker-planer/) to
	 * /solution-configurator/ per the owner's 2026-10-12 ruling; the German
	 * request lands on the twin's own address.
	 */
	public function test_the_configurators_former_addresses_go_to_the_page(): void {
		$this->wordpress();
		$this->default_language = 'en';
		$this->languages        = array( 'en', 'de' );

		$this->assertSame( self::HOME . '/solution-configurator/', ( new Redirects() )->target( '/linker-planner/' ) );

		$this->current_language = 'de';
		$this->post_ids         = array( self::HOME . '/solution-configurator/' => 71 );
		$this->post_twins       = array( 71 => array( 'de' => 72 ) );
		$this->permalinks       = array( 72 => self::HOME . '/de/loesungskonfigurator/' );

		$this->assertSame( self::HOME . '/de/loesungskonfigurator/', ( new Redirects() )->target( '/de/linker-planer/' ) );
	}

	/**
	 * The advisor's old addresses go to the Genie page: the slug moved from
	 * /linker-advisor/ (the German twin /de/linker-berater/) to /genie/ on
	 * the owner's 2026-10-13 ruling; the German request lands on the twin's
	 * own address.
	 */
	public function test_the_advisors_former_addresses_go_to_the_page(): void {
		$this->wordpress();
		$this->default_language = 'en';
		$this->languages        = array( 'en', 'de' );

		$this->assertSame( self::HOME . '/genie/', ( new Redirects() )->target( '/linker-advisor/' ) );

		$this->current_language = 'de';
		$this->post_ids         = array( self::HOME . '/genie/' => 71 );
		$this->post_twins       = array( 71 => array( 'de' => 72 ) );
		$this->permalinks       = array( 72 => self::HOME . '/de/genie/' );

		$this->assertSame( self::HOME . '/de/genie/', ( new Redirects() )->target( '/de/linker-berater/' ) );
		$this->assertSame( self::HOME . '/de/genie/', ( new Redirects() )->target( '/de/linker-advisor/' ) );
	}

	/**
	 * Addresses that still exist stay: null means no redirect.
	 */
	public function test_live_addresses_stay(): void {
		$this->wordpress();

		$this->assertNull( ( new Redirects() )->target( '/design-canvas-exhibition/' ) );
		$this->assertNull( ( new Redirects() )->target( '/products/' ) );
		$this->assertNull( ( new Redirects() )->target( '/de/produkte/' ) );
		$this->assertNull( ( new Redirects() )->target( '/compare-products/' ) );
		$this->assertNull( ( new Redirects() )->target( '/' ) );
	}

	/**
	 * A product or category the map does not know is left to WordPress.
	 */
	public function test_addresses_outside_the_maps_stay(): void {
		$this->wordpress();
		$this->product  = 'goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh';
		$this->category = 'heimspeicher';

		$this->assertNull( ( new Redirects() )->target( '/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/' ) );
		$this->assertNull( ( new Redirects() )->target( '/product-category/heimspeicher/' ) );
		$this->assertNull( ( new Redirects() )->target( '/blog/' ) );
	}

	/**
	 * Without Polylang there is no German site to localize into, and the map's
	 * English target is what answers.
	 */
	public function test_a_german_address_without_polylang_goes_to_the_english_target(): void {
		$this->wordpress();
		$this->product = 'pylontech-force-h2-system-7-1';
		$this->shelf( 11, 'home-storage' );

		$this->assertSame(
			self::HOME . '/product-category/home-storage/',
			( new Redirects() )->target( '/de/produkt/pylontech-force-h2-system-7-1/' )
		);
	}
}
