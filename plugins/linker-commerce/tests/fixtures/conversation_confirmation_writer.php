<?php
/** Native confirmation competitor; synthetic local sources only, no provider calls.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
global $argv;
if ( ! isset( $argv[1], $argv[2], $argv[3], $argv[4] ) ) {
	exit( 2 );
}
require $argv[1] . '/wp-load.php';
if ( 'local' !== wp_get_environment_type() ) {
	exit( 3 );
}
file_put_contents( $argv[2] . '.ready', 'ready' );
$linker_commerce_deadline = microtime( true ) + 15;
while ( ! is_file( $argv[3] ) && microtime( true ) < $linker_commerce_deadline ) {
	usleep( 1000 );
}
if ( ! is_file( $argv[3] ) ) {
	exit( 2 );
}
$linker_commerce_mail = new Linker\Tools\Genie\ConversationMail( new Linker\Tools\Genie\Conversations(), new Linker\Tools\Genie\Thread(), null, new Linker\Tools\Genie\RateLimit( 'synthetic568confirmation', 100, DAY_IN_SECONDS ) );
file_put_contents( $argv[2], (string) wp_json_encode( $linker_commerce_mail->confirm( $argv[4] ) ) );
