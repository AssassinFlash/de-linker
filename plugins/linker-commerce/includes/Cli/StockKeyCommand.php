<?php
/**
 * The `wp linker-commerce stock-key` command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Cli;

use Linker\Commerce\Stock\PushKey;
use WP_CLI;

/**
 * Sets, replaces or removes the stock push key (ticket #69). The key is the
 * only credential of the stock push endpoint; it lives as its SHA-256 hash
 * in the option PushKey::OPTION and is never printed after the one run that
 * generated it. No key set means the endpoint rejects everything — the
 * dormant state the channel ships in.
 */
final class StockKeyCommand {

	/**
	 * Sets (or generates) the push key, or removes it.
	 *
	 * ## OPTIONS
	 *
	 * [--set=<key>]
	 * : Store this key. Without the option a key is generated and printed
	 * once — pass it to the ERP and keep it elsewhere; it cannot be read
	 * back.
	 *
	 * [--clear]
	 * : Remove the key: the endpoint rejects every request again.
	 *
	 * [--user=<login>]
	 * : Run as the given administrator.
	 *
	 * @when after_wp_load
	 *
	 * @param array<int, string>   $args       Positional arguments.
	 * @param array<string, mixed> $assoc_args Options.
	 */
	public function __invoke( array $args, array $assoc_args ): void {
		unset( $args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator: wp linker-commerce stock-key --user=<admin>.' );
		}

		if ( isset( $assoc_args['clear'] ) ) {
			PushKey::clear();
			WP_CLI::success( 'Push key removed: the stock endpoint rejects every request until a key is set.' );
			return;
		}

		if ( isset( $assoc_args['set'] ) ) {
			$key = (string) $assoc_args['set'];
			if ( '' === $key ) {
				WP_CLI::error( '--set needs a non-empty key.' );
			}
			$hash = PushKey::set( $key );
			WP_CLI::success( sprintf( 'Push key stored (sha256 %s…). It is not readable back; replace it with another --set or remove it with --clear.', substr( $hash, 0, 12 ) ) );
			return;
		}

		$key  = PushKey::generate();
		$hash = PushKey::set( $key );
		WP_CLI::log( $key );
		WP_CLI::success( sprintf( 'New push key generated above (stored as sha256 %s…), printed this once. Pass it to the ERP as the %s header and keep it elsewhere.', substr( $hash, 0, 12 ), PushKey::HEADER ) );
	}
}
