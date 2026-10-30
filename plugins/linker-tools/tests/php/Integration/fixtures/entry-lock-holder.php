<?php
/**
 * Holds one tab's cold-mint lock while the test resolves that tab.
 *
 * `php entry-lock-holder.php <wp root> <tab> <ready file> <release file>`
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.Security.ValidatedSanitizedInput, WordPress.Security.EscapeOutput, WordPress.WP.AlternativeFunctions -- a command-line fixture. The arguments are this test's own.
if ( ! isset( $argv ) ) {
	exit( 2 );
}
[ , $linker_tools_root, $linker_tools_tab, $linker_tools_ready, $linker_tools_release_file ] = $argv;
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require_once $linker_tools_root . '/wp-load.php';

global $wpdb;
$linker_tools_store = new Linker\Tools\Genie\Conversations();
$linker_tools_name  = new ReflectionMethod( $linker_tools_store, 'browser_claim_lock_name' );
$linker_tools_name->setAccessible( true );
$linker_tools_lock = (string) $linker_tools_name->invoke( $linker_tools_store, (string) $linker_tools_tab );
$linker_tools_got  = $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', $linker_tools_lock ) );
if ( '1' !== (string) $linker_tools_got ) {
	fwrite( STDERR, "entry lock was not available\n" );
	exit( 3 );
}

$linker_tools_released = false;
$linker_tools_release  = static function () use ( $wpdb, $linker_tools_lock, &$linker_tools_released ): void {
	if ( $linker_tools_released ) {
		return;
	}
	$linker_tools_released = true;
	$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $linker_tools_lock ) );
};
register_shutdown_function( $linker_tools_release );

file_put_contents( $linker_tools_ready, getmypid() . "\n", FILE_APPEND | LOCK_EX );
$linker_tools_deadline = microtime( true ) + 10;
while ( ! file_exists( $linker_tools_release_file ) ) {
	if ( microtime( true ) > $linker_tools_deadline ) {
		fwrite( STDERR, "entry lock holder was not released\n" );
		exit( 4 );
	}
	usleep( 10000 );
}
$linker_tools_release();
