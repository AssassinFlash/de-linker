<?php
/** Local browser fixture; saves and restores its own records, queue and limits. */
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Outbox;

if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
	throw new RuntimeException( 'Local isolated WordPress required.' );
}
global $wpdb;
$mode = $args[0] ?? '';
$key = 'linker_246_round2_browser';
if ( 'setup' === $mode ) {
	if ( false !== get_option( $key ) ) {
		throw new RuntimeException( 'Browser fixture already exists; clean it up first.' );
	}
	$state = array( 'email' => $args[1], 'options' => array(), 'limits' => $wpdb->get_results( "SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE 'linker_commerce_limit_%'", ARRAY_A ), 'transient' => get_transient( 'linker_contact_' . md5( '127.0.0.1' ) ), 'marker' => (int) $wpdb->get_var( "SELECT MAX(ID) FROM {$wpdb->posts} WHERE post_type='linker_mail_job'" ) );
	foreach ( array( Throttle::OPTION, TestMode::OPTION ) as $option ) {
		$state['options'][$option] = get_option( $option );
	}
	$product = new WC_Product_Simple();
	$product->set_name( '246 browser fixture' );
	$product->set_regular_price( '100' );
	$product->save();
	$state['product'] = $product->get_id();
	update_option( $key, $state, false );
	$wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE 'linker_commerce_limit_%'" );
	delete_transient( 'linker_contact_' . md5( '127.0.0.1' ) );
	( new TestMode() )->enable( 'tester246@example.test' );
	update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ), false );
	if ( 'capped' === ( $args[2] ?? '' ) ) {
		for ( $i = 0; $i < 10; ++$i ) { ( new \Linker\Commerce\Inquiry\ReceiptLimit() )->take(); }
	}
	echo wp_json_encode( array( 'product' => $product->get_id() ) );
	return;
}
$state = get_option( $key );
if ( ! is_array( $state ) ) { throw new RuntimeException( 'No browser fixture to read or restore.' ); }
$orders = wc_get_orders( array( 'billing_email' => $state['email'], 'limit' => -1 ) );
$jobs = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE post_type='linker_mail_job' AND ID > %d ORDER BY ID", $state['marker'] ) );
if ( 'read' === $mode ) {
	echo wp_json_encode( array( 'orders' => array_map( static fn ( $order ) => array( 'status' => $order->get_status(), 'source' => $order->get_meta( '_linker_inquiry_source' ), 'skipped' => $order->get_meta( '_linker_receipt_skipped' ), 'items' => count( $order->get_items() ) ), $orders ), 'mail' => array_map( static fn ( $id ) => json_decode( get_post_meta( $id, '_linker_mail_message', true ), true ), $jobs ) ) );
	return;
}
if ( 'cleanup' !== $mode ) { throw new RuntimeException( 'Unknown fixture mode.' ); }
foreach ( $orders as $order ) { $order->delete( true ); }
foreach ( $jobs as $id ) {
	as_unschedule_all_actions( Outbox::HOOK, array( (int) $id ), Outbox::GROUP );
	wp_delete_post( (int) $id, true );
}
$product = wc_get_product( $state['product'] );
if ( $product ) { $product->delete( true ); }
foreach ( $state['options'] as $option => $value ) {
	if ( false === $value ) { delete_option( $option ); } else { update_option( $option, $value, false ); }
}
$wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE 'linker_commerce_limit_%'" );
foreach ( $state['limits'] as $row ) { $wpdb->insert( $wpdb->options, array_merge( $row, array( 'autoload' => 'off' ) ) ); }
delete_transient( 'linker_contact_' . md5( '127.0.0.1' ) );
if ( false !== $state['transient'] ) { set_transient( 'linker_contact_' . md5( '127.0.0.1' ), $state['transient'], HOUR_IN_SECONDS ); }
delete_option( $key );
