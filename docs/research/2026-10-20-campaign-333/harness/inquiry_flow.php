<?php
/**
 * Campaign #333 — confirmation-card flow. Local instance only.
 *
 * Reads the inquiry card, changes the product, reads the card again, and POSTs
 * the first digest only when it no longer matches. A matching digest is never
 * posted, so this script cannot send an inquiry. Mail is short-circuited.
 * Price and stock are restored on the way out.
 *
 * File-level const is illegal here: `wp eval-file` includes this file from
 * inside a method, and PHP compiles const only in the global scope.
 *
 * Usage: just wp c333 eval-file <absolute path to this file>
 */

add_filter(
	'pre_wp_mail',
	static function () {
		return true;
	}
);

$c333_product = 4107;
$c333_twin    = 6628;
$c333_user    = 45;
$c333_new     = '1701';

/**
 * @return array{price: string, status: string}
 */
function c333_snap( int $id ): array {
	$product = wc_get_product( $id );
	return array(
		'price'  => $product instanceof WC_Product ? (string) $product->get_regular_price( 'edit' ) : '',
		'status' => $product instanceof WC_Product ? (string) $product->get_stock_status() : '',
	);
}

/**
 * @param array{price: string, status: string} $snap
 */
function c333_restore( int $id, array $snap ): void {
	$product = wc_get_product( $id );
	if ( ! $product instanceof WC_Product ) {
		return;
	}
	$product->set_regular_price( $snap['price'] );
	$product->set_price( $snap['price'] );
	$product->set_stock_status( $snap['status'] );
	$product->save();
}

$snapshots = array(
	$c333_product => c333_snap( $c333_product ),
	$c333_twin    => c333_snap( $c333_twin ),
);
register_shutdown_function(
	static function () use ( $snapshots ): void {
		foreach ( $snapshots as $id => $snap ) {
			c333_restore( (int) $id, $snap );
		}
	}
);

try {
	wp_set_current_user( $c333_user );
	$post_id = wp_insert_post(
		array(
			'post_type'   => 'linker_conversation',
			'post_status' => 'private',
			'post_author' => $c333_user,
			'post_title'  => 'c333 inquiry flow',
		)
	);
	$cookie = 'linker_conversation';
	$_COOKIE[ $cookie ] = (int) $post_id . '.' . hash_hmac( 'sha256', $cookie . '|' . (int) $post_id, wp_salt( 'auth' ) );

	if ( function_exists( 'wc_load_cart' ) ) {
		wc_load_cart();
	}
	$added = WC()->cart->add_to_cart( $c333_product, 1 );

	$orders_before = count(
		wc_get_orders(
			array(
				'customer_id' => $c333_user,
				'limit'       => -1,
				'return'      => 'ids',
			)
		)
	);

	/**
	 * @param array<string, mixed> $params
	 * @return array<string, mixed>
	 */
	$c333_inquiry = static function ( string $method, array $params ): array {
		$request = new WP_REST_Request( $method, '/linker-ai/v1/genie/inquiry' );
		foreach ( $params as $key => $value ) {
			$request->set_param( $key, $value );
		}
		$response = rest_do_request( $request );
		$data     = $response->get_data();
		return array(
			'status' => $response->get_status(),
			'data'   => is_array( $data ) ? $data : array( 'raw' => $data ),
		);
	};

	$before = $c333_inquiry( 'GET', array( 'locale' => 'en' ) );
	$digest = (string) ( $before['data']['lines_digest'] ?? '' );
	$lines  = $before['data']['lines'] ?? array();

	foreach ( array( $c333_product, $c333_twin ) as $id ) {
		$product = wc_get_product( $id );
		if ( $product instanceof WC_Product ) {
			$product->set_regular_price( $c333_new );
			$product->set_price( $c333_new );
			$product->save();
		}
	}
	WC()->cart->empty_cart();
	$added_after_price = WC()->cart->add_to_cart( $c333_product, 1 );
	$after_price       = $c333_inquiry( 'GET', array( 'locale' => 'en' ) );
	$price_digest      = (string) ( $after_price['data']['lines_digest'] ?? '' );
	$posted_price      = null;
	if ( '' !== $digest && $digest !== $price_digest ) {
		$posted_price = $c333_inquiry(
			'POST',
			array(
				'locale'  => 'en',
				'lines'   => $digest,
				'message' => 'c333 stale price — must not send',
			)
		);
	}

	foreach ( array( $c333_product, $c333_twin ) as $id ) {
		$product = wc_get_product( $id );
		if ( $product instanceof WC_Product ) {
			$product->set_regular_price( $snapshots[ $id ]['price'] );
			$product->set_price( $snapshots[ $id ]['price'] );
			$product->set_stock_status( 'outofstock' );
			$product->save();
		}
	}
	WC()->cart->empty_cart();
	$added_after_stock = WC()->cart->add_to_cart( $c333_product, 1 );
	$stock_card        = $c333_inquiry( 'GET', array( 'locale' => 'en' ) );
	$stock_digest      = (string) ( $stock_card['data']['lines_digest'] ?? '' );
	$posted_stock      = null;
	if ( '' !== $digest && $digest !== $stock_digest ) {
		$posted_stock = $c333_inquiry(
			'POST',
			array(
				'locale'  => 'en',
				'lines'   => $digest,
				'message' => 'c333 stale stock — must not send',
			)
		);
	}

	$orders_after = count(
		wc_get_orders(
			array(
				'customer_id' => $c333_user,
				'limit'       => -1,
				'return'      => 'ids',
			)
		)
	);

	if ( (int) $post_id > 0 ) {
		wp_delete_post( (int) $post_id, true );
	}

	echo wp_json_encode(
		array(
			'orders_before'        => $orders_before,
			'orders_after'         => $orders_after,
			'added'                => $added,
			'added_after_price'    => $added_after_price,
			'added_after_stock'    => $added_after_stock,
			'before'               => $before,
			'after_price'          => $after_price,
			'price_digest_changed' => $digest !== $price_digest,
			'posted_price'         => $posted_price,
			'stock_card'           => $stock_card,
			'stock_digest_changed' => $digest !== $stock_digest,
			'posted_stock'         => $posted_stock,
			'visible_lines_before' => $lines,
		)
	);
	echo "\n";
} catch ( Throwable $failure ) {
	fwrite( STDERR, 'c333-throw ' . $failure::class . ' ' . $failure->getMessage() . ' @ ' . $failure->getFile() . ':' . $failure->getLine() . "\n" );
	echo "{\"error\":" . wp_json_encode( $failure->getMessage() ) . "}\n";
	exit( 1 );
}
