<?php
/** Bounded reminders for the staff review queue.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Health;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Settings\Options;

/** Runs from the existing independent minute recovery, never a public request. */
final class ReviewReminder {
	public const OPTION = 'linker_commerce_review_reminders';
	/** Owner-approved hourly follow-up and strict 24-message rolling daily ceiling (#545). */
	public const PER_DAY = 24;
	/**
	 * Connect the read boundary and the existing queue.
	 *
	 * @param ReviewSummary $summary Read-only aggregate.
	 * @param JobStore      $jobs Existing mail queue.
	 */
	public function __construct( private readonly ReviewSummary $summary = new ReviewSummary(), private readonly JobStore $jobs = new JobStore() ) {}
	/** Hand one aggregate to Outbox at the first recovery tick, subject to durable bounds. */
	public function tick(): void {
		Lock::run(
			'review-reminder',
			function (): void {
				global $wpdb;
				$data = $this->summary->get();
				if ( is_wp_error( $data ) ) {
					return; }
			// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Cache-free state under the native connection mutex, atomically committed with its job.
				$raw   = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", self::OPTION ) );
				$state = is_string( $raw ) ? json_decode( $raw, true ) : array();
				if ( ! is_array( $state ) || '' !== $wpdb->last_error || ( null !== $raw && ! is_array( $state['events'] ?? null ) ) ) {
					return; }
				$now    = time();
				$events = array_values( array_filter( is_array( $state['events'] ?? null ) ? $state['events'] : array(), static fn ( $time ): bool => is_int( $time ) && $time > $now - DAY_IN_SECONDS ) );
				if ( 0 === $data['count'] ) {
					$state['active'] = false;
				} elseif ( count( $events ) >= self::PER_DAY || ( true === ( $state['active'] ?? false ) && (int) ( $state['last'] ?? 0 ) > $now - HOUR_IN_SECONDS ) || ( isset( $state['job'] ) && null !== $this->jobs->load( (int) $state['job'] ) ) ) {
					return;
				}
				$state['events'] = $events;
				$job             = 0;
				$action          = 0;
				$message         = $data['count'] > 0 ? $this->message( $data, $now ) : null;
				$slot            = null !== $message ? ( new Throttle() )->next_message_slot( $now, $message ) : $now;
				if ( ! \Linker\Commerce\Mail\BudgetTransaction::begin() ) {
					return; }
				try {
					if ( null !== $message ) {
						$job      = $this->jobs->create( $message );
						$readback = $this->jobs->load( $job );
						if ( null === $readback || $readback['message']->to_array() !== $message->to_array() ) {
							throw new \RuntimeException( 'review_reminder_job_failed' ); }
						$action = as_schedule_single_action( max( $now + 1, $slot ), Outbox::HOOK, array( $job ), Outbox::GROUP, true );
						if ( $action <= 0 ) {
							throw new \RuntimeException( 'review_reminder_schedule_failed' ); }
						$state['events'][] = $now;
						$state['active']   = true;
						$state['last']     = $now;
						$state['job']      = $job;
					}
					$written = $wpdb->query( $wpdb->prepare( "INSERT INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, %s, 'off') ON DUPLICATE KEY UPDATE option_value = VALUES(option_value)", self::OPTION, wp_json_encode( $state ) ) );
					if ( false === $written ) {
						throw new \RuntimeException( 'review_reminder_state_failed' ); }
					if ( false === $wpdb->query( 'COMMIT' ) ) {
						throw new \RuntimeException( 'review_reminder_commit_failed' ); }
					wp_cache_delete( self::OPTION, 'options' );
					wp_cache_delete( 'notoptions', 'options' );
				} catch ( \Throwable $error ) {
					$wpdb->query( 'ROLLBACK' );
					if ( $job > 0 ) {
						clean_post_cache( $job ); }
					if ( $action > 0 ) {
						try {
							\ActionScheduler::store()->cancel_action( $action ); } catch ( \Throwable $ignored ) {
												/* The native transaction already removed this action. */
							return; }
					}
				}
			// phpcs:enable
			}
		);
	}
	/**
	 * Render only the staff aggregate and the native admin URL.
	 *
	 * @param array{count:int,oldest:int,url:string} $data Verified queue aggregate.
	 * @param int                                    $now Snapshot time.
	 */
	private function message( array $data, int $now ): Message {
		$locale = new LocaleSwitch();
		$locale->to( LocaleSwitch::team_default() );
		try {
			$subject = __( 'Saved inquiries need staff review', 'linker-commerce' );
			/* translators: 1: count, 2: oldest age, 3: snapshot time, 4: native staff review URL. */
			$body    = sprintf( __( "Saved inquiries awaiting staff review: %1\$d.\nOldest inquiry: %2\$s ago.\nCount checked: %3\$s.\nReview saved inquiries: %4\$s\n\nThese inquiries are saved. Their individual team notifications have not been released.", 'linker-commerce' ), $data['count'], human_time_diff( $data['oldest'], $now ), wp_date( 'Y-m-d H:i:s T', $now ), $data['url'] );
			$options = new Options();
			$sender  = $options->notify_sender();
			$headers = Message::mark_internal( array( sprintf( 'From: %s <%s>', $sender->name, $sender->email ), 'Content-Type: text/plain; charset=UTF-8' ) );
			if ( array() !== $options->notify_bcc() ) {
				$headers[] = 'Bcc: ' . implode( ', ', $options->notify_bcc() ); }
			return new Message( array( $options->notify_to() ), $subject, $body, $headers, array(), true );
		} finally {
			$locale->back(); }
	}
}
