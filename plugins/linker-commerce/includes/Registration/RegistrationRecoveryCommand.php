<?php
/**
 * Independent native recovery of the bounded pending registration handoff.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * The same durable source as native minute recovery; never creates another queue.
 */
final class RegistrationRecoveryCommand {

	/**
	 * Recover each pending native notice without a customer retry or page visit.
	 */
	public function __invoke(): void {
		\WP_CLI::success( sprintf( 'Examined %d pending registration accounts.', RegistrationNotices::recover() ) );
	}
}
