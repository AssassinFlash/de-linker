<?php
/** Remove only this ticket's explicitly owned screenshot fixtures. */
if ( wp_get_environment_type() !== 'local' || (int) wp_parse_url( (string) get_option( 'home' ), PHP_URL_PORT ) !== 9129 ) {
    throw new RuntimeException( 'Only the c254 local instance is allowed.' );
}
$orders = array();
foreach ( $args as $id ) {
    $order = wc_get_order( (int) $id );
    if ( ! $order || ! $order->get_meta( '_linker_254_visual_fixture' ) ) {
        throw new RuntimeException( 'Order is not an owned visual fixture.' );
    }
    $orders[] = $order;
}
$user = get_user_by( 'login', 'i254-visual' );
if ( $user && ! get_user_meta( $user->ID, '_linker_254_visual_fixture', true ) ) {
    throw new RuntimeException( 'Customer is not an owned visual fixture.' );
}
foreach ( $orders as $order ) { $order->delete( true ); }
if ( $user ) {
    require_once ABSPATH . 'wp-admin/includes/user.php';
    wp_delete_user( $user->ID );
}
echo 'Removed owned screenshot records only.', "\n";
