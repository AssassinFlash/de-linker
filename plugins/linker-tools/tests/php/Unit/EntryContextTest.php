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
use WP_REST_Request;

/**
 * Scope response and the native identity comparison.
 *
 * @covers \Linker\Tools\Genie\EntryContext
 * @covers \Linker\Tools\Genie\Conversations::entry_scope
 */
final class EntryContextTest extends TestCase {
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
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/entry-context' );
		$request->set_param( 'tab', '6aebdb40-58dc-4831-a9e5-f43c0260a281' );
		$response = ( new EntryContext() )->read( $request );
		$this->assertSame( array( 'scope' ), array_keys( $response->get_data() ) );
		$this->assertSame( 'private, no-store', $response->get_headers()['Cache-Control'] );
		$this->assertSame( 'Cookie', $response->get_headers()['Vary'] );
		$this->assertStringNotContainsString( 'private-auth-token', $response->get_data()['scope'] );
	}
}
