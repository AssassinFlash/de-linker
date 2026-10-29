<?php
/**
 * Tests for the bot guard of Genie's two public forms.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\FormGuard;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The honeypot and the signed start time of "email me this conversation"
 * (#235) and "Let Linker contact me" (#243). The limits run against a real
 * database (RateLimitTest, GenieContactTest).
 *
 * @covers \Linker\Tools\Genie\FormGuard
 */
final class FormGuardTest extends TestCase {

	/**
	 * The site's salt for the signatures.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
	}

	/**
	 * A guard of one door.
	 *
	 * @param string $name The door.
	 */
	private static function guard( string $name = 'genie_contact' ): FormGuard {
		return new FormGuard( $name, 3, 20 );
	}

	/**
	 * A guest's fields from a stamp.
	 *
	 * @param array{started: string, nonce: string} $stamp The stamp.
	 * @param string                                $trap  The honeypot's value.
	 * @return array<string, string>
	 */
	private static function fields( array $stamp, string $trap = '' ): array {
		return array(
			'website'       => $trap,
			'started'       => $stamp['started'],
			'started_nonce' => $stamp['nonce'],
		);
	}

	/**
	 * A start time this door signed, old enough and young enough, passes.
	 */
	public function test_a_signed_start_time_inside_its_life_passes(): void {
		$guard = self::guard();
		$this->assertTrue( $guard->passes( self::fields( $guard->stamp( 1000 ) ), 1000 + FormGuard::MIN_SECONDS ) );
		$this->assertTrue( $guard->passes( self::fields( $guard->stamp( 1000 ) ), 1000 + FormGuard::STAMP_LIFETIME ) );
	}

	/**
	 * Sooner than the floor, or older than the stamp's life, fails.
	 */
	public function test_too_soon_or_too_old_fails(): void {
		$guard = self::guard();
		$this->assertFalse( $guard->passes( self::fields( $guard->stamp( 1000 ) ), 1000 + FormGuard::MIN_SECONDS - 1 ) );
		$this->assertFalse( $guard->passes( self::fields( $guard->stamp( 1000 ) ), 1000 + FormGuard::STAMP_LIFETIME + 1 ) );
	}

	/**
	 * A cached anonymous page may reuse one stamp for the public TTL.
	 *
	 * 21600 seconds is litespeed.conf.cache-ttl_pub. The stamp has no user id.
	 */
	public function test_public_page_ttl_does_not_invalidate_a_shared_stamp(): void {
		$guard = self::guard();
		$stamp = $guard->stamp( 1700000000 );
		$this->assertTrue( $guard->passes( self::fields( $stamp ), 1700000000 + 21600 ) );
		$this->assertTrue( ( new FormGuard( 'genie_contact', 3, 20 ) )->passes( self::fields( $stamp ), 1700000000 + 21600 ) );
		$tampered    = $stamp['nonce'];
		$tampered[0] = 'a' === $tampered[0] ? 'b' : 'a';
		$this->assertFalse(
			$guard->passes(
				array(
					'website'       => '',
					'started'       => $stamp['started'],
					'started_nonce' => $tampered,
				),
				1700000000 + 21600
			)
		);
	}

	/**
	 * A time moved back by the sender, a bare time or nothing fails.
	 *
	 * @testWith ["900", "keep"]
	 *           ["1000", "0000"]
	 *           ["", ""]
	 *           ["abc", "keep"]
	 *
	 * @param string $started The start time sent.
	 * @param string $nonce   The signature sent; `keep` keeps the real one of 1000.
	 */
	public function test_a_start_time_this_door_did_not_sign_fails( string $started, string $nonce ): void {
		$guard = self::guard();
		$real  = $guard->stamp( 1000 );
		$this->assertFalse(
			$guard->passes(
				array(
					'website'       => '',
					'started'       => $started,
					'started_nonce' => 'keep' === $nonce ? $real['nonce'] : $nonce,
				),
				5000
			)
		);
	}

	/**
	 * One door's stamp proves nothing at the other.
	 */
	public function test_a_stamp_of_one_door_fails_at_the_other(): void {
		$mail = self::guard( 'genie_mail' )->stamp( 1000 );
		$this->assertFalse( self::guard( 'genie_contact' )->passes( self::fields( $mail ), 2000 ) );
	}

	/**
	 * A filled honeypot is a bot, whatever else it sent.
	 */
	public function test_a_filled_honeypot_is_a_trap(): void {
		$guard  = self::guard();
		$fields = self::fields( $guard->stamp( 1000 ), 'https://spam.example' );
		$this->assertTrue( $guard->trapped( $fields ) );
		$this->assertFalse( $guard->passes( $fields, 2000 ) );
		$this->assertFalse( $guard->trapped( self::fields( $guard->stamp( 1000 ) ) ) );
	}
}
