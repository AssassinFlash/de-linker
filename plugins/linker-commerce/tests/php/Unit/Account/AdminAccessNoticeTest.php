<?php
/**
 * The admin explanation's public hook, destination and scalar field boundaries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\AdminAccessNotice;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Session_Tokens;

/**
 * WordPress owns the session; only Woo's recorded decision selects the notice.
 *
 * @covers \Linker\Commerce\Account\AdminAccessNotice
 */
final class AdminAccessNoticeTest extends TestCase {

	/** Deliberately differs from Polylang's default to verify its configuration. */
	private const COOKIE_NAME = 'notice-language-cookie';

	/** Original query.
	 *
	 * @var array<string, mixed>
	 */
	private array $query;

	/** Original cookies.
	 *
	 * @var array<string, mixed>
	 */
	private array $cookies;

	/** Fixture session token returned by the WordPress boundary.
	 *
	 * @var string
	 */
	private string $token = 'notice-session';

	/** Loads the real language helper; Polylang and WordPress stay boundaries. */
	public static function setUpBeforeClass(): void {
		require_once dirname( __DIR__, 5 ) . '/linker-i18n/includes/Languages.php';
		if ( ! defined( 'PLL_COOKIE' ) ) {
			define( 'PLL_COOKIE', self::COOKIE_NAME ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Polylang's configurable cookie constant.
		}
	}

	/** Saves request globals and seeds a native session fixture. */
	public function setUp(): void {
		parent::setUp();
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Save and restore the unit fixture query, not form processing.
		$this->query   = $_GET;
		$this->cookies = $_COOKIE;
		$_GET          = array( 'admin-access' => 'staff' );
		$_COOKIE       = array();
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 42 ) );
		WP_Mock::userFunction( 'wp_get_session_token', array( 'return' => fn (): string => $this->token ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Session_Tokens::get_instance( 42 )->update(
			$this->token,
			array(
				'expiration' => PHP_INT_MAX,
				'ip'         => '127.0.0.1',
			)
		);
	}

	/** Restores globals and removes only this test's sessions. */
	public function tearDown(): void {
		$_GET    = $this->query;
		$_COOKIE = $this->cookies;
		foreach ( array( 'notice-session', 'other-session' ) as $token ) {
			WP_Session_Tokens::get_instance( 42 )->destroy( $token );
		}
		parent::tearDown();
	}

	/** A marker by itself is not evidence that Woo denied this session. */
	public function test_a_query_marker_without_a_woo_decision_does_not_select_the_notice(): void {
		$this->assertFalse( AdminAccessNotice::requested() );
	}
	/** Woo's denial survives the redirect as the same session's decision. */
	public function test_a_woo_denial_selects_the_explanation_on_the_next_request(): void {
		$notice = new AdminAccessNotice();
		WP_Mock::expectFilterAdded( 'wp_redirect', array( $notice, 'destination' ) );
		$this->assertTrue( $notice->protect( true ) );
		$this->assertTrue( AdminAccessNotice::requested() );
		$session = WP_Session_Tokens::get_instance( 42 )->get( $this->token );
		$this->assertIsArray( $session );
		$this->assertArrayHasKey( 'ip', $session );
		$this->assertSame( '127.0.0.1', $session['ip'] );
		$this->assertSame( PHP_INT_MAX, $session['expiration'] ?? null );
	}

	/** A later Woo allow decision replaces the old denial without a role rule. */
	public function test_a_woo_allow_decision_clears_the_recorded_denial(): void {
		$notice = new AdminAccessNotice();
		WP_Mock::expectFilterAdded( 'wp_redirect', array( $notice, 'destination' ) );
		$notice->protect( true );
		$this->assertFalse( $notice->protect( false ) );
		$this->assertFalse( AdminAccessNotice::requested() );
	}

	/** Another session of the same customer does not inherit the denial. */
	public function test_the_decision_is_scoped_to_the_current_wordpress_session(): void {
		$notice = new AdminAccessNotice();
		WP_Mock::expectFilterAdded( 'wp_redirect', array( $notice, 'destination' ) );
		$notice->protect( true );
		$this->token = 'other-session';
		$this->assertFalse( AdminAccessNotice::requested() );
	}

	/** The configured Polylang cookie chooses its German page, not a literal cookie name. */
	public function test_destination_uses_the_configured_polylang_cookie_and_german_twin(): void {
		$_COOKIE[ self::COOKIE_NAME ] = 'de';
		$_COOKIE['pll_language']      = 'en';
		$this->destination_fixture( 20 );
		$this->assertSame( 'https://example.test/de/mein-konto/?admin-access=staff', ( new AdminAccessNotice() )->destination( 'https://example.test/my-account/' ) );
	}

	/**
	 * Cookie validation and missing twins retain a usable native destination.
	 *
	 * @dataProvider destination_cases
	 * @param mixed  $cookie Language cookie, null when absent.
	 * @param int    $twin Polylang's German twin id, zero when missing.
	 * @param bool   $exists Whether the twin post still exists.
	 * @param string $expected Expected account URL.
	 */
	public function test_destination_language_and_twin_fallbacks( $cookie, int $twin, bool $exists, string $expected ): void {
		if ( null !== $cookie ) {
			$_COOKIE[ self::COOKIE_NAME ] = $cookie;
		}
		$this->destination_fixture( $twin, $exists );
		$this->assertSame( $expected, ( new AdminAccessNotice() )->destination( 'https://example.test/native-account/' ) );
	}

	/**
	 * Literal language and twin fallbacks from the account URL contract.
	 *
	 * @return array<string, array{mixed, int, bool, string}>
	 */
	public static function destination_cases(): array {
		return array(
			'English preference'   => array( 'en', 20, true, 'https://example.test/my-account/?admin-access=staff' ),
			'German preference'    => array( 'de', 20, true, 'https://example.test/de/mein-konto/?admin-access=staff' ),
			'absent cookie'        => array( null, 20, true, 'https://example.test/my-account/?admin-access=staff' ),
			'unsupported language' => array( 'xx', 20, true, 'https://example.test/my-account/?admin-access=staff' ),
			'array cookie'         => array( array( 'de' ), 20, true, 'https://example.test/my-account/?admin-access=staff' ),
			'missing German twin'  => array( 'de', 0, false, 'https://example.test/my-account/?admin-access=staff' ),
			'deleted German twin'  => array( 'de', 20, false, 'https://example.test/my-account/?admin-access=staff' ),
		);
	}

	/** If even the account permalink is unavailable, keep Woo's own destination. */
	public function test_destination_keeps_the_native_url_when_the_account_has_no_permalink(): void {
		$this->destination_fixture( 0, false, false );
		$this->assertSame( 'https://example.test/native-account/?admin-access=staff', ( new AdminAccessNotice() )->destination( 'https://example.test/native-account/' ) );
	}

	/** The complete LC field map uses the session's customer and native URLs. */
	public function test_the_field_map_supplies_reviewed_text_escaped_identity_and_native_action_urls(): void {
		foreach ( array( '__', 'esc_html__', 'esc_url' ) as $function ) {
			WP_Mock::passthruFunction( $function );
		}
		$notice = new AdminAccessNotice();
		WP_Mock::expectFilterAdded( 'wp_redirect', array( $notice, 'destination' ) );
		$notice->protect( true );
		$user             = new \WP_User();
		$user->user_email = 'customer+<tag>@example.test';
		WP_Mock::userFunction( 'wp_get_current_user', array( 'return' => $user ) );
		WP_Mock::userFunction( 'esc_html', array( 'return' => static fn ( string $text ): string => htmlspecialchars( $text, ENT_QUOTES, 'UTF-8' ) ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'https://example.test/wp-admin/' ) );
		WP_Mock::userFunction(
			'wp_login_url',
			array(
				'args'   => array( 'https://example.test/wp-admin/' ),
				'return' => 'https://example.test/wp-login.php?redirect_to=admin',
			)
		);
		WP_Mock::userFunction(
			'wp_logout_url',
			array(
				'args'   => array( 'https://example.test/wp-login.php?redirect_to=admin' ),
				'return' => 'https://example.test/wp-login.php?action=logout&signed=fixture',
			)
		);
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'args'   => array( 'myaccount' ),
				'return' => 'https://example.test/my-account/',
			)
		);
		foreach ( array(
			'title'         => 'Linker staff only',
			'identity'      => 'You are signed in as customer+&lt;tag&gt;@example.test (customer account).',
			'explanation'   => 'The admin area is for Linker staff only.',
			'staff-label'   => 'Sign out and sign in as staff',
			'account-label' => 'Go to my account',
			'staff-url'     => 'https://example.test/wp-login.php?action=logout&signed=fixture',
			'account-url'   => 'https://example.test/my-account/',
			'unknown'       => '',
		) as $key => $expected ) {
			$this->assertSame( $expected, $notice->field( array( 'key' => $key ) ), $key );
		}
	}

	/** A read-only marker never exposes identity or actions without Woo's denial. */
	public function test_fields_are_empty_without_a_recorded_denial(): void {
		$this->assertSame( '', ( new AdminAccessNotice() )->field( array( 'key' => 'identity' ) ) );
	}

	/** WordPress/Polylang URL boundaries around the real Languages helper.
	 *
	 * @param int  $translation Translation id returned by Polylang.
	 * @param bool $exists Whether the translated post exists.
	 * @param bool $permalink Whether the account has a permalink.
	 */
	private function destination_fixture( int $translation, bool $exists = true, bool $permalink = true ): void {
		WP_Mock::userFunction( 'remove_filter' );
		$this->options( array( 'woocommerce_myaccount_page_id' => 10 ) );
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $value ): string => strtolower( (string) preg_replace( '/[^a-zA-Z0-9_-]/', '', $value ) ) ) );
		WP_Mock::userFunction( 'pll_languages_list', array( 'return' => array( 'en', 'de' ) ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn ( int $id, string $language ): int => 'de' === $language ? $translation : 10 ) );
		WP_Mock::userFunction( 'get_post', array( 'return' => $exists ? new \WP_Post( (object) array( 'ID' => 20 ) ) : null ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => static fn ( int $id ) => $permalink ? ( 20 === $id ? 'https://example.test/de/mein-konto/' : 'https://example.test/my-account/' ) : false ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( string $key, string $value, string $url ): string => $url . '?' . $key . '=' . $value ) );
	}
}
