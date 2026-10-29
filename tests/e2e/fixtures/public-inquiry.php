<?php
/**
 * Local browser fixture with isolated records and mail.
 * The eval-file entry point keeps strict typing in the included helper.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Tests\E2E\BrowserFixture;
use Linker\Commerce\Tests\E2E\PublicInquiryAssessment;


require_once __DIR__ . '/BrowserFixture.php';
require_once __DIR__ . '/public-inquiry-assessment.php';

( static function ( array $args ): void {
	$mode    = $args[0] ?? '';
	$fixture = new BrowserFixture( 'linker_246_round2_browser', 'tester246@example.test' );
	// Outbox rows this inquiry's real handoff recorded. The email substring is only
	// an isolation heuristic; a team message can miss it and still be this order's job.
	$owned_jobs = static function ( array $orders ): array {
		global $wpdb;
		$ids = array();
		foreach ( $orders as $order ) {
			$order_id = $order->get_id();
			$auth     = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order_id );
			if ( is_array( $auth ) && is_array( $auth['jobs'] ?? null ) ) {
				foreach ( $auth['jobs'] as $entry ) {
					$ids[] = (int) ( $entry['id'] ?? 0 );
				}
			}
			$bound = $wpdb->get_col( $wpdb->prepare( "SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key = %s AND meta_value = %s", '_linker_mail_inquiry', (string) $order_id ) );
			foreach ( is_array( $bound ) ? $bound : array() as $job_id ) {
				$ids[] = (int) $job_id;
			}
		}
		return array_values( array_filter( array_unique( $ids ) ) );
	};
	if ( 'setup' === $mode ) {
		PublicInquiryAssessment::remove();
		try {
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
			PublicInquiryAssessment::install();
		} catch ( Throwable $error ) {
			PublicInquiryAssessment::remove();
			throw $error;
		}
		echo wp_json_encode( array( 'product' => $product->get_id() ) );
		return;
	}
	$orders = $fixture->orders();
	$jobs   = $fixture->jobs();
	if ( 'read' === $mode ) {
		// The subject is the guest handoff, not the opportunistic wake. While
		// linker_246_assessment_fixture is on, this poll runs that inquiry's
		// real SendAuthorization under the shared worker lock. A busy lock is
		// left for the next poll; the wait and the wake are unchanged.
		if ( '1' === (string) get_option( PublicInquiryAssessment::OPTION, '' ) ) {
			foreach ( $orders as $order ) {
				$id = $order->get_id();
				\Linker\Commerce\Inquiry\Assessment\Lock::run(
					'async-worker',
					static function () use ( $id ): void {
						( new \Linker\Commerce\Inquiry\Assessment\Queue() )->process( $id );
					}
				);
			}
			$orders = $fixture->orders();
			foreach ( $orders as $order ) {
				$order->read_meta_data( true );
			}
			$jobs  = $fixture->jobs();
			$store = new \Linker\Commerce\Mail\JobStore();
			$seen  = array_fill_keys( $jobs, true );
			foreach ( $owned_jobs( $orders ) as $job_id ) {
				if ( isset( $seen[ $job_id ] ) || null === $store->load( $job_id ) ) {
					continue;
				}
				$jobs[]          = $job_id;
				$seen[ $job_id ] = true;
			}
		}
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
	try {
		foreach ( $owned_jobs( $orders ) as $job_id ) {
			if ( 'linker_mail_job' === get_post_type( $job_id ) ) {
				wp_delete_post( $job_id, true );
			}
		}
		$fixture->cleanup();
	} finally {
		PublicInquiryAssessment::remove();
	}
} )( $args );
