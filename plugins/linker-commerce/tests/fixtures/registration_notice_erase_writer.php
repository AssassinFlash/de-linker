<?php
/** Native independent erasure after the original notice writer loses its connection.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
require dirname( __DIR__ ) . '/php/integration-bootstrap.php';
$linker_commerce_fixture = json_decode( (string) stream_get_contents( STDIN ), true );
if ( ! is_array( $linker_commerce_fixture ) || ! isset( $linker_commerce_fixture['user'] ) || ! is_int( $linker_commerce_fixture['user'] ) || $linker_commerce_fixture['user'] < 1 ) {
	exit( 2 );
}
add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
echo wp_json_encode( array( 'erased' => \Linker\Commerce\Registration\RegistrationNotices::erase( $linker_commerce_fixture['user'] ) ) );
