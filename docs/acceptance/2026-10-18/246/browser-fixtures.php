<?php
/** Local-only browser fixtures: just wp c246 eval-file <this file> setup|cleanup. */
if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || wp_parse_url( home_url(), PHP_URL_HOST ) !== '127.0.0.1' ) {
	throw new RuntimeException( 'Local isolated WordPress required.' );
}
$mode = $args[0] ?? 'setup';
if ( 'cleanup' === $mode ) {
	foreach ( array( 'guest246@example.test', 'guest246de@example.test', 'tester246-approved@example.test', 'tester246-pending@example.test', 'tester246-restricted@example.test' ) as $email ) {
		foreach ( wc_get_orders( array( 'billing_email' => $email, 'limit' => -1 ) ) as $order ) {
			$order->delete( true );
		}
	}
	require_once ABSPATH . 'wp-admin/includes/user.php';
	foreach ( (array) get_option( 'linker_246_browser_users', array() ) as $id ) {
		$user = get_userdata( $id );
		if ( $user && str_starts_with( $user->user_login, 'linker246-' ) ) {
			wp_delete_user( $id );
		}
	}
	delete_option( 'linker_246_browser_users' );
	echo "Cleaned #246 browser fixtures.\n";
	return;
}
$created = (array) get_option( 'linker_246_browser_users', array() );
foreach ( array( 'approved', 'pending', 'restricted' ) as $status ) {
	$login = 'linker246-' . $status;
	$id = username_exists( $login );
	if ( ! $id ) {
		$id = wp_insert_user( array( 'user_login' => $login, 'user_email' => 'tester246-' . $status . '@example.test', 'user_pass' => wp_generate_password( 32 ), 'role' => 'customer', 'first_name' => 'Maria', 'last_name' => 'Test', 'display_name' => 'Maria Test' ) );
		if ( is_wp_error( $id ) ) {
			throw new RuntimeException( $id->get_error_message() );
		}
		$created[] = $id;
	}
	$customer = new WC_Customer( $id );
	$customer->set_billing_first_name( 'Maria' );
	$customer->set_billing_last_name( 'Test' );
	$customer->set_billing_email( 'tester246-' . $status . '@example.test' );
	$customer->set_billing_company( '246 Fixture GmbH' );
	$customer->save();
	update_user_meta( $id, 'linker_approval_status', $status );
	update_user_meta( $id, 'linker_approval_reason', 'restricted' === $status ? 'Please add your company VAT ID.' : '' );
	echo $login . ' ' . $id . ' ' . $status . PHP_EOL;
}
update_option( 'linker_246_browser_users', array_values( array_unique( $created ) ), false );
