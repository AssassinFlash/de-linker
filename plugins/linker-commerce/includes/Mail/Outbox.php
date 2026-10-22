<?php
/**
 * Every outgoing email: sent at once when the quota allows, otherwise queued.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use WP_Error;
use Linker\Commerce\Inquiry\Assessment\Lock;
use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

	/**
	 * Takes every wp_mail() call of the site (WooCommerce's emails included) on
	 * pre_wp_mail. A message goes out at once when the Throttle allows; otherwise,
	 * and after a failed attempt, it waits in the JobStore for an Action Scheduler
	 * action. Retries follow RETRY_DELAYS, then the message is marked failed and
	 * logged. Each attempt sends the message once, recipients and blind copies
	 * together, so a retry never repeats a mailbox that already received it.
	 *
	 * The queue is written from the arguments this filter is handed, before
	 * TestMode::redirect() changes who the attempt is sent to. WordPress runs
	 * the wp_mail filter before pre_wp_mail (wp-includes/pluggable.php), so a
	 * rewrite registered on wp_mail would already have replaced those arguments
	 * by the time this filter runs, and the queue would no longer be the routing
	 * data an assertion reads (AGENTS.md §5).
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
	 * Explicit marker of the message being delivered, kept across test redirection.
	 *
	 * @var bool
	 */
	private bool $internal = false;

	/**
	 * Whether this pass must use PHP mail after an SMTP failure.
	 *
	 * @var bool
	 */
	private bool $fallback = false;

	/**
	 * Whether the active delivery selected SMTP, including identity rejection.
	 *
	 * @var bool
	 */
	private bool $smtp_attempt = false;

	/**
	 * Sets up the outbox.
	 *
	 * @param JobStore     $jobs      The queue.
	 * @param Throttle     $throttle  The sending rate.
	 * @param TestMode     $test_mode The test-mode switch of outgoing mail.
	 * @param InternalSmtp $smtp      Internal authenticated transport (#297).
	 * @param SmtpOutcome  $outcome   The last SMTP result for health reporting.
	 */
	public function __construct(
		private readonly JobStore $jobs,
		private readonly Throttle $throttle,
		private readonly TestMode $test_mode = new TestMode(),
		private readonly InternalSmtp $smtp = new InternalSmtp(),
		private readonly SmtpOutcome $outcome = new SmtpOutcome()
	) {
	}

	/**
	 * Takes over a wp_mail() call; runs on pre_wp_mail.
	 *
	 * @param  null|bool            $pre  Value from an earlier filter, null to send.
	 * @param  array<string, mixed> $atts The call's arguments.
	 * @return null|bool Null to let wp_mail() send (our own attempt), true once the message is sent or queued.
	 */
	public function intercept( $pre, array $atts ) {
		if ( null !== $pre || $this->delivering ) {
			return $pre;
		}
		try {
			$joined = $this->jobs->transaction_active();
		} catch ( \Throwable $error ) {
			CapacityHealth::failed();
			return false;
		}
		$message = Prepared::current() ?? Message::from_wp_mail( $atts );
		$reset   = ResetNotice::take( $atts );
		$job     = '' !== $reset ? Capacity::within( $reset, fn (): int => $this->jobs->create( $message ) ) : $this->jobs->create( $message );
		if ( $job < 1 ) {
			CapacityHealth::failed();
			return false;
		}
		if ( $joined ) {
			NativeTransaction::after_commit(
				function () use ( $job ): void {
					$this->retry( $job );
				}
			);
			// Job and action join the caller's transaction. No external mail can
			// escape before commit; rollback removes both native pending rows.
			$this->schedule( $job, time() + 1 );
			return true;
		}
		Lock::run(
			'mail-job-' . $job,
			function () use ( $message, $job ): void {
				$this->attempt( $message, 0, $job );
			}
		);
		// A durable job owns the notification even when transport is deferred.
		return true;
	}

	/**
	 * Attempts a queued message again; runs on the Action Scheduler hook.
	 *
	 * @param int $job_id Job id.
	 */
	public function retry( int $job_id ): void {
		if ( $this->jobs->transaction_active() ) {
			NativeTransaction::after_commit(
				function () use ( $job_id ): void {
					$this->retry( $job_id );
				}
			);
			$this->schedule( $job_id, time() + 1 );
			return;
		}
		$inquiry = NotificationHold::inquiry( $job_id );
		$work    = function () use ( $job_id ): void {
			if ( NotificationHold::job_held( $job_id ) ) {
				return;
			}
			$locked = Lock::run(
				'mail-job-' . $job_id,
				function () use ( $job_id ): void {
					clean_post_cache( $job_id );
					$job = $this->jobs->load( $job_id );
					if ( null !== $job ) {
						$this->attempt( $job['message'], $job['attempts'], $job_id );
					}
				}
			);
			if ( ! $locked ) {
				as_schedule_single_action( time() + 1, self::HOOK, array( $job_id ), self::GROUP, true );
			}
		};
		if ( $inquiry > 0 ) {
			if ( ! Lock::run( 'release-' . $inquiry, $work ) && ! NotificationHold::job_held( $job_id ) ) {
				as_schedule_single_action( time() + 1, self::HOOK, array( $job_id ), self::GROUP, true );
			}
			return;
		}
		$work();
	}

	/**
	 * Keeps the error of a failed send; runs on wp_mail_failed.
	 *
	 * @param WP_Error $error The failure.
	 */
	public function remember_error( WP_Error $error ): void {
		if ( $this->delivering ) {
			// SMTP server replies may echo authentication data. Only this fixed
			// diagnostic enters the retry queue, logger and digest (#297).
			$this->error = $this->internal ? InternalSmtp::FAILURE_MESSAGE : $error->get_error_message();
		}
	}

	/**
	 * Native phpmailer_init hook, scoped to an active Outbox attempt.
	 *
	 * @param PHPMailer $mailer WordPress's reusable mailer.
	 * @throws Exception When selected SMTP configuration disappears before setup.
	 */
	public function configure_mailer( PHPMailer $mailer ): void {
		if ( $this->delivering ) {
			$this->smtp_attempt = $this->internal && ! $this->fallback;
			if ( ! $this->smtp->configure( $mailer, $this->smtp_attempt ) && $this->smtp_attempt ) {
				throw new Exception( esc_html( InternalSmtp::FAILURE_MESSAGE ) );
			}
		}
	}

	/**
	 * Sends a message now, or queues it for its next slot or retry.
	 *
	 * @param  Message $message  Message.
	 * @param  int     $attempts Failed attempts so far.
	 * @param  int     $job_id   Job id, 0 while the message is not queued.
	 * @return bool Whether the message was sent in this attempt.
	 */
	private function attempt( Message $message, int $attempts, int $job_id ): bool {
		$now       = time();
		$critical  = $message->critical || ( $job_id > 0 && $this->jobs->critical( $job_id ) );
		$transport = $message->is_internal() && $this->smtp->available() ? Throttle::SMTP : Throttle::PHP;
		$slot      = $this->throttle->reserve( $now, $transport, $critical, $message->category );
		if ( $slot > $now ) {
			$this->schedule( $job_id > 0 ? $job_id : $this->jobs->create( $message ), $slot );
			return false;
		}

		$this->delivering = true;
		$this->error      = '';
		$this->internal   = $message->is_internal();
		// Test mode rewrites the recipients on the way out alone. $message is
		// what was queued, and it keeps the recipients the routing data names
		// (Mail\TestMode); only this attempt's copy is redirected.
		$delivery       = $this->test_mode->redirect( $message );
		$this->fallback = Throttle::PHP === $transport;
		try {
			$sent = $this->deliver( $delivery );
			if ( $this->smtp_attempt ) {
				$reason = $this->smtp->failure_reason();
				$this->outcome->record( $sent, $reason );
				if ( ! $sent ) {
					wc_get_logger()->warning(
						'Internal SMTP failed; PHP fallback requires its own available budget. Reason: ' . $reason . '.',
						array( 'source' => self::LOG_SOURCE )
					);
						$fallback_now = time();
						$wait_until   = $this->throttle->reserve( $fallback_now, Throttle::PHP, $critical, $message->category );
					if ( $wait_until === $fallback_now ) {
						$this->fallback = true;
						$sent           = $this->deliver( $delivery );
					}
				}
			}
		} finally {
			$this->delivering   = false;
			$this->internal     = false;
			$this->fallback     = false;
			$this->smtp_attempt = false;
		}

		if ( $sent ) {
			if ( $job_id > 0 ) {
				$this->jobs->delete( $job_id );
			}
			// The one record of a delivery that every PHP the site runs on
			// writes. The host's mail.log is written by the web PHP alone: the
			// cron runner (`wp cron event run --due-now`, docs/specs/17-cutover.md)
			// runs the CLI PHP, whose mail.log is unset (read on the host
			// 2026-10-17), so the digest, the health alert and every retry left
			// no trace there.
			wc_get_logger()->info(
				sprintf( 'Email "%s" sent to %s%s.', $message->subject, implode( ', ', $delivery->to ), self::blind_copies( $delivery->headers ) ),
				array( 'source' => self::LOG_SOURCE )
			);
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
		$this->schedule( $job_id, $this->throttle->next_message_slot( $now + $delay, $message, $critical ) );
		wc_get_logger()->warning(
			sprintf( 'Email "%s" to %s failed (attempt %d: %s); next attempt in %d s.', $message->subject, implode( ', ', $message->to ), $attempts, $this->error, $delay ),
			array( 'source' => self::LOG_SOURCE )
		);
		return false;
	}

	/**
	 * One native delivery, clearing the reusable mailer's authentication on exit.
	 *
	 * @param Message $message Send-side copy, already redirected for tests.
	 */
	private function deliver( Message $message ): bool {
		$this->smtp_attempt = false;
		try {
			return wp_mail( $message->to, $message->subject, $message->body, $message->headers, $message->attachments );
		} catch ( Exception $error ) {
			// phpmailer_init runs outside WordPress's send() catch. Both this
			// path and wp_mail_failed use one secret-free diagnostic (#297).
			$this->error = $this->internal ? InternalSmtp::FAILURE_MESSAGE : $error->getMessage();
			return false;
		} finally {
			if ( isset( $GLOBALS['phpmailer'] ) && $GLOBALS['phpmailer'] instanceof PHPMailer ) {
				$this->smtp->reset( $GLOBALS['phpmailer'] );
			}
		}
	}

	/**
	 * Schedules an attempt of a queued message.
	 *
	 * @param int $job_id Job id.
	 * @param int $time   Unix time of the attempt.
	 */
	private function schedule( int $job_id, int $time ): void {
		if ( $job_id > 0 ) {
			$this->jobs->reschedule( $job_id, $time );
		}
	}

	/**
	 * ", bcc …" for the log line of a delivery, '' without blind copies.
	 *
	 * @param string[] $headers Header lines, "Name: value".
	 */
	private static function blind_copies( array $headers ): string {
		foreach ( $headers as $line ) {
			if ( 0 === stripos( $line, 'Bcc:' ) ) {
				return ', bcc ' . trim( substr( $line, 4 ) );
			}
		}
		return '';
	}
}
