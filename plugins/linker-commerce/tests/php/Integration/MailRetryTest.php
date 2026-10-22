<?php
/**
 * The mail queue with WordPress's mailer and Action Scheduler.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use ActionScheduler_QueueRunner;
use ActionScheduler_Store;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Throttle;

/**
 * A message whose first three sends fail is retried by Action Scheduler at the
 * set delays and delivered once (docs/specs/11-commerce.md, acceptance).
 *
 * @coversNothing
 */
final class MailRetryTest extends IntegrationTestCase {

	/**
	 * Three failures, then one delivery.
	 */
	public function test_three_failures_then_one_delivery(): void {
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		delete_option( Throttle::OPTION );
		$subject    = 'Linker integration test ' . self::tag();
		$failures   = 3;
		$deliveries = 0;
		$fail       = static function ( $mailer ) use ( &$failures ): void {
			if ( $failures > 0 ) {
				--$failures;
				$mailer->clearAllRecipients();
			}
		};
		$count      = static function ( array $mail ) use ( &$deliveries, $subject ): void {
			if ( isset( $mail['subject'] ) && $mail['subject'] === $subject ) {
				++$deliveries;
			}
		};
		add_action( 'phpmailer_init', $fail, PHP_INT_MAX );
		add_action( 'wp_mail_succeeded', $count );
		$this->later(
			static function () use ( $fail, $count ): void {
				remove_action( 'phpmailer_init', $fail, PHP_INT_MAX );
				remove_action( 'wp_mail_succeeded', $count );
			}
		);

		$this->assertTrue( wp_mail( 'buyer@example.test', $subject, 'One message, three failures.' ) );
		// This message's own job, so retries left over from earlier runs are never picked up.
		$jobs   = get_posts(
			array(
				'post_type'      => \Linker\Commerce\Mail\JobStore::POST_TYPE,
				'post_status'    => 'any',
				'posts_per_page' => 1,
				'orderby'        => 'ID',
				'order'          => 'DESC',
			)
		);
		$job_id = (int) ( $jobs[0]->ID ?? 0 );
		$delays = array();
		for ( $attempt = 1; $attempt <= 3; ++$attempt ) {
			$pending = as_get_scheduled_actions(
				array(
					'hook'     => Outbox::HOOK,
					'status'   => ActionScheduler_Store::STATUS_PENDING,
					// The retry's args are the job's id; matching the post's
					// content finds this message's retry, never another run's.
					'search'   => (string) $job_id,
					'orderby'  => 'date',
					'order'    => 'DESC',
					'per_page' => 1,
				)
			);
			$this->assertCount( 1, $pending, "A retry is scheduled after failure {$attempt}." );
			$action_id = (int) array_key_first( $pending );
			$delays[]  = $pending[ $action_id ]->get_schedule()->get_date()->getTimestamp() - time();
			ActionScheduler_QueueRunner::instance()->process_action( $action_id, 'linker integration test' );
		}

		$this->assertSame( 0, $failures );
		$this->assertSame( 1, $deliveries, 'Delivered once.' );
		foreach ( array_slice( Outbox::RETRY_DELAYS, 0, 3 ) as $index => $delay ) {
			$this->assertEqualsWithDelta( $delay, $delays[ $index ], 5, 'Retry delay ' . ( $index + 1 ) );
		}
	}
}
