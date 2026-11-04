<?php
/**
 * Opaque marketing recovery scope and native identity boundaries.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\EntryContext;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Scope response, the native identity comparison and the route's allowance.
 *
 * @covers \Linker\Tools\Genie\EntryContext
 * @covers \Linker\Tools\Genie\Conversations::entry_scope
 */
final class EntryContextTest extends TestCase {

	/**
	 * The database double behind the allowance, installed per test.
	 *
	 * @var ClaimOptionsDouble
	 */
	private ClaimOptionsDouble $db;

	/**
	 * An address to limit by, and a database behind the allowance.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->db               = new ClaimOptionsDouble();
		$_SERVER['REMOTE_ADDR'] = '203.0.113.7';
		// phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the double stands in for the limiter's statements.
		$GLOBALS['wpdb'] = $this->db;
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return_arg' => 0 ) );
		// A browser cookie makes entry_scope() try to close this tab's claim;
		// with no row stored that is a quiet no-op, whichever mocks an earlier
		// test has already defined process-wide.
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => false ) );
		WP_Mock::userFunction( 'delete_option', array( 'return' => true ) );
		// Same-origin admission: the site, and a URL parser behind it.
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://de-linker.test' ) );
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static fn( string $url ): array|false => self::url_pieces( $url ),
			)
		);
	}

	/**
	 * Removes the database double and the address.
	 */
	public function tearDown(): void {
		parent::tearDown();
		unset( $GLOBALS['wpdb'], $_SERVER['REMOTE_ADDR'] );
	}

	/**
	 * A cross-site refusal is translated: the failure copy's __() needs a
	 * handler in this suite too.
	 */
	private function allow_translation(): void {
		WP_Mock::userFunction(
			'__',
			array(
				'return' => static fn( string $text ): string => $text,
			)
		);
	}

	/**
	 * A same-origin POST of this site, as the browser client sends it.
	 *
	 * @param array<string, string> $headers Added request headers.
	 */
	private function request( array $headers = array() ): WP_REST_Request {
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/entry-context' );
		$request->set_param( 'tab', '6aebdb40-58dc-4831-a9e5-f43c0260a281' );
		$request->set_header( 'origin', 'https://de-linker.test' );
		foreach ( $headers as $name => $value ) {
			$request->set_header( $name, $value );
		}
		return $request;
	}

	/**
	 * The route with its allowance's UPDATE answers queued in order: every 1
	 * grants a take, every 0 refuses one (RateLimit's check-and-increment).
	 *
	 * @param array<int, int> $update_answers In-order results of the limiter's UPDATE.
	 */
	private function entry( array $update_answers = array( 1, 1 ) ): EntryContext {
		$this->db->update_answers = $update_answers;
		return new EntryContext();
	}

	/** Actual server identity and browser changes cannot share a recovery scope. */
	public function test_scope_changes_with_guest_browser_user_and_auth_session(): void {
		$user  = 0;
		$token = '';
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'return' => static function () use ( &$user ): int {
					return $user;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_get_session_token',
			array(
				'return' => static function () use ( &$token ): string {
					return $token;
				},
			)
		);
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-only-site-secret' ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
		$store                                    = new class() extends Conversations {
			/** Existing retention owner is irrelevant to comparison tests. */
			protected function cookie_expire(): int {
				return 1234567890; }
		};
		$tab                                      = '6aebdb40-58dc-4831-a9e5-f43c0260a281';
		$_COOKIE[ Conversations::BROWSER_COOKIE ] = str_repeat( 'a', 32 );
		$guest                                    = $store->entry_scope( $tab );
		$this->assertSame( $guest, $store->entry_scope( $tab ) );
		$this->assertMatchesRegularExpression( '/^[a-f0-9]{64}$/', $guest );
		$_COOKIE[ Conversations::BROWSER_COOKIE ] = str_repeat( 'b', 32 );
		$this->assertNotSame( $guest, $store->entry_scope( $tab ) );
		$user  = 17;
		$token = 'native-auth-session-one';
		$login = $store->entry_scope( $tab );
		$this->assertNotSame( $guest, $login );
		$token = 'native-auth-session-two';
		$this->assertNotSame( $login, $store->entry_scope( $tab ) );
		$user = 18;
		$this->assertNotSame( $login, $store->entry_scope( $tab ) );
		$user  = 0;
		$token = '';
		$this->assertNotSame( $login, $store->entry_scope( $tab ) );
		unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
	}

	/** The public response contains only a comparison value and cannot be shared. */
	public function test_context_response_is_private_and_has_no_identity_fields(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 17 ) );
		WP_Mock::userFunction( 'wp_get_session_token', array( 'return' => 'private-auth-token' ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'private-site-salt' ) );
		$response = $this->entry()->read( $this->request() );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( array( 'scope' ), array_keys( $response->get_data() ) );
		$this->assertSame( 'private, no-store', $response->get_headers()['Cache-Control'] );
		$this->assertSame( 'Cookie', $response->get_headers()['Vary'] );
		$this->assertStringNotContainsString( 'private-auth-token', $response->get_data()['scope'] );
	}

	/**
	 * The connection's hourly allowance spent: a plain 429, and no identity
	 * is resolved for a refused read (get_current_user_id is not mocked, so
	 * reaching the scope would fail this test by itself).
	 */
	public function test_a_spent_connection_allowance_is_a_429(): void {
		$refusal = $this->entry( array( 0 ) )->read( $this->request() );

		$this->assertInstanceOf( WP_Error::class, $refusal );
		$this->assertSame( 'linker_entry_context_quota', $refusal->get_error_code() );
		$this->assertSame( 429, $refusal->get_error_data()['status'] );
	}

	/** The site-wide daily cap spent: the same plain 429. */
	public function test_a_spent_site_cap_is_the_same_429(): void {
		$refusal = $this->entry( array( 1, 0 ) )->read( $this->request() );

		$this->assertInstanceOf( WP_Error::class, $refusal );
		$this->assertSame( 'linker_entry_context_quota', $refusal->get_error_code() );
		$this->assertSame( 429, $refusal->get_error_data()['status'] );
	}

	/**
	 * A cross-site page's opaque no-cors POST is refused before anything it
	 * could burn: neither the caller's own allowance nor the site's day is
	 * spent on a request this site never asked for.
	 */
	public function test_a_cross_site_post_is_refused_without_spending_the_allowance(): void {
		$this->allow_translation();
		$refusal = $this->entry( array( 0, 0 ) )->read(
			$this->request( array( 'sec-fetch-site' => 'cross-site' ) )
		);

		$this->assertInstanceOf( WP_Error::class, $refusal );
		$this->assertSame( 'linker_planner_origin', $refusal->get_error_code() );
		$this->assertSame( 403, $refusal->get_error_data()['status'] );
		$this->assertSame( array(), $this->db->queries, 'A cross-site refusal touches no allowance row.' );
	}

	/**
	 * The URL pieces Origin compares, as wp_parse_url would answer them.
	 *
	 * @param string $url Parsed URL.
	 * @return array<string, mixed>|false The pieces, false when unparseable.
	 */
	private static function url_pieces( string $url ): array|false {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- the double stands in for wp_parse_url itself; this is the one parse.
		$parsed = \parse_url( $url );
		if ( false === $parsed ) {
			return false;
		}
		$out = array();
		foreach ( array( 'scheme', 'host', 'port', 'user', 'pass', 'path', 'query', 'fragment' ) as $key ) {
			if ( array_key_exists( $key, $parsed ) ) {
				$out[ $key ] = $parsed[ $key ];
			}
		}
		return $out;
	}
}
