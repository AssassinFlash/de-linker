<?php
/**
 * Local-only representative account-review states, rerunnable after snapshot load.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\VatProfile;

if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) ) {
	throw new RuntimeException( 'This fixture is only for an isolated local instance.' );
}

update_option( TestMode::OPTION, 'tester@example.test' );
// Hold all fixture notifications in Outbox, without a transport attempt.
update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ) );

// This dedicated instance is a controlled queue fixture; the source snapshot
// stays untouched. Only fixture users are exercised by the browser acceptance.
foreach ( get_users( array( 'role' => 'customer' ) ) as $linker_commerce_fixture_existing ) {
	if ( ( new Approval() )->is_subject( $linker_commerce_fixture_existing->ID ) ) {
		update_user_meta( $linker_commerce_fixture_existing->ID, Approval::STATUS_META, Approval::APPROVED );
	}
}

$linker_commerce_fixture_accounts = array(
	array(
		'login'   => 'a227-review-en',
		'company' => 'Review Solar GmbH',
		'first'   => 'Maria',
		'last'    => 'Beispiel',
		'country' => 'DE',
		'type'    => 'installer',
		'locale'  => 'en_US',
		'vat'     => VatProfile::VALID,
		'vat_id'  => 'DE000000000',
	),
	array(
		'login'   => 'a227-review-de',
		'company' => 'Sonnenbau Prüfung GmbH',
		'first'   => 'Martin',
		'last'    => 'Beispiel',
		'country' => 'AT',
		'type'    => 'distributor',
		'locale'  => 'de_DE_formal',
		'vat'     => VatProfile::UNVERIFIED,
		'vat_id'  => 'ATU00000000',
	),
	array(
		'login'   => 'a227-review-bot',
		'company' => 'Example What is SEO Services',
		'first'   => 'Avery',
		'last'    => 'Example',
		'country' => 'SE',
		'type'    => 'epc',
		'locale'  => 'en_US',
		'vat'     => VatProfile::NONE,
		'vat_id'  => '',
	),
);
$linker_commerce_fixture_ids      = array();
foreach ( $linker_commerce_fixture_accounts as $linker_commerce_fixture_row ) {
	$linker_commerce_fixture_user = get_user_by( 'login', $linker_commerce_fixture_row['login'] );
	$linker_commerce_fixture_id   = $linker_commerce_fixture_user ? $linker_commerce_fixture_user->ID : wp_insert_user(
		array(
			'user_login' => $linker_commerce_fixture_row['login'],
			'user_pass'  => wp_generate_password(),
			'user_email' => $linker_commerce_fixture_row['login'] . '@example.test',
			'role'       => 'customer',
		)
	);
	if ( is_wp_error( $linker_commerce_fixture_id ) ) {
		throw new RuntimeException( $linker_commerce_fixture_id->get_error_message() );
	}
	$linker_commerce_fixture_customer = new WC_Customer( $linker_commerce_fixture_id );
	$linker_commerce_fixture_customer->set_billing_company( $linker_commerce_fixture_row['company'] );
	$linker_commerce_fixture_customer->set_billing_first_name( $linker_commerce_fixture_row['first'] );
	$linker_commerce_fixture_customer->set_billing_last_name( $linker_commerce_fixture_row['last'] );
	$linker_commerce_fixture_customer->set_first_name( $linker_commerce_fixture_row['first'] );
	$linker_commerce_fixture_customer->set_last_name( $linker_commerce_fixture_row['last'] );
	$linker_commerce_fixture_customer->set_display_name( $linker_commerce_fixture_row['first'] . ' ' . $linker_commerce_fixture_row['last'] );
	$linker_commerce_fixture_customer->set_billing_country( $linker_commerce_fixture_row['country'] );
	$linker_commerce_fixture_customer->set_billing_address_1( 'Fixture Street 1' );
	$linker_commerce_fixture_customer->set_billing_city( 'Fixture City' );
	$linker_commerce_fixture_customer->set_billing_postcode( '12345' );
	$linker_commerce_fixture_customer->update_meta_data( CustomerRole::META, $linker_commerce_fixture_row['type'] );
	$linker_commerce_fixture_customer->save();
	update_user_meta( $linker_commerce_fixture_id, Approval::STATUS_META, Approval::PENDING );
	update_user_meta( $linker_commerce_fixture_id, Approval::REASON_META, '' );
	delete_user_meta( $linker_commerce_fixture_id, Approval::CHANGED_AT_META );
	delete_user_meta( $linker_commerce_fixture_id, Approval::CHANGED_BY_META );
	update_user_meta( $linker_commerce_fixture_id, 'locale', $linker_commerce_fixture_row['locale'] );
	update_user_meta( $linker_commerce_fixture_id, VatProfile::STATUS_META, $linker_commerce_fixture_row['vat'] );
	// Synthetic IDs and saved verdicts exercise the UI; this never calls VIES.
	update_user_meta( $linker_commerce_fixture_id, VatProfile::VAT_META, $linker_commerce_fixture_row['vat_id'] );
	$linker_commerce_fixture_ids[ $linker_commerce_fixture_row['login'] ] = $linker_commerce_fixture_id;
}
echo wp_json_encode( $linker_commerce_fixture_ids );
