<?php
/** Local-only readback of the one browser inquiry; no email bodies or keys are exported. */
if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || wp_parse_url( home_url(), PHP_URL_HOST ) !== '127.0.0.1' ) {
	throw new RuntimeException( 'Local isolated WordPress required.' );
}
$orders = wc_get_orders( array( 'billing_email' => 'guest246de@example.test', 'limit' => 1, 'orderby' => 'ID', 'order' => 'DESC' ) );
$order = $orders[0] ?? null;
if ( ! $order instanceof WC_Order ) {
	throw new RuntimeException( 'The browser inquiry is missing.' );
}
$messages = array();
foreach ( get_posts( array( 'post_type' => 'linker_mail_job', 'post_status' => 'any', 'posts_per_page' => 200 ) ) as $job ) {
	$message = json_decode( get_post_meta( $job->ID, '_linker_mail_message', true ), true );
	if ( is_array( $message ) && ( str_contains( $message['subject'], '#' . $order->get_order_number() ) || in_array( 'guest246de@example.test', $message['to'], true ) ) ) {
		$messages[] = array( 'id' => $job->ID, 'to' => $message['to'], 'subject' => $message['subject'], 'headers' => $message['headers'] );
	}
}
$result = array(
	'instance' => 'c246',
	'snapshot' => '20261018-0238',
	'feature_head' => '5fee9624da570291cbdf899cb13255138c1f1a36',
	'customer_id' => $order->get_customer_id(),
	'order_id' => $order->get_id(),
	'status' => $order->get_status(),
	'locale' => $order->get_meta( '_linker_locale' ),
	'source' => $order->get_meta( '_linker_inquiry_source' ),
	'guest_billing_country' => $order->get_billing_country(),
	'items' => array_map( static fn( $item ) => array( 'product_id' => $item->get_product_id(), 'quantity' => $item->get_quantity(), 'name' => $item->get_name() ), array_values( $order->get_items() ) ),
	'outbox' => $messages,
	'mail_transport' => 'local files; quota filled before browser submit, so both messages queued',
);
if ( 0 !== $result['customer_id'] || 'inquiry-received' !== $result['status'] || count( $messages ) !== 2 ) {
	throw new RuntimeException( 'The guest record or its queued mail pair does not match.' );
}
echo wp_json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE );
