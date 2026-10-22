<?php
/**
 * Two real worker processes exercise the production ledger.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
require $argv[1] . '/wp-load.php';
file_put_contents( $argv[2] . '.ready', 'ready' );
$linker_commerce_budget_deadline = microtime( true ) + 15;
while ( ! is_file( $argv[3] ) && microtime( true ) < $linker_commerce_budget_deadline ) {
	usleep( 1000 );
}
if ( ! is_file( $argv[3] ) ) {
	exit( 2 );
}
$linker_commerce_budget_now  = (int) $argv[4];
$linker_commerce_budget_slot = ( new Linker\Commerce\Mail\Throttle() )->reserve( $linker_commerce_budget_now, Linker\Commerce\Mail\Throttle::SMTP );
file_put_contents( $argv[2], (string) $linker_commerce_budget_slot );
