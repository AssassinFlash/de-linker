<?php
/**
 * Stock-edge probes for campaign #333, in one PHP process.
 *
 * Snapshot, register the shutdown restore, push, read, then restore and read
 * back. The shutdown hook still runs when the Python parent is SIGKILL'd:
 * this process exits on its own and puts the catalogue back. A Python
 * finally does not.
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

$accounts   = c333_accounts();
$priced     = $accounts['products']['priced'];
$rfq        = $accounts['products']['rfq'];
$priced_id  = (int) $priced['en'];
$rfq_id     = (int) $rfq['en'];
$priced_sku = (string) $priced['sku'];
$rfq_sku    = (string) $rfq['sku'];
$priced_url = (string) $priced['permalink'];
$approved   = c333_user_id( 'approved' );
$tracked    = array( $priced_id, (int) $priced['de'], $rfq_id, (int) $rfq['de'] );

$snapshots = array();
foreach ( $tracked as $id ) {
	$snapshots[ $id ] = c333_snap( $id );
}
if ( \Linker\Commerce\Stock\PushKey::is_set() ) {
	throw new RuntimeException( 'push key was already set' );
}

$conversation = 0;
register_shutdown_function(
	static function () use ( $snapshots, &$conversation ): void {
		foreach ( $snapshots as $id => $snap ) {
			c333_restore( (int) $id, $snap );
		}
		\Linker\Commerce\Stock\PushKey::clear();
		if ( $conversation > 0 ) {
			wp_delete_post( $conversation, true );
		}
	}
);

// The turn inside this process may take the harness TURN_TIMEOUT (180 s).
// 200 s is that ceiling plus the snapshot and the restore. PHP's default
// 30 s would abort the model.
set_time_limit( 200 );

try {
	$backorder = array();
	foreach (
		wc_get_products(
			array(
				'status'       => 'publish',
				'stock_status' => 'onbackorder',
				// A sample of published onbackorder rows, not the whole catalogue.
				// Five is enough for the badge to disagree with in_stock.
				'limit'        => 5,
				'return'       => 'ids',
			)
		) as $id
	) {
		$backorder[] = (int) $id;
	}

	$key = \Linker\Commerce\Stock\PushKey::generate();
	\Linker\Commerce\Stock\PushKey::set( $key );

	$pushes = array();
	$push   = static function ( array $items, string $id, string $expect ) use ( $key, &$pushes ): void {
		$result   = c333_rest(
			'POST',
			'/linker/v1/stock',
			array( 'items' => $items ),
			array( 'X-Linker-Stock-Key' => $key )
		);
		$pushes[] = array(
			'id'     => $id,
			'expect' => $expect,
			'status' => $result['status'],
			'body'   => $result['data'],
		);
	};

	$push( array( array( 'sku' => $priced_sku, 'qty' => -1 ) ), 'stock-negative-qty', 'invalid_qty' );
	$push( array( array( 'sku' => $priced_sku, 'qty' => 0 ) ), 'stock-qty-on-unmanaged', 'not_stock_managed' );
	$push( array( array( 'sku' => $priced_sku, 'state' => 'onbackorder' ) ), 'stock-reject-backorder', 'invalid_state' );
	$push(
		array(
			array( 'sku' => $priced_sku, 'state' => 'outofstock' ),
			array( 'sku' => $rfq_sku, 'state' => 'outofstock' ),
		),
		'stock-state-out',
		'outofstock'
	);

	// UserContext::TTL. The probe lives as long as a product token, not longer.
	$token    = c333_token( $approved, 120 );
	$ability  = c333_ability(
		'linker/get-product',
		array(
			'product_id' => $priced_id,
			'lang'       => 'en',
		),
		$token
	);
	$page     = c333_page_text( $priced_url );
	$store    = c333_rest(
		'GET',
		'/wc/store/v1/products',
		array(
			'include' => array( $priced_id ),
			'lang'    => 'en',
		)
	);
	$question = 'Is the SAJ H2-10K-T3 in stock right now?';
	$turn     = c333_rest(
		'POST',
		'/linker-ai/v1/genie/turn',
		array(
			'locale'   => 'en',
			'messages' => array(
				array(
					'role'    => 'user',
					'content' => $question,
				),
			),
			'page'     => array(
				'type'       => 'product',
				'url'        => $priced_url,
				'title'      => 'SAJ H2-10K-T3',
				'product_id' => $priced_id,
			),
		)
	);
	if ( isset( $turn['data']['conversation_id'] ) ) {
		$conversation = (int) $turn['data']['conversation_id'];
	}

	$push( array( array( 'sku' => $priced_sku, 'state' => 'instock' ) ), 'stock-state-restore', 'instock' );
	\Linker\Commerce\Stock\PushKey::clear();

	$back_rows = array();
	foreach ( $backorder as $id ) {
		$product = wc_get_product( $id );
		if ( $product instanceof WC_Product ) {
			$product->set_stock_status( 'onbackorder' );
			$product->save();
		}
		$looked      = c333_ability(
			'linker/get-product',
			array(
				'product_id' => $id,
				'lang'       => 'en',
			)
		);
		$back_rows[] = array(
			'product_id' => $id,
			'commerce'   => c333_commerce( $looked ),
			'page_text'  => c333_page_text( home_url( '/?p=' . $id ) ),
		);
	}

	foreach ( $snapshots as $id => $snap ) {
		c333_restore( (int) $id, $snap );
	}
	if ( $conversation > 0 ) {
		wp_delete_post( $conversation, true );
		$conversation = 0;
	}

	$stream = $turn['data']['stream'] ?? '';
	echo wp_json_encode(
		array(
			'pushes'            => $pushes,
			'ability_after_out' => array(
				'commerce'  => c333_commerce( $ability ),
				'page_text' => $page,
			),
			'store_after_out'   => $store['data'],
			'turn_after_out'    => array(
				'status'          => $turn['status'],
				'stream'          => is_string( $stream ) ? $stream : '',
				'conversation_id' => (int) ( $turn['data']['conversation_id'] ?? 0 ),
			),
			'backorder'         => $back_rows,
			'catalog'           => c333_catalog_read( $tracked ),
		)
	);
	echo "\n";
} catch ( Throwable $failure ) {
	fwrite( STDERR, 'c333-throw ' . $failure::class . ' ' . $failure->getMessage() . ' @ ' . $failure->getFile() . ':' . $failure->getLine() . "\n" );
	echo '{"error":' . wp_json_encode( $failure->getMessage() ) . "}\n";
	exit( 1 );
}
