<?php
/**
 * The `wp linker-commerce registration-blocks` command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Cli;

use Linker\Commerce\Registration\BlockedRegistrations;
use WP_CLI;

/**
 * Prints the counted bot refusals of the public registration form (#225): a
 * blocked registration writes no account and no mail, so this counter is its
 * evidence. `--reset` starts the count over.
 */
final class RegistrationBlocksCommand {

	/**
	 * Prints the counts, or clears them.
	 *
	 * ## OPTIONS
	 *
	 * [--reset]
	 * : Remove the stored counts.
	 *
	 * @when after_wp_load
	 *
	 * @param array<int, string>   $args       Positional arguments.
	 * @param array<string, mixed> $assoc_args Options.
	 */
	public function __invoke( array $args, array $assoc_args ): void {
		unset( $args );
		if ( isset( $assoc_args['reset'] ) ) {
			BlockedRegistrations::reset();
			WP_CLI::success( 'Registration block counts cleared.' );
			return;
		}
		$counts = BlockedRegistrations::counts();
		if ( 0 === $counts['total'] ) {
			WP_CLI::log( 'No blocked registrations.' );
			return;
		}
		foreach ( $counts['counts'] as $reason => $count ) {
			WP_CLI::log( sprintf( '%s: %d', $reason, $count ) );
		}
		WP_CLI::log( sprintf( 'total: %d · last: %s', $counts['total'], $counts['last'] ) );
	}
}
