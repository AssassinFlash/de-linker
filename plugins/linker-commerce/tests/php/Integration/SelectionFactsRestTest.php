<?php
/**
 * The selection-facts route over HTTP on a local WordPress.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\SelectionFactSet;
use Linker\Commerce\Tests\Support\LiveProducts;
use Linker\Commerce\Tests\Support\MocksProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * GET and OPTIONS /wp-json/linker/v1/selection-facts as an anonymous visitor
 * on a local WordPress whose products come from
 * tests/fixtures/load-live-products.php (with or without
 * tools/migrate/7-facts.py applied). The site's address is the environment
 * variable LINKER_COMMERCE_TEST_SITE, e.g. http://127.0.0.1:8107; without it
 * the tests are skipped (CI has no site), and with it but a site that does not
 * answer they fail.
 *
 * @coversNothing
 */
final class SelectionFactsRestTest extends TestCase {

	use MocksProducts;

	/**
	 * The fixture's unpublished product.
	 */
	private const DRAFT = 4124;

	/**
	 * Base URL of the local site.
	 *
	 * @var string
	 */
	private string $site = '';

	/**
	 * Skips when no local site is configured; fails when the configured site
	 * does not answer.
	 */
	public function setUp(): void {
		parent::setUp();
		$site = (string) getenv( 'LINKER_COMMERCE_TEST_SITE' );
		if ( '' === $site ) {
			$this->markTestSkipped( 'Set LINKER_COMMERCE_TEST_SITE to a local WordPress seeded with tests/fixtures/load-live-products.php.' );
		}
		$this->site = rtrim( $site, '/' );
		if ( 0 === self::request( 'GET', $this->site . '/wp-json/' )['status'] ) {
			$this->fail( "{$this->site} does not answer." );
		}
	}

	/**
	 * An anonymous visitor gets, for every published fixture product, what
	 * SelectionFacts computes from the same product data, without a cookie or a
	 * no-cache header.
	 */
	public function test_anonymous_answer_is_the_contract(): void {
		$ids      = array_keys( LiveProducts::published() );
		$response = $this->get( $ids );

		$this->assertSame( 200, $response['status'] );
		$this->assertArrayNotHasKey( 'set-cookie', $response['headers'] );
		$this->assertStringNotContainsString( 'no-cache', $response['headers']['cache-control'] ?? '' );
		$this->assertIsArray( $response['body'] );
		$this->assertEqualsCanonicalizing( $ids, array_map( 'intval', array_keys( $response['body'] ) ) );

		// The site holds the fixture, or the fixture after 7-facts.py: 6480 has no application before.
		$migrated = 'home' === $response['body']['6480']['application'];
		$products = LiveProducts::published( $migrated );
		foreach ( $ids as $id ) {
			$product = $products[ $id ];
			$this->mock_product( $id, $product['categories'], $product['attributes']['pa_application'] ?? array(), $product['attributes']['pa_phase'] ?? array(), $product['figures'] );
			// JSON has no float type: 10.0 arrives as 10, so the comparison is by value.
			$this->assertEquals( SelectionFacts::for_product( $id )->to_array(), $response['body'][ (string) $id ], (string) $id );
		}
	}

	/**
	 * Unpublished products and IDs that are not products are left out; an
	 * answer without products is an empty object.
	 */
	public function test_only_published_products_are_answered(): void {
		$response = $this->get( array( self::DRAFT, 3555, 999999999 ) );
		$this->assertSame( 200, $response['status'] );
		$this->assertSame( array( '3555' ), array_map( 'strval', array_keys( (array) $response['body'] ) ) );

		$response = $this->get( array( self::DRAFT ) );
		$this->assertSame( 200, $response['status'] );
		$this->assertSame( '{}', $response['raw'] );
	}

	/**
	 * 100 IDs are answered; 101 are a 400 before any product is read.
	 */
	public function test_at_most_100_ids(): void {
		$this->assertSame( 200, $this->get( range( 1, 100 ) )['status'] );

		$response = $this->get( range( 1, 101 ) );
		$this->assertSame( 400, $response['status'] );
		$this->assertSame( 'rest_invalid_param', $response['body']['code'] );
		$this->assertSame( 'rest_too_many_items', $response['body']['data']['details']['ids']['code'] );
	}

	/**
	 * The ids parameter is required and holds positive integers.
	 *
	 * @testWith [""]
	 *           ["ids=abc"]
	 *           ["ids=0"]
	 *           ["ids=-5"]
	 *
	 * @param string $query Query string.
	 */
	public function test_bad_ids_are_a_400( string $query ): void {
		$response = self::request( 'GET', $this->site . '/wp-json/linker/v1/selection-facts?' . $query );

		$this->assertSame( 400, $response['status'] );
		$this->assertContains( $response['body']['code'], array( 'rest_missing_callback_param', 'rest_invalid_param' ) );
	}

	/**
	 * OPTIONS shows the schema the three consumers share.
	 */
	public function test_options_shows_the_schema(): void {
		WP_Mock::passthruFunction( '__' );
		$response = self::request( 'OPTIONS', $this->site . '/wp-json/linker/v1/selection-facts' );

		$this->assertSame( 200, $response['status'] );
		$schema = $response['body']['schema'];
		$this->assertSame( 'selection-facts', $schema['title'] );
		$this->assertSame( SelectionFactSet::schema()['required'], $schema['additionalProperties']['required'] );
		$this->assertSame( array_keys( SelectionFactSet::schema()['properties'] ), array_keys( $schema['additionalProperties']['properties'] ) );
	}

	/**
	 * GET of the route for the given IDs.
	 *
	 * @param int[] $ids Product IDs.
	 * @return array{status: int, headers: array<string, string>, raw: string, body: mixed}
	 */
	private function get( array $ids ): array {
		return self::request( 'GET', $this->site . '/wp-json/linker/v1/selection-facts?ids=' . implode( ',', $ids ) );
	}

	/**
	 * One anonymous HTTP request; status 0 when nothing answers.
	 *
	 * @param non-empty-string $method HTTP method.
	 * @param string           $url    URL.
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
