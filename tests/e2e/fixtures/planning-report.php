<?php
/**
 * A local inquiry carrying one frozen planning report.
 *
 * The stored context is written the way the planner writes it
 * (Context::reference over an engine-owned handoff), and the engine's two
 * calls are answered by PlanningReportEngineFixture. Everything the browser
 * then touches is production: the inquiry page, the download route, the
 * Tools reader and its hash comparisons.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Planning\Context;
use Linker\Commerce\Tests\Fixtures\PlanningReportEngineFixture;

require_once dirname( __DIR__, 3 ) . '/plugins/linker-commerce/tests/fixtures/PlanningReportEngineFixture.php';

( static function ( array $args ): void {
	$mode = $args[0] ?? '';

	if ( 'customer' === $mode ) {
		$login    = (string) ( $args[1] ?? '' );
		$password = (string) ( $args[2] ?? '' );
		if ( '' === $login || '' === $password ) {
			throw new RuntimeException( 'usage: customer <login> <password>' );
		}
		$email = "{$login}@example.test";
		$id    = wp_insert_user(
			array(
				'user_login' => $login,
				'user_email' => $email,
				'user_pass'  => $password,
				'role'       => 'customer',
			)
		);
		if ( is_wp_error( $id ) ) {
			throw new RuntimeException( 'the fixture customer was not created: ' . $id->get_error_message() );
		}
		update_user_meta( $id, 'linker_approval_status', 'approved' );
		echo (string) $id;
		return;
	}

	if ( 'setup' === $mode ) {
		$login    = (string) ( $args[1] ?? '' );
		$password = (string) ( $args[2] ?? '' );
		$tag      = strtolower( (string) ( $args[3] ?? '' ) );
		if ( '' === $login || '' === $password || '' === $tag ) {
			throw new RuntimeException( 'usage: setup <login> <password> <tag>' );
		}
		$email = "{$login}@example.test";
		$id    = wp_insert_user(
			array(
				'user_login' => $login,
				'user_email' => $email,
				'user_pass'  => $password,
				'role'       => 'customer',
			)
		);
		if ( is_wp_error( $id ) ) {
			throw new RuntimeException( 'the fixture customer was not created: ' . $id->get_error_message() );
		}
		update_user_meta( $id, 'linker_approval_status', 'approved' );
		foreach ( array(
			'first_name' => 'Maria',
			'last_name'  => 'Beispiel',
			'email'      => $email,
			'company'    => 'E2E Report GmbH',
		) as $key => $value ) {
			update_user_meta( $id, 'billing_' . $key, $value );
		}

		// A fixture inquiry is created, never submitted: its status hooks are
		// removed in this request so no mail job is queued for it.
		remove_all_actions( 'woocommerce_order_status_pending_to_inquiry-received' );
		remove_all_actions( 'woocommerce_order_status_pending_to_inquiry-received_notification' );
		$order = wc_create_order( array( 'customer_id' => $id ) );
		if ( ! $order instanceof WC_Order ) {
			throw new RuntimeException( 'the fixture inquiry was not created' );
		}
		$order->set_payment_method( 'linker_inquiry' );
		$order->set_billing_email( $email );
		$order->set_billing_first_name( 'Maria' );
		$order->set_billing_last_name( 'Beispiel' );
		$order->set_billing_company( 'E2E Report GmbH' );
		$order->update_meta_data( '_linker_locale', 'en_US' );
		$product = wc_get_product( (int) ( $args[4] ?? 0 ) );
		if ( $product instanceof WC_Product ) {
			$order->add_product( $product, 1 );
		}

		$pdf     = "%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n";
		$handoff = array(
			'schema_version'  => 1,
			'id'              => bin2hex( random_bytes( 16 ) ),
			'snapshot_sha256' => hash( 'sha256', 'e2e-snapshot' ),
			'snapshot'        => array(
				'schema_version'       => 1,
				'kind'                 => 'planning_products_v1',
				'project_id'           => bin2hex( random_bytes( 16 ) ),
				'title'                => 'E2E roof plan',
				'revision'             => 2,
				'input_sha256'         => hash( 'sha256', 'e2e-input' ),
				'report_run_id'        => bin2hex( random_bytes( 16 ) ),
				'report_source_sha256' => hash( 'sha256', 'e2e-source' ),
				'report_sha256'        => hash( 'sha256', 'e2e-report' ),
				'pdf'                  => array(
					'asset_id'   => bin2hex( random_bytes( 16 ) ),
					'sha256'     => hash( 'sha256', $pdf ),
					'media_type' => 'application/pdf',
				),
				'items'                => array(
					array(
						'product_id' => $product instanceof WC_Product ? $product->get_id() : 1,
						'quantity'   => 1,
						'label'      => $product instanceof WC_Product ? $product->get_name() : 'Fixture product',
					),
				),
			),
		);
		$order->update_meta_data(
			Context::META,
			(string) wp_json_encode( array( $handoff['id'] => array( 'reference' => Context::reference( $handoff ) ) ) )
		);
		$order->set_status( 'inquiry-received' );
		$order->calculate_totals( false );
		$order->save();

		PlanningReportEngineFixture::install( $handoff, $pdf );
		// The customer's link is the order's own key; it is what the receipt emails.
		echo wp_json_encode(
			array(
				'customer' => $id,
				'order'    => $order->get_id(),
				'handoff'  => $handoff['id'],
				'key'      => $order->get_order_key(),
			)
		);
		return;
	}

	if ( 'answer' === $mode ) {
		// Each call states the whole answer: the flags not named are off.
		$changes = array(
			'refuse_handoff'  => false,
			'refuse_content'  => false,
			'replace_content' => false,
		);
		foreach ( array_slice( $args, 1 ) as $flag ) {
			$changes[ (string) $flag ] = true;
		}
		PlanningReportEngineFixture::answer( $changes );
		echo 'answered';
		return;
	}

	if ( 'cleanup' === $mode ) {
		$order_id  = (int) ( $args[1] ?? 0 );
		$order     = $order_id > 0 ? wc_get_order( $order_id ) : false;
		if ( $order instanceof WC_Order ) {
			$order->delete( true );
		}
		require_once ABSPATH . 'wp-admin/includes/user.php';
		foreach ( array_slice( $args, 2 ) as $customer ) {
			if ( (int) $customer > 0 ) {
				wp_delete_user( (int) $customer );
			}
		}
		PlanningReportEngineFixture::remove();
		echo 'removed';
		return;
	}

	throw new RuntimeException( 'unknown mode ' . $mode );
} )( $args ?? array() );
