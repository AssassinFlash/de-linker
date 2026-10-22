<?php
/** Pending-review aggregate delivery bounds.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Health\PendingReviews;
use Linker\Commerce\Health\ReviewReminder;
use Linker\Commerce\Health\ReviewSummary;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;

/** Real native queue records; all generated mail remains tester-isolated.
 *
 * @coversNothing
 */
final class ReviewReminderTest extends IntegrationTestCase {
	/** Preserve the independent reminder ledger across fixtures. */
	protected function setUp(): void {
		parent::setUp();
		$locale = get_option( 'linker_commerce_team_locale' );
		update_option( 'linker_commerce_team_locale', 'en_US', false );
		$this->later(
			static function () use ( $locale ): void {
				false === $locale ? delete_option( 'linker_commerce_team_locale' ) : update_option( 'linker_commerce_team_locale', $locale, false );
			}
		);
		$before = get_option( ReviewReminder::OPTION );
		delete_option( ReviewReminder::OPTION );
		$this->later(
			static function () use ( $before ): void {
				false === $before ? delete_option( ReviewReminder::OPTION ) : update_option( ReviewReminder::OPTION, $before, false );
			}
		);
	}
	/** First tick creates one critical aggregate; repeated ticks never create per-record messages. */
	public function test_first_tick_then_hourly_and_daily_bounds_survive_new_batches(): void {
		$now      = time();
		$data     = array(
			'count'  => 3,
			'oldest' => $now - 300,
			'url'    => admin_url( 'edit.php?post_type=shop_order&linker_review=1' ),
		);
		$summary  = new ReviewSummary(
			static function () use ( &$data ): array {
				return $data;
			}
		);
		$reminder = new ReviewReminder( $summary );
		$marker   = self::newest_mail_job();
		$reminder->tick();
		$jobs = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $jobs );
		$job = ( new JobStore() )->load( $jobs[0] );
		$this->assertNotNull( $job );
		$this->assertTrue( $job['message']->critical );
		$this->assertStringContainsString( 'Saved inquiries awaiting staff review: 3.', $job['message']->body );
		$this->assertStringContainsString( $data['url'], $job['message']->body );
		$this->assertStringNotContainsString( 'Customer payload', $job['message']->body );
		$this->assertIsInt( as_next_scheduled_action( Outbox::HOOK, array( $jobs[0] ), Outbox::GROUP ) );
		$reminder->tick();
		$this->assertCount( 1, self::mail_jobs_after( $marker ) );
		$state = json_decode( get_option( ReviewReminder::OPTION ), true );
		$this->assertCount( 1, $state['events'] );
		( new JobStore() )->delete( $jobs[0] );
		$reminder->tick();
		$this->assertCount( 0, self::mail_jobs_after( $marker ), 'No hourly repeat until the hour passes.' );
		$state['last'] = $now - HOUR_IN_SECONDS;
		update_option( ReviewReminder::OPTION, wp_json_encode( $state ), false );
		$reminder->tick();
		$this->assertCount( 1, self::mail_jobs_after( $marker ) );
		foreach ( self::mail_jobs_after( $marker ) as $id ) {
			as_unschedule_all_actions( Outbox::HOOK, array( $id ), Outbox::GROUP );
			( new JobStore() )->delete( $id );
		}
		$state['events'] = array_fill( 0, ReviewReminder::PER_DAY, $now - 60 );
		$state['active'] = false;
		$state['job']    = 0;
		update_option( ReviewReminder::OPTION, wp_json_encode( $state ), false );
		$data['count'] = 0;
		$reminder->tick();
		$data['count'] = 5;
		$reminder->tick();
		$this->assertCount( 0, self::mail_jobs_after( $marker ), 'A new batch does not reset the global rolling-day ceiling.' );
		$this->assertCount( 24, json_decode( get_option( ReviewReminder::OPTION ), true )['events'] );
	}
	/** Missing or failed aggregate data stays visible in the digest and creates no bogus message. */
	public function test_reminder_original_job_ack_and_action_roll_back_with_the_outer_owner(): void {
		global $wpdb;
		$other   = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$summary = new ReviewSummary(
			static fn (): array => array(
				'count'  => 1,
				'oldest' => time() - 60,
				'url'    => admin_url( 'edit.php?post_type=shop_order' ),
			)
		);
		$wpdb->query( 'START TRANSACTION' );
		$job = 0;
		try {
			( new ReviewReminder( $summary ) )->tick();
			self::assertTrue( \Linker\Commerce\Mail\Capacity::transaction_active() );
			$state = json_decode( get_option( ReviewReminder::OPTION ), true );
			$job   = (int) $state['job'];
			self::assertGreaterThan( 0, $job );
			self::assertSame( '1', $wpdb->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM %i WHERE ID=%d', $wpdb->posts, $job ) ) );
			self::assertSame( '0', $other->get_var( $other->prepare( 'SELECT COUNT(*) FROM %i WHERE ID=%d', $wpdb->posts, $job ) ) );
			self::assertNull( $other->get_var( $other->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, ReviewReminder::OPTION ) ) );
			self::assertCount(
				1,
				as_get_scheduled_actions(
					array(
						'hook'   => Outbox::HOOK,
						'args'   => array( $job ),
						'group'  => Outbox::GROUP,
						'status' => 'pending',
					),
					'ids'
				)
			);
		} finally {
			$wpdb->query( 'ROLLBACK' );
			$other->close();
			clean_post_cache( $job );
			wp_cache_delete( $job, 'post_meta' );
			foreach ( array( ReviewReminder::OPTION, \Linker\Commerce\Protection\IntakeStore::OPTION, 'notoptions' ) as $key ) {
				wp_cache_delete( $key, 'options' ); }
		}
		self::assertNull( ( new JobStore() )->load( $job ) );
		self::assertFalse( get_option( ReviewReminder::OPTION ) );
		self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $job ), Outbox::GROUP ) );
	}

	/** An acknowledged native state write must be read back, not inferred from a non-error query. */
	public function test_reminder_state_write_failure_does_not_leave_a_job_or_recovery_action(): void {
		global $wpdb;
		$summary = new ReviewSummary(
			static fn (): array => array(
				'count'  => 1,
				'oldest' => time() - 60,
				'url'    => admin_url( 'edit.php?post_type=shop_order' ),
			)
		);
		$fail    = static function ( string $sql ): string {
			return str_starts_with( $sql, 'INSERT INTO' ) && str_contains( $sql, ReviewReminder::OPTION ) ? 'SELECT 0' : $sql;
		};
		$before  = self::newest_mail_job();
		add_filter( 'query', $fail, 998 );
		try {
			( new ReviewReminder( $summary ) )->tick(); } finally {
			remove_filter( 'query', $fail, 998 ); }
			self::assertSame( $before, self::newest_mail_job() );
			wp_cache_delete( ReviewReminder::OPTION, 'options' );
			wp_cache_delete( 'notoptions', 'options' );
			self::assertFalse( get_option( ReviewReminder::OPTION ) );
			self::assertFalse( \Linker\Commerce\Mail\Capacity::transaction_active() );
	}

	/** Missing or failed aggregate data stays visible in the digest and creates no bogus message. */
	public function test_failed_summary_does_not_mean_zero_or_spend_a_reminder(): void {
		$summary = new ReviewSummary( static fn () => new \WP_Error( 'fixture', 'Unavailable.' ) );
		$marker  = self::newest_mail_job();
		( new ReviewReminder( $summary ) )->tick();
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
		$this->assertFalse( get_option( ReviewReminder::OPTION ) );
		$block = new PendingReviews( $summary );
		$this->assertCount( 1, $block->entries() );
		$this->assertStringContainsString( 'unavailable', $block->entries()[0]['label'] );
		$this->assertSame( '', $block->entries()[0]['url'] );
	}
}
