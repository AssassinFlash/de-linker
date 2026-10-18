<?php
/** Local browser fixture for the pending account lifecycle. */
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Registration\Approval;

if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
	throw new RuntimeException( 'Local isolated WordPress required.' );
}
global $wpdb;
$key  = 'linker_222_browser';
$mode = $args[0] ?? '';
// Read back the fixture-owned options from storage between CLI/web requests.
// Deleted SQL rows may still have a persistent cache entry; never flush the site.
foreach ( array( $key, Throttle::OPTION, TestMode::OPTION ) as $option ) {
	wp_cache_delete( $option, 'options' );
}
if ( 'setup' === $mode ) {
	if ( false !== get_option( $key ) ) {
		throw new RuntimeException( 'An existing fixture must be restored before another run.' );
	}
	$state = array(
		'email' => $args[1],
		'options' => array( Throttle::OPTION => get_option( Throttle::OPTION ), TestMode::OPTION => get_option( TestMode::OPTION ) ),
		'marker' => (int) $wpdb->get_var( "SELECT MAX(ID) FROM {$wpdb->posts} WHERE post_type='linker_mail_job'" ),
		'limits' => $wpdb->get_results( "SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE 'linker_commerce_limit_%'", ARRAY_A ),
	);
	update_option( $key, $state, false );
	$wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE 'linker_commerce_limit_%'" );
	( new TestMode() )->enable( 'tester222@example.test' );
	update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ), false );
	return;
}
$state = get_option( $key );
if ( ! is_array( $state ) ) {
	throw new RuntimeException( 'No browser fixture to read or restore.' );
}
$user = get_user_by( 'email', $state['email'] );
$jobs = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE post_type='linker_mail_job' AND ID > %d ORDER BY ID", $state['marker'] ) );
// A concurrent local mail job is not owned by this fixture, even if newer.
$jobs = array_values( array_filter( $jobs, static function ( $id ) use ( $state ) {
	$message = json_decode( get_post_meta( $id, '_linker_mail_message', true ), true );
	return is_array( $message ) && ( in_array( $state['email'], $message['to'], true ) || str_contains( $message['body'], $state['email'] ) );
} ) );
$orders = wc_get_orders( array( 'billing_email' => $state['email'], 'limit' => -1 ) );
if ( 'read' === $mode ) {
	echo wp_json_encode( array(
		'user' => $user ? $user->ID : 0,
		'status' => $user ? ( new Approval() )->status( $user->ID ) : '',
		'stored_status' => $user ? $wpdb->get_var( $wpdb->prepare( "SELECT meta_value FROM {$wpdb->usermeta} WHERE user_id=%d AND meta_key=%s", $user->ID, Approval::STATUS_META ) ) : null,
		'orders' => array_map( static fn ( $order ) => array( 'customer' => $order->get_customer_id(), 'status' => $order->get_status(), 'items' => $order->get_item_count() ), $orders ),
		'mail' => array_map( static function ( $id ) {
			$message = json_decode( get_post_meta( $id, '_linker_mail_message', true ), true );
			return array_intersect_key( $message, array_flip( array( 'to', 'headers', 'subject' ) ) );
		}, $jobs ),
	) );
	return;
}
if ( in_array( $mode, array( 'approved', 'restricted', 'rejected' ), true ) ) {
	if ( ! $user ) { throw new RuntimeException( 'No registered customer.' ); }
	$staff = get_user_by( 'email', '857558227@qq.com' );
	if ( ! $staff || ! user_can( $staff, 'edit_users' ) ) { throw new RuntimeException( 'The designated employee is unavailable.' ); }
	wp_set_current_user( $staff->ID );
	if ( ! ( new Approval() )->set( $user->ID, $mode, $args[1] ?? '' ) ) { throw new RuntimeException( 'Decision refused.' ); }
	echo wp_json_encode( array( 'user' => $user->ID, 'status' => ( new Approval() )->status( $user->ID ), 'stored_status' => $wpdb->get_var( $wpdb->prepare( "SELECT meta_value FROM {$wpdb->usermeta} WHERE user_id=%d AND meta_key=%s", $user->ID, Approval::STATUS_META ) ) ) );
	return;
}
if ( 'deliver-one' === $mode ) {
	foreach ( $jobs as $id ) {
		$message = json_decode( get_post_meta( $id, '_linker_mail_message', true ), true );
		if ( in_array( $state['email'], $message['to'], true ) ) {
			delete_option( Throttle::OPTION );
			try { do_action( Outbox::HOOK, (int) $id ); }
			finally { update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ), false ); }
			return;
		}
	}
	throw new RuntimeException( 'No customer mail queued.' );
}
if ( 'cleanup' !== $mode ) { throw new RuntimeException( 'Unknown fixture operation.' ); }
foreach ( $orders as $order ) { $order->delete( true ); }
foreach ( $jobs as $id ) {
	as_unschedule_all_actions( Outbox::HOOK, array( (int) $id ), Outbox::GROUP );
	wp_delete_post( (int) $id, true );
}
if ( $user ) {
	require_once ABSPATH . 'wp-admin/includes/user.php';
	wp_delete_user( $user->ID );
}
foreach ( $state['options'] as $option => $value ) {
	if ( false === $value ) { delete_option( $option ); } else { update_option( $option, $value, false ); }
	wp_cache_delete( $option, 'options' );
}
$wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE 'linker_commerce_limit_%'" );
foreach ( $state['limits'] as $row ) { $wpdb->insert( $wpdb->options, array_merge( $row, array( 'autoload' => 'off' ) ) ); }
delete_option( $key );
wp_cache_delete( $key, 'options' );
