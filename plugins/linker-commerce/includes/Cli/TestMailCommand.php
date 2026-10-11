<?php
/**
 * The `wp linker-commerce test-mail` command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Cli;

use Linker\Commerce\Mail\TestMode;
use WP_CLI;

/**
 * Sets and removes the test-mode switch of outgoing mail (Mail\TestMode,
 * AGENTS.md §5): while it is on, every message the site sends goes to one
 * address, so a test scenario sends exactly one mail per message and no
 * customer, team or Bcc mailbox is reached. Turn it off after the scenario.
 */
final class TestMailCommand {

	/**
	 * Sets up the command.
	 *
	 * @param TestMode $test_mode The test-mode switch.
	 */
	public function __construct( private readonly TestMode $test_mode = new TestMode() ) {}

	/**
	 * Sends every outgoing email to one address.
	 *
	 * ## OPTIONS
	 *
	 * [--to=<address>]
	 * : The single address. Defaults to chester@de-linker.com.
	 *
	 * ## EXAMPLES
	 *
	 *     wp linker-commerce test-mail on
	 *     wp linker-commerce test-mail on --to=tester@example.test
	 *
	 * @when after_wp_load
	 *
	 * @param array<int, string>   $args       Positional arguments.
	 * @param array<string, mixed> $assoc_args Options.
	 */
	public function on( array $args, array $assoc_args ): void {
		unset( $args );
		$address = isset( $assoc_args['to'] ) ? (string) $assoc_args['to'] : TestMode::DEFAULT_TO;
		if ( ! $this->test_mode->enable( $address ) ) {
			WP_CLI::error( sprintf( '"%s" is not an email address: test mode stays off.', $address ) );
		}
		WP_CLI::success( sprintf( 'Test mode is on: every email goes to %s. Remove it with `wp linker-commerce test-mail off`.', $this->test_mode->address() ) );
	}

	/**
	 * Sends emails to their recipients again.
	 *
	 * ## EXAMPLES
	 *
	 *     wp linker-commerce test-mail off
	 *
	 * @when after_wp_load
	 *
	 * @param array<int, string>   $args       Positional arguments.
	 * @param array<string, mixed> $assoc_args Options.
	 */
	public function off( array $args, array $assoc_args ): void {
		unset( $args, $assoc_args );
		if ( ! $this->test_mode->disable() ) {
			WP_CLI::error( 'The switch could not be removed: test mode is still on.' );
		}
		WP_CLI::success( 'Test mode is off: emails go to their recipients again.' );
	}

	/**
	 * Reports whether test mode is on, and where mail goes.
	 *
	 * ## EXAMPLES
	 *
	 *     wp linker-commerce test-mail status
	 *
	 * @when after_wp_load
	 *
	 * @param array<int, string>   $args       Positional arguments.
	 * @param array<string, mixed> $assoc_args Options.
	 */
	public function status( array $args, array $assoc_args ): void {
		unset( $args, $assoc_args );
		$address = $this->test_mode->address();
		if ( '' === $address ) {
			WP_CLI::log( 'Test mode is off: emails go to their recipients.' );
			return;
		}
		WP_CLI::log( sprintf( 'Test mode is on: every email goes to %s.', $address ) );
	}
}
