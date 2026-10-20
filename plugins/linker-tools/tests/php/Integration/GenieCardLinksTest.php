<?php
/**
 * Genie cards link to the product page of the same language.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

// phpcs:disable WordPress.WP.AlternativeFunctions -- these tests run outside WordPress: HTTP through PHP itself.

/**
 * Four accounts — approved, pending, restricted, and a guest — read the Store
 * API the way a Genie card does (`include` of the English ids, `lang` of the
 * turn). The permalink is that language's product page: English `/product/…`,
 * German `/de/produkt/…`. Each page answers 200 in that language
 * (`html lang`). Registered for #339 as s1-card-permalink-locale (#413).
 *
 * The products are the live snapshot's (SAJ H2-10K-T3, 4107; GoodWe
 * GW208.9-BAT-LCD-G10, 1957). The accounts are made for the test and removed
 * again.
 *
 *     LINKER_TOOLS_SITE=http://127.0.0.1:9108 LINKER_TOOLS_WP=<wp wrapper> \
 *     vendor/bin/phpunit --testsuite integration --filter GenieCardLinksTest
 *
 * CI runs `just test`, the unit suite (`phpunit.xml.dist` defaultTestSuite).
 * This class is the integration suite. Without LINKER_TOOLS_SITE it skips in
 * SiteTestCase, the same precedent as the other live-snapshot integration
 * tests — the suite note in phpunit.xml.dist. That skip is expected in CI;
 * this file is not a unit test the check job runs.
 *
 * @coversNothing
 */
final class GenieCardLinksTest extends SiteTestCase {

	/**
	 * The SAJ H2-10K-T3 of the live snapshot.
	 */
	private const PRICED = 4107;

	/**
	 * The GoodWe GW208.9-BAT-LCD-G10 of the live snapshot.
	 */
	private const PROJECT = 1957;

	/**
	 * The test accounts by approval state.
	 *
	 * @var array<string, int>
	 */
	private static array $users = array();

	/**
	 * Makes one customer per approval state.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		if ( '' === self::$site ) {
			return;
		}
		foreach ( array( 'approved', 'pending', 'restricted' ) as $state ) {
			// 3 bytes is 6 hex characters: a rerun does not reuse a leftover login.
			$login                 = 'genie-links-' . $state . '-' . bin2hex( random_bytes( 3 ) );
			$id                    = (int) trim(
				self::wp(
					array(
						'eval',
						sprintf(
							'$id = wp_insert_user( array( "user_login" => "%1$s", "user_email" => "%1$s@example.test", "user_pass" => wp_generate_password(), "role" => "customer" ) ); update_user_meta( $id, "linker_approval_status", "%2$s" ); echo $id;',
							$login,
							$state
						),
					)
				)
			);
			self::$users[ $state ] = $id;
		}
	}

	/**
	 * Removes the test customers.
	 */
	public static function tearDownAfterClass(): void {
		if ( array() !== self::$users ) {
			self::wp( array_merge( array( 'user', 'delete' ), array_map( 'strval', array_values( self::$users ) ), array( '--yes' ) ) );
		}
		self::$users = array();
		parent::tearDownAfterClass();
	}

