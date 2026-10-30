<?php
/**
 * Two first entry-context reads of one tab.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Genie\Conversations;
use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open, WordPress.Security.ValidatedSanitizedInput -- the parallel test starts PHP processes. This file reads the browser cookie the code under test just wrote; the format check is the sanitizer.

/**
 * A cookieless sibling used to mint a second browser key. Both the sequential
 * gap (the second request is already in flight) and two overlapping processes
 * must share one scope and one cookie, until a request presents that cookie.
 * After it is presented, a later cookieless request on the same tab is a new
 * guest. A different cookie remains a different owner.
 *
 * @covers \Linker\Tools\Genie\Conversations::entry_scope
 */
final class EntryScopeConcurrencyTest extends TestCase {

	/**
	 * Tab used by the in-process sibling.
	 */
	private const TAB = '6aebdb40-58dc-4831-a9e5-f43c0260a281';

	/**
	 * Tab used by the overlapping processes, distinct from the in-process tab.
	 */
	private const PARALLEL_TAB = '7b1c2d3e-4f50-4612-a345-6789abcdef01';

	/**
	 * Tab whose open claim must survive another tab presenting its cookie.
	 */
	private const OTHER_TAB = '8c2d3e4f-5061-4723-b456-789abcdef012';

	/**
	 * Tab whose cold mint is deliberately held by another process.
	 */
	private const LOCKED_TAB = '9d3e4f50-6172-4834-c567-89abcdef0123';

	/**
	 * Browser cookie this process had before the test, if any.
	 *
	 * @var string
	 */
	private string $previous_browser = '';

	/**
	 * Whether this process had a browser cookie to restore.
	 *
	 * @var bool
	 */
	private bool $had_browser = false;

	/**
	 * Skips unless the integration configuration ran the bootstrap.
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just up); the unit suite does not load WordPress.' );
		}
	}

	/**
	 * Drops the browser cookie so the first read is a cold mint.
	 */
	protected function setUp(): void {
		parent::setUp();
		if ( isset( $_COOKIE[ Conversations::BROWSER_COOKIE ] ) && is_string( $_COOKIE[ Conversations::BROWSER_COOKIE ] ) ) {
			$this->previous_browser = $_COOKIE[ Conversations::BROWSER_COOKIE ];
			$this->had_browser      = true;
		}
		unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
	}

	/**
	 * Restores the process cookie and deletes this test's claims.
	 */
	protected function tearDown(): void {
		$this->delete_claim( self::TAB );
		$this->delete_claim( self::PARALLEL_TAB );
		$this->delete_claim( self::OTHER_TAB );
		$this->delete_claim( self::LOCKED_TAB );
		if ( $this->had_browser ) {
			$_COOKIE[ Conversations::BROWSER_COOKIE ] = $this->previous_browser;
		} else {
			unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		}
		if ( false === has_action( Conversations::BROWSER_ACTION ) ) {
			add_action( Conversations::BROWSER_ACTION, array( new Conversations(), 'send_browser_cookie' ), 10, 5 );
		}
		parent::tearDown();
	}

	/**
	 * The second request has not stored Set-Cookie yet. It must adopt the
	 * first key. A later request that presents that cookie keeps the scope.
	 * A different cookie does not, and is not replaced.
	 */
	public function test_a_cookieless_sibling_adopts_the_same_guest_scope(): void {
		$store      = new Conversations();
		$dispatched = array();
		$this->silence_browser_cookie();
		add_action(
			Conversations::BROWSER_ACTION,
			static function ( $value ) use ( &$dispatched ): void {
				$dispatched[] = $value;
			},
			10,
			1
		);
		$first = $store->entry_scope( self::TAB );
		$key   = $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? '';
		$this->assertMatchesRegularExpression( '/^[0-9a-f]{32}$/', is_string( $key ) ? $key : '' );
		$this->assertMatchesRegularExpression( '/^[0-9a-f]{64}$/', $first );

		unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		$second = $store->entry_scope( self::TAB );
		$again  = $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? '';
		$this->assertSame( $first, $second );
		$this->assertSame( $key, $again );
		$this->assertSame( array( $key, $key ), $dispatched );

		$sent = 0;
		add_action(
			Conversations::BROWSER_ACTION,
			static function () use ( &$sent ): void {
				++$sent;
			}
		);
		$_COOKIE[ Conversations::BROWSER_COOKIE ] = $key;
		$this->assertSame( $first, $store->entry_scope( self::TAB ) );
		$this->assertSame( 0, $sent );
		$this->assertSame( $key, $_COOKIE[ Conversations::BROWSER_COOKIE ] );

		$_COOKIE[ Conversations::BROWSER_COOKIE ] = str_repeat( 'b', 32 );
		$this->assertNotSame( $first, $store->entry_scope( self::TAB ) );
		$this->assertSame( str_repeat( 'b', 32 ), $_COOKIE[ Conversations::BROWSER_COOKIE ] );
	}

