<?php
/**
 * Approved home-page price turn while the catalogue price is 1701.
 *
 * 1701 is not a catalogue constant. It is a figure a stale 1680 card cannot
 * match. The shutdown hook restores the snapshot if this process dies before
 * the explicit restore. The password and the token are not printed.
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

$accounts  = c333_accounts();
$priced    = $accounts['products']['priced'];
$ids       = array( (int) $priced['en'], (int) $priced['de'] );
$snapshots = array();
foreach ( $ids as $id ) {
	$snapshots[ $id ] = c333_snap( $id );
}
$approved     = c333_user_id( 'approved' );
$conversation = 0;
$changed      = '1701';

register_shutdown_function(
	static function () use ( $snapshots, &$conversation ): void {
		foreach ( $snapshots as $id => $snap ) {
			c333_restore( (int) $id, $snap );
		}
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
	foreach ( $ids as $id ) {
		$product = wc_get_product( $id );
		if ( $product instanceof WC_Product ) {
			$product->set_regular_price( $changed );
			$product->set_price( $changed );
			$product->save();
		}
	}

	wp_set_current_user( $approved );
	$turn = c333_rest(
		'POST',
		'/linker-ai/v1/genie/turn',
		array(
			'locale'   => 'en',
			'messages' => array(
				array(
					'role'    => 'user',
					'content' => 'What is the net price of the SAJ H2-10K-T3?',
				),
			),
			'page'     => array(
				'type'  => 'home',
				'url'   => home_url( '/' ),
				'title' => 'Linker',
			),
		),
		array(),
		false
	);
	if ( isset( $turn['data']['conversation_id'] ) ) {
		$conversation = (int) $turn['data']['conversation_id'];
	}

	wp_set_current_user( 0 );
	foreach ( $snapshots as $id => $snap ) {
		c333_restore( (int) $id, $snap );
	}
	if ( $conversation > 0 ) {
		wp_delete_post( $conversation, true );
		$conversation = 0;
	}

	$tracked = c333_product_ids();
	$stream  = $turn['data']['stream'] ?? '';
	echo wp_json_encode(
		array(
			'status' => $turn['status'],
			'stream' => is_string( $stream ) ? $stream : '',
			'catalog' => c333_catalog_read(
				array( $tracked['priced'], $tracked['priced_de'], $tracked['rfq'], $tracked['rfq_de'] )
			),
		)
	);
	echo "\n";
} catch ( Throwable $failure ) {
	fwrite( STDERR, 'c333-throw ' . $failure::class . ' ' . $failure->getMessage() . ' @ ' . $failure->getFile() . ':' . $failure->getLine() . "\n" );
	echo '{"error":' . wp_json_encode( $failure->getMessage() ) . "}\n";
	exit( 1 );
}
