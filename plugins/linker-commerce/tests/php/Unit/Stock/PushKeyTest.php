<?php
/**
 * Tests for the stock push key.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Stock;

use Linker\Commerce\Stock\PushKey;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Tests for PushKey.
 *
 * @covers \Linker\Commerce\Stock\PushKey
 */
final class PushKeyTest extends TestCase {

	/**
	 * Without a stored hash nothing verifies and nothing is set.
	 */
	public function test_without_a_key_everything_is_rejected(): void {
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( PushKey::OPTION, '' ),
				'return' => '',
			)
		);

		$this->assertFalse( PushKey::is_set() );
		$this->assertFalse( PushKey::verify( 'anything' ) );
		$this->assertFalse( PushKey::verify( '' ) );
		$this->assertSame( '', PushKey::fingerprint() );
	}

	/**
	 * A stored hash verifies only its own key, in constant time on the hashes.
	 */
	public function test_verify_accepts_only_the_stored_key(): void {
		$key = 'erp-push-key-2026';
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( PushKey::OPTION, '' ),
				'return' => hash( 'sha256', $key ),
			)
		);

		$this->assertTrue( PushKey::is_set() );
		$this->assertTrue( PushKey::verify( $key ) );
		$this->assertFalse( PushKey::verify( 'erp-push-key-2027' ) );
		$this->assertFalse( PushKey::verify( '' ) );
		$this->assertSame( substr( hash( 'sha256', $key ), 0, 12 ), PushKey::fingerprint() );
	}

	/**
	 * Only the hash is stored, not the key; clearing removes the option.
	 */
	public function test_set_stores_the_hash_and_clear_removes_it(): void {
		$stored = '';
		WP_Mock::userFunction(
			'update_option',
			array(
				'times'  => 1,
				'args'   => array(
					PushKey::OPTION,
					Mockery::on(
						static function ( $value ) use ( &$stored ): bool {
							$stored = (string) $value;
							return is_string( $value ) && 64 === strlen( $value );
						}
					),
					false,
				),
				'return' => true,
			)
		);
		$hash = PushKey::set( 'the-key' );
		$this->assertSame( hash( 'sha256', 'the-key' ), $hash );
		$this->assertSame( $hash, $stored );
		$this->assertStringNotContainsString( 'the-key', $stored );

		WP_Mock::userFunction(
			'delete_option',
			array(
				'times'  => 1,
				'args'   => array( PushKey::OPTION ),
				'return' => true,
			)
		);
		PushKey::clear();
		$this->assertConditionsMet();
	}

	/**
	 * A generated key is 64 lowercase hex characters, and every one differs.
	 */
	public function test_generated_keys_are_hex_and_distinct(): void {
		$first = PushKey::generate();
		$this->assertSame( 64, strlen( $first ) );
		$this->assertMatchesRegularExpression( '/^[0-9a-f]{64}$/', $first );
		$this->assertNotSame( $first, PushKey::generate() );
	}
}
