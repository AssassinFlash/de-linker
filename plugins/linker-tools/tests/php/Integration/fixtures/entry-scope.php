<?php
/**
 * One process resolving a cookieless entry scope.
 *
 * `php entry-scope.php <wp root> <tab> <ready file>`
 *
 * Waits until a second process has also reached the barrier, then resolves
 * the scope with no browser cookie. Prints JSON `{scope, key}` on stdout.
 * EntryScopeConcurrencyTest starts two of these at once.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.Security.ValidatedSanitizedInput, WordPress.Security.EscapeOutput, WordPress.WP.AlternativeFunctions -- a command-line fixture. The arguments are this test's own.
if ( ! isset( $argv ) ) {
	exit( 2 );
}
[ , $linker_tools_root, $linker_tools_tab, $linker_tools_ready ] = $argv;
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require_once $linker_tools_root . '/wp-load.php';

file_put_contents( $linker_tools_ready, getmypid() . "\n", FILE_APPEND | LOCK_EX );

/**
 * Pid lines in the ready file.
 */
$linker_tools_pids = static function () use ( $linker_tools_ready ): int {
	$linker_tools_lines = file( $linker_tools_ready, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES );
	if ( ! is_array( $linker_tools_lines ) ) {
		return 0;
	}
	$linker_tools_count = 0;
	foreach ( $linker_tools_lines as $linker_tools_line ) {
		if ( 1 === preg_match( '/^\d+$/', $linker_tools_line ) ) {
			++$linker_tools_count;
		}
	}
	return $linker_tools_count;
};

// 20 s is the ceiling for this process to see the peer's pid line. Each
// process loads WordPress via wp-load.php before writing its pid. 20 s is
// longer than one local bootstrap plus the 10 ms poll gap. A stuck peer
// fails here instead of hanging the suite.
$linker_tools_deadline = microtime( true ) + 20;
while ( $linker_tools_pids() < 2 ) {
	if ( microtime( true ) > $linker_tools_deadline ) {
		fwrite( STDERR, "peer did not reach the entry-scope barrier\n" );
		exit( 3 );
	}
	usleep( 10000 );
}

unset( $_COOKIE[ Linker\Tools\Genie\Conversations::BROWSER_COOKIE ] );
$linker_tools_scope = ( new Linker\Tools\Genie\Conversations() )->entry_scope( (string) $linker_tools_tab );
$linker_tools_key   = $_COOKIE[ Linker\Tools\Genie\Conversations::BROWSER_COOKIE ] ?? '';
echo (string) wp_json_encode(
	array(
		'scope' => $linker_tools_scope,
		'key'   => is_string( $linker_tools_key ) ? $linker_tools_key : '',
	)
);
