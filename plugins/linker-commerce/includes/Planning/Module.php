<?php
/**
 * Native Woo draft, inquiry and report-consumer integration.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

/** All visual output remains native semantic data; no page template or CSS. */
final class Module {
	/** Register native product/context lifecycle and private file access. */
	public function register(): void {
		$context = new Context();
		add_filter( 'linker_commerce_planning_draft_apply', array( new DraftTransfer(), 'apply' ), 10, 3 );
		add_filter( 'linker_commerce_planning_draft_preview', array( new DraftPreview(), 'read' ), 10, 3 );
		add_filter( 'linker_commerce_planning_draft_read', array( new DraftTransfer(), 'receipt' ), 10, 3 );
		add_filter( 'woocommerce_get_item_data', array( $context, 'item_data' ), 10, 2 );
		add_action( 'woocommerce_checkout_create_order_line_item', array( $context, 'line' ), 10, 3 );
		add_action( 'woocommerce_order_details_after_order_table', array( $context, 'render' ) );
		add_action( 'woocommerce_email_after_order_table', array( $context, 'email' ), 10, 3 );
		add_action( 'woocommerce_cart_emptied', array( $context, 'emptied' ) );
		add_action( 'rest_api_init', array( new ReportDownload(), 'register' ) );
	}
}
