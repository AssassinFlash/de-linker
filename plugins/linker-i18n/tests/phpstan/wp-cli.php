<?php
/**
 * Declarations of the WP-CLI API the plugin's command uses, for PHPStan.
 *
 * The package php-stubs/wp-cli-stubs has no release for wordpress-stubs 7 (its tagged
 * versions require wordpress-stubs ^6.0 or lower), so the calls are declared
 * here with WP-CLI 2.12's signatures (php/class-wp-cli.php, php/utils.php).
 * Never loaded at runtime.
 *
 * @package Linker\I18n
 */

// phpcs:disable

namespace {
	/**
	 * WP-CLI.
	 */
	class WP_CLI {

		/**
		 * Registers a command.
		 *
		 * @param string                 $name     Command name.
		 * @param callable|object|string $callable Command implementation.
		 * @param array<string, mixed>   $args     Arguments.
		 */
		public static function add_command( $name, $callable, $args = array() ): bool {}

		/**
		 * Prints a line.
		 *
		 * @param string $message Message.
		 */
		public static function log( $message ): void {}

		/**
		 * Prints a success message.
		 *
		 * @param string $message Message.
		 */
		public static function success( $message ): void {}

		/**
		 * Prints an error and exits.
		 *
		 * @param string|WP_Error $message Message.
		 * @param bool|int        $exit    Exit code, or whether to exit.
		 * @return never
		 */
		public static function error( $message, $exit = true ) {}
	}
}

namespace WP_CLI\Utils {
	/**
	 * Prints items in a format.
	 *
	 * @param string                           $format Format.
	 * @param array<int, array<string, mixed>> $items  Items.
	 * @param array<int, string>|string        $fields Fields.
	 */
	function format_items( $format, $items, $fields ): void {}
}
