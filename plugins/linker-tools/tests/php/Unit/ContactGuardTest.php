<?php
/**
 * Tests for the contact card's public-form checks.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\ContactGuard;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The honeypot and the signed start time (the counters run against a real
 * database: linker-commerce's GenieContactTest).
 *
 * @covers \Linker\Tools\Genie\ContactGuard
 */
final class ContactGuardTest extends TestCase {

	/**
	 * The site's salt for the signatures.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
	}

	/**
	 * A start time this site signed, old enough, passes.
	 */
	public function test_a_signed_start_time_old_enough_passes(): void {
		$guard = new ContactGuard();
		$this->assertSame( '', $guard->screen( '', $guard->started( 1000 ), 1000 + ContactGuard::MIN_SECONDS ) );
	}

	/**
	 * Sooner than the floor is early.
	 */
	public function test_a_request_sooner_than_the_floor_is_early(): void {
		$guard = new ContactGuard();
		$this->assertSame( 'early', $guard->screen( '', $guard->started( 1000 ), 1000 + ContactGuard::MIN_SECONDS - 1 ) );
	}

	/**
	 * A time with another signature, a bare time or nothing is invalid.
	 *
	 * @testWith ["1000.0000"]
	 *           ["1000"]
	 *           [""]
	 *           ["abc.def"]
	 *
	 * @param string $started The start time sent.
	 */
	public function test_a_start_time_this_site_did_not_sign_is_invalid( string $started ): void {
		$this->assertSame( 'invalid', ( new ContactGuard() )->screen( '', $started, 5000 ) );
	}

	/**
	 * A start time moved back by the sender breaks its signature.
	 */
	public function test_moving_the_time_back_breaks_the_signature(): void {
		$guard  = new ContactGuard();
		$signed = $guard->started( 1000 );
		$moved  = '900' . substr( $signed, 4 );
		$this->assertSame( 'invalid', $guard->screen( '', $moved, 1001 ) );
	}

	/**
	 * A filled honeypot is a bot, whatever else it sent.
	 */
	public function test_a_filled_honeypot_is_a_trap(): void {
		$guard = new ContactGuard();
		$this->assertSame( 'trap', $guard->screen( 'https://spam.example', $guard->started( 1000 ), 2000 ) );
	}
}
