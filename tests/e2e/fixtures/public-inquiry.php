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
					// Enforce mode caps receipts through the ledger-backed
					// ReceiptBudget site day, not the legacy option counter.
					// A distinct target each time fills the shared site
					// allowance without tripping a per-target cap first.
					\Linker\Commerce\Protection\ReceiptBudget::take( "cap-fixture-{$i}@example.test", "cap-fixture-{$i}" );
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
	if ( 'cleanup' === $mode ) {
		// No fixture installed is itself clean, and reading the records of an
		// absent state would refuse; re-running cleanup must stay safe.
		if ( false !== get_option( 'linker_246_round2_browser' ) ) {
			$orders = $fixture->orders();
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
		} else {
			PublicInquiryAssessment::remove();
		}
		return;
	}
	if ( 'process' === $mode ) {
		// Drive the real assessment pipeline to its settled state. The submit
		// request's own wake usually claims the order first and runs the
		// genuine classification concurrently, holding the same database mutex
		// for the whole model attempt. process() is zero-wait by design, so a
		// second call only returns while that worker runs; this waits on the
		// worker's own mutex instead of re-claiming on a timer. The mu-plugin
		// fixture answers the classifier call with a deterministic normal
		// verdict, so no model is spent and no request leaves the machine.
		$terminal = array( 'normal', 'manual', 'quarantined', 'invalidated' );
		// Three claimed model attempts' worth of the real bound
		// (Queue::WAIT_SECONDS): enough for the concurrent worker to finish its
		// claim plus this loop's own claim and handoff. A retry window is not
		// waited out — the fixture's answer is deterministic, so a retry means
		// the answer was rejected, and reporting the unsettled status is the
		// diagnosis instead of a longer wait.
		$deadline = microtime( true ) + 3 * \Linker\Commerce\Inquiry\Assessment\Queue::WAIT_SECONDS;
		$statuses = array();
		foreach ( $fixture->orders() as $order ) {
			$id = $order->get_id();
			while ( microtime( true ) < $deadline ) {
				$state  = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $id );
				$status = is_array( $state ) ? (string) ( $state['status'] ?? '' ) : '';
				if ( in_array( $status, $terminal, true ) ) {
					break;
				}
				// Block on the same mutex the worker holds until it finishes;
				// the order is then claimed here when it is still pending, and
				// a classified one is handed off by recover(). Lock::run's
				// bounded wait paces the loop, so no iteration is a blind sleep.
				\Linker\Commerce\Inquiry\Assessment\Lock::run( 'send-process-' . $id, static function (): void {}, 1 );
				\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $id );
				\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $id );
			}
			$final           = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $id );
			$statuses[ $id ] = is_array( $final ) ? (string) ( $final['status'] ?? '' ) : 'unreadable';
		}
		echo wp_json_encode(
			array(
				'processed' => count( $fixture->orders() ),
				'statuses'  => $statuses,
			)
		);
		return;
	}
	$orders = $fixture->orders();
	$jobs   = $fixture->jobs();
	if ( 'read' !== $mode ) {
		throw new RuntimeException( 'Unknown fixture mode.' );
	}
	$store = new \Linker\Commerce\Mail\JobStore();
	$seen  = array_fill_keys( $jobs, true );
	foreach ( $owned_jobs( $orders ) as $job_id ) {
		if ( isset( $seen[ $job_id ] ) || null === $store->load( $job_id ) ) {
			continue;
		}
		$jobs[]          = $job_id;
		$seen[ $job_id ] = true;
	}
	echo wp_json_encode(
		array(
			'orders' => array_map(
				static fn( $order ) => array(
					'status'        => $order->get_status(),
					'customer'      => $order->get_customer_id(),
					'source'        => $order->get_meta( '_linker_inquiry_source' ),
					'skipped'       => $order->get_meta( '_linker_receipt_skipped' ),
					'items'         => count( $order->get_items() ),
					'authorization' => ( static function ( int $id ): array {
						$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $id );
						return is_array( $state ) ? array(
							'status'    => $state['status'] ?? null,
							'team_only' => $state['team_only'] ?? false,
							'jobs'      => array_keys( $state['jobs'] ?? array() ),
						) : array();
					} )( $order->get_id() ),
				),
				$orders
			),
			'mail'   => array_map( static fn( $id ) => json_decode( get_post_meta( $id, '_linker_mail_message', true ), true ), $jobs ),
		)
	);
} )( $args );
