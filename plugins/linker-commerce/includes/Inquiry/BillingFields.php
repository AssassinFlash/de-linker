<?php
/**
 * Optional account billing fields, using Woo's field definitions and renderer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Registration\VatProfile;
use WC_Customer;

/** Native account address and VAT data; the guest form never reads these. */
final class BillingFields {

	/** Woo billing properties not already provided by the reply details. */
	private const FIELDS = array( 'address_1', 'address_2', 'city', 'postcode', 'country', 'state', 'phone', 'vat_id' );

	/**
	 * Prefills saved account data and accepts only these optional billing edits.
	 *
	 * @param array<string, mixed> $post Unslashed request or no edits.
	 * @return array<string, string>
	 */
	public static function values( array $post = array() ): array {
		if ( ! is_user_logged_in() ) {
			return array();
		}
		$customer         = new WC_Customer( get_current_user_id() );
		$stored           = $customer->get_billing();
		$stored['vat_id'] = $customer->get_meta( VatProfile::VAT_META );
		$values           = array();
		foreach ( self::FIELDS as $field ) {
			$key            = 'billing_' . $field;
			$saved          = $stored[ $field ] ?? '';
			$values[ $key ] = isset( $post[ $key ] ) && is_string( $post[ $key ] ) ? sanitize_text_field( $post[ $key ] ) : ( is_string( $saved ) ? $saved : '' );
		}
		return $values;
	}

	/** Woo renders the fields with its country choices, labels and autocomplete. */
	public static function render(): string {
		$values = self::values();
		$fields = WC()->checkout()->get_checkout_fields( 'billing' );
		$html   = '';
		foreach ( $values as $key => $value ) {
			if ( ! isset( $fields[ $key ] ) ) {
				continue;
			}
			$field                = $fields[ $key ];
			$field['required']    = false;
			$field['return']      = true;
			$field['input_class'] = array( 'linker-form-input' );
			$html                .= woocommerce_form_field( $key, $field, $value );
		}
		return $html;
	}
}
