<?php
/**
 * The short-lived identity token the service may present on ability calls.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\UserContext;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for UserContext.
 *
 * @covers \Linker\Tools\Genie\UserContext
 */
final class UserContextTest extends TestCase {

	/**
	 * The request's server variables, restored after each test.
	 *
	 * @var array<string, mixed>
	 */
	private array $server = array();

	/**
	 * Remembers $_SERVER for the test.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->server = $_SERVER;
	}

	/**
	 * Puts $_SERVER back.
	 */
	public function tearDown(): void {
		$_SERVER = $this->server;
		parent::tearDown();
	}

	/**
	 * A guest gets no token, and knowing that must not cost a salt lookup.
	 */
	public function test_a_guest_gets_no_token(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );

		$this->assertSame( '', ( new UserContext() )->mint() );
		$this->assertConditionsMet();
	}

	/**
	 * A token names its user, and only until it expires.
	 */
	public function test_a_minted_token_names_its_user(): void {
		$this->wp_functions();
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 44 ) );

		$context = new UserContext();
		$token   = $context->mint();

		$this->assertSame( 44, $context->user_id( $token ) );
		$this->assertConditionsMet();
	}

	/**
	 * A tampered payload, a wrong signature and an expired token are all nobody.
	 */
	public function test_a_tampered_or_expired_token_is_refused(): void {
		$this->wp_functions();

		$context = new UserContext();

		$this->assertSame( 0, $context->user_id( 'nonsense' ) );
		$this->assertSame( 0, $context->user_id( '44|9999999999|made-up' ) );
		$this->assertSame( 0, $context->user_id( '44|' . ( time() - 1 ) . '|' . $this->signature( '44|' . ( time() - 1 ) ) ) );
		// Another user's payload cannot be carried by this signature.
		$this->assertSame( 0, $context->user_id( '45|' . ( time() + 60 ) . '|' . $this->signature( '44|' . ( time() + 60 ) ) ) );
		$this->assertConditionsMet();
	}

	/**
	 * The header is only read on ability requests, and never over a session.
	 */
	public function test_determine_accepts_the_header_on_ability_requests_only(): void {
		$this->wp_functions();
		$token                                 = '44|' . ( time() + 60 ) . '|' . $this->signature( '44|' . ( time() + 60 ) );
		$_SERVER['HTTP_X_LINKER_USER_CONTEXT'] = $token;
		$context                               = new UserContext();

		$_SERVER['REQUEST_URI'] = '/wp-json/linker/v1/engineering-feed';
		$this->assertFalse( $context->determine( false ), 'a feed request stays anonymous' );

		$_SERVER['REQUEST_URI'] = '/wp-json/wp-abilities/v1/abilities/linker%2Finquiry-status/run';
		$this->assertSame( 44, $context->determine( false ) );

		// A session WordPress already established always wins.
		$this->assertSame( 7, $context->determine( 7 ) );

		// A bad token does not become a user.
		$_SERVER['HTTP_X_LINKER_USER_CONTEXT'] = '44|9999999999|made-up';
		$this->assertFalse( $context->determine( false ) );

		unset( $_SERVER['HTTP_X_LINKER_USER_CONTEXT'] );
		$this->assertFalse( $context->determine( false ), 'no header, no user' );
		$this->assertConditionsMet();
	}

	/**
	 * The site's auth salt signs the token.
	 *
	 * @param string $payload `user|expiry`.
	 */
	private function signature( string $payload ): string {
		return hash_hmac( 'sha256', UserContext::HEADER . $payload, 'test-salt' );
	}

	/**
	 * The WordPress functions these paths need.
	 */
	private function wp_functions(): void {
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction(
			'sanitize_text_field',
			array( 'return' => static fn( $value ) => trim( (string) $value ) )
		);
		WP_Mock::userFunction( 'add_filter', array( 'return' => true ) );
	}
}
