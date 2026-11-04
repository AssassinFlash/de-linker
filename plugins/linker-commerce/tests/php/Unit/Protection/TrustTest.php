<?php
/**
 * Tests for the session-bound genie challenge trust.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Trust;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The trust window, its row shape and its write-path purge (WP_Mock).
 *
 * @covers \Linker\Commerce\Protection\Trust
 */
final class TrustTest extends TestCase {

	/**
	 * The fixed server clock, moved by each test.
	 *
	 * @var int
	 */
	private int $now = 1799000000;

	/**
	 * The options the row reads and writes go through.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array();

	/**
	 * An in-memory WordPress: options, cache, and the grant's SQL.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->options = array();
		// phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the double stands in for the options table.
		$GLOBALS['wpdb']       = new TrustDatabaseDouble();
		$GLOBALS['wpdb']->rows = &$this->options;
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'trust-test-salt' ) );
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => function ( string $name, mixed $fallback = false ): mixed {
					return array_key_exists( $name, $this->options ) ? $this->options[ $name ] : $fallback;
				},
			)
		);
		WP_Mock::userFunction(
			'delete_option',
			array(
				'return' => function ( string $name ): bool {
					unset( $this->options[ $name ] );
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction(
			'maybe_serialize',
			array(
				'return' => static fn( mixed $value ): string => is_array( $value ) ? serialize( $value ) : (string) $value, // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.serialize_serialize -- the double mirrors wpdb's serialization of option values, never live data.
			)
		);
	}

	/**
	 * Removes the database double.
	 */
	public function tearDown(): void {
		parent::tearDown();
		unset( $GLOBALS['wpdb'] );
	}

	/**
	 * A guest identity bound to one fixed browser cookie hash.
	 */
	private function identity(): Identity {
		return new Identity( hash( 'sha256', 'trust-test-browser' ), '' );
	}

	/**
	 * The trust store on the test's fixed clock.
	 */
	private function trust(): Trust {
		$now = $this->now;
		return new Trust(
			static function () use ( $now ): int {
				return $now;
			}
		);
	}

	/**
	 * One solved challenge admits the genie turns of that identity only.
	 */
	public function test_a_solved_challenge_admits_one_identity_for_the_window(): void {
		$this->assertFalse( $this->trust()->admitted( 'genie', $this->identity() ) );

		$this->trust()->grant( 'genie', $this->identity() );

		$this->assertTrue( $this->trust()->admitted( 'genie', $this->identity() ) );
		$this->assertFalse( $this->trust()->admitted( 'genie', new Identity( hash( 'sha256', 'another-browser' ), '' ) ), 'Trust never crosses identities.' );
	}

	/**
	 * The window ends: a grant is not admitted after WINDOW seconds.
	 */
	public function test_the_window_expires(): void {
		$this->trust()->grant( 'genie', $this->identity() );
		$this->now += Trust::WINDOW;

		$this->assertFalse( $this->trust()->admitted( 'genie', $this->identity() ) );
	}

	/**
	 * A grant late in one bucket stays valid early in the next: the read
	 * checks the previous bucket's row too, and its expiry does the deciding.
	 */
	public function test_a_late_grant_crosses_the_bucket_boundary(): void {
		// One second before the bucket boundary inside the window.
		$this->now = ( intdiv( $this->now, Trust::WINDOW ) + 1 ) * Trust::WINDOW - 1;
		$this->trust()->grant( 'genie', $this->identity() );

		// Early in the next bucket the same row must still admit.
		$this->now += 2;
		$this->assertTrue( $this->trust()->admitted( 'genie', $this->identity() ) );

		// Past the window's own end it must not, even though the row exists.
		$this->now += Trust::WINDOW;
		$this->assertFalse( $this->trust()->admitted( 'genie', $this->identity() ) );
	}

	/**
	 * A fresh verification within the window starts the window again.
	 */
	public function test_a_renewed_grant_restarts_the_window(): void {
		$this->trust()->grant( 'genie', $this->identity() );
		$this->now += Trust::WINDOW - 10;
		$this->trust()->grant( 'genie', $this->identity() );

		$this->now += Trust::WINDOW - 20;
		$this->assertTrue( $this->trust()->admitted( 'genie', $this->identity() ) );
	}

	/**
	 * Revocation withdraws the trust at once.
	 */
	public function test_revocation_withdraws_the_trust(): void {
		$this->trust()->grant( 'genie', $this->identity() );
		$this->trust()->revoke( 'genie', $this->identity() );

		$this->assertFalse( $this->trust()->admitted( 'genie', $this->identity() ) );
	}

	/**
	 * Every grant drops rows two or more buckets old — expired by
	 * construction — and never the still-valid previous bucket.
	 */
	public function test_each_grant_purges_only_expired_buckets(): void {
		$this->trust()->grant( 'genie', $this->identity() );

		$purge = $GLOBALS['wpdb']->queries[0];
		$this->assertStringContainsString( 'DELETE FROM wp_options', $purge );
		$this->assertStringContainsString( 'linker\_commerce\_trust\_genie.%', $purge, 'The purge is scoped by esc_like to this action.' );
		$this->assertStringContainsString( str_pad( (string) ( intdiv( $this->now, Trust::WINDOW ) - 1 ), 10, '0', STR_PAD_LEFT ), $purge, 'Only rows older than the previous bucket go.' );
		$this->assertStringContainsString( 'INSERT IGNORE', $GLOBALS['wpdb']->queries[1] );
	}

	/**
	 * The row name carries the action and the identity binding's hash, never
	 * a raw credential.
	 */
	public function test_the_row_name_is_scoped_and_pseudonymous(): void {
		$this->trust()->grant( 'genie', $this->identity() );

		$insert = $GLOBALS['wpdb']->queries[1];
		$this->assertStringContainsString( 'linker_commerce_trust_genie.' . substr( md5( $this->identity()->binding() ), 0, 12 ) . '.', $insert );
		$this->assertStringNotContainsString( 'trust-test-browser', $insert );
	}
}
