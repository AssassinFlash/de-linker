<?php
/**
 * Genie's prices follow the account, on the real instance.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

// phpcs:disable WordPress.WP.AlternativeFunctions -- these tests run outside WordPress: HTTP through PHP itself.

/**
 * Four accounts — approved, pending, restricted, and a guest — ask the
 * product abilities the way Genie's service does: over HTTP, with the shell's
 * own customer token (UserContext) or none. Each reads what its own product
 * page shows: the approved account the page's price line, word for word and
 * in both languages; the others the page's sentence in place of a price
 * (#242, docs/specs/13-genie.md 目标 8). The accounts are made for the test and
 * removed again; the products are the live snapshot's (SAJ H2-10K-T3, 4107;
 * GoodWe GW208.9-BAT-LCD-G10, 1957, quoted per project).
 *
 * Run against an instance loaded with the snapshot:
 *
 *     LINKER_TOOLS_SITE=http://127.0.0.1:9108 LINKER_TOOLS_WP=<wp wrapper> \
 *     vendor/bin/phpunit --testsuite integration --filter GeniePricesTest
 *
 * @coversNothing
 */
final class GeniePricesTest extends SiteTestCase {

	/**
	 * The SAJ H2-10K-T3 of the live snapshot: priced, orderable.
	 */
	private const PRICED = 4107;

	/**
	 * The GoodWe GW208.9-BAT-LCD-G10 of the live snapshot: quoted per project.
	 */
	private const PROJECT = 1957;

