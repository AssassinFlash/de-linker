<?php
/**
 * Current inquiry business evidence, frozen before notification scheduling.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use WC_Order;
use WC_Order_Item_Product;

/** Woo fields are authoritative; the optional tools filter supplies owned context. */
final class Snapshot {
	/** All available business fields, without system secrets or unrelated history.
	 *
	 * @param WC_Order             $order Inquiry before its received transition.
	 * @param array<string, mixed> $context Trusted originating Genie link, if present.
	 * @return array<string, mixed>
	 * @param bool                 $owned_context Include only the trusted current browser context.
	 */
	public static function make( WC_Order $order, array $context = array(), bool $owned_context = true ): array {
		$products = array();
		foreach ( $order->get_items() as $item ) {
			if ( $item instanceof WC_Order_Item_Product ) {
				$product    = $item->get_product();
				$products[] = array(
					'id'           => $item->get_product_id(),
					'variation_id' => $item->get_variation_id(),
					'name'         => $item->get_name(),
					'sku'          => $product instanceof \WC_Product ? $product->get_sku() : '',
					'quantity'     => $item->get_quantity(),
					'total'        => $item->get_total(),
				);
			}
		}
		$handoff = $order->get_meta( \Linker\Commerce\Genie\Module::HANDOFF_META );
		if ( is_array( $handoff ) ) {
			$context = array_merge( $context, $handoff );
		}
		/**
		 * Reads only a current/owned conversation. Does not create a conversation.
		 *
		 * @since 0.1.0
		 *
		 * @param array<string, mixed> $evidence Missing until linker-tools answers.
		 * @param array<string, mixed> $context Trusted source link.
		 * @param bool                $contact Contact forms have no implicit thread.
		 */
		$evidence     = $owned_context ? apply_filters( 'linker_commerce_inquiry_assessment_context', array( 'status' => 'unavailable' ), $context, 'contact' === $order->get_meta( '_linker_inquiry_source' ) ) : array( 'status' => 'unavailable' );
		$user         = $order->get_customer_id();
		$account      = get_user_by( 'id', $user );
		$registration = array();
		if ( $account instanceof \WP_User ) {
			$fields       = new \Linker\Commerce\Registration\Fields( new \Linker\Commerce\Registration\VatProfile( new \Linker\Commerce\Registration\ViesClient() ), new \Linker\Commerce\Registration\Approval() );
			$registration = ( new \Linker\Commerce\Registration\RegistrationInformation( $fields ) )->rows( $account );
		}
		return array(
			'submission' => array(
				'source'    => $order->get_meta( '_linker_inquiry_source' ),
				'locale'    => $order->get_meta( \Linker\Commerce\Inquiry\OrderLocale::META ),
				'topic'     => $order->get_meta( '_linker_inquiry_topic' ),
				'billing'   => $order->get_address( 'billing' ),
				'message'   => $order->get_customer_note(),
				'selection' => \Linker\Commerce\Contact\SelectionContext::stored( $order->get_meta( \Linker\Commerce\Contact\SelectionContext::META ) ),
				'summary'   => $order->get_meta( \Linker\Commerce\Inquiry\Sender::SUMMARY_META ),
				'handoff'   => is_array( $handoff ) ? $handoff : array(),
			),
			'account'    => array(
				'registration' => $registration,
				'id'           => $user,
				'status'       => $user > 0 ? get_user_meta( $user, \Linker\Commerce\Registration\Approval::STATUS_META, true ) : 'guest',
				'vat'          => $user > 0 ? get_user_meta( $user, \Linker\Commerce\Registration\VatProfile::VAT_META, true ) : '',
			),
			'products'   => $products,
			'context'    => $evidence,
		);
	}
}
