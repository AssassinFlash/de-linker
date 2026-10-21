<?php
/**
 * Independent recovery heartbeat, suitable for the host's actual cron.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

/** Run every minute, also when WordPress has no visitors. */
final class RecoveryCommand {
	/** Release expired inquiries and repair a committed Outbox handoff. */
	public function __invoke(): void {
		$count = ( new Queue() )->recover();
		\WP_CLI::success( sprintf( 'Examined %d pending inquiry assessments.', $count ) );
	}
}
