<?php
/**
 * Test-owned native DB worker; no HTTP, model or outgoing mail consumer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
require $argv[1] . '/wp-load.php';
file_put_contents( $argv[2] . '.ready', 'ready' );
$linker_commerce_capacity_deadline = microtime( true ) + 15;
while ( ! is_file( $argv[3] ) && microtime( true ) < $linker_commerce_capacity_deadline ) {
	usleep( 1000 );
}
if ( ! is_file( $argv[3] ) ) {
	exit( 2 );
}
$linker_commerce_capacity_start   = microtime( true );
$linker_commerce_capacity_message = new Linker\Commerce\Mail\Message( array( 'tester246@example.test' ), 'Synthetic last writer', str_repeat( 'x', 4096 ), array(), array() );
$linker_commerce_capacity_job     = ( new Linker\Commerce\Mail\JobStore() )->create( $linker_commerce_capacity_message );
file_put_contents(
	$argv[2],
	(string) wp_json_encode(
		array(
			'job'     => $linker_commerce_capacity_job,
			'seconds' => microtime( true ) - $linker_commerce_capacity_start,
		)
	)
);
