<?php
/**
 * The `wp linker-commerce present` command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Cli;

use Linker\Commerce\Presentation\Templates;
use Linker\Commerce\Presentation\Tokens;
use WP_CLI;

/**
 * Writes LiveCanvas templates and Additional CSS from the files in this plugin.
 */
final class PresentCommand {

	/**
	 * Installs the presentation layer into the current site: LiveCanvas templates,
	 * Additional CSS tokens, and (optionally) stripping tokens from header partials.
	 *
	 * ## OPTIONS
	 *
	 * [--detach-partials]
	 * : Also remove the inlined tokens.css block from LiveCanvas header/footer partials.
	 *
	 * @when after_wp_load
	 *
	 * @param array<int, string>    $args       Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function __invoke( array $args, array $assoc_args ): void {
		unset( $args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator: wp linker-commerce present --user=<admin>.' );
		}
		$settings = get_option( 'lc_settings', array() );
		if ( ! is_array( $settings ) ) {
			$settings = array();
		}
		$settings['enable-dynamic-templating'] = 1;
		update_option( 'lc_settings', $settings );

		$report = ( new Templates() )->sync();
		WP_CLI::log( sprintf( 'templates: created %d, updated %d, unchanged %d', $report['created'], $report['updated'], $report['unchanged'] ) );

		( new Tokens() )->install();
		WP_CLI::log( 'tokens: Additional CSS' );

		if ( isset( $assoc_args['detach-partials'] ) ) {
			$stripped = ( new Tokens() )->detach_from_partials();
			WP_CLI::log( sprintf( 'partials: stripped tokens from %d', $stripped ) );
		}

		if ( class_exists( \WindPress\WindPress\Core\Cache::class ) ) {
			WP_CLI::log( 'windpress: cache present (compile from the WindPress admin)' );
		}

		WP_CLI::success( 'Presentation installed.' );
	}
}
