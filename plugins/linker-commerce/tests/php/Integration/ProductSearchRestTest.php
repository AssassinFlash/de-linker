<?php
/**
 * The catalogue search route over HTTP on a local WordPress.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use PHPUnit\Framework\TestCase;

/**
 * GET /wp-json/linker/v1/catalog-search as the search box calls it: on a
 * local site with its real products (the snapshot's catalogue). The site's
 * address is the environment variable LINKER_COMMERCE_TEST_SITE, e.g.
 * http://127.0.0.1:8927; without it the tests are skipped (CI has no site),
 * and with it but a site that does not answer they fail.
 *
 * @coversNothing
 */
final class ProductSearchRestTest extends TestCase {


	/**
	 * Base URL of the local site.
	 *
	 * @var string
	 */
	private string $site = '';

	/**
	 * The catalogue's first published product, from the engineering feed: its
	 * ID, item number and name as the site serves them.
	 *
	 * @var array{id: int, sku: string, name: string}
	 */
	private array $product = array(
		'id'   => 0,
		'sku'  => '',
		'name' => '',
	);

	/**
	 * Skips when no local site is configured; fails when the configured site
	 * does not answer; picks a real product to search for.
	 */
	public function setUp(): void {
		parent::setUp();
		$site = (string) getenv( 'LINKER_COMMERCE_TEST_SITE' );
		if ( '' === $site ) {
			$this->markTestSkipped( 'Set LINKER_COMMERCE_TEST_SITE to a local WordPress with the catalogue.' );
		}
		$this->site = rtrim( $site, '/' );
		$feed       = self::request( 'GET', $this->site . '/wp-json/linker/v1/engineering-feed' );
		if ( 0 === $feed['status'] ) {
			$this->fail( "{$this->site} does not answer." );
		}
		$this->assertSame( 200, $feed['status'], 'The engineering feed answers on ' . $this->site );
		foreach ( (array) ( $feed['body']['products'] ?? array() ) as $product ) {
			$sku = (string) ( $product['sku'] ?? '' );
			if ( '' !== $sku ) {
				$this->product = array(
					'id'   => (int) $product['id'],
					'sku'  => $sku,
					'name' => (string) ( $product['name'] ?? '' ),
				);
				break;
			}
		}
		$this->assertNotSame( 0, $this->product['id'], 'The site serves at least one product with an item number.' );
	}

	/**
	 * The item number, however it is typed, answers with the product — its
	 * entry number, its page and the selection facts of the catalogue's data
	 * layer. Separators and case do not decide the match.
	 *
	 * @testWith ["{sku}"]
	 *           ["{sku_lower}"]
	 *
	 * @param string $query The query, with placeholders filled in.
	 */
	public function test_the_item_number_answers_with_its_product( string $query ): void {
		$query    = str_replace( array( '{sku}', '{sku_lower}' ), array( $this->product['sku'], strtolower( $this->product['sku'] ) ), $query );
		$response = $this->search( $query );

		$this->assertSame( 200, $response['status'] );
		$this->assertArrayNotHasKey( 'set-cookie', $response['headers'] );
		$this->assertStringNotContainsString( 'no-cache', $response['headers']['cache-control'] ?? '' );
		$ids = array_column( (array) $response['body']['items'], 'id' );
		$this->assertContains( $this->product['id'], $ids );
		$item = $response['body']['items'][ array_search( $this->product['id'], $ids, true ) ];
		$this->assertSame( $this->product['sku'], $item['sku'] );
		$this->assertStringContainsString( $this->product['name'], $item['title'] );
		$this->assertStringStartsWith( $this->site . '/', $item['url'] );
		$facts = (array) $item['facts'];
		foreach ( array( 'device_class', 'application', 'phase', 'ac_power_kw', 'pv_input_kw', 'usable_kwh', 'nominal_kwh' ) as $key ) {
			$this->assertArrayHasKey( $key, $facts, 'The always-present keys of the selection-facts contract.' );
		}
		$this->assertSame(
			array(),
			array_diff( array_keys( $facts ), array( 'device_class', 'application', 'phase', 'ac_power_kw', 'pv_input_kw', 'usable_kwh', 'nominal_kwh', 'kwh_range', 'ac_apparent_kva' ) ),
			'Only the contract keys appear.'
		);
	}

