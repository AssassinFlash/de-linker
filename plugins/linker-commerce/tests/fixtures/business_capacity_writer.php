<?php
/**
 * Isolated final business writer on an independent native DB connection.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
global $argv;
if ( ! isset( $argv[1], $argv[2], $argv[3], $argv[4] ) ) {
	exit( 2 );
}
putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Exclusive local worker, never production.
require $argv[1] . '/wp-load.php';
if ( 'local' !== wp_get_environment_type() ) {
	exit( 3 );
}
add_filter( 'pre_option_linker_inquiry_assessment_enabled', static fn (): string => 'no' );
add_filter( 'woocommerce_email_enabled_linker_new_inquiry', '__return_false' );
add_filter( 'woocommerce_email_enabled_linker_inquiry_received', '__return_false' );
wp_set_current_user( 0 );
file_put_contents( $argv[2] . '.ready', 'ready' );
$linker_commerce_business_deadline = microtime( true ) + 15;
while ( ! is_file( $argv[3] ) && microtime( true ) < $linker_commerce_business_deadline ) {
	usleep( 1000 );
}
if ( ! is_file( $argv[3] ) ) {
	exit( 2 );
}
$linker_commerce_business_details = Linker\Commerce\Contact\Submission::from_post(
	array(
		'name'    => 'Synthetic business writer',
		'email'   => $argv[4],
		'message' => str_repeat( 'x', 3000 ),
		'consent' => '1',
		'lang'    => 'en',
	)
);
if ( ! $linker_commerce_business_details instanceof Linker\Commerce\Contact\Submission ) {
	exit( 3 );
}
$linker_commerce_business_start  = microtime( true );
$linker_commerce_business_result = ( new Linker\Commerce\Inquiry\Sender() )->message( $linker_commerce_business_details );
file_put_contents(
	$argv[2],
	(string) wp_json_encode(
		array(
			'order'   => $linker_commerce_business_result instanceof WC_Order ? $linker_commerce_business_result->get_id() : 0,
			'error'   => $linker_commerce_business_result instanceof WP_Error ? $linker_commerce_business_result->get_error_code() : '',
			'seconds' => microtime( true ) - $linker_commerce_business_start,
		)
	)
);
