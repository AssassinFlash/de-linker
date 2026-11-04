<?php
/**
 * Tests for the hourly browser-claim reclamation.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\BrowserClaim;
use Linker\Tools\Genie\Conversations;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The scan, its bounds and its schedule, with the options table in memory.
 *
 * @covers \Linker\Tools\Genie\BrowserClaim
 */
final class BrowserClaimTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-tools/linker-tools.php';

	/**
	 * The database double, installed as the global in setUp().
	 *
	 * @var ClaimDatabaseDouble
	 */
	private ClaimDatabaseDouble $db;

	/**
	 * The options the scan reads and writes, as the options API would.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array();

	/**
	 * An in-memory options table and options API.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->db = new ClaimDatabaseDouble();
		// phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the database double stands in for the options table.
		$GLOBALS['wpdb'] = $this->db;
		$this->options   = array();
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => function ( string $name, mixed $fallback = false ): mixed {
					return array_key_exists( $name, $this->options ) ? $this->options[ $name ] : $fallback;
				},
			)
		);
		WP_Mock::userFunction(
			'update_option',
			array(
				'return' => function ( string $name, mixed $value ): bool {
					$this->options[ $name ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction(
			'maybe_unserialize',
			array(
				'return' => static function ( string $value ): mixed {
					// phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged, WordPress.PHP.DiscouragedPHPFunctions.serialize_unserialize -- the double mirrors maybe_unserialize() over the scan's own rows, with object injection disabled.
					$unserialized = @unserialize( $value, array( 'allowed_classes' => false ) );
					return false === $unserialized ? $value : $unserialized;
				},
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
	 * One claim row as the scan selects it.
	 *
	 * @param int    $id    option_id.
	 * @param string $key   Claimed key.
	 * @param int    $until Expiry timestamp.
	 */
	private function row( int $id, string $key, int $until ): \stdClass {
		return (object) array(
			'option_id'    => $id,
			'option_name'  => Conversations::BROWSER_CLAIM_PREFIX . str_pad( (string) $id, 32, 'a', STR_PAD_LEFT ),
			'option_value' => serialize( // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.serialize_serialize -- the scan reads serialized option values; the fixture writes one, with no live data.
				array(
					'key'   => $key,
					'until' => $until,
				)
			),
		);
	}

	/**
	 * Without an hourly event, one is scheduled an hour out.
	 */
	public function test_schedules_the_hourly_sweep_once(): void {
		WP_Mock::userFunction(
			'wp_schedule_event',
			array(
				'times'  => 1,
				'args'   => array( WP_Mock\Functions::type( 'int' ), 'hourly', BrowserClaim::HOOK ),
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => false ) );

		( new BrowserClaim( self::FILE ) )->schedule();
		$this->assertConditionsMet();
	}

	/**
	 * An event already being scheduled is left alone.
	 */
	public function test_leaves_the_scheduled_event_alone(): void {
		WP_Mock::userFunction( 'wp_schedule_event', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => 12345 ) );

		( new BrowserClaim( self::FILE ) )->schedule();
		$this->assertConditionsMet();
	}

	/**
	 * Registration hangs the scan on init and clears itself on deactivation.
	 */
	public function test_register_and_deactivate_hold_the_schedule(): void {
		$claim = new BrowserClaim( self::FILE );
		WP_Mock::expectActionAdded( 'init', array( $claim, 'schedule' ) );
		WP_Mock::expectActionAdded( BrowserClaim::HOOK, array( $claim, 'sweep' ) );
		WP_Mock::userFunction(
			'register_deactivation_hook',
			array(
				'times' => 1,
				'args'  => array( self::FILE, array( $claim, 'deactivate' ) ),
			)
		);

		$claim->register();

		WP_Mock::userFunction(
			'wp_clear_scheduled_hook',
			array(
				'times' => 1,
				'args'  => array( BrowserClaim::HOOK ),
			)
		);
		WP_Mock::userFunction(
			'delete_option',
			array(
				'times' => 1,
				'args'  => array( BrowserClaim::CURSOR ),
			)
		);

		$claim->deactivate();
		$this->assertConditionsMet();
	}

	/**
	 * The scan takes rows past its grace and damaged rows, keeps the rest,
	 * and resets the cursor when the table ran to its end.
	 */
	public function test_sweep_takes_stale_and_damaged_rows_only(): void {
		$fresh          = $this->row( 1, str_repeat( 'a', 32 ), time() + 20 );
		$edge           = $this->row( 2, str_repeat( 'b', 32 ), time() - 30 );
		$stale          = $this->row( 3, str_repeat( 'c', 32 ), time() - BrowserClaim::GRACE - 60 );
		$broken         = (object) array(
			'option_id'    => 4,
			'option_name'  => Conversations::BROWSER_CLAIM_PREFIX . str_pad( '4', 32, 'b', STR_PAD_LEFT ),
			'option_value' => 'not-a-claim',
		);
		$this->db->rows = array( $fresh, $edge, $stale, $broken );

		( new BrowserClaim( self::FILE ) )->sweep();

		$this->assertSame(
			array( $fresh->option_name, $edge->option_name ),
			array_column( $this->db->rows, 'option_name' ),
			'The unexpired claim and the one 30 s past expiry stay; the hour-stale one and the damaged one go.'
		);
		$this->assertSame( 0, $this->options[ BrowserClaim::CURSOR ], 'A short batch resets the cursor for the next hour.' );
		$this->assertConditionsMet();
	}

	/**
	 * The grace is the sweep's, not the purge's: the publish-time cleanup takes
	 * every claim row, because no live claim can exist at a deploy.
	 */
	public function test_purge_takes_rows_the_sweep_keeps(): void {
		$edge           = $this->row( 1, str_repeat( 'b', 32 ), time() - 30 );
		$this->db->rows = array( $edge );

		( new BrowserClaim( self::FILE ) )->sweep();
		$this->assertCount( 1, $this->db->rows );

		( new BrowserClaim( self::FILE ) )->purge();
		$this->assertCount( 0, $this->db->rows );
		$this->assertConditionsMet();
	}

	/**
	 * A full batch does not end the run: the walk goes on to the short batch
	 * behind it and only then resets the cursor.
	 */
	public function test_a_full_batch_does_not_end_the_walk(): void {
		for ( $id = 1; $id <= BrowserClaim::BATCH + 1; ++$id ) {
			$this->db->rows[] = $this->row( $id, str_repeat( 'c', 32 ), time() - BrowserClaim::GRACE - 60 );
		}

		( new BrowserClaim( self::FILE ) )->sweep();

		$this->assertCount( 0, $this->db->rows, 'The full batch and the short one behind it both went.' );
		$this->assertSame( 0, $this->options[ BrowserClaim::CURSOR ], 'A run that reached its end resets the cursor.' );
		$this->assertConditionsMet();
	}

	/**
	 * A backlog bigger than one run's bound stops after MAX_BATCHES batches;
	 * the cursor hands the rest to the next hour's run.
	 */
	public function test_the_walk_stops_at_max_batches(): void {
		$total = BrowserClaim::BATCH * BrowserClaim::MAX_BATCHES + 5;
		for ( $id = 1; $id <= $total; ++$id ) {
			$this->db->rows[] = $this->row( $id, str_repeat( 'd', 32 ), time() - BrowserClaim::GRACE - 60 );
		}

		( new BrowserClaim( self::FILE ) )->sweep();

		$this->assertCount( 5, $this->db->rows, 'One run examines at most BATCH × MAX_BATCHES rows.' );
		$this->assertSame( BrowserClaim::BATCH * BrowserClaim::MAX_BATCHES, $this->options[ BrowserClaim::CURSOR ] );
		$this->assertConditionsMet();
	}

	/**
	 * The scan resumes at the stored cursor, not from the oldest row again.
	 */
	public function test_the_scan_resumes_at_the_cursor(): void {
		$this->db->rows                        = array(
			$this->row( 1, str_repeat( 'e', 32 ), time() - BrowserClaim::GRACE - 60 ),
			$this->row( 2, str_repeat( 'f', 32 ), time() - BrowserClaim::GRACE - 60 ),
		);
		$this->options[ BrowserClaim::CURSOR ] = 1;

		( new BrowserClaim( self::FILE ) )->sweep();

		$this->assertSame(
			array( Conversations::BROWSER_CLAIM_PREFIX . str_pad( '1', 32, 'a', STR_PAD_LEFT ) ),
			array_column( $this->db->rows, 'option_name' ),
			'Only the row beyond the cursor was even examined.'
		);
		$this->assertConditionsMet();
	}

	/**
	 * The LIKE prefix goes through esc_like(): the claim prefix's underscores
	 * are literals, not single-character wildcards.
	 */
	public function test_the_prefix_is_escaped_for_like(): void {
		$this->db->rows = array();

		( new BrowserClaim( self::FILE ) )->sweep();

		$scans = array_filter(
			$this->db->selects,
			static fn( string $sql ): bool => str_contains( $sql, 'SELECT' )
		);
		$this->assertNotEmpty( $scans );
		foreach ( $scans as $sql ) {
			$this->assertStringContainsString( "LIKE 'linker\\_genie\\_browser\\_claim\\_%'", $sql );
		}
		$this->assertConditionsMet();
	}
}
