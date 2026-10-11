<?php
/**
 * Retention of Genie conversations: guests expire, users stay.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_User;

/**
 * Deletes guest conversations past their retention days, so the
 * `linker_conversation` posts grow with the site's use and not forever
 * (issue #67, GAP-18). A conversation stays when a user account with an
 * email address owns it — registered users keep their history; anonymous
 * threads, and threads whose owner has no email address, go. The daily
 * WP-Cron event scans and hands each expired conversation to one Action
 * Scheduler job, so the cron request stays light and the deletion is
 * observable and retried there. Deletion goes through wp_delete_post(),
 * never through SQL. WordPress core has no expiry for post types (only its
 * trash purge, on a different schedule), so the scan is this plugin's.
 */
class Retention {

	/**
	 * WP-Cron hook of the daily scan, and Action Scheduler group of the jobs.
	 */
	public const HOOK  = 'linker_tools_conversation_sweep';
	public const GROUP = 'linker-tools';

	/**
	 * Action Scheduler hook of the one-time delete jobs.
	 */
	public const DELETE_HOOK = 'linker_tools_conversation_delete';

	/**
	 * How long a conversation without an owner with an email address is kept,
	 * in days (issue #67: "N=90 起步" — the starting value; a change is a
	 * policy decision, not a code change).
	 */
	public const RETENTION_DAYS = 90;

	/**
	 * Conversations per scan batch. WordPress cannot query "post_author = 0"
	 * (WP_Query ignores an author of 0), so each batch is filtered by the
	 * retention rule in PHP; batches keep the daily cost at a handful of
	 * ID-only queries.
	 */
	public const SCAN_BATCH = 100;

	/**
	 * Batches per daily scan: at most SCAN_BATCH × MAX_BATCHES conversations
	 * are examined and at most that many delete jobs are scheduled per day.
	 * 20 × 100 covers any realistic backlog of expired guest threads; the
	 * retained threads of registered users (one per user) are re-scanned on
	 * the way, which is what the batching pays for.
	 */
	public const MAX_BATCHES = 20;

	/**
	 * Sets up the retention.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Adds the retention's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this, 'schedule' ) );
		add_action( self::HOOK, array( $this, 'sweep' ) );
		add_action( self::DELETE_HOOK, array( $this, 'delete' ) );
		register_deactivation_hook( $this->plugin_file, array( $this, 'deactivate' ) );
	}

	/**
	 * Schedules the daily scan; runs on init, so a missing event comes back
	 * without an activation hook.
	 */
	public function schedule(): void {
		if ( false === wp_next_scheduled( self::HOOK ) ) {
			wp_schedule_event( time(), 'daily', self::HOOK );
		}
	}

	/**
	 * Removes the daily event and the delete jobs still pending; runs on
	 * deactivation. The next scan reschedules whatever is still expired.
	 */
	public function deactivate(): void {
		wp_clear_scheduled_hook( self::HOOK );
		// Null matches every args set: every pending delete job of this group
		// goes, whatever conversation it carries.
		as_unschedule_all_actions( self::DELETE_HOOK, null, self::GROUP ); // @phpstan-ignore argument.type (Action Scheduler's own default is null; the stub narrows it to array)
	}

	/**
	 * The daily scan; runs on the WP-Cron hook. Walks the expired conversations
	 * oldest first and schedules one delete job per conversation the retention
	 * rule gives up.
	 */
	public function sweep(): void {
		for ( $batch = 1; $batch <= self::MAX_BATCHES; ++$batch ) {
			$ids = get_posts(
				array(
					'post_type'      => Conversations::POST_TYPE,
					'post_status'    => 'private',
					'fields'         => 'ids',
					'posts_per_page' => self::SCAN_BATCH,
					'paged'          => $batch,
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
				if ( $this->is_deletable( (int) $id ) ) {
					as_schedule_single_action( time(), self::DELETE_HOOK, array( (int) $id ), self::GROUP );
				}
			}
			if ( count( $ids ) < self::SCAN_BATCH ) {
				break;
			}
		}
	}

	/**
	 * One conversation's delete job; runs on the Action Scheduler hook. The
	 * rule is checked again here: between the scan and the job a guest may
	 * have logged in and claimed the thread.
	 *
	 * @param int $conversation_id Conversation post ID.
	 */
	public function delete( int $conversation_id ): void {
		if ( $this->is_deletable( $conversation_id ) ) {
			wp_delete_post( $conversation_id, true );
		}
	}

	/**
	 * The retention rule, the single implementation that both the scan and the
	 * delete job read: a conversation goes when it is past its retention days
	 * and no user account with an email address holds it. A registered user
	 * always has an email address, so in practice this means: guests go,
	 * registered users stay.
	 *
	 * @param int $conversation_id Conversation post ID.
	 */
	public function is_deletable( int $conversation_id ): bool {
		$post = get_post( $conversation_id );
		if ( null === $post || Conversations::POST_TYPE !== $post->post_type || 'private' !== $post->post_status ) {
			return false;
		}
		if ( $post->post_date_gmt >= $this->cutoff() ) {
			return false;
		}
		$author = (int) $post->post_author;
		if ( 0 === $author ) {
			return true;
		}
		$user = get_userdata( $author );
		return ! ( $user instanceof WP_User ) || '' === $user->user_email;
	}

	/**
	 * Conversations created before this moment (UTC) are past their retention
	 * days.
	 */
	private function cutoff(): string {
		return gmdate( 'Y-m-d H:i:s', time() - self::RETENTION_DAYS * DAY_IN_SECONDS );
	}
}
