<?php
/**
 * Two independent local connections exercise native notification release locks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

$linker_commerce_root = getenv( 'LINKER_WP_ROOT' );
if ( false === $linker_commerce_root ) {
	exit( 2 );
}
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Native local bootstrap.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require $linker_commerce_root . '/wp-load.php';
if ( 'local' !== wp_get_environment_type() ) {
	exit( 3 );
}
add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
$linker_commerce_id      = (int) ( $argv[1] ?? 0 );
$linker_commerce_user    = (int) ( $argv[2] ?? 0 );
$linker_commerce_basis   = (string) ( $argv[3] ?? '' );
$linker_commerce_barrier = (string) ( $argv[4] ?? '' );
$linker_commerce_mode    = (string) ( $argv[5] ?? 'release' );
wp_set_current_user( $linker_commerce_user );
if ( 'hold-lock' === $linker_commerce_mode ) {
	\Linker\Commerce\Inquiry\Assessment\Lock::run(
		'release-' . $linker_commerce_id,
		static function () use ( $linker_commerce_barrier ): void {
			file_put_contents( $linker_commerce_barrier, 'locked' );
			usleep( 1500000 ); // Deliberately overlap the local second connection.
		}
	);
	exit( 0 );
}
$linker_commerce_until = microtime( true ) + 5;
while ( 'go' !== file_get_contents( $linker_commerce_barrier ) && microtime( true ) < $linker_commerce_until ) {
	usleep( 10000 );
}
$linker_commerce_result = \Linker\Commerce\Mail\NotificationHold::release( $linker_commerce_id, $linker_commerce_basis );
echo wp_json_encode( is_wp_error( $linker_commerce_result ) ? array( 'error' => $linker_commerce_result->get_error_code() ) : array( 'job' => $linker_commerce_result['job'] ) );
