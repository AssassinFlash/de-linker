<?php
/**
 * Reads the DeepSeek key without executing a config file or persisting secrets.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Process credentials take precedence over the user's private env file.
 */
final class Credentials {

	/**
	 * Reads only DEEPSEEK_API_KEY; the optional directory isolates file tests.
	 *
	 * @param string|null $config_directory Private config directory; null resolves HOME.
	 * @phpstan-impure Reads mutable process credentials and the filesystem.
	 */
	public static function deepseek_key( ?string $config_directory = null ): string {
		$process = getenv( 'DEEPSEEK_API_KEY' );
		if ( is_string( $process ) && '' !== trim( $process ) ) {
			return trim( $process );
		}
		$environment = $_ENV['DEEPSEEK_API_KEY'] ?? ''; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- process credentials, not request input.
		if ( is_string( $environment ) && '' !== trim( $environment ) ) {
			return trim( $environment );
		}
		if ( null === $config_directory ) {
			$directory = getenv( 'HOME' );
			if ( ! is_string( $directory ) || '' === $directory ) {
				return '';
			}
			$config_directory = $directory . '/.config/terravolt-builder';
		}
		$path = $config_directory . '/deepseek.env';
		if ( ! is_readable( $path ) ) {
			return '';
		}
		$bytes = file_get_contents( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- private config outside the website and repository.
		foreach ( false === $bytes ? array() : explode( "\n", $bytes ) as $line ) {
			$line = trim( $line );
			if ( str_starts_with( $line, '#' ) || ! str_contains( $line, '=' ) ) {
				continue;
			}
			list( $name, $value ) = explode( '=', $line, 2 );
			if ( 'DEEPSEEK_API_KEY' === trim( $name ) ) {
				return trim( $value, " \t\r\n\"'" );
			}
		}
		return '';
	}
}
