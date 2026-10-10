<?php
/**
 * Static-analysis stubs for wp-cli: wp-cli is neither in the WordPress stubs
 * nor shipped by this plugin, and the runtime doubles (wordpress.php) name
 * their exception through a class_alias, which static analysis cannot see.
 * phpstan reads this file via scanFiles; the test bootstrap never loads it.
 * Only the surface production code and tests touch is declared.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

// phpcs:ignoreFile -- third-party symbol declarations for static analysis; the
// WordPress prefix and naming sniffs do not apply to wp-cli's own names.

namespace {
	class WP_CLI {

		/**
		 * The commands add_command registered; the runtime double records them
		 * and the dispatch test reads them back.
		 *
		 * @var array<string, object>
		 */
		public static $registered_commands = array();

		public static function error( string $message ): void {
			throw new \WP_CLI\ExitException( $message );
		}

		public static function log( string $message ): void {
		}

		public static function success( string $message ): void {
		}

		public static function warning( string $message ): void {
		}

		/**
		 * @param string                $name    Command name.
		 * @param callable|object|array $command The command implementation.
		 */
		public static function add_command( string $name, $command ): void {
		}
	}
}

namespace WP_CLI {

	class ExitException extends \Exception {
	}
}
