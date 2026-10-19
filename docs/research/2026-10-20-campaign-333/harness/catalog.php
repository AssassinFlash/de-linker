<?php
/**
 * Shared catalogue, order and token helpers for the #333 harness.
 *
 * No file-level const: `wp eval-file` includes a file from inside a method,
 * and PHP compiles const only in the global scope. No side effects. Callers
 * register their own shutdown hooks.
 *
 * A second include returns immediately.
 */

if ( function_exists( 'c333_accounts' ) ) {
	return;
}

/**
 * The fixture next to the evidence. Ids only; callers must not echo passwords.
 *
 * @return array<string, mixed>
 */
function c333_accounts(): array {
	$home = getenv( 'HOME' );
	if ( ! is_string( $home ) || '' === $home ) {
		throw new RuntimeException( 'HOME is unset' );
	}
	$path = $home . '/de-linker-data/campaign-333/accounts.json';
	$raw  = file_get_contents( $path );
	if ( ! is_string( $raw ) ) {
		throw new RuntimeException( 'accounts.json is missing' );
	}
	$data = json_decode( $raw, true );
	if ( ! is_array( $data ) ) {
		throw new RuntimeException( 'accounts.json is not an object' );
	}
	return $data;
}

/**
 * A fixture customer id. Never users outside pending, restricted and approved.
 */
function c333_user_id( string $state ): int {
	$accounts = c333_accounts();
	$users    = $accounts['users'] ?? null;
	$row      = is_array( $users ) ? ( $users[ $state ] ?? null ) : null;
	$id       = is_array( $row ) ? ( $row['id'] ?? 0 ) : 0;
	if ( ! is_numeric( $id ) || (int) $id < 1 ) {
		throw new RuntimeException( 'missing user id for ' . $state );
	}
	return (int) $id;
}

/**
 * Priced and RFQ posts, EN and the DE twin.
 *
 * @return array{priced: int, priced_de: int, rfq: int, rfq_de: int}
 */
function c333_product_ids(): array {
	$products = c333_accounts()['products'] ?? null;
	if ( ! is_array( $products ) ) {
		throw new RuntimeException( 'accounts.json has no products' );
	}
	$priced = $products['priced'] ?? null;
	$rfq    = $products['rfq'] ?? null;
	if ( ! is_array( $priced ) || ! is_array( $rfq ) ) {
		throw new RuntimeException( 'accounts.json products are incomplete' );
	}
	return array(
		'priced'    => (int) $priced['en'],
		'priced_de' => (int) $priced['de'],
		'rfq'       => (int) $rfq['en'],
		'rfq_de'    => (int) $rfq['de'],
	);
}

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

/**
 * The four catalogue rows and whether the push channel is open.
 *
 * @param array<int, int> $ids
 * @return array{key: bool, products: array<string, array{regular: string, stock: string}>}
 */
function c333_catalog_read( array $ids ): array {
	$products = array();
	foreach ( $ids as $id ) {
		$snap                    = c333_snap( (int) $id );
		$products[ (string) $id ] = array(
			'regular' => $snap['price'],
			'stock'   => $snap['status'],
		);
	}
	$key = class_exists( \Linker\Commerce\Stock\PushKey::class ) && \Linker\Commerce\Stock\PushKey::is_set();
	return array(
		'key'      => $key,
		'products' => $products,
	);
}

/**
 * The known-good catalogue from accounts.json: priced rows at their regular
 * price and instock, RFQ rows onbackorder, push channel closed.
 *
 * @return array{key: bool, products: array<string, array{regular: string, stock: string}>}
 */
function c333_force_known_good(): array {
	$accounts = c333_accounts();
	$priced   = $accounts['products']['priced'] ?? null;
	$rfq      = $accounts['products']['rfq'] ?? null;
	if ( ! is_array( $priced ) || ! is_array( $rfq ) ) {
		throw new RuntimeException( 'accounts.json products are incomplete' );
	}
	$price = (string) $priced['price'];
	foreach ( array( (int) $priced['en'], (int) $priced['de'] ) as $id ) {
		$product = wc_get_product( $id );
		if ( $product instanceof WC_Product ) {
			$product->set_regular_price( $price );
			$product->set_price( $price );
			$product->set_stock_status( 'instock' );
			$product->save();
		}
	}
	foreach ( array( (int) $rfq['en'], (int) $rfq['de'] ) as $id ) {
		$product = wc_get_product( $id );
		if ( $product instanceof WC_Product ) {
			$product->set_stock_status( 'onbackorder' );
			$product->save();
		}
	}
	if ( class_exists( \Linker\Commerce\Stock\PushKey::class ) ) {
		\Linker\Commerce\Stock\PushKey::clear();
	}
	return c333_catalog_read(
		array( (int) $priced['en'], (int) $priced['de'], (int) $rfq['en'], (int) $rfq['de'] )
	);
}

