<?php
/** Records belonging to one local browser transfer. */

use Linker\Commerce\Inquiry\Assessment\AuthorizationStore;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Mail\Outbox;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\ContactRequest;
use Linker\Tools\Genie\InquiryRequest;

[ $command, $email ] = $args;
if ( 'local' !== wp_get_environment_type() || ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || ! has_filter( 'pre_wp_mail', 'linker_local_capture_mail' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) || ! preg_match( '/^e2e-transfer-[a-f0-9-]{36}@example\.test$/D', $email ) ) {
	throw new RuntimeException( 'A unique local review customer and a file mail sink are required.' );
}
if ( 'account' === $command ) {
	$status = $args[2];
	if ( ! in_array( $status, array( 'approved', 'pending' ), true ) ) {
		throw new RuntimeException( 'Unknown customer role.' );
	}
	$id = wp_insert_user( array( 'user_email' => $email, 'user_login' => strstr( $email, '@', true ), 'user_pass' => wp_generate_password(), 'role' => 'customer', 'first_name' => 'Genie', 'last_name' => 'Review' ) );
	if ( is_wp_error( $id ) ) {
		throw new RuntimeException( $id->get_error_message() );
	}
	update_user_meta( $id, 'linker_approval_status', $status );
	echo get_user_meta( $id, 'linker_approval_status', true );
	return;
}
$orders = wc_get_orders( array( 'billing_email' => $email, 'limit' => -1 ) );
$conversation = (int) ( $args[2] ?? 0 );
$actions      = array();
if ( $conversation > 0 && Conversations::POST_TYPE === get_post_type( $conversation ) ) {
	foreach ( array( 'genie_contact' => ContactRequest::NOTE, 'genie_inquiry' => InquiryRequest::NOTE ) as $action => $key ) {
		foreach ( get_post_meta( $conversation, $key, false ) as $note ) {
			if ( is_array( $note ) && $email === ( $note['email'] ?? '' ) ) {
				$actions[ (int) $note['order'] ] = $action;
			}
		}
	}
}
if ( 'read' === $command ) {
	$rows = array();
	foreach ( $orders as $order ) {
		$lines = array();
		foreach ( $order->get_items() as $item ) {
			$lines[] = array( 'name' => $item->get_name(), 'quantity' => $item->get_quantity() );
		}
		$rows[] = array( 'id' => $order->get_id(), 'source' => $order->get_meta( '_linker_inquiry_source' ), 'transfer' => $actions[ $order->get_id() ] ?? null, 'summary' => is_array( $order->get_meta( \Linker\Commerce\Inquiry\Sender::SUMMARY_META ) ), 'locale' => OrderLocale::of( $order ), 'status' => $order->get_status(), 'lines' => $lines, 'message' => $order->get_customer_note() );
	}
	echo wp_json_encode( $rows );
	return;
}
if ( 'tick' === $command ) {
	foreach ( $orders as $order ) {
		do_action( Queue::PROCESS, $order->get_id() );
		$authorization = AuthorizationStore::read( $order->get_id() );
		foreach ( is_array( $authorization ) ? ( $authorization['jobs'] ?? array() ) : array() as $job ) {
			if ( ! empty( $job['id'] ) ) {
				do_action( Outbox::HOOK, (int) $job['id'] );
			}
		}
	}
	return;
}
if ( 'cleanup' === $command ) {
	global $wpdb;
	foreach ( $orders as $order ) {
		$jobs = $wpdb->get_col( $wpdb->prepare( "SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key = '_linker_mail_inquiry' AND meta_value = %s", (string) $order->get_id() ) );
		foreach ( $jobs as $job ) {
			if ( 'linker_mail_job' === get_post_type( $job ) ) {
				wp_delete_post( (int) $job, true );
			}
		}
		$order->delete( true );
	}
	$user = get_user_by( 'email', $email );
	if ( $conversation > 0 && Conversations::POST_TYPE === get_post_type( $conversation ) && ( array() !== $actions || $user && (int) $user->ID === (int) get_post_field( 'post_author', $conversation ) ) ) {
		wp_delete_post( $conversation, true );
	}
	if ( $user ) {
		wp_delete_user( $user->ID );
	}
	return;
}
throw new RuntimeException( 'Unknown review operation.' );
