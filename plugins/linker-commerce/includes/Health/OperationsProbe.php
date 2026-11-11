<?php
/**
 * Read-only operational measurements behind the digest's operations block.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Health;

use Closure;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Protection\BusinessCapacity;
use WP_Error;

/**
 * Every dimension reports its own failure: an unreadable bound is never a
 * silent zero, the rule ReviewSummary already applies to the review queue.
 * Nothing here writes, reserves, charges or sends.
 */
final class OperationsProbe {

	/**
	 * Pending actions read in one ordered page. The most overdue actions are the
	 * oldest end of the date-ascending page, so a full page still counts them
	 * exactly; the block reports the total as a floor rather than loading an
	 * unbounded queue.
	 */
	public const QUEUE_SAMPLE = 500;

	/**
	 * Production readers of the same options and mail ledger. The two closures
	 * exist for the unit tests, which never open a database.
	 *
	 * @param Throttle      $throttle  Rolling transport budgets (#545).
	 * @param ReviewSummary $reviews   Quarantined inquiries awaiting staff review.
	 * @param Closure|null  $occupancy Business envelope reader; null uses the live registry.
	 * @param Closure|null  $manifest  Publication manifest reader; null uses the live manifest.
	 */
	public function __construct(
		private readonly Throttle $throttle = new Throttle(),
		private readonly ReviewSummary $reviews = new ReviewSummary(),
		private readonly ?Closure $occupancy = null,
		private readonly ?Closure $manifest = null
	) {}

	/**
	 * Pending Action Scheduler deliveries, how late the latest one is, and the
	 * overdue tail.
	 *
	 * Pending actions are normally scheduled in the future — production on
	 * 2026-11-11 held 17, the earliest 36 minutes ahead — so a queue is healthy
	 * while nothing is past its slot. An action is overdue when it sits more
	 * than a day past that slot: Outbox::RETRY_DELAYS ends at 86 400 seconds,
	 * so nothing a day late is still retrying, it is stuck. The 2026-11-11 host
	 * MySQL outage took the queue away for 90 minutes and nothing pushed an
	 * alert; #535 left 38 real notifications held after the 2026-10-22 wave
	 * (docs/specs/545-mail-capacity/SPEC.md).
	 *
	 * @param int $now Unix time of the digest.
	 * @return array{pending: int, capped: bool, lateness: int, overdue: int}|WP_Error
	 */
	public function queue( int $now ): array|WP_Error {
		$actions = $this->pending_actions();
		if ( ! is_array( $actions ) ) {
			return new WP_Error( 'operations_queue_unreadable', 'The delivery queue could not be read.' );
		}
		$lateness = 0;
		$overdue  = 0;
		$dated    = 0;
		foreach ( $actions as $action ) {
			$slot = $this->scheduled( $action );
			if ( 0 === $slot ) {
				continue;
			}
			++$dated;
			$late     = max( 0, $now - $slot );
			$lateness = max( $lateness, $late );
			if ( $late > DAY_IN_SECONDS ) {
				++$overdue;
			}
		}
		if ( array() !== $actions && 0 === $dated ) {
			return new WP_Error( 'operations_queue_unreadable', 'The delivery queue could not be read.' );
		}
		return array(
			'pending'  => count( $actions ),
			'capped'   => count( $actions ) === self::QUEUE_SAMPLE,
			'lateness' => $lateness,
			'overdue'  => $overdue,
		);
	}

	/**
	 * Attempts already charged in each channel's rolling day.
	 *
	 * @param int $now Unix time of the digest.
	 * @return array{php: int, smtp: int}|WP_Error
	 */
	public function mail( int $now ): array|WP_Error {
		$php  = $this->throttle->used( $now, Throttle::PHP );
		$smtp = $this->throttle->used( $now, Throttle::SMTP );
		if ( null === $php || null === $smtp ) {
			return new WP_Error( 'operations_mail_unreadable', 'The mail budget could not be read.' );
		}
		return array(
			'php'  => $php,
			'smtp' => $smtp,
		);
	}

	/**
	 * Unhandled inquiries of the site envelope and quarantined inquiries.
	 *
	 * @return array{unhandled: int, bytes: int, quarantined: int}|WP_Error
	 */
	public function intake(): array|WP_Error {
		$occupancy = null !== $this->occupancy ? ( $this->occupancy )() : BusinessCapacity::occupancy();
		if ( $occupancy instanceof WP_Error ) {
			return $occupancy;
		}
		if ( ! is_array( $occupancy ) || ! is_int( $occupancy['unhandled'] ?? null ) || ! is_int( $occupancy['bytes'] ?? null ) ) {
			return new WP_Error( 'operations_intake_unreadable', 'The unhandled inquiry envelope could not be read.' );
		}
		$reviews = $this->reviews->get();
		if ( $reviews instanceof WP_Error ) {
			return new WP_Error( 'operations_quarantine_unreadable', 'The pending-review queue could not be read.' );
		}
		return array(
			'unhandled'   => $occupancy['unhandled'],
			'bytes'       => $occupancy['bytes'],
			'quarantined' => $reviews['count'],
		);
	}

	/**
	 * Prepared products per consumer, from the current manifest.
	 *
	 * The manifest is the same authoritative read the staff CLI prints
	 * (`wp linker-commerce publication manifest`) and the dry-run used during
	 * the 2026-11-11 recovery; a failed read is an alert, not a zero.
	 *
	 * @return array{engineering: int, knowledge: int, total: int}|WP_Error
	 */
	public function publication(): array|WP_Error {
		if ( null !== $this->manifest ) {
			$manifest = ( $this->manifest )();
		} else {
			try {
				$manifest = Publication::manifest();
			} catch ( \Throwable $error ) {
				return new WP_Error( 'operations_publication_unreadable', 'The publication manifest could not be read.' );
			}
		}
		if ( ! is_array( $manifest['products'] ?? null ) ) {
			return new WP_Error( 'operations_publication_unreadable', 'The publication manifest could not be read.' );
		}
		$counts = array(
			'engineering' => 0,
			'knowledge'   => 0,
			'total'       => 0,
		);
		foreach ( $manifest['products'] as $product ) {
			if ( ! is_array( $product ) || ! is_array( $product['ready'] ?? null ) ) {
				return new WP_Error( 'operations_publication_unreadable', 'The publication manifest could not be read.' );
			}
			++$counts['total'];
			foreach ( array( 'engineering', 'knowledge' ) as $consumer ) {
				if ( true === ( $product['ready'][ $consumer ] ?? false ) ) {
					++$counts[ $consumer ];
				}
			}
		}
		return $counts;
	}

	/**
	 * The native pending page, deliberately untyped: Action Scheduler returns
	 * null on a failed read, and that must never look like an empty queue.
	 *
	 * @return mixed
	 */
	private function pending_actions() {
		return as_get_scheduled_actions(
			array(
				'status'   => 'pending',
				'per_page' => self::QUEUE_SAMPLE,
				'orderby'  => 'date',
				'order'    => 'ASC',
			)
		);
	}

	/**
	 * The slot a pending action sits in, or 0 when it carries none.
	 *
	 * @param mixed $action Native pending action.
	 */
	private function scheduled( mixed $action ): int {
		if ( ! is_object( $action ) || ! method_exists( $action, 'get_schedule' ) ) {
			return 0;
		}
		$schedule = $action->get_schedule();
		if ( ! is_object( $schedule ) || ! method_exists( $schedule, 'get_date' ) ) {
			return 0;
		}
		$date = $schedule->get_date();
		return $date instanceof \DateTimeInterface ? $date->getTimestamp() : 0;
	}
}