	/**
	 * The card's link is the product page in the card's language.
	 *
	 * @testWith ["approved", "en"]
	 *           ["approved", "de"]
	 *           ["pending", "en"]
	 *           ["pending", "de"]
	 *           ["restricted", "en"]
	 *           ["restricted", "de"]
	 *           ["guest", "en"]
	 *           ["guest", "de"]
	 *
	 * @param string $state Approval state, or "guest".
	 * @param string $lang  The card's language.
	 */
	public function test_the_card_links_to_the_product_page_in_its_language( string $state, string $lang ): void {
		$products = $this->store_products( $state, $lang );
		$by_id    = array();
		foreach ( $products as $product ) {
			$by_id[ (int) $product['id'] ] = $product;
		}
		$this->assertEqualsCanonicalizing(
			array( self::PRICED, self::PROJECT ),
			array_map( 'intval', array_keys( $by_id ) )
		);

		foreach ( array( self::PRICED, self::PROJECT ) as $id ) {
			$permalink = (string) $by_id[ $id ]['permalink'];
			$path      = self::path( $permalink );
			if ( 'de' === $lang ) {
				$this->assertMatchesRegularExpression( '#/de/produkt/[^/]+/$#', $path, $state . ' ' . $id );
			} else {
				$this->assertMatchesRegularExpression( '#/product/[^/]+/$#', $path, $state . ' ' . $id );
				$this->assertStringNotContainsString( '/de/', $path, $state . ' ' . $id );
			}
			$page = $this->fetch( $path, $state );
			$this->assertSame( 200, $page['status'], $permalink );
			$matched = preg_match( '/<html[^>]*\blang="([^"]+)"/', $page['body'], $lang_attr );
			$this->assertSame( 1, $matched, 'no html lang on ' . $path );
			$this->assertSame( 'de' === $lang ? 'de-DE' : 'en-US', $lang_attr[1], $path );
		}

		if ( 'guest' === $state && 'de' === $lang ) {
			$this->assertStringContainsString( 'Preise nach Anmeldung', (string) $by_id[ self::PRICED ]['price_html'] );
			$this->assertStringContainsString( 'Angebot pro Projekt', (string) $by_id[ self::PROJECT ]['price_html'] );
		}
	}

	/**
	 * The Store API products a card asks for, as that account.
	 *
	 * @param string $state Approval state, or "guest".
	 * @param string $lang  Language.
	 * @return list<array<string, mixed>>
	 */
	private function store_products( string $state, string $lang ): array {
		$path = '/wp-json/wc/store/v1/products?include=' . self::PRICED . ',' . self::PROJECT . '&per_page=2&lang=' . $lang;
		$page = $this->fetch( $path, $state );
		$this->assertSame( 200, $page['status'], $page['body'] );
		$decoded = json_decode( $page['body'], true );
		$this->assertIsArray( $decoded );
		$products = array();
		foreach ( $decoded as $product ) {
			$this->assertIsArray( $product );
			$products[] = $product;
		}
		return $products;
	}

	/**
	 * A page of the site as the account sees it (its login cookie, or none).
	 *
	 * @param string $path  Path and query.
	 * @param string $state Approval state, or "guest".
	 * @return array{status: int, body: string}
	 */
	private function fetch( string $path, string $state ): array {
		$headers = "Accept: text/html, application/json\r\n";
		if ( 'guest' !== $state ) {
			// 600 seconds covers this test's requests; the account is deleted after.
			$cookie   = trim( self::wp( array( 'eval', sprintf( 'echo LOGGED_IN_COOKIE . "=" . rawurlencode( wp_generate_auth_cookie( %d, time() + 600, "logged_in" ) );', self::$users[ $state ] ) ) ) );
			$headers .= 'Cookie: ' . $cookie . "\r\n";
		}
		$context = stream_context_create(
			array(
				'http' => array(
					'header'        => $headers,
					'ignore_errors' => true,
					// Same read budget as SiteTestCase::get().
					'timeout'       => 120,
				),
			)
		);
		$body    = file_get_contents( self::$site . $path, false, $context );
		$status  = 0;
		foreach ( $http_response_header as $line ) {
			if ( 1 === preg_match( '#^HTTP/\S+ (\d{3})#', $line, $match ) ) {
				$status = (int) $match[1];
			}
		}
		return array(
			'status' => $status,
			'body'   => false === $body ? '' : $body,
		);
	}

	/**
	 * The path and query of a URL: the instance's own host may differ from the
	 * address the test reaches it at.
	 *
	 * @param string $url URL.
	 */
	private static function path( string $url ): string {
		$path  = (string) parse_url( $url, PHP_URL_PATH );
		$query = parse_url( $url, PHP_URL_QUERY );
		return $path . ( is_string( $query ) ? '?' . $query : '' );
	}
}
