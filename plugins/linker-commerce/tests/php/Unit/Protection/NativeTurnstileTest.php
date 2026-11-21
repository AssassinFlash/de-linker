<?php
/**
 * The native submit handler authenticates the visitor before requiring a token.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Protection\Turnstile;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The session and the native submission determine validation.
 *
 * @covers \Linker\Commerce\Protection\Turnstile
 */
final class NativeTurnstileTest extends TestCase {

	/** An approved or pending signed-in account needs no provider request. */
	public function test_signed_in_contact_needs_no_token(): void {
		WP_Mock::userFunction( 'is_user_logged_in' )->andReturn( true );
		$this->assertTrue( Turnstile::check( 'contact', array() ) );
	}

	/** The WordPress session, not a posted login flag, determines guest verification. */
	public function test_guest_with_no_response_is_refused_before_provider_dispatch(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_user_logged_in' )->andReturn( false );
		$result = Turnstile::check( 'inquiry', array( 'logged_in' => 'true' ) );
		$this->assertInstanceOf( \WP_Error::class, $result );
		$this->assertSame( 'linker_admission_proof', $result->get_error_code() );
	}
}
