<?php
/**
 * Local native worker killed after committed job/source/action, before transport.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
global $argv;
if ( ! isset( $argv[1], $argv[2], $argv[3], $argv[4] ) ) {
	exit( 2 );
}
require $argv[1] . '/wp-load.php';
$linker_commerce_crash_user = get_userdata( (int) $argv[4] );
if ( ! $linker_commerce_crash_user instanceof WP_User ) {
	exit( 6 ); }
$linker_commerce_crash_message = Linker\Commerce\Mail\Prepared::capture(
	static function () use ( $linker_commerce_crash_user ): void {
		wp_password_change_notification( $linker_commerce_crash_user );
	}
);
if ( ! $linker_commerce_crash_message instanceof Linker\Commerce\Mail\Message || ! Linker\Commerce\Mail\NativeOrigin::valid( $linker_commerce_crash_message ) ) {
	exit( 7 ); }
$linker_commerce_crash_job = ( new Linker\Commerce\Mail\JobStore() )->create(
	$linker_commerce_crash_message,
	0,
	static function ( int $id ) use ( $argv ): void {
		update_option( $argv[3], $id, false );
	}
);
if ( $linker_commerce_crash_job < 1 ) {
	exit( 3 );
}
file_put_contents( $argv[2], (string) $linker_commerce_crash_job );
$linker_commerce_crash_pid = getmypid();
if ( ! is_int( $linker_commerce_crash_pid ) ) {
	exit( 5 );
}
posix_kill( $linker_commerce_crash_pid, SIGKILL );
exit( 4 );
