<?php
/** Preserve the existing local staff's Woo session around a price-access check. */

if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
	throw new RuntimeException( 'Local isolated WordPress required.' );
}

global $wpdb;
$key   = 'linker_draft_visual_staff_session';
$user  = get_user_by( 'email', '857558227@qq.com' );
if ( ! $user || ! user_can( $user, 'manage_woocommerce' ) ) {
	throw new RuntimeException( 'Expected local staff account.' );
}
$table = $wpdb->prefix . 'woocommerce_sessions';
$meta  = '_woocommerce_persistent_cart_' . get_current_blog_id();
if ( 'snapshot' === ( $args[0] ?? '' ) ) {
	if ( false !== get_option( $key ) ) {
		throw new RuntimeException( 'Restore the previous staff fixture first.' );
	}
	update_option(
		$key,
		array(
			'user'    => $user->ID,
			'row'     => $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$table} WHERE session_key = %s", (string) $user->ID ), ARRAY_A ),
			'exists'  => metadata_exists( 'user', $user->ID, $meta ),
			'cart'    => get_user_meta( $user->ID, $meta, true ),
		),
		false
	);
	return;
}
if ( 'restore' !== ( $args[0] ?? '' ) ) {
	throw new RuntimeException( 'Unknown staff fixture operation.' );
}
$state = get_option( $key );
if ( ! is_array( $state ) || $state['user'] !== $user->ID ) {
	throw new RuntimeException( 'No matching staff fixture snapshot.' );
}
( new WC_Session_Handler() )->delete_session( (string) $user->ID );
if ( null !== $state['row'] ) {
	if ( false === $wpdb->replace( $table, $state['row'] ) ) {
		throw new RuntimeException( 'Staff session restoration failed.' );
	}
}
if ( $state['exists'] ) {
	update_user_meta( $user->ID, $meta, $state['cart'] );
} else {
	delete_user_meta( $user->ID, $meta );
}
$restored = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$table} WHERE session_key = %s", (string) $user->ID ), ARRAY_A );
if ( $restored !== $state['row'] || get_user_meta( $user->ID, $meta, true ) !== $state['cart'] ) {
	throw new RuntimeException( 'Staff fixture readback differs from its snapshot.' );
}
delete_option( $key );
