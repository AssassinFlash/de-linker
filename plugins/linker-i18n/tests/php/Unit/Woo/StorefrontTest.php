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
	 * (`include=` keeps those ids) links each one to its German page.
	 * Registered for #339 as s1-card-permalink-locale (#413).
	 */
	public function test_german_store_products_link_to_the_german_page(): void {
		$storefront = $this->german_products();
		$body       = array(
			$this->product( 24, 'http://example.test/product/saj/', 'Preise nach Anmeldung' ),
			$this->product( 25, 'http://example.test/product/lone/', 'Angebot pro Projekt' ),
			$this->product( 249, 'http://example.test/de/produkt/saj/', 'Preise nach Anmeldung' ),
		);

		$linked = $this->dispatch( $storefront, '/wc/store/v1/products', $body );

		$this->assertTrue( $linked['wrote'] );
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
		$this->assertFalse( $this->dispatch( $this->storefront(), '/wc/store/v1/products', $one )['wrote'] );

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
		$this->assertFalse( $this->dispatch( $this->storefront(), '/wc/store/v1/products', $one )['wrote'] );

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
		$this->assertFalse( $this->dispatch( $storefront, '/wc/store/v1/cart', $one )['wrote'] );
		$this->assertFalse( $this->dispatch( $storefront, '/wc/store/v1/products/categories', $one )['wrote'] );
		$this->assertFalse( $this->dispatch( $storefront, '/wc/store/v1/products/24', $one, 404 )['wrote'] );
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
	 * @param Storefront   $storefront Storefront under test.
	 * @param string       $route      REST route.
	 * @param array<mixed> $body       Response body.
	 * @param int          $status     HTTP status.
	 * @return array{wrote: bool, body: array<mixed>}
	 */
	private function dispatch( Storefront $storefront, string $route, array $body, int $status = 200 ): array {
		$request = Mockery::mock( 'WP_REST_Request' );
		$request->shouldReceive( 'get_route' )->andReturn( $route );
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

		return array(
			'wrote' => is_array( $written ),
			'body'  => is_array( $written ) ? $written : $body,
		);
	}
}
