<?php
/** Disabled automatic reminder producer; retained for existing recovery callbacks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Health;

use Linker\Commerce\Mail\JobStore;

/** Owner ruling 2026-10-23: review reminders must consume no mail allowance. */
final class ReviewReminder {
	/** Historical state remains intact for audit and rollback. */
	public const OPTION = 'linker_commerce_review_reminders';
	/** Historical ceiling, retained for existing state readers, not an emission policy. */
	public const PER_DAY = 24;

	/**
	 * Keep the existing callback construction contract without reading its data.
	 *
	 * @param ReviewSummary $summary Historical aggregate reader, deliberately unused.
	 * @param JobStore      $jobs Historical queue, deliberately unused.
	 */
	public function __construct( ReviewSummary $summary = new ReviewSummary(), JobStore $jobs = new JobStore() ) {
		unset( $summary, $jobs );
	}

	/** Existing recovery registration remains callable without producing mail or state writes. */
	public function tick(): void {
		// Permanently disabled by the owner; see docs/specs/533-stop-review-reminders.md.
	}
}
