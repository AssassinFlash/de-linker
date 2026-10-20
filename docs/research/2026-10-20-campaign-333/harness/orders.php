<?php
/**
 * Own-order isolation for campaign #333.
 *
 * The orders are itemless. set_total writes the figure InquiryStatus echoes
 * back from get_total(). That is the ability bypass (#414). A customer-visible
 * inquiry list may still hide the total; this script does not open that list.
 *
 * Cleanup is WC_Order::delete(true). wp_delete_post is a no-op under HPOS.
 * The shutdown hook deletes the ids this process created if it dies first.
 * It does not delete any other customer's orders.
 *
 * Usage: just wp c333 eval-file <absolute path>
 */

require __DIR__ . '/catalog.php';

add_filter(
	'pre_wp_mail',
	static function () {
		return true;
	}
);

$created = array();
register_shutdown_function(
	static function () use ( &$created ): void {
		if ( array() !== $created ) {
			c333_delete_orders( array_values( $created ) );
		}
	}
);

try {
	$made  = array();
	$price = (string) c333_accounts()['products']['priced']['price'];
	foreach ( array( 'pending', 'restricted', 'approved' ) as $state ) {
		$user  = c333_user_id( $state );
		$order = wc_create_order( array( 'customer_id' => $user ) );
		if ( ! $order instanceof WC_Order ) {
			throw new RuntimeException( 'wc_create_order failed for ' . $state );
		}
		$order->set_status( 'inquiry-received' );
		$order->set_currency( 'EUR' );
		// Hand-set, and there are no line items. See the file comment.
		$order->set_total( $price );
		$order->save();
		$made[ $state ]     = $order->get_id();
		$created[ $state ]  = $order->get_id();
	}

	$seen = array();
	foreach ( $made as $state => $order_id ) {
		unset( $order_id );
		// UserContext::TTL. The probe lives as long as a product token, not longer.
		$token    = c333_token( c333_user_id( (string) $state ), 120 );
		$response = c333_ability( 'linker/inquiry-status', array(), $token );
		$data     = $response['data'];
		if ( isset( $data['result'] ) && is_array( $data['result'] ) ) {
			$data = $data['result'];
		}
		$rows = array();
		$list = $data['inquiries'] ?? null;
		if ( is_array( $list ) ) {
			foreach ( $list as $item ) {
				if ( ! is_array( $item ) ) {
					continue;
				}
				$rows[] = array(
					'id'    => $item['id'] ?? null,
					'total' => isset( $item['total'] ) ? (string) $item['total'] : '',
				);
			}
		}
		$seen[ $state ] = array(
			'status'    => $response['status'],
			'inquiries' => $rows,
		);
	}

	$cleanup = c333_delete_orders( array_values( $created ) );
	$created = array();

	echo wp_json_encode(
		array(
			'made'      => $made,
			'seen'      => $seen,
			'remaining' => $cleanup['remaining'],
		)
	);
	echo "\n";
} catch ( Throwable $failure ) {
	fwrite( STDERR, 'c333-throw ' . $failure::class . ' ' . $failure->getMessage() . ' @ ' . $failure->getFile() . ':' . $failure->getLine() . "\n" );
	echo '{"error":' . wp_json_encode( $failure->getMessage() ) . "}\n";
	exit( 1 );
}
