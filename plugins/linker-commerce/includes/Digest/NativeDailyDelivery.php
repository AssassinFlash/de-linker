<?php
/**
 * One ordinary digest admission per Berlin day.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use DateTimeImmutable;
use DateTimeZone;
use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\CapacityHealth;
use Linker\Commerce\Mail\Prepared;

/** Overlapping cron consumers share one ordinary delivery receipt. */
final class NativeDailyDelivery implements Delivery {

	/**
	 * Captures the native message, admits it once, then hands that exact message to Outbox.
	 *
	 * The receipt is not a critical reservation: the digest stays on the ordinary
	 * transport path, and a second consumer cannot create another job.
	 *
	 * @param DigestEmail $email Complete native email producer.
	 * @param Block[]     $blocks Frozen business blocks.
	 */
	public function send( DigestEmail $email, array $blocks ): void {
		$message = Prepared::capture( static fn (): null => $email->send_report( $blocks ) );
		if ( null === $message || $message->critical ) {
			$this->unavailable( 'digest_native_capture_unavailable' );
			return;
		}

		$sent = Capacity::with_ordinary_delivery(
			$this->operation(),
			static fn (): bool => Prepared::within(
				$message,
				static fn (): bool => wp_mail(
					$message->to,
					$message->subject,
					$message->body,
					$message->headers,
					$message->attachments
				)
			)
		);
		if ( true !== $sent && ! Capacity::ordinary_delivery_duplicate() ) {
			$this->unavailable( 'digest_native_delivery_unavailable' );
		}
	}

	/**
	 * Stable server-owned operation identity; independent of request input.
	 */
	private function operation(): string {
		$now = new DateTimeImmutable( 'now', new DateTimeZone( Scheduler::TIMEZONE ) );
		return 'digest:' . $now->format( 'Y-m-d' );
	}

	/**
	 * A missing digest is a failure, never an unbounded direct send.
	 *
	 * @param string $reason Fixed operational reason.
	 */
	private function unavailable( string $reason ): void {
		CapacityHealth::failed();
		wc_get_logger()->error( 'Daily digest was not admitted: ' . $reason . '.', array( 'source' => 'linker-mail' ) );
	}
}