	/**
	 * The sentence the card shows for each reason (linker-tools GenieCard),
	 * which must be the product page's own (linker-commerce ProductView).
	 */
	private const SENTENCES = array(
		'login'      => 'Net price after partner sign-in',
		'pending'    => 'Prices after approval',
		'restricted' => 'Not available for your account',
		'project'    => 'Quoted per project',
	);

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
		foreach ( array( 'approved', 'pending', 'restricted' ) as $state ) {
			$login                 = 'genie-prices-' . $state . '-' . bin2hex( random_bytes( 3 ) );
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
	 * Each account reads from the ability what its own product page shows.
	 *
	 * @testWith ["approved", "en"]
	 *           ["approved", "de"]
	 *           ["pending", "en"]
	 *           ["restricted", "de"]
	 *           ["guest", "en"]
	 *
	 * @param string $state Approval state, or "guest".
	 * @param string $lang  The turn's language.
	 */
	public function test_each_account_reads_what_its_product_page_shows( string $state, string $lang ): void {
		$commerce = $this->commerce( self::PRICED, $lang, $this->token( $state ) );
		$page     = $this->page_price( self::PRICED, $lang, $state );

		if ( 'approved' === $state ) {
			$this->assertTrue( $commerce['price_visible'] );
			$this->assertSame( $page, $commerce['price_text'] );
			$this->assertMatchesRegularExpression( 'de' === $lang ? '/^1\.680,00\x{a0}€$/u' : '/^€1,680\.00$/u', $page );
			return;
		}
		$this->assertFalse( $commerce['price_visible'] );
		$this->assertArrayNotHasKey( 'price', $commerce );
		$this->assertArrayNotHasKey( 'price_text', $commerce );
		$this->assertSame( 'guest' === $state ? 'login' : $state, $commerce['price_reason'] );
		// The English page's sentence; the German page says it in German.
		if ( 'en' === $lang ) {
			$this->assertSame( self::SENTENCES[ $commerce['price_reason'] ], $page );
		}
	}

	/**
	 * A product quoted per project shows its price to nobody, the approved
	 * account included, on the English page, on its German twin and in Genie.
	 */
	public function test_a_product_quoted_per_project_has_no_price_for_the_approved_account(): void {
		$commerce = $this->commerce( self::PROJECT, 'en', $this->token( 'approved' ) );

		$this->assertFalse( $commerce['price_visible'] );
		$this->assertSame( 'project', $commerce['price_reason'] );
		$this->assertSame( self::SENTENCES['project'], $this->page_price( self::PROJECT, 'en', 'approved' ) );
		$this->assertSame( 'Angebot pro Projekt', $this->page_price( self::PROJECT, 'de', 'approved' ) );
	}

	/**
	 * A token that is forged or expired answers as a guest.
	 */
	public function test_a_forged_or_expired_token_reads_as_a_guest(): void {
		$approved = self::$users['approved'];
		$forged   = $approved . '|' . ( time() + 60 ) . '|' . str_repeat( '0', 64 );
		$expired  = trim( self::wp( array( 'eval', sprintf( '$p = "%1$d|" . ( time() - 1 ); echo $p . "|" . hash_hmac( "sha256", Linker\Tools\Genie\UserContext::HEADER . $p, wp_salt( "auth" ) );', $approved ) ) ) );

		foreach ( array( $forged, $expired ) as $token ) {
			$commerce = $this->commerce( self::PRICED, 'en', $token );
			$this->assertFalse( $commerce['price_visible'] );
			$this->assertSame( 'login', $commerce['price_reason'] );
		}
	}

	/**
	 * The shell tells the service whether the account is approved by the
	 * site's own rule, not by being signed in.
	 */
	public function test_the_shell_reads_partner_from_the_price_rule(): void {
		foreach ( array(
			'approved'   => 'yes',
			'pending'    => 'no',
			'restricted' => 'no',
		) as $state => $partner ) {
			$said = trim( self::wp( array( 'eval', sprintf( 'wp_set_current_user( %d ); echo true === apply_filters( "linker_commerce_visitor_sees_prices", false ) ? "yes" : "no";', self::$users[ $state ] ) ) ) );
			$this->assertSame( $partner, $said, $state );
		}
		$this->assertSame( 'no', trim( self::wp( array( 'eval', 'wp_set_current_user( 0 ); echo true === apply_filters( "linker_commerce_visitor_sees_prices", false ) ? "yes" : "no";' ) ) ) );
	}

	/**
	 * The shell's customer token for a state, '' for the guest.
	 *
	 * @param string $state Approval state, or "guest".
	 */
	private function token( string $state ): string {
		if ( 'guest' === $state ) {
			return '';
		}
		return trim( self::wp( array( 'eval', sprintf( 'wp_set_current_user( %d ); echo ( new Linker\Tools\Genie\UserContext() )->mint();', self::$users[ $state ] ) ) ) );
	}

	/**
	 * The commerce object get-product answers, asked as the service asks it.
	 *
	 * @param int    $product Product.
	 * @param string $lang    Language.
	 * @param string $token   Customer token, '' for a guest.
	 * @return array<string, mixed>
	 */
	private function commerce( int $product, string $lang, string $token ): array {
		$headers = "Accept: application/json\r\n";
		if ( '' !== $token ) {
			$headers .= 'X-Linker-User-Context: ' . $token . "\r\n";
		}
		$context = stream_context_create(
			array(
				'http' => array(
					'header'        => $headers,
					'ignore_errors' => true,
					'timeout'       => 60,
				),
			)
		);
		$body    = file_get_contents( self::$site . '/wp-json/wp-abilities/v1/abilities/linker/get-product/run?input%5Bproduct_id%5D=' . $product . '&input%5Blang%5D=' . $lang, false, $context );
		$decoded = json_decode( (string) $body, true );
		$this->assertIsArray( $decoded, (string) $body );
		$this->assertIsArray( $decoded['commerce'] ?? null );
		return $decoded['commerce'];
	}

	/**
	 * The price line the product page shows the account, as text.
	 *
	 * @param int    $product Product (English).
	 * @param string $lang    Page language.
	 * @param string $state   Approval state, or "guest".
	 */
	private function page_price( int $product, string $lang, string $state ): string {
		$url     = trim( self::wp( array( 'eval', sprintf( 'echo get_permalink( "de" === "%2$s" ? pll_get_post( %1$d, "de" ) : %1$d );', $product, $lang ) ) ) );
		$headers = '';
		if ( 'guest' !== $state ) {
			$cookie   = trim( self::wp( array( 'eval', sprintf( 'echo LOGGED_IN_COOKIE . "=" . rawurlencode( wp_generate_auth_cookie( %d, time() + 600, "logged_in" ) );', self::$users[ $state ] ) ) ) );
			$headers .= 'Cookie: ' . $cookie . "\r\n";
		}
		$context = stream_context_create(
			array(
				'http' => array(
					'header'        => $headers,
					'ignore_errors' => true,
					'timeout'       => 120,
				),
			)
		);
		$html    = (string) file_get_contents( self::$site . self::path( $url ), false, $context );
		$this->assertSame( 1, preg_match( '#<div class="pdp-price">(.*?)</div>#s', $html, $match ), 'no price line on ' . $url );
		return trim( html_entity_decode( strip_tags( $match[1] ?? '' ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
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
