<?php
/**
 * One independent PHP request for PublicSubmissionTest's parallel submissions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
require dirname( __DIR__, 2 ) . '/integration-bootstrap.php';
$linker_commerce_email  = $argv[1];
$linker_commerce_door   = $argv[2];
$linker_commerce_start  = (float) $argv[3];
$_SERVER['REMOTE_ADDR'] = '127.0.0.246';
wp_set_current_user( 0 );
wc_load_cart();
WC()->cart->empty_cart();
$linker_commerce_stamp = (string) ( time() - 5 );
$linker_commerce_post  = array(
	'name'                 => 'Parallel tester',
	'email'                => $linker_commerce_email,
	'message'              => 'Parallel public inquiry.',
	'consent'              => '1',
	'linker_contact_nonce' => wp_create_nonce( 'linker_contact_form' ),
	'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
	'linker_started'       => $linker_commerce_stamp,
	'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $linker_commerce_stamp ),
);
// Widen the write interval to exercise contenders passing a non-atomic check.
add_action(
	'woocommerce_new_order',
	static function (): void {
		usleep( 250000 );
	}
);
while ( microtime( true ) < $linker_commerce_start ) {
	usleep( 1000 );
}
if ( 'contact' === $linker_commerce_door ) {
	echo ( new Linker\Commerce\Contact\Handler() )->process( $linker_commerce_post );
} else {
	$linker_commerce_result = ( new Linker\Commerce\Inquiry\Handler() )->process( $linker_commerce_post );
	echo $linker_commerce_result instanceof WC_Order ? 'sent' : $linker_commerce_result->get_error_code();
}
