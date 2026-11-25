<?php
/**
 * Access the isolated Woo records backing this customer's browser journey.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Inquiry\Assessment\AuthorizationStore;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Planning\Context;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Commerce\Quotation\Emails\QuotationIssuedEmail;
use Linker\Commerce\Quotation\Issuer;

if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
	throw new RuntimeException( 'A local mail sink is required.' );
}
[ $operation, $email ] = $args;
if ( ! preg_match( '/^e2e-known-[a-f0-9-]+(?:-other)?@example\.test$/D', $email ) ) {
	throw new RuntimeException( 'Expected this browser fixture’s synthetic customer.' );
}
$orders = wc_get_orders(
	array(
		'billing_email' => $email,
		'limit'         => 2,
	)
);
if ( 'cleanup' === $operation ) {
	foreach ( $orders as $order ) {
		if ( $order->get_meta( IntakeStore::META ) ) {
			IntakeStore::forget( $order );
		}
		$order->delete( true );
	}
	$user = get_user_by( 'email', $email );
	if ( $user ) {
		wp_delete_user( $user->ID );
	}
	return;
}
if ( 'account' === $operation ) {
	$id = wp_insert_user(
		array(
			'user_login'   => strtok( $email, '@' ),
			'user_email'   => $email,
			'user_pass'    => $args[2],
			'display_name' => 'Konstanz Review',
			'first_name'   => 'Konstanz',
			'last_name'    => 'Review',
			'role'         => 'customer',
		)
	);
	if ( is_wp_error( $id ) ) {
		throw new RuntimeException( $id->get_error_message() );
	}
	update_user_meta( $id, 'linker_approval_status', 'approved' );
	echo (int) $id;
	return;
}
if ( 'owned-inquiry' === $operation ) {
	$user = get_user_by( 'email', $email );
	$order = wc_create_order( array( 'customer_id' => $user->ID, 'status' => 'inquiry-received' ) );
	$order->set_billing_email( $email );
	$order->set_billing_first_name( 'Konstanz' );
	$order->set_customer_note( 'Existing 8 kWp array in Konstanz. Annual electricity use from bill: 6,200 kWh.' );
	$order->save();
	return;
}
if ( 1 !== count( $orders ) ) {
	throw new RuntimeException( 'The customer needs one Woo inquiry.' );
}
$order = $orders[0];
if ( 'order' === $operation ) {
	echo wp_json_encode(
		array(
			'id'       => $order->get_id(),
			'number'   => $order->get_order_number(),
			'locale'   => OrderLocale::of( $order ),
			'owner'    => $order->get_customer_id(),
			'status'   => $order->get_status(),
			'lines'    => count( $order->get_items() ),
			'note'     => $order->get_customer_note(),
			'project'  => $order->get_meta( Context::PROJECT_META ),
			'quote'    => $order->get_meta( Issuer::NUMBER_META ),
			'edit_url' => $order->get_edit_order_url(),
		)
	);
	return;
}
if ( 'deliver' === $operation ) {
	if ( 'receipt' === $args[2] ) {
		\Linker\Commerce\Tests\E2E\PublicInquiryAssessment::process( $order->get_id() );
		$authorization = AuthorizationStore::read( $order->get_id() );
		$job = (int) ( $authorization['jobs']['receipt']['id'] ?? 0 );
	} else {
		$job = (int) $order->get_meta( QuotationIssuedEmail::JOB );
	}
	if ( $job ) {
		$actions = as_get_scheduled_actions(
			array(
				'hook'     => Outbox::HOOK,
				'args'     => array( $job ),
				'group'    => Outbox::GROUP,
				'status'   => ActionScheduler_Store::STATUS_PENDING,
				'per_page' => 1,
			)
		);
		foreach ( $actions as $id => $action ) {
			$schedule = $action->get_schedule();
			if ( $schedule instanceof ActionScheduler_NullSchedule || $schedule->get_date()->getTimestamp() <= time() ) {
				ActionScheduler_QueueRunner::instance()->process_action( $id, 'Known project quotation' );
			}
		}
	}
	return;
}
throw new RuntimeException( 'Unknown fixture operation.' );
