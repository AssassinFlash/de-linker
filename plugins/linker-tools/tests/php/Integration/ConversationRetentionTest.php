<?php
/**
 * The conversation retention on the real instance.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use ActionScheduler_QueueRunner;
use ActionScheduler_Store;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Retention;
use PHPUnit\Framework\TestCase;

/**
 * The daily scan runs on its cron hook against real `linker_conversation`
 * posts: the expired guest thread gets its delete job and the job deletes it
 * through wp_delete_post(); a fresh thread and a registered user's thread
 * stay (issue #67, GAP-18).
 *
 * @coversNothing
 */
final class ConversationRetentionTest extends TestCase {

	/**
	 * Skips unless the integration configuration ran the bootstrap (see
	 * Linker\Commerce\Tests\Integration\IntegrationTestCase for the mark).
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just up); the unit suite does not load WordPress.' );
		}
	}

	/**
	 * Conversations the tests created.
	 *
	 * @var list<int>
	 */
	private array $conversations = array();

	/**
	 * Removes the fixture conversations.
	 */
	protected function tearDown(): void {
		foreach ( $this->conversations as $id ) {
			wp_delete_post( $id, true );
		}
		$this->conversations = array();
		parent::tearDown();
	}

	/**
	 * A conversation post as the plugin makes one, backdated by the caller.
	 *
	 * @param int $age_seconds Age of the thread in seconds.
	 * @param int $author      Post author: 0 is a guest.
	 */
	private function conversation( int $age_seconds, int $author = 0 ): int {
		$created = gmdate( 'Y-m-d H:i:s', time() - $age_seconds );
		$id      = wp_insert_post(
			array(
				'post_type'     => Conversations::POST_TYPE,
				'post_status'   => 'private',
				'post_title'    => 'linker-it-' . wp_generate_password( 8, false ),
				'post_author'   => $author,
				'post_date'     => $created,
				'post_date_gmt' => $created,
			),
			true
		);
		$this->assertIsInt( $id );
		$this->conversations[] = $id;
		return $id;
	}

	/**
	 * The pending delete jobs of one conversation.
	 *
	 * @param int $conversation_id Conversation post ID.
	 * @return array<int|string, mixed>
	 */
	private static function pending_jobs( int $conversation_id ): array {
		return as_get_scheduled_actions(
			array(
				'hook'     => Retention::DELETE_HOOK,
				'status'   => ActionScheduler_Store::STATUS_PENDING,
				'group'    => Retention::GROUP,
				// The job's args are the conversation's ID; matching the ID
				// finds this thread's job, never another run's.
				'search'   => (string) $conversation_id,
				'orderby'  => 'date',
				'order'    => 'DESC',
				'per_page' => 10,
			)
		);
	}

	/**
	 * The cron trigger path: the daily scan on its hook schedules exactly the
	 * expired guest thread, and its job deletes that thread and nothing else.
	 */
	public function test_sweep_schedules_and_the_job_deletes_the_expired_guest(): void {
		$expired = $this->conversation( ( Retention::RETENTION_DAYS + 1 ) * DAY_IN_SECONDS );
		$fresh   = $this->conversation( DAY_IN_SECONDS );
		$claimed = $this->conversation( ( Retention::RETENTION_DAYS + 1 ) * DAY_IN_SECONDS, 1 );

		/** This hook is the retention's own daily event (Retention::HOOK), delivered by WP-Cron.
		 *
		 * @since 0.1.0
		 */
		do_action( Retention::HOOK ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- the retention's own hook constant.

		$jobs = self::pending_jobs( $expired );
		$this->assertNotEmpty( $jobs, 'The expired guest thread has a delete job.' );
		$this->assertEmpty( self::pending_jobs( $fresh ), 'A fresh thread has none.' );
		$this->assertEmpty( self::pending_jobs( $claimed ), "A registered user's thread has none." );

		$action_id     = (int) array_key_first( $jobs );
		$before_delete = get_post( $expired );
		$this->assertInstanceOf( \WP_Post::class, $before_delete );
		ActionScheduler_QueueRunner::instance()->process_action( $action_id, 'linker integration test' );

		$this->assertNull( get_post( $expired ), 'The expired guest thread is gone.' );
		$this->assertSame( 'private', get_post_status( $fresh ), 'The fresh thread stays.' );
		$this->assertSame( 'private', get_post_status( $claimed ), "The registered user's thread stays." );
	}

	/**
	 * The delete job re-checks the rule when it runs: a thread claimed between
	 * the scan and the job stays.
	 */
	public function test_the_job_keeps_a_thread_claimed_after_the_scan(): void {
		$retention = new Retention( WP_PLUGIN_DIR . '/linker-tools/linker-tools.php' );
		$expired   = $this->conversation( ( Retention::RETENTION_DAYS + 1 ) * DAY_IN_SECONDS );

		// Still a guest: the rule gives the thread up, and wp_delete_post takes it.
		$this->assertTrue( $retention->is_deletable( $expired ) );
		$retention->delete( $expired );
		$this->assertNull( get_post( $expired ) );

		$claimed = $this->conversation( ( Retention::RETENTION_DAYS + 1 ) * DAY_IN_SECONDS );
		$this->assertNotSame(
			0,
			wp_update_post(
				array(
					'ID'          => $claimed,
					'post_author' => 1,
				)
			)
		);
		$this->assertFalse( $retention->is_deletable( $claimed ), 'A registered user holds the thread.' );
		$retention->delete( $claimed );
		$this->assertSame( 'private', get_post_status( $claimed ), 'The claimed thread stays.' );
	}
}
