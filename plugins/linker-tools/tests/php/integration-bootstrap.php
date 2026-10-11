<?php
/**
 * PHPUnit bootstrap of the integration tests: loads the local WordPress
 * instance named by LINKER_WP_ROOT, after checking that its linker-tools is
 * this checkout. Notices and deprecations of WordPress and WooCommerce
 * themselves are not turned into failures (phpunit.integration.xml.dist).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

$linker_tools_root = getenv( 'LINKER_WP_ROOT' );
if ( ! is_string( $linker_tools_root ) || ! is_file( $linker_tools_root . '/wp-load.php' ) ) {
	fwrite( STDERR, "LINKER_WP_ROOT must name the WordPress directory of a local instance (just up), e.g. ~/de-linker-local/a/wordpress.\n" ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite
	exit( 1 );
}

require_once dirname( __DIR__, 2 ) . '/vendor/autoload.php';

// A CLI request to the instance's front end: no theme, no page output.
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
// phpcs:disable WordPress.Security.ValidatedSanitizedInput -- defaults for a command-line run, read by WordPress, not by this file.
$_SERVER['HTTP_HOST']   = $_SERVER['HTTP_HOST'] ?? 'localhost';
$_SERVER['REQUEST_URI'] = $_SERVER['REQUEST_URI'] ?? '/';
// phpcs:enable
require_once $linker_tools_root . '/wp-load.php';

$linker_tools_installed = realpath( WP_PLUGIN_DIR . '/linker-tools' );
if ( realpath( dirname( __DIR__, 2 ) ) !== $linker_tools_installed || ! in_array( 'linker-tools/linker-tools.php', (array) get_option( 'active_plugins', array() ), true ) ) {
	fwrite( STDERR, "The instance's linker-tools must be this checkout and active; it is {$linker_tools_installed}.\n" ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite, WordPress.Security.EscapeOutput.OutputNotEscaped
	exit( 1 );
}