	/**
	 * Presenting the minted cookie closes only that tab's claim. The same tab's
	 * next cookieless read is a new guest. The old cookie still opens the old
	 * scope and is not replaced. Another tab's unpresented claim stays open.
	 */
	public function test_presenting_the_cookie_opens_a_new_guest_on_the_same_tab(): void {
		$store = new Conversations();
		$this->silence_browser_cookie();
		$other_scope = $store->entry_scope( self::OTHER_TAB );
		$other_key   = $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? '';
		$this->assertMatchesRegularExpression( '/^[0-9a-f]{32}$/', is_string( $other_key ) ? $other_key : '' );

		unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		$first = $store->entry_scope( self::TAB );
		$key   = $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? '';
		$this->assertNotSame( $other_key, $key );
		$this->assertNotSame( $other_scope, $first );

		unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		$this->assertSame( $first, $store->entry_scope( self::TAB ) );
		$this->assertSame( $key, $_COOKIE[ Conversations::BROWSER_COOKIE ] );

		$sent = 0;
		add_action(
			Conversations::BROWSER_ACTION,
			static function () use ( &$sent ): void {
				++$sent;
			}
		);
		$_COOKIE[ Conversations::BROWSER_COOKIE ] = $key;
		$this->assertSame( $first, $store->entry_scope( self::TAB ) );
		$this->assertSame( 0, $sent );
		$this->assertSame( $key, $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		$this->assertFalse( get_option( $this->claim_name( self::TAB ), false ) );

		unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		$guest     = $store->entry_scope( self::TAB );
		$guest_key = $_COOKIE[ Conversations::BROWSER_COOKIE ] ?? '';
		$this->assertNotSame( $first, $guest );
		$this->assertNotSame( $key, $guest_key );
		$this->assertMatchesRegularExpression( '/^[0-9a-f]{32}$/', is_string( $guest_key ) ? $guest_key : '' );

		unset( $_COOKIE[ Conversations::BROWSER_COOKIE ] );
		$this->assertSame( $other_scope, $store->entry_scope( self::OTHER_TAB ) );
		$this->assertSame( $other_key, $_COOKIE[ Conversations::BROWSER_COOKIE ] );

		$_COOKIE[ Conversations::BROWSER_COOKIE ] = $key;
		$this->assertSame( $first, $store->entry_scope( self::TAB ) );
		$this->assertSame( $key, $_COOKIE[ Conversations::BROWSER_COOKIE ] );
	}

	/**
	 * Two processes reach the mint together. Neither response may carry a
	 * private scope the other's cookie cannot open.
	 */
	public function test_overlapping_first_requests_share_one_guest_scope(): void {
		$root  = (string) getenv( 'LINKER_WP_ROOT' );
		$ready = tempnam( sys_get_temp_dir(), 'genie-entry-scope-' );
		$this->assertIsString( $ready );
		file_put_contents( $ready, '' );
		$running = array();
		$pipes   = array();
		foreach ( array( 0, 1 ) as $index ) {
			$process = proc_open(
				array( PHP_BINARY, '-d', 'memory_limit=2048M', __DIR__ . '/fixtures/entry-scope.php', $root, self::PARALLEL_TAB, $ready ),
				array(
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes[ $index ]
			);
			$this->assertIsResource( $process );
			$running[ $index ] = $process;
		}
		$results = array();
		foreach ( $running as $index => $process ) {
			$out = (string) stream_get_contents( $pipes[ $index ][1] );
			$err = (string) stream_get_contents( $pipes[ $index ][2] );
			fclose( $pipes[ $index ][1] );
			fclose( $pipes[ $index ][2] );
			$this->assertSame( 0, proc_close( $process ), $err . $out );
			$decoded = json_decode( $out, true );
			$this->assertIsArray( $decoded, $out );
			$results[] = $decoded;
		}
		unlink( $ready );

		$this->assertSame( $results[0]['scope'], $results[1]['scope'] );
		$this->assertSame( $results[0]['key'], $results[1]['key'] );
		$this->assertMatchesRegularExpression( '/^[0-9a-f]{32}$/', (string) $results[0]['key'] );
		$this->assertMatchesRegularExpression( '/^[0-9a-f]{64}$/', (string) $results[0]['scope'] );

		$this->silence_browser_cookie();
		$_COOKIE[ Conversations::BROWSER_COOKIE ] = (string) $results[0]['key'];
		$this->assertSame( (string) $results[0]['scope'], ( new Conversations() )->entry_scope( self::PARALLEL_TAB ) );
	}

	/**
	 * A real REST request must return before the browser's five-second budget
	 * when another process holds the cold mint. Its fallback publishes a claim,
	 * and a second cookieless request must reuse that scope.
	 */
	public function test_lock_contention_leaves_client_budget_headroom(): void {
		$root  = (string) getenv( 'LINKER_WP_ROOT' );
		$ready = tempnam( sys_get_temp_dir(), 'genie-entry-lock-' );
		$this->assertIsString( $ready );
		$release = $ready . '.release';

		$pipes   = array();
		$process = null;
		$exit    = null;
		$err     = '';
		$out     = '';
		try {
			file_put_contents( $ready, '' );
			$this->delete_claim( self::LOCKED_TAB );
			$process = proc_open(
				array( PHP_BINARY, '-d', 'memory_limit=2048M', __DIR__ . '/fixtures/entry-lock-holder.php', $root, self::LOCKED_TAB, $ready, $release ),
				array(
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes
			);
			$this->assertIsResource( $process );

			$deadline = microtime( true ) + 10;
			while ( '' === trim( (string) file_get_contents( $ready ) ) ) {
				if ( microtime( true ) > $deadline ) {
					$this->fail( 'lock holder did not become ready' );
				}
				usleep( 10000 );
			}

			$body = wp_json_encode( array( 'tab' => self::LOCKED_TAB ) );
			$this->assertIsString( $body );
			$started  = microtime( true );
			$response = wp_remote_post(
				rest_url( 'linker-ai/v1/genie/entry-context' ),
				array(
					'timeout' => 12,
					'headers' => array(
						'Content-Type' => 'application/json',
						'X-WP-Nonce'   => wp_create_nonce( 'wp_rest' ),
					),
					'body'    => $body,
				)
			);
			$elapsed  = microtime( true ) - $started;
			$this->assertFalse( is_wp_error( $response ), is_wp_error( $response ) ? $response->get_error_message() : '' );
			$this->assertSame( 200, wp_remote_retrieve_response_code( $response ) );
			$this->assertGreaterThanOrEqual( 0.75, $elapsed, 'entry_scope bypassed the held named lock' );
			$this->assertLessThan( 2.0, $elapsed, 'entry_scope waited at the five-second client boundary' );
			$data = json_decode( (string) wp_remote_retrieve_body( $response ), true );
			$this->assertIsArray( $data, (string) wp_remote_retrieve_body( $response ) );
			$claim = get_option( $this->claim_name( self::LOCKED_TAB ), false );
			$this->assertIsArray( $claim );
			$key = $claim['key'] ?? '';
			$this->assertMatchesRegularExpression( '/^[0-9a-f]{32}$/', is_string( $key ) ? $key : '' );
			$expected = hash_hmac( 'sha256', self::LOCKED_TAB . '|guest:' . $key, wp_salt( 'auth' ) );
			$this->assertSame( $expected, $data['scope'] ?? null );

			$second_body = wp_json_encode( array( 'tab' => self::LOCKED_TAB ) );
			$this->assertIsString( $second_body );
			$second = wp_remote_post(
				rest_url( 'linker-ai/v1/genie/entry-context' ),
				array(
					'timeout' => 12,
					'headers' => array(
						'Content-Type' => 'application/json',
						'X-WP-Nonce'   => wp_create_nonce( 'wp_rest' ),
					),
					'body'    => $second_body,
				)
			);
			$this->assertFalse( is_wp_error( $second ), is_wp_error( $second ) ? $second->get_error_message() : '' );
			$this->assertSame( 200, wp_remote_retrieve_response_code( $second ) );
			$second_data = json_decode( (string) wp_remote_retrieve_body( $second ), true );
			$this->assertIsArray( $second_data, (string) wp_remote_retrieve_body( $second ) );
			$this->assertSame( $expected, $second_data['scope'] ?? null );
		} finally {
			file_put_contents( $release, '' );
			if ( is_resource( $process ) ) {
				$stopped  = false;
				$deadline = microtime( true ) + 5;
				while ( microtime( true ) < $deadline ) {
					$status = proc_get_status( $process );
					if ( ! $status['running'] ) {
						$exit    = $status['exitcode'];
						$stopped = true;
						break;
					}
					usleep( 10000 );
				}
				if ( ! $stopped ) {
					proc_terminate( $process, 9 );
					usleep( 100000 );
				}
				stream_set_blocking( $pipes[1], false );
				stream_set_blocking( $pipes[2], false );
				$out = (string) stream_get_contents( $pipes[1] );
				$err = (string) stream_get_contents( $pipes[2] );
				fclose( $pipes[1] );
				fclose( $pipes[2] );
				$closed = proc_close( $process );
				if ( null === $exit || -1 === $exit ) {
					$exit = $closed;
				}
			}
			if ( file_exists( $release ) ) {
				unlink( $release );
			}
			if ( file_exists( $ready ) ) {
				unlink( $ready );
			}
		}
		$this->assertSame( 0, $exit, $err . $out );
	}

	/**
	 * Stops the site listener from calling setcookie() during this CLI run.
	 */
	private function silence_browser_cookie(): void {
		remove_all_actions( Conversations::BROWSER_ACTION );
	}

	/**
	 * Deletes the claim row for one tab.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function delete_claim( string $tab ): void {
		delete_option( $this->claim_name( $tab ) );
	}

	/**
	 * Option name of one tab's claim.
	 *
	 * @param string $tab Client tab identity.
	 */
	private function claim_name( string $tab ): string {
		return Conversations::BROWSER_CLAIM_PREFIX . substr( hash( 'sha256', $tab ), 0, 32 );
	}
}
