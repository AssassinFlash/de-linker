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
	 * The token signs a request in only on the routes WordPress parsed for the
	 * abilities it was issued for (inquiry-status, read-solution,
	 * search-products, get-product), and the user is signed out again after the
	 * answer.
	 *
	 * @testWith ["/wp-abilities/v1/abilities/linker/inquiry-status/run", 44]
	 *           ["/wp-abilities/v1/abilities/linker/read-solution/run", 44]
	 *           ["/wp-abilities/v1/abilities/linker/search-products/run", 44]
	 *           ["/wp-abilities/v1/abilities/linker/get-product/run", 44]
	 *           ["/wp-abilities/v1/abilities/linker/compare-products/run", 0]
	 *           ["/wp-abilities/v1/abilities/linker/handoff-team/run", 0]
	 *           ["/wp-abilities/v1/abilities", 0]
	 *           ["/linker/v1/engineering-feed", 0]
	 *           ["/linker-ai/v1/genie/turn", 0]
	 *
	 * @param string $route The route WordPress parsed.
	 * @param int    $user  The user the request runs as.
	 */
	public function test_the_token_works_only_on_the_abilities_it_was_issued_for( string $route, int $user ): void {
		$this->wp_functions();
		$signed  = $this->sign_in_recorder();
		$request = new \WP_REST_Request( 'GET', $route );
		$request->set_header( 'x_linker_user_context', $this->token( 44 ) );

		$context = new UserContext();
		$this->assertNull( $context->enter( null, null, $request ) );
		$this->assertSame( $user > 0 ? array( 44 ) : array(), $signed->users );

		$response = $context->leave( new \WP_REST_Response( array() ), null, $request );
		if ( $user > 0 ) {
			$this->assertSame( array( 44, 0 ), $signed->users, 'signed out after the answer' );
			$this->assertSame( 'no-store, private', $response->get_headers()['Cache-Control'] ?? null );
		} else {
			$this->assertSame( array(), $response->get_headers() );
		}
	}

	/**
	 * A query string that names an ability route does not move the request:
	 * the route is the one WordPress parsed, not text found in the address.
	 */
	public function test_a_forged_query_string_is_refused(): void {
		$this->wp_functions();
		$signed                 = $this->sign_in_recorder();
		$_SERVER['REQUEST_URI'] = '/wp-json/linker-ai/v1/genie/turn?x=/wp-abilities/v1/abilities/linker/get-product/run';
		$request                = new \WP_REST_Request( 'GET', '/linker-ai/v1/genie/turn' );
		$request->set_header( 'x_linker_user_context', $this->token( 44 ) );

		( new UserContext() )->enter( null, null, $request );

		$this->assertSame( array(), $signed->users );
	}

	/**
	 * Only a read (GET) is signed in; a session WordPress already established,
	 * a bad token and a missing header all leave the request as it is.
	 */
	public function test_other_requests_stay_as_they_are(): void {
		$this->wp_functions();
		$signed  = $this->sign_in_recorder();
		$route   = '/wp-abilities/v1/abilities/linker/get-product/run';
		$context = new UserContext();

		$post = new \WP_REST_Request( 'POST', $route );
		$post->set_header( 'x_linker_user_context', $this->token( 44 ) );
		$context->enter( null, null, $post );

		$forged = new \WP_REST_Request( 'GET', $route );
		$forged->set_header( 'x_linker_user_context', '44|9999999999|made-up' );
		$context->enter( null, null, $forged );

		$context->enter( null, null, new \WP_REST_Request( 'GET', $route ) );

		// A result another filter already decided is passed through untouched.
		$decided = new \WP_REST_Request( 'GET', $route );
		$decided->set_header( 'x_linker_user_context', $this->token( 44 ) );
		$this->assertSame( 'decided', $context->enter( 'decided', null, $decided ) );

		$this->assertSame( array(), $signed->users );
	}

	/**
	 * A visitor WordPress already signed in (the cookie) keeps that session.
	 */
	public function test_a_session_always_wins(): void {
		$this->wp_functions( true );
		$signed  = $this->sign_in_recorder();
		$request = new \WP_REST_Request( 'GET', '/wp-abilities/v1/abilities/linker/get-product/run' );
		$request->set_header( 'x_linker_user_context', $this->token( 44 ) );

		( new UserContext() )->enter( null, null, $request );

		$this->assertSame( array(), $signed->users );
	}

	/**
	 * A valid token for a user.
	 *
	 * @param int $user User.
	 */
	private function token( int $user ): string {
		$payload = $user . '|' . ( time() + 60 );
		return $payload . '|' . $this->signature( $payload );
	}

	/**
	 * Records wp_set_current_user() calls in `users`.
	 */
	private function sign_in_recorder(): \stdClass {
		$signed        = new \stdClass();
		$signed->users = array();
		WP_Mock::userFunction(
			'wp_set_current_user',
			array(
				'return' => static function ( int $user ) use ( $signed ) {
					$signed->users[] = $user;
					return null;
				},
			)
		);
		return $signed;
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
	 *
	 * @param bool $signed_in Whether WordPress already signed a visitor in.
	 */
	private function wp_functions( bool $signed_in = false ): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $signed_in ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction(
			'sanitize_text_field',
			array( 'return' => static fn( $value ) => trim( (string) $value ) )
		);
		WP_Mock::userFunction( 'add_filter', array( 'return' => true ) );
	}
}