	/**
	 * A query that names nothing answers with no items — still a 200, still
	 * the same shape.
	 */
	public function test_an_unknown_query_answers_empty(): void {
		$response = $this->search( 'zz-no-such-product-' . (string) random_int( 1000, 9999 ) );

		$this->assertSame( 200, $response['status'] );
		$this->assertSame( array(), $response['body']['items'] );
	}

	/**
	 * The route's bounds: a query shorter than two characters and a limit
	 * outside 1..12 are 400s before any product is read.
	 *
	 * @testWith ["q=a"]
	 *           ["q=%C3%BC"]
	 *           ["q=ab&limit=0"]
	 *           ["q=ab&limit=13"]
	 *           [""]
	 *
	 * @param string $query Query string.
	 */
	public function test_bad_queries_are_a_400( string $query ): void {
		$response = self::request( 'GET', $this->site . '/wp-json/linker/v1/catalog-search?' . $query );

		$this->assertSame( 400, $response['status'] );
		$this->assertContains( $response['body']['code'], array( 'rest_missing_callback_param', 'rest_invalid_param' ) );
	}

	/**
	 * `lang=de` answers the German products with their German addresses: the
	 * search box of the German catalogue links where the German catalogue
	 * does.
	 */
	public function test_the_language_picks_the_products_and_their_addresses(): void {
		$response = $this->search( $this->product['sku'], 'de' );
		if ( array() === $response['body']['items'] ) {
			$this->markTestSkipped( 'The site has no German version of the product (no Polylang twins).' );
		}
		$this->assertSame( 200, $response['status'] );
		$item = $response['body']['items'][0];
		$this->assertStringStartsWith( $this->site . '/de/', $item['url'] );
	}

	/**
	 * GET of the route for a query.
	 *
	 * @param  string $query The query.
	 * @param  string $lang  Optional language.
	 * @return array{status: int, headers: array<string, string>, raw: string, body: mixed}
	 */
	private function search( string $query, string $lang = '' ): array {
		$url = $this->site . '/wp-json/linker/v1/catalog-search?q=' . rawurlencode( $query );
		if ( '' !== $lang ) {
			$url .= '&lang=' . rawurlencode( $lang );
		}
		return self::request( 'GET', $url );
	}

	/**
	 * One anonymous HTTP request; status 0 when nothing answers.
	 *
	 * @param  non-empty-string $method HTTP method.
	 * @param  string           $url    URL.
	 * @return array{status: int, headers: array<string, string>, raw: string, body: mixed}
	 */
	private static function request( string $method, string $url ): array {
     // phpcs:disable WordPress.WP.AlternativeFunctions -- the test calls the site from outside, without WordPress's HTTP API.
		$handle = curl_init( $url );
		curl_setopt_array(
			$handle,
			array(
				CURLOPT_CUSTOMREQUEST  => $method,
				CURLOPT_RETURNTRANSFER => true,
				CURLOPT_HEADER         => true,
				CURLOPT_TIMEOUT        => 60,
			)
		);
		$response    = curl_exec( $handle );
		$status      = (int) curl_getinfo( $handle, CURLINFO_RESPONSE_CODE );
		$header_size = (int) curl_getinfo( $handle, CURLINFO_HEADER_SIZE );
		// Released by unset(), not curl_close(): the close call was the phpcs
		// deprecation report's target (#158 openQ 2), and dropping the
		// reference frees the handle the same way at function scope.
		unset( $handle );
     // phpcs:enable

		if ( ! is_string( $response ) ) {
			return array(
				'status'  => 0,
				'headers' => array(),
				'raw'     => '',
				'body'    => null,
			);
		}
		$headers = array();
		foreach ( explode( "\r\n", substr( $response, 0, $header_size ) ) as $line ) {
			if ( str_contains( $line, ':' ) ) {
				list( $name, $value )                   = explode( ':', $line, 2 );
				$headers[ strtolower( trim( $name ) ) ] = trim( $value );
			}
		}
		$raw = substr( $response, $header_size );

		return array(
			'status'  => $status,
			'headers' => $headers,
			'raw'     => $raw,
			'body'    => json_decode( $raw, true ),
		);
	}
}
