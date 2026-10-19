<?php
/**
 * Tests for the German shop on the English products.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Woo;

use Linker\I18n\Languages;
use Linker\I18n\Tests\Unit\PolylangDouble;
use Linker\I18n\Woo\Storefront;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Storefront.
 *
 * @covers \Linker\I18n\Woo\Storefront
 */
final class StorefrontTest extends TestCase {

	/**
	 * Whether the request runs in the admin.
	 *
	 * @var bool
	 */
	private static bool $admin = false;

	/**
	 * The storefront of the current test.
	 */
	private function storefront(): Storefront {
		WP_Mock::userFunction( 'is_admin', array( 'return' => static fn(): bool => self::$admin ) );
		return new Storefront( new Languages() );
	}

	/**
	 * The mocks the quoted name needs: the wrapper string, tag stripping and
	 * the German title.
	 *
	 * @param array<int, string> $titles Post ID => title.
	 */
	private function names( array $titles ): void {
		WP_Mock::userFunction(
			'_x',
			array(
				'args'   => array( '&ldquo;%s&rdquo;', 'Item name in quotes', 'woocommerce' ),
				'return' => static fn( string $format ): string => $format,
			)
		);
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn( string $text ): string => trim( preg_replace( '/<[^>]*>/', '', $text ) ?? $text ) ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => static fn( $id ) => $titles[ (int) $id ] ?? '' ) );
	}

	/**
	 * A German product is asked for its selection facts through its English
	 * twin; an English product answers itself, and a German product without
	 * a twin keeps its ID.
	 */
	public function test_facts_answer_through_the_english_product(): void {
		PolylangDouble::mock(
			array(
				5 => 'en',
				7 => 'de',
				9 => 'de',
			),
			array( 5 => 7 )
		);
		$storefront = $this->storefront();

		$this->assertSame( 5, $storefront->facts_product_id( 7 ) );
		$this->assertSame( 5, $storefront->facts_product_id( 5 ) );
		$this->assertSame( 9, $storefront->facts_product_id( 9 ) );
	}

	/**
	 * A German request names the German product in the add-to-cart notice's
	 * quotes: the notice takes its name from get_the_title(), which the
	 * get_name() filter does not reach.
	 */
	public function test_german_notice_names_the_german_product(): void {
		self::$admin = false;
		PolylangDouble::mock(
			array(
				24  => 'en',
				249 => 'de',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'de'
		);
		$this->names(
			array(
				24  => 'SAJ CB2 (battery cabinet)',
				249 => 'SAJ CB2 (Batteriespeicherschrank)',
			)
		);

		$quoted = $this->storefront()->quoted_item_name( '&ldquo;SAJ CB2 (battery cabinet)&rdquo;', 24 );

		$this->assertSame( '&ldquo;SAJ CB2 (Batteriespeicherschrank)&rdquo;', $quoted );
	}

	/**
	 * An English request, and a product with no German version, keep
	 * WooCommerce's own name in the quotes.
	 */
	public function test_other_requests_and_untranslated_products_keep_the_name(): void {
		$english = '&ldquo;SAJ CB2 (battery cabinet)&rdquo;';

		self::$admin = false;
		PolylangDouble::mock(
			array(
				24 => 'en',
				25 => 'en',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'en'
		);
		$this->names( array( 249 => 'SAJ CB2 (Batteriespeicherschrank)' ) );
		$this->assertSame( $english, $this->storefront()->quoted_item_name( $english, 24 ), 'English request' );

		self::$admin = false;
		PolylangDouble::mock( array( 25 => 'en' ), array(), array(), array(), 'de' );
		$this->names( array() );
		$this->assertSame( $english, $this->storefront()->quoted_item_name( $english, 25 ), 'No German version' );

		self::$admin = true;
		PolylangDouble::mock( array( 24 => 'en' ), array( 24 => 249 ), array(), array(), 'de' );
		$this->names( array() );
		$this->assertSame( $english, $this->storefront()->quoted_item_name( $english, 24 ), 'Admin request' );
	}

	/**
	 * A German Store API answer that was asked for English products
	 * (`include=` keeps those ids, `lang=de`) links each English product that
	 * has a twin. Registered for #339 as s1-card-permalink-locale (#413).
	 * The count is permalinks that differ, not whether set_data() ran.
	 */
	public function test_german_store_products_link_to_the_german_page(): void {
		$storefront = $this->german_products();
		$body       = array(
			$this->product( 24, 'http://example.test/product/saj/', 'Preise nach Anmeldung' ),
			$this->product( 25, 'http://example.test/product/lone/', 'Angebot pro Projekt' ),
			$this->product( 249, 'http://example.test/de/produkt/saj/', 'Preise nach Anmeldung' ),
		);

		$linked = $this->dispatch( $storefront, '/wc/store/v1/products', $body );

		$this->assertSame( 1, $linked['changed'] );
		$this->assertSame( array( 24, 25, 249 ), array_column( $linked['body'], 'id' ) );
		$this->assertSame( 'http://example.test/de/produkt/saj/', $linked['body'][0]['permalink'] );
		$this->assertSame( 'http://example.test/product/lone/', $linked['body'][1]['permalink'] );
		$this->assertSame( 'http://example.test/de/produkt/saj/', $linked['body'][2]['permalink'] );
		$this->assertSame( 'Preise nach Anmeldung', $linked['body'][0]['price_html'] );
		$this->assertSame( 'Angebot pro Projekt', $linked['body'][1]['price_html'] );
	}

	/**
	 * One product, by id or by slug, gets the same German link. English, an
	 * admin screen, another route and an error stay as WooCommerce wrote them.
	 */
	public function test_only_a_german_product_response_is_relinked(): void {
		$storefront = $this->german_products();
		$one        = $this->product( 24, 'http://example.test/product/saj/' );
		$by_id      = $this->dispatch( $storefront, '/wc/store/v1/products/24', $one );
		$by_slug    = $this->dispatch( $storefront, '/wc/store/v1/products/saj-slug', $one );

		$this->assertSame( 1, $by_id['changed'] );
		$this->assertSame( 1, $by_slug['changed'] );
		$this->assertSame( 'http://example.test/de/produkt/saj/', $by_id['body']['permalink'] );
		$this->assertSame( 'http://example.test/de/produkt/saj/', $by_slug['body']['permalink'] );

		self::$admin = false;
		PolylangDouble::mock(
			array(
				24  => 'en',
				249 => 'de',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'en'
		);
		$this->assertSame( 0, $this->dispatch( $this->storefront(), '/wc/store/v1/products', $one, 200, 'en' )['changed'] );

		self::$admin = true;
		PolylangDouble::mock(
			array(
				24  => 'en',
				249 => 'de',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'de'
		);
		$this->assertSame( 0, $this->dispatch( $this->storefront(), '/wc/store/v1/products', $one, 200, 'de' )['changed'] );

		self::$admin = false;
		PolylangDouble::mock(
			array(
				24  => 'en',
				25  => 'en',
				249 => 'de',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'de'
		);
		$storefront = $this->storefront();
		$this->assertSame( 0, $this->dispatch( $storefront, '/wc/store/v1/cart', $one )['changed'] );
		$this->assertSame( 0, $this->dispatch( $storefront, '/wc/store/v1/products/categories', $one )['changed'] );
		$this->assertSame( 0, $this->dispatch( $storefront, '/wc/store/v1/products/24', $one, 404 )['changed'] );
	}

	/**
	 * `lang=all` lists every language and RestLang enters none. A German page
	 * making that request keeps each English permalink.
	 */
	public function test_lang_all_from_a_german_context_keeps_english_permalinks(): void {
		$body   = array(
			$this->product( 24, 'http://example.test/product/saj/' ),
			$this->product( 25, 'http://example.test/product/lone/' ),
		);
		$linked = $this->dispatch( $this->german_products(), '/wc/store/v1/products', $body, 200, 'all' );

		$this->assertSame( 0, $linked['changed'] );
		$this->assertSame( 'http://example.test/product/saj/', $linked['body'][0]['permalink'] );
		$this->assertSame( 'http://example.test/product/lone/', $linked['body'][1]['permalink'] );
	}

	/**
	 * No `lang` parameter is not a German request, even when the ambient
	 * language is German. `lang=de` is, even when the ambient language is English.
	 */
	public function test_only_an_explicit_german_lang_relinks(): void {
		$one    = $this->product( 24, 'http://example.test/product/saj/' );
		$absent = $this->dispatch( $this->german_products(), '/wc/store/v1/products', $one, 200, null );
		$this->assertSame( 0, $absent['changed'] );
		$this->assertSame( 'http://example.test/product/saj/', $absent['body']['permalink'] );

		self::$admin = false;
		PolylangDouble::mock(
			array(
				24  => 'en',
				249 => 'de',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'en'
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn( $id ): string|false => 249 === (int) $id ? 'http://example.test/de/produkt/saj/' : false,
			)
		);
		$linked = $this->dispatch( $this->storefront(), '/wc/store/v1/products/24', $one, 200, 'de' );

		$this->assertSame( 1, $linked['changed'] );
		$this->assertSame( 'http://example.test/de/produkt/saj/', $linked['body']['permalink'] );
	}

	/**
	 * StoreApiPrices sets `prices` to null. That value still has the key, and
	 * the product still takes the German permalink — `isset( 'prices' )` would
	 * miss it the moment the price filter runs first.
	 */
	public function test_a_product_with_null_prices_still_links_to_german(): void {
		$product           = $this->product( 24, 'http://example.test/product/saj/' );
		$product['prices'] = null;
		$linked            = $this->dispatch( $this->german_products(), '/wc/store/v1/products', array( $product ) );

		$this->assertSame( 1, $linked['changed'] );
		$this->assertNull( $linked['body'][0]['prices'] );
		$this->assertSame( 'http://example.test/de/produkt/saj/', $linked['body'][0]['permalink'] );
	}

	/**
	 * Product routes are the collection and one product. WooCommerce 11.2.0's
	 * sibling routes (`src/StoreApi/RoutesController.php`, `get_path_regex()`)
	 * are not, including the pattern `get_route()` returns and a further
	 * segment. The exclusion is the whole segment: a longer slug still matches.
	 */
	public function test_product_routes_exclude_woocommerce_sibling_routes(): void {
		$this->assertSame(
			array( 'attributes', 'brands', 'categories', 'collection-data', 'reviews', 'tags' ),
			Storefront::STORE_PRODUCT_NEIGHBOURS
		);
		foreach ( Storefront::STORE_PRODUCT_NEIGHBOURS as $segment ) {
			$this->assertMatchesRegularExpression( '/^[a-z0-9-]+$/', $segment, $segment );
		}

		$storefront = $this->german_products();
		$one        = $this->product( 24, 'http://example.test/product/saj/' );
		// The path WooCommerce registers, which is what WP_REST_Request::get_route() returns.
		$siblings = array(
			'/wc/store/v1/products/attributes',
			'/wc/store/v1/products/attributes/(?P<id>[\d]+)',
			'/wc/store/v1/products/attributes/(?P<attribute_id>[\d]+)/terms',
			'/wc/store/v1/products/brands',
			'/wc/store/v1/products/brands/(?P<identifier>[\w-]+)',
			'/wc/store/v1/products/categories',
			'/wc/store/v1/products/categories/(?P<id>[\d]+)',
			'/wc/store/v1/products/collection-data',
			'/wc/store/v1/products/reviews',
			'/wc/store/v1/products/tags',
			'/wc/store/v1/products/categories/12',
			'/wc/store/v1/products/attributes/3/terms',
		);
		foreach ( $siblings as $route ) {
			$this->assertSame( 0, $this->dispatch( $storefront, $route, $one )['changed'], $route );
		}

		$products = array(
			'/wc/store/v1/products',
			'/wc/store/v1/products/(?P<id>[\d]+)',
			'/wc/store/v1/products/(?P<slug>[\S]+)',
			'/wc/store/v1/products/24',
			'/wc/store/v1/products/saj-slug',
			'/wc/store/v1/products/categories-extra',
		);
		foreach ( $products as $route ) {
			$linked = $this->dispatch( $storefront, $route, $one );
			$this->assertSame( 1, $linked['changed'], $route );
			$this->assertSame( 'http://example.test/de/produkt/saj/', $linked['body']['permalink'], $route );
		}
	}

	/**
	 * The products of a German shop: 24 has German twin 249, 25 has none.
	 */
	private function german_products(): Storefront {
		self::$admin = false;
		PolylangDouble::mock(
			array(
				24  => 'en',
				25  => 'en',
				249 => 'de',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'de'
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn( $id ): string|false => 249 === (int) $id ? 'http://example.test/de/produkt/saj/' : false,
			)
		);
		return $this->storefront();
	}

	/**
	 * One Store API product, as the schema gives it.
	 *
	 * @param int    $id         Product ID.
	 * @param string $permalink  Permalink WooCommerce wrote.
	 * @param string $price_html Price copy, when the test names one.
	 * @return array<string, mixed>
	 */
	private function product( int $id, string $permalink, string $price_html = '' ): array {
		return array(
			'id'         => $id,
			'permalink'  => $permalink,
			'prices'     => array( 'price' => '168000' ),
			'price_html' => $price_html,
		);
	}

	/**
	 * Runs the product-link filter.
	 *
	 * `changed` counts permalinks that differ from the input. A call to
	 * set_data() that leaves every permalink as it was counts as zero.
	 *
	 * @param Storefront   $storefront Storefront under test.
	 * @param string       $route      REST route.
	 * @param array<mixed> $body       Response body.
	 * @param int          $status     HTTP status.
	 * @param string|null  $lang       The request's `lang` parameter.
	 * @return array{changed: int, body: array<mixed>}
	 */
	private function dispatch( Storefront $storefront, string $route, array $body, int $status = 200, ?string $lang = 'de' ): array {
		$request = Mockery::mock( 'WP_REST_Request' );
		$request->shouldReceive( 'get_route' )->andReturn( $route );
		$request->shouldReceive( 'get_param' )->with( 'lang' )->andReturn( $lang );
		$response = Mockery::mock( 'WP_REST_Response' );
		$response->shouldReceive( 'get_status' )->andReturn( $status )->byDefault();
		$response->shouldReceive( 'get_data' )->andReturn( $body )->byDefault();
		$written = null;
		$response->shouldReceive( 'set_data' )->andReturnUsing(
			static function ( $next ) use ( &$written ): void {
				$written = $next;
			}
		);

		$storefront->store_product_links( $response, array(), $request );

		$next = is_array( $written ) ? $written : $body;
		return array(
			'changed' => $this->changed_permalinks( $body, $next ),
			'body'    => $next,
		);
	}

	/**
	 * How many product permalinks differ.
	 *
	 * @param array<mixed> $before Response WooCommerce wrote.
	 * @param array<mixed> $after  Response after the filter.
	 */
	private function changed_permalinks( array $before, array $after ): int {
		if ( is_string( $before['permalink'] ?? null ) ) {
			return ( $after['permalink'] ?? null ) !== $before['permalink'] ? 1 : 0;
		}
		$changed = 0;
		foreach ( $before as $key => $item ) {
			if ( ! is_array( $item ) || ! is_string( $item['permalink'] ?? null ) ) {
				continue;
			}
			$next = $after[ $key ] ?? null;
			if ( ! is_array( $next ) || ( $next['permalink'] ?? null ) !== $item['permalink'] ) {
				++$changed;
			}
		}
		return $changed;
	}
}
