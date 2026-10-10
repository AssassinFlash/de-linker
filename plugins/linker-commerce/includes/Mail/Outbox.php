<?php
/**
 * Every outgoing email: sent at once when the quota allows, otherwise queued.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use WP_Error;

/**
 * Takes every wp_mail() call of the site (WooCommerce's emails included) on
 * pre_wp_mail. A message goes out at once when the Throttle allows; otherwise,
 * and after a failed attempt, it waits in the JobStore for an Action Scheduler
 * action. Retries follow RETRY_DELAYS, then the message is marked failed and
 * logged. Each attempt sends the message once, recipients and blind copies
 * together, so a retry never repeats a mailbox that already received it.
 */
final class Outbox {

	/**
	 * Action Scheduler hook and group of the attempts.
	 */
	public const HOOK  = 'linker_commerce_mail_attempt';
	public const GROUP = 'linker-commerce';

	/**
	 * Seconds to wait after the first, second, … failed attempt: 1, 5 and 30
	 * minutes, then 2, 6, 12 and 24 hours (docs/specs/11-commerce.md, Mail).
	 * Together they span more than the rolling 24-hour window of the host's
	 * quota, so a message refused because the quota was used up is tried again
	 * after the window has moved on (mail-root-cause.md §5 M3, §9).
	 */
	public const RETRY_DELAYS = array( 60, 300, 1800, 7200, 21600, 43200, 86400 );

	/**
	 * Logger source of the mail log (WooCommerce → Status → Logs).
	 */
	public const LOG_SOURCE = 'linker-mail';

	/**
	 * Whether this object is calling wp_mail() itself right now.
	 *
	 * @var bool
	 */
	private bool $delivering = false;

	/**
	 * Error message of the attempt in progress.
	 *
	 * @var string
	 */
	private string $error = '';

	/**
	 * Sets up the outbox.
	 *
	 * @param JobStore $jobs     The queue.
	 * @param Throttle $throttle The sending rate.
	 */
	public function __construct(
		private readonly JobStore $jobs,
		private readonly Throttle $throttle
	) {}

	/**
	 * Takes over a wp_mail() call; runs on pre_wp_mail.
	 *
	 * @param null|bool            $pre  Value from an earlier filter, null to send.
	 * @param array<string, mixed> $atts The call's arguments.
	 * @return null|bool Null to let wp_mail() send (our own attempt), true once the message is sent or queued.
	 */
	public function intercept( $pre, array $atts ) {
		if ( null !== $pre || $this->delivering ) {
			return $pre;
		}
		$this->attempt( Message::from_wp_mail( $atts ), 0, 0 );
		return true;
	}

	/**
	 * Attempts a queued message again; runs on the Action Scheduler hook.
	 *
	 * @param int $job_id Job id.
	 */
	public function retry( int $job_id ): void {
		$job = $this->jobs->load( $job_id );
		if ( null !== $job ) {
			$this->attempt( $job['message'], $job['attempts'], $job_id );
		}
	}

	/**
	 * Keeps the error of a failed send; runs on wp_mail_failed.
	 *
	 * @param WP_Error $error The failure.
	 */
	public function remember_error( WP_Error $error ): void {
		if ( $this->delivering ) {
			$this->error = $error->get_error_message();
		}
	}

	/**
	 * Sends a message now, or queues it for its next slot or retry.
	 *
	 * @param Message $message  Message.
	 * @param int     $attempts Failed attempts so far.
	 * @param int     $job_id   Job id, 0 while the message is not queued.
	 * @return bool Whether the message was sent in this attempt.
	 */
	private function attempt( Message $message, int $attempts, int $job_id ): bool {
		$now  = time();
		$slot = $this->throttle->next_slot( $now );
		if ( $slot > $now ) {
			$this->schedule( $job_id > 0 ? $job_id : $this->jobs->create( $message ), $slot );
			return false;
		}

		$this->throttle->record( $now );
		$this->delivering = true;
		$this->error      = '';
		try {
			$sent = wp_mail( $message->to, $message->subject, $message->body, $message->headers, $message->attachments );
		} finally {
			$this->delivering = false;
		}

		if ( $sent ) {
			if ( $job_id > 0 ) {
				$this->jobs->delete( $job_id );
			}
			return true;
		}

		++$attempts;
		$job_id = $job_id > 0 ? $job_id : $this->jobs->create( $message );
		if ( $attempts > count( self::RETRY_DELAYS ) ) {
			$this->jobs->fail( $job_id, $attempts, $this->error );
			wc_get_logger()->error(
				sprintf( 'Email "%s" to %s not sent after %d attempts: %s', $message->subject, implode( ', ', $message->to ), $attempts, $this->error ),
				array( 'source' => self::LOG_SOURCE )
			);
			return false;
		}
		$this->jobs->record_failure( $job_id, $attempts, $this->error );
		$delay = self::RETRY_DELAYS[ $attempts - 1 ];
		$this->schedule( $job_id, $now + $delay );
		wc_get_logger()->warning(
			sprintf( 'Email "%s" to %s failed (attempt %d: %s); next attempt in %d s.', $message->subject, implode( ', ', $message->to ), $attempts, $this->error, $delay ),
			array( 'source' => self::LOG_SOURCE )
		);
		return false;
	}

	/**
	 * Schedules an attempt of a queued message.
	 *
	 * @param int $job_id Job id.
	 * @param int $time   Unix time of the attempt.
	 */
	private function schedule( int $job_id, int $time ): void {
		if ( $job_id > 0 ) {
			as_schedule_single_action( $time, self::HOOK, array( $job_id ), self::GROUP );
		}
	}
}
