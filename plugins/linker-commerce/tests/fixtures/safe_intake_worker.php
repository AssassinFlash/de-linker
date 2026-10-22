<?php
/**
 * Independent native connections race for the last persistent review slot.
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
$linker_commerce_barrier                                 = (string) ( $argv[1] ?? '' );
$linker_commerce_email                                   = (string) ( $argv[2] ?? '' );
$_COOKIE[ \Linker\Commerce\Protection\Identity::COOKIE ] = substr( hash( 'sha256', $linker_commerce_email ), 0, 32 );
$_SERVER['REMOTE_ADDR']                                  = '127.0.0.245';
wc_load_cart();
WC()->cart->empty_cart();
$linker_commerce_started = (string) time();
$linker_commerce_post    = array(
	'name'                 => 'Concurrent fixture',
	'email'                => $linker_commerce_email,
	'message'              => 'Please advise on a battery.',
	'consent'              => '1',
	'linker_started'       => $linker_commerce_started,
	'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $linker_commerce_started ),
	'linker_inquiry_nonce' => wp_create_nonce( \Linker\Commerce\Inquiry\Handler::ACTION ),
	'linker_request_id'    => wp_generate_uuid4(),
	'linker_proof'         => '',
	'linker_draft_hash'    => WC()->cart->get_cart_hash(),
);
$linker_commerce_until   = microtime( true ) + 5;
while ( 'go' !== file_get_contents( $linker_commerce_barrier ) && microtime( true ) < $linker_commerce_until ) {
	usleep( 10000 );
}
$linker_commerce_result = ( new \Linker\Commerce\Inquiry\Handler() )->process( $linker_commerce_post );
echo wp_json_encode( is_wp_error( $linker_commerce_result ) ? array( 'error' => $linker_commerce_result->get_error_code() ) : array( 'order' => $linker_commerce_result->get_id() ) );
