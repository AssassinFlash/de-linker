<?php
/** Owned screenshot data. Run only through wp-c254.sh; never deployed. */
if ( wp_get_environment_type() !== 'local' || (int) wp_parse_url( (string) get_option( 'home' ), PHP_URL_PORT ) !== 9129 ) {
    throw new RuntimeException( 'Only the c254 local instance is allowed.' );
}
$login = 'i254-visual';
$user = get_user_by( 'login', $login );
if ( $user && ! get_user_meta( $user->ID, '_linker_254_visual_fixture', true ) ) {
    throw new RuntimeException( 'Visual fixture name is already owned.' );
}
if ( ! $user ) {
    add_filter( 'pre_wp_mail', '__return_true', 0 );
    $id = wp_insert_user( array( 'user_login' => $login, 'user_pass' => wp_generate_password(), 'user_email' => 'i254-visual@example.test', 'first_name' => 'Jan', 'last_name' => 'Muster', 'role' => 'customer', 'locale' => 'de_DE_formal' ) );
    if ( is_wp_error( $id ) ) { throw new RuntimeException( $id->get_error_message() ); }
    update_user_meta( $id, '_linker_254_visual_fixture', true );
    update_user_meta( $id, Linker\Commerce\Registration\Approval::STATUS_META, 'approved' );
    $customer = new WC_Customer( $id );
    $customer->set_billing_first_name( 'Jan' );
    $customer->set_billing_last_name( 'Muster' );
    $customer->set_billing_email( 'i254-visual@example.test' );
    $customer->set_billing_company( 'Beispielbetrieb GmbH' );
    $customer->set_billing_country( 'DE' );
    $customer->set_billing_city( 'Berlin' );
    $customer->set_billing_postcode( '10115' );
    $customer->set_billing_address_1( 'Musterstraße 1' );
    $customer->save();
    remove_filter( 'pre_wp_mail', '__return_true', 0 );
    echo $id;
} else {
    echo $user->ID;
}
