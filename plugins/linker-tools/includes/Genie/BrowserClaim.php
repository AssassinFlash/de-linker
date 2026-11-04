<?php
/**
 * Hourly reclamation of Genie browser-claim rows whose tab never returned.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Deletes expired `linker_genie_browser_claim_*` option rows on an hourly
 * WP-Cron event (#906). The claim's only in-request deletion path is the tab
 * presenting the browser cookie (`Conversations::close_browser_claim()`), so
 * a visitor that never returns — closed tab, another device, a crawler —
 * leaked its row forever: the row's key is a random tab UUID's hash, and
 * lazy deletion needs a reader that never comes. The scan is bounded and
 * cursor-based, needs no lock (the grace keeps it far from any live claim),
 * and runs hourly rather than daily so a 1 req/s crawl of the cookieless
 * entry-context tops out at ~3 600 rows instead of 86 400
 * (docs/research/2026-11-04-browser-claim-reclamation.md §3c).
 */
final class BrowserClaim {

	/**
	 * WP-Cron hook of the hourly scan.
	 */
	public const HOOK = 'linker_tools_browser_claim_sweep';

	/**
	 * The scan's option_id cursor, not autoloaded; 0 starts from the oldest row.
	 */
	public const CURSOR = 'linker_tools_browser_claim_cursor';

	/**
	 * Rows per scan batch. Each batch is one SELECT and at most one DELETE.
	 */
	public const BATCH = 500;

	/**
	 * Batches per run: at most BATCH × MAX_BATCHES rows are examined per hour.
	 */
	public const MAX_BATCHES = 20;

	/**
	 * Seconds past a claim's expiry before the scan may take it. Far above
	 * BROWSER_CLAIM_SECONDS (20), so a mint in flight during the scan — or a
	 * tab re-minting right now — is never deleted underneath its window; the
	 * only rows taken have been unusable for an hour.
	 */
	public const GRACE = 3600;

	/**
	 * Sets up the reclamation.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Adds the reclamation's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this, 'schedule' ) );
		add_action( self::HOOK, array( $this, 'sweep' ) );
		register_deactivation_hook( $this->plugin_file, array( $this, 'deactivate' ) );
	}

	/**
	 * Schedules the hourly scan; runs on init, so a missing event comes back
	 * without an activation hook (the Resources reply cleanup does the same).
	 */
	public function schedule(): void {
		if ( false === wp_next_scheduled( self::HOOK ) ) {
			wp_schedule_event( time() + HOUR_IN_SECONDS, 'hourly', self::HOOK );
		}
	}

	/**
	 * Removes the hourly event and the cursor; runs on deactivation. The rows
	 * themselves stay: a reactivation's first scan takes them again.
	 */
	public function deactivate(): void {
		wp_clear_scheduled_hook( self::HOOK );
		delete_option( self::CURSOR );
	}

	/**
	 * The hourly scan; runs on the WP-Cron hook. Walks the claim rows in
	 * option_id order and deletes every one whose claim has been expired
	 * longer than the grace — including a row whose stored value is damaged,
	 * because such a row can never be adopted by any request.
	 */
	public function sweep(): void {
		$this->scan( self::GRACE );
	}

	/**
	 * The publish-time cleanup: every claim row goes, without a grace. At
	 * publish the oldest row in the table is days past its 20-second window,
	 * so no live claim exists; the one cost is a tab minting at exactly this
	 * moment re-minting its key once (#906 §5.3). Runs once per deploy, not
	 * from the cron hook.
	 */
	public function purge(): void {
		$this->scan( 0 );
	}

	/**
	 * One bounded, cursor-based walk of the claim rows.
	 *
	 * @param int $grace Seconds past expiry before a row may be taken.
	 */
	private function scan( int $grace ): void {
		global $wpdb;
		// The prefix ends in an underscore: esc_like() keeps it from acting
		// as the single-character wildcard it is in LIKE (RateLimit does the same).
		$prefix = $wpdb->esc_like( Conversations::BROWSER_CLAIM_PREFIX ) . '%';
		for ( $batch = 1; $batch <= self::MAX_BATCHES; ++$batch ) {
			$cursor = (int) get_option( self::CURSOR, 0 );
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- a bounded private reclamation scan, no cached ownership decision.
			$rows = $wpdb->get_results(
				$wpdb->prepare(
					"SELECT option_id, option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE %s AND option_id > %d ORDER BY option_id ASC LIMIT %d",
					$prefix,
					$cursor,
					self::BATCH
				)
			);
			if ( array() === $rows ) {
				update_option( self::CURSOR, 0, false );
				return;
			}
			$expired = array();
			foreach ( $rows as $row ) {
				if ( $this->is_stale( (string) $row->option_value, $grace ) ) {
					$expired[] = (string) $row->option_name;
				}
			}
			if ( array() !== $expired ) {
				$this->delete( $expired );
			}
			update_option(
				self::CURSOR,
				count( $rows ) < self::BATCH ? 0 : (int) end( $rows )->option_id,
				false
			);
			if ( count( $rows ) < self::BATCH ) {
				return;
			}
		}
	}

	/**
	 * Whether a claim row may be taken: past its expiry by the grace, or
	 * damaged beyond adoption (no numeric `until` nothing could adopt).
	 *
	 * @param string $value The stored, still-serialized option value.
	 * @param int    $grace Seconds past expiry before a row may be taken.
	 */
	private function is_stale( string $value, int $grace ): bool {
		$stored = maybe_unserialize( $value );
		$until  = is_array( $stored ) ? ( $stored['until'] ?? null ) : null;
		return ! is_numeric( $until ) || (int) $until < time() - $grace;
	}

	/**
	 * Deletes claim rows by name and drops their cache entries.
	 *
	 * @param array<int, string> $names Option names, all of the claim prefix.
	 */
	private function delete( array $names ): void {
		global $wpdb;
		$placeholders = implode( ',', array_fill( 0, count( $names ), '%s' ) );
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- a bounded private reclamation delete; the cache entries are dropped right after it.
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared, WordPress.DB.PreparedSQLPlaceholders.UnfinishedPrepare -- one placeholder per spread name, the IN (...) pattern WordPress documents; the placeholder list is built from the same count as the values.
		$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name IN ( {$placeholders} )", ...$names ) );
		foreach ( $names as $name ) {
			wp_cache_delete( $name, 'options' );
		}
		wp_cache_delete( 'notoptions', 'options' );
	}
}
