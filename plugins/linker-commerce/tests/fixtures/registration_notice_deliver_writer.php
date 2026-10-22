<?php
/**
 * Independent native notice handoff for the eraser connection-loss fixture.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
require dirname( __DIR__ ) . '/php/integration-bootstrap.php';
$linker_commerce_fixture = json_decode( (string) stream_get_contents( STDIN ), true );
if ( ! is_array( $linker_commerce_fixture ) || ! isset( $linker_commerce_fixture['user'] ) || ! is_int( $linker_commerce_fixture['user'] ) || $linker_commerce_fixture['user'] < 1 ) {
	exit( 2 );
}
add_filter( 'action_scheduler_allow_async_request_runner', '__return_false', 999 );
add_filter( 'pre_wp_mail', '__return_false', PHP_INT_MAX );
add_filter( 'pre_http_request', static fn () => new \WP_Error( 'fixture_no_network' ), PHP_INT_MAX );
\Linker\Commerce\Registration\RegistrationNotices::deliver( $linker_commerce_fixture['user'], 'received' );
$linker_commerce_state = \Linker\Commerce\Registration\RegistrationNotices::read( $linker_commerce_fixture['user'] );
echo wp_json_encode(
	array(
		'received' => $linker_commerce_state['received']['state'] ?? '',
		'job'      => $linker_commerce_state['received']['job'] ?? 0,
	)
);
