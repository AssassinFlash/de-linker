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
		add_filter( 'linker_commerce_planning_inquiry_form', array( $this, 'inquiry_form' ), 10, 3 );
		add_filter( 'linker_commerce_planning_draft_apply', array( new DraftTransfer(), 'apply' ), 10, 3 );
		add_filter( 'linker_commerce_planning_draft_preview', array( new DraftPreview(), 'read' ), 10, 3 );
		add_filter( 'linker_commerce_planning_draft_read', array( new DraftTransfer(), 'receipt' ), 10, 3 );
		add_filter( 'woocommerce_get_item_data', array( $context, 'item_data' ), 10, 2 );
		add_action( 'woocommerce_before_cart', array( $context, 'cart_phase_notices' ) );
		add_action( 'woocommerce_checkout_create_order_line_item', array( $context, 'line' ), 10, 3 );
		add_action( 'woocommerce_order_details_after_order_table', array( $context, 'render' ) );
		add_action( 'woocommerce_admin_order_data_after_order_details', array( $context, 'render' ) );
		add_action( 'woocommerce_email_after_order_table', array( $context, 'email' ), 10, 3 );
		add_action( 'woocommerce_cart_emptied', array( $context, 'emptied' ) );
		add_action( 'rest_api_init', array( new ReportDownload(), 'register' ) );
	}

	/** Native inquiry form and the current draft it will send.
	 *
	 * @param mixed               $previous Earlier filter result.
	 * @param string              $language Requested planner language.
	 * @param array<string,mixed> $project  Owner-verified project revision.
	 * @return array<string,mixed>
	 */
	public function inquiry_form( mixed $previous, string $language, array $project ): array {
		unset( $previous );
		wc_load_cart();
		$active = Context::active();
		$lines  = array();
		foreach ( WC()->cart->get_cart() as $line ) {
			$source  = $line[ DraftTransfer::LINE_META ] ?? '';
			$lines[] = array(
				'product_id'    => (int) $line['product_id'],
				'label'         => $line['data']->get_name(),
				'quantity'      => $line['quantity'],
				'project_id'    => $active[ $source ]['snapshot']['project_id'] ?? null,
				'project_title' => $active[ $source ]['snapshot']['title'] ?? null,
			);
		}
		return array(
			'schema_version'    => 1,
			'inquiry_form_html' => ( new \Linker\Commerce\Inquiry\Form() )->planning( $language, $project ),
			'inquiry_lines'     => $lines,
		);
	}
}
