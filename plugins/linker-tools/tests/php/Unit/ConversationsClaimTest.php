<?php
/**
 * Tests for the cold browser-key claim's deletion and publication.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Conversations;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The claim lifecycle: what a returning tab may delete, and which key a
 * concurrent mint leaves in the row (#906).
 *
 * @covers \Linker\Tools\Genie\Conversations
 */
final class ConversationsClaimTest extends TestCase {

	private const TAB   = '6aebdb40-58dc-4831-a9e5-f43c0260a281';
	public const MINTED = '0123456789abcdef0123456789abcdef';

	/**
	 * The database double, installed as the global in setUp().
	 *
	 * @var ClaimOptionsDouble
	 */
	private ClaimOptionsDouble $db;

	/**
	 * The claim option name of this test's tab.
	 *
	 * @var string
	 */
	private string $name = '';

	/**
	 * An in-memory options store behind the options API and the claim SQL.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->db   = new ClaimOptionsDouble();
		$this->name = Conversations::BROWSER_CLAIM_PREFIX . substr( hash( 'sha256', self::TAB ), 0, 32 );
		// phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the double stands in for the options table.
		$GLOBALS['wpdb'] = $this->db;
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'claim-test-salt' ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_ssl', array( 'return' => false ) );
		$db = $this->db;
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static fn( string $name, mixed $fallback = false ): mixed => $db->get( $name, $fallback ),
			)
		);
		WP_Mock::userFunction(
			'delete_option',
			array(
				'return' => static fn( string $name ): bool => $db->delete( $name ),
			)
		);
		WP_Mock::userFunction(
			'update_option',
			array(
				'return' => static function ( string $name, mixed $value ) use ( $db ): bool {
					$db->set( $name, $value );
					$db->updated[ $name ] = $value;
					return true;
				},
			)
		);
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
	 * A claim row exists and is expired: the tab returns with its browser
	 * cookie, and the row still goes. The former expiry short-circuit read
	 * the claim back as '' and returned, so a returning tab could only
	 * delete inside the claim window — human rhythm leaked every row (#906).
	 */
	public function test_a_returning_tab_deletes_its_expired_claim_row(): void {
		$this->db->set(
			$this->name,
			array(
				'key'   => str_repeat( 'a', 32 ),
				'until' => time() - 100,
			)
		);
		$_COOKIE                = array( Conversations::BROWSER_COOKIE => str_repeat( 'a', 32 ) );
		$this->db->lock_answers = array( '1' );

		$scope = $this->conversations()->entry_scope( self::TAB );

		$this->assertMatchesRegularExpression( '/^[a-f0-9]{64}$/', $scope );
		$this->assertFalse( $this->db->get( $this->name, false ), 'The expired claim row is gone.' );
		$this->assertConditionsMet();
	}

	/**
	 * No claim row: the returning tab locks nothing and deletes nothing.
	 */
	public function test_a_returning_tab_without_a_row_deletes_nothing(): void {
		$_COOKIE = array( Conversations::BROWSER_COOKIE => str_repeat( 'a', 32 ) );

		$this->conversations()->entry_scope( self::TAB );

		$this->assertSame( array(), $this->db->queries, 'Without a row there is no lock and no delete.' );
		$this->assertConditionsMet();
	}

	/**
	 * A concurrent loser's insert is ignored, not applied: the first writer
	 * keeps its key and the loser adopts it. add_option()'s ON DUPLICATE KEY
	 * UPDATE would have overwritten the winner (#906 §4.4).
	 */
	public function test_a_lost_concurrent_mint_adopts_the_first_writers_key(): void {
		$_COOKIE                               = array();
		$winner                                = str_repeat( 'a', 32 );
		$this->db->insert_answers              = array( 0 );
		$this->db->lock_answers                = array( '1' );
		$this->db->committed_on_ignored_insert = array(
			'key'   => $winner,
			'until' => time() + 3600,
		);
		WP_Mock::expectAction( 'linker_tools_set_genie_browser_cookie', $winner, 1000000, '/', '', false );

		$this->conversations()->entry_scope( self::TAB );

		$this->assertStringContainsString( 'INSERT IGNORE', $this->db->queries[0], 'Publication inserts ignoring a duplicate key.' );
		$this->assertStringNotContainsString( 'ON DUPLICATE', $this->db->queries[0], 'A losing insert never overwrites the winner.' );
		$this->assertArrayNotHasKey( $this->name, $this->db->updated, 'The winner was not rewritten.' );
		$this->assertConditionsMet();
	}

	/**
	 * The only row the read-back cannot serve is one already expired — never
	 * a live winner. That row is rewritten with this request's fresh claim.
	 */
	public function test_an_unreadable_loser_rewrites_only_an_unusable_row(): void {
		$_COOKIE                               = array();
		$this->db->insert_answers              = array( 0 );
		$this->db->lock_answers                = array( '1' );
		$this->db->committed_on_ignored_insert = array(
			'key'   => str_repeat( 'c', 32 ),
			'until' => time() - 1,
		);
		WP_Mock::expectAction( 'linker_tools_set_genie_browser_cookie', self::MINTED, 1000000, '/', '', false );

		$this->conversations()->entry_scope( self::TAB );

		$rewritten = $this->db->updated[ $this->name ] ?? null;
		$this->assertIsArray( $rewritten, 'The unusable row was rewritten.' );
		$this->assertSame( self::MINTED, $rewritten['key'] );
		$this->assertGreaterThan( time(), (int) $rewritten['until'], 'The rewrite is a fresh claim, not the expired one.' );
		$this->assertConditionsMet();
	}

	/**
	 * A Conversations whose guest cookies always expire at one fixed second
	 * and whose minted key is fixed.
	 */
	private function conversations(): Conversations {
		return new class() extends Conversations {
			/**
			 * The fixed expiry second.
			 */
			protected function cookie_expire(): int {
				return 1000000;
			}

			/**
			 * The fixed browser key.
			 */
			protected function new_browser_key(): string {
				return ConversationsClaimTest::MINTED;
			}
		};
	}
}
