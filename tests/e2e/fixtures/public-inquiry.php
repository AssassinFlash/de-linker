<?php
/**
 * Local browser fixture with isolated records and mail.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

use Linker\Commerce\Tests\E2E\BrowserFixture;


require_once __DIR__ . '/BrowserFixture.php';

( static function ( array $args ): void {
	$mode    = $args[0] ?? '';
	$fixture = new BrowserFixture( 'linker_246_round2_browser', 'tester246@example.test' );
	if ( 'setup' === $mode ) {
		$fixture->setup( $args[1] );
		$product = new WC_Product_Simple();
		$product->set_name( '246 browser fixture' );
		$product->set_regular_price( '100' );
		$product->save();
		$fixture->add_product( $product->get_id() );
		if ( 'capped' === ( $args[2] ?? '' ) ) {
			for ( $i = 0; $i < 10; ++$i ) {
				( new \Linker\Commerce\Inquiry\ReceiptLimit() )->take();
			}
		}
		echo wp_json_encode( array( 'product' => $product->get_id() ) );
		return;
	}
	$orders = $fixture->orders();
	$jobs   = $fixture->jobs();
	if ( 'read' === $mode ) {
		echo wp_json_encode(
			array(
				'orders' => array_map(
					static fn ( $order ) => array(
						'status'   => $order->get_status(),
						'customer' => $order->get_customer_id(),
						'source'   => $order->get_meta( '_linker_inquiry_source' ),
						'skipped'  => $order->get_meta( '_linker_receipt_skipped' ),
						'items'    => count( $order->get_items() ),
					),
					$orders
				),
				'mail'   => array_map( static fn ( $id ) => json_decode( get_post_meta( $id, '_linker_mail_message', true ), true ), $jobs ),
			)
		);
		return;
	}
	if ( 'cleanup' !== $mode ) {
		throw new RuntimeException( 'Unknown fixture mode.' );
	}
	$fixture->cleanup();
} )( $args );
