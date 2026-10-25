<?php
/**
 * Independent native erasure connection for the staff-release race.
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
$linker_commerce_order = wc_get_order( (int) ( $argv[1] ?? 0 ) );
if ( ! $linker_commerce_order instanceof \WC_Order ) {
	exit( 4 );
}
try {
	\WC_Privacy_Erasers::remove_order_personal_data( $linker_commerce_order );
	echo wp_json_encode( array( 'status' => 'erased' ) );
} catch ( \RuntimeException $linker_commerce_error ) {
	echo wp_json_encode( array( 'status' => $linker_commerce_error->getMessage() ) );
}
