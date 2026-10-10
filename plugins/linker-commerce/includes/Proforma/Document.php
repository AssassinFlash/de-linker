<?php
/**
 * What a Proforma invoice says.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Proforma;

use DateTimeImmutable;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Vocabulary\LocaleFormat;
use WC_Order;
use WC_Order_Item_Product;

/**
 * Collects the content of a Proforma invoice from the inquiry and the
 * settings: seller and bank account, buyer, lines, tax as WooCommerce
 * calculated it for the inquiry, total, number and validity.
 */
final class Document {

	/**
	 * Days a Proforma invoice is valid (owner ruling 2026-10-09, AGENTS.md §2).
	 */
	public const VALID_DAYS = 30;

	/**
	 * Sets up the document.
	 *
	 * @param Options $options The plugin settings.
	 */
	public function __construct( private readonly Options $options ) {}

	/**
	 * The day a Proforma issued at a time stops being valid.
	 *
	 * @param DateTimeImmutable $issued Time of issue.
	 */
	public static function valid_until( DateTimeImmutable $issued ): DateTimeImmutable {
		return $issued->modify( '+' . self::VALID_DAYS . ' days' );
	}

	/**
	 * The template data of a Proforma invoice, in the current language.
	 *
	 * @param WC_Order          $order  Inquiry.
	 * @param string            $number Proforma number.
	 * @param DateTimeImmutable $issued Time of issue.
	 * @return array<string, mixed>
	 */
	public function data( WC_Order $order, string $number, DateTimeImmutable $issued ): array {
		$currency = array( 'currency' => $order->get_currency() );
		$lines    = array();
		$position = 0;
		foreach ( $order->get_items() as $item ) {
			if ( ! $item instanceof WC_Order_Item_Product ) {
				continue;
			}
			$product = $item->get_product();
			$lines[] = array(
				'position' => ++$position,
				'name'     => $item->get_name(),
				'sku'      => $product instanceof \WC_Product ? $product->get_sku() : '',
				'quantity' => $item->get_quantity(),
				'unit'     => wc_price( $order->get_item_subtotal( $item, false, true ), $currency ),
				'total'    => wc_price( (float) $item->get_total(), $currency ),
			);
		}
		$fees = array();
		foreach ( $order->get_fees() as $fee ) {
			$fees[] = array(
				'name'  => $fee->get_name(),
				'total' => wc_price( (float) $fee->get_total(), $currency ),
			);
		}
		$taxes = array();
		foreach ( $order->get_tax_totals() as $tax ) {
			$taxes[] = array(
				'label'  => (string) $tax->label,
				'amount' => (string) $tax->formatted_amount,
			);
		}

		$address = $order->get_address( 'billing' );
		unset( $address['first_name'], $address['last_name'], $address['company'], $address['email'], $address['phone'] );
		$format = LocaleFormat::date_format();

		return array(
			'number'      => $number,
			'inquiry'     => '#' . $order->get_order_number(),
			'issued'      => wp_date( $format, $issued->getTimestamp() ),
			'valid_until' => wp_date( $format, self::valid_until( $issued )->getTimestamp() ),
			'seller'      => $this->options->seller(),
			'bank'        => $this->options->bank(),
			'buyer'       => array(
				'company' => $order->get_billing_company(),
				'name'    => $order->get_formatted_billing_full_name(),
				'address' => array_values( array_filter( explode( '<br/>', WC()->countries->get_formatted_address( $address ) ) ) ),
				'vat_id'  => (string) $order->get_meta( '_' . VatProfile::VAT_META ),
				'email'   => $order->get_billing_email(),
			),
			'lines'       => $lines,
			'fees'        => $fees,
			'subtotal'    => wc_price( (float) $order->get_subtotal(), $currency ),
			'taxes'       => $taxes,
			'total'       => wc_price( (float) $order->get_total(), $currency ),
		);
	}
}
