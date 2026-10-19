<?php
/**
 * Runtime stand-in for WP-CLI. PHPStan reads tests/phpstan/wp-cli.php instead.
 *
 * @package Linker\I18n
 */

// phpcs:disable

declare( strict_types = 1 );

namespace WP_CLI {
	if ( ! class_exists( ExitException::class, false ) ) {
		/**
		 * Stands in for exit() so a test can read the exit code.
		 */
		class ExitException extends \Exception {}
	}
}

namespace {
	if ( ! class_exists( 'WP_CLI', false ) ) {
		/**
		 * The lines the command prints.
		 */
		class WP_CLI {

			/**
			 * Where error() writes. A test points this at a memory stream.
			 *
			 * @var resource|null
			 */
			public static $stderr;

			/**
			 * Prints a line on standard output.
			 *
			 * @param string $message Message.
			 */
			public static function log( $message ): void {
				echo $message . "\n";
			}

			/**
			 * Prints a success line on standard output.
			 *
			 * @param string $message Message.
			 */
			public static function success( $message ): void {
				echo 'Success: ' . $message . "\n";
			}

			/**
			 * Prints an error on the captured stream and stops the command.
			 *
			 * @param string|WP_Error $message Message.
			 * @param bool|int        $exit    Exit code, or whether to exit.
			 * @throws \WP_CLI\ExitException When the command exits.
			 */
			public static function error( $message, $exit = true ): void {
				$line   = 'Error: ' . $message . "\n";
				$target = is_resource( self::$stderr ) ? self::$stderr : STDERR;
				fwrite( $target, $line );
				if ( false === $exit ) {
					return;
				}
				throw new \WP_CLI\ExitException( (string) $message, is_int( $exit ) ? $exit : 1 );
			}
		}
	}
}