/**
 * HPOS keeps orders out of the posts table. wp_delete_post does not delete
 * them. Read the ids back; a non-empty remaining list means the delete missed.
 *
 * @param array<int, int|string> $ids
 * @return array{deleted: array<int, int>, remaining: array<int, int>}
 */
function c333_delete_orders( array $ids ): array {
	$deleted = array();
	foreach ( $ids as $id ) {
		$order = wc_get_order( (int) $id );
		if ( $order instanceof WC_Order ) {
			$order->delete( true );
			$deleted[] = (int) $id;
		}
	}
	$remaining = array();
	foreach ( $ids as $id ) {
		$order = wc_get_order( (int) $id );
		if ( $order instanceof WC_Order ) {
			$remaining[] = (int) $id;
		}
	}
	return array(
		'deleted'   => $deleted,
		'remaining' => $remaining,
	);
}

/**
 * Every order owned by these customers. The follow-up sweep uses this.
 * It does not widen the set past the ids it is given.
 *
 * @param array<int, int> $user_ids
 * @return array{deleted: array<int, int>, remaining: array<int, int>}
 */
function c333_delete_customer_orders( array $user_ids ): array {
	$found = wc_get_orders(
		array(
			'customer_id' => array_map( 'intval', $user_ids ),
			'limit'       => -1,
			'return'      => 'ids',
		)
	);
	$ids = array();
	foreach ( (array) $found as $id ) {
		$ids[] = (int) $id;
	}
	return c333_delete_orders( $ids );
}

if ( ! class_exists( 'C333Mint' ) ) {
	/**
	 * UserContext::sign is protected. One subclass, used by every probe.
	 */
	class C333Mint extends \Linker\Tools\Genie\UserContext {
		public function make( int $user, int $expiry ): string {
			$payload = $user . '|' . $expiry;
			return $payload . '|' . $this->sign( $payload );
		}
	}
}

/**
 * A customer token. Offset is seconds from now (negative for an expired one).
 */
function c333_token( int $user, int $offset ): string {
	$mint = new C333Mint();
	return $mint->make( $user, time() + $offset );
}

/**
 * One REST dispatch. `$as_guest` clears the current user first so a token
 * header is what signs the request in. A cookie-shaped probe passes false
 * after it has already called wp_set_current_user.
 *
 * @param array<string, mixed> $params
 * @param array<string, string> $headers
 * @return array{status: int, data: array<mixed>}
 */
function c333_rest( string $method, string $route, array $params = array(), array $headers = array(), bool $as_guest = true ): array {
	if ( $as_guest ) {
		wp_set_current_user( 0 );
	}
	$request = new WP_REST_Request( $method, $route );
	foreach ( $headers as $name => $value ) {
		$request->set_header( (string) $name, (string) $value );
	}
	if ( 'GET' === $method ) {
		$request->set_query_params( $params );
	} else {
		foreach ( $params as $key => $value ) {
			$request->set_param( (string) $key, $value );
		}
	}
	$response = rest_do_request( $request );
	$data     = $response->get_data();
	if ( ! is_array( $data ) ) {
		$data = array( 'raw' => $data );
	}
	return array(
		'status' => $response->get_status(),
		'data'   => $data,
	);
}

/**
 * @param array<string, mixed> $input
 * @return array{status: int, data: array<mixed>}
 */
function c333_ability( string $name, array $input, string $token = '' ): array {
	$headers = array();
	if ( '' !== $token ) {
		$headers['X-Linker-User-Context'] = $token;
	}
	return c333_rest(
		'GET',
		'/wp-abilities/v1/abilities/' . $name . '/run',
		array( 'input' => $input ),
		$headers,
		true
	);
}

/**
 * @param array{status: int, data: array<mixed>} $response
 * @return array<string, mixed>
 */
function c333_commerce( array $response ): array {
	$data = $response['data'];
	if ( isset( $data['result'] ) && is_array( $data['result'] ) ) {
		$data = $data['result'];
	}
	$commerce = $data['commerce'] ?? array();
	return is_array( $commerce ) ? $commerce : array();
}

/**
 * Visible text of a public page. Stock badges are element text, so stripping
 * tags keeps them. An aria-label does not survive this; compare rows are
 * graded from their markup in Python.
 */
function c333_page_text( string $url ): string {
	$response = wp_remote_get(
		$url,
		array(
			'timeout'     => 30,
			'redirection' => 3,
		)
	);
	if ( is_wp_error( $response ) ) {
		return '';
	}
	$html = (string) wp_remote_retrieve_body( $response );
	$text = preg_replace( '/\s+/', ' ', wp_strip_all_tags( $html ) );
	return trim( is_string( $text ) ? $text : '' );
}
