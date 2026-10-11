<?php
/**
 * Retention of the stock push audit rows.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Stock;

/**
 * Deletes the audit rows of the stock pushes once they are past their
 * retention days, so `linker_stock_batch` grows with what the ERP pushes and
 * not forever (ticket #69). The channel is built for an ERP that pushes about
 * every fifteen minutes: roughly a hundred rows a day, tens of thousands a
 * year — the ever-growing audit table the ticket set out to avoid must not
 * come back under a new post type. A daily WP-Cron event walks the expired
 * rows oldest first and deletes them in batches through wp_delete_post(),
 * never through SQL; a batch that comes back short says the window is drained.
 * The rows are written by BatchLog, read by nothing and shown nowhere, so
 * nothing but this policy depends on them staying.
 */
final class Retention {

	/**
	 * WP-Cron hook of the daily sweep.
	 */
	public const HOOK = 'linker_commerce_stock_batch_sweep';

	/**
	 * How long an audit row is kept, in days (ticket #69: ninety days to start
	 * with; another number is a policy change, not a code change).
	 */
	public const RETENTION_DAYS = 90;

	/**
	 * Rows per delete batch: a batch is one ID-only query plus its deletes.
	 */
	public const SCAN_BATCH = 100;

	/**
	 * Batches per daily sweep. SCAN_BATCH × MAX_BATCHES rows go at most per
	 * day, which is far above the steady state the ERP produces (a hundred
	 * rows a day against a ninety-day retention) — the batching exists for the
	 * first sweep of a grown table and for a push storm, not as a limit anyone
	 * is meant to run into.
	 */
	public const MAX_BATCHES = 20;

	/**
	 * Sets up the retention.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Adds the retention's hooks. The module registers it on plugins_loaded; a
	 * deactivation request loads the active plugins before WordPress fires the
	 * plugin's deactivation hook, so the hook added here still runs.
	 */
	public function register(): void {
		add_action( 'init', array( $this, 'schedule' ) );
		add_action( self::HOOK, array( $this, 'sweep' ) );
		register_deactivation_hook( $this->plugin_file, array( $this, 'deactivate' ) );
	}

	/**
	 * Schedules the daily sweep; runs on init, so a missing event comes back
	 * without an activation hook.
	 */
	public function schedule(): void {
		if ( false === wp_next_scheduled( self::HOOK ) ) {
			wp_schedule_event( time(), 'daily', self::HOOK );
		}
	}

	/**
	 * Removes the daily event; runs on deactivation. The next request with the
	 * plugin active schedules it again.
	 */
	public function deactivate(): void {
		wp_clear_scheduled_hook( self::HOOK );
	}

	/**
	 * The daily sweep; runs on the WP-Cron hook. Deletes the expired rows
	 * oldest first, one batch at a time, until a batch comes back short (the
	 * window is drained) or the batch limit is reached.
	 */
	public function sweep(): void {
		for ( $batch = 1; $batch <= self::MAX_BATCHES; ++$batch ) {
			// Always the first page: this batch is deleted before the next
			// query runs, so page one is again the oldest rows still there.
			// A scan that only scheduled the deleting would have to page
			// through the window instead, because nothing moves under it.
			$ids = get_posts(
				array(
					'post_type'      => BatchLog::POST_TYPE,
					'post_status'    => 'private',
					'fields'         => 'ids',
					'posts_per_page' => self::SCAN_BATCH,
					'paged'          => 1,
					'orderby'        => 'date',
					'order'          => 'ASC',
					'date_query'     => array(
						array(
							'column' => 'post_date_gmt',
							'before' => $this->cutoff(),
						),
					),
				)
			);
			if ( array() === $ids ) {
				break;
			}
			foreach ( $ids as $id ) {
				wp_delete_post( (int) $id, true );
			}
			if ( count( $ids ) < self::SCAN_BATCH ) {
				break;
			}
		}
	}

	/**
	 * Rows written before this moment (UTC) are past their retention days.
	 */
	private function cutoff(): string {
		return gmdate( 'Y-m-d H:i:s', time() - self::RETENTION_DAYS * DAY_IN_SECONDS );
	}
}
