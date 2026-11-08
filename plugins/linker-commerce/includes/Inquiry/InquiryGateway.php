<?php
/**
 * The only way to send an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use WC_Order;
use WC_Payment_Gateway;

/**
 * The only "payment" gateway: it sends the inquiry. Nothing is ever paid on
 * this site; the quotation is written and sent offline by the team (owner
 * ruling 2026-11-08).
 */
final class InquiryGateway extends WC_Payment_Gateway {

	/**
	 * Gateway id.
	 */
	public const ID = 'linker_inquiry';

	/**
	 * Sets up the gateway. It is always on: without it no inquiry can be sent.
	 */
	public function __construct() {
		$this->id                 = self::ID;
		$this->has_fields         = false;
		$this->enabled            = 'yes';
		$this->supports           = array( 'products' );
		$this->method_title       = 'Inquiry';
		$this->method_description = 'Sends the inquiry without payment. The team replies offline. Always on: it is the only way to send an inquiry.';
	}

	/**
	 * Title shown on the inquiry page, in the visitor's language.
	 */
	public function get_title() {
		/** This filter is documented in woocommerce/includes/abstracts/abstract-wc-payment-gateway.php */
		return apply_filters( 'woocommerce_gateway_title', __( 'Inquiry', 'linker-commerce' ), $this->id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce's own filter, applied as WC_Payment_Gateway::get_title() applies it.
	}

	/**
	 * Text under the title.
	 */
	public function get_description() {
		/** This filter is documented in woocommerce/includes/abstracts/abstract-wc-payment-gateway.php */
		return apply_filters( 'woocommerce_gateway_description', __( 'We check your inquiry and reply with your quotation by email.', 'linker-commerce' ), $this->id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce's own filter, applied as WC_Payment_Gateway::get_description() applies it.
	}

	/**
	 * Name in the admin list of payment methods.
	 */
	public function get_method_title() {
		return __( 'Inquiry', 'linker-commerce' );
	}

	/**
	 * Description in the admin list of payment methods.
	 */
	public function get_method_description() {
		return __( 'Sends the inquiry free of charge. The team replies offline with the quotation. Always on: it is the only way to send an inquiry.', 'linker-commerce' );
	}

	/**
	 * Nothing to set up.
	 */
	public function needs_setup() {
		return false;
	}

	/**
	 * Marks the inquiry as received and sends the customer to the confirmation page.
	 *
	 * @param int $order_id Order id.
	 * @return array{result: string, redirect: string}
	 */
	public function process_payment( $order_id ) {
		$order = wc_get_order( $order_id );
		if ( ! $order instanceof WC_Order ) {
			return array(
				'result'   => 'failure',
				'redirect' => '',
			);
		}
		$order->update_status( Statuses::RECEIVED );
		WC()->cart->empty_cart();
		return array(
			'result'   => 'success',
			'redirect' => $this->get_return_url( $order ),
		);
	}
}
