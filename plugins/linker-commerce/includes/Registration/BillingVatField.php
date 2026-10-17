<?php
/**
 * The VAT ID as a WooCommerce billing field.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WC_Customer;
use WC_Order;

/**
 * Makes the VAT ID a billing field of WooCommerce: the Proforma request page and
 * the company page show it filled in, WooCommerce stores it on the customer and
 * on the inquiry, and staff see it with its VIES verdict. A changed number is
 * checked again (VatProfile).
 */
final class BillingVatField {

	/**
	 * Sets up the field.
	 *
	 * @param VatProfile $vat The VAT check.
	 */
	public function __construct( private readonly VatProfile $vat ) {}

	/**
	 * Adds the field after the company; runs on woocommerce_billing_fields.
	 *
	 * @param array<string, array<string, mixed>> $fields Billing fields.
	 * @return array<string, array<string, mixed>>
	 */
	public function billing_fields( array $fields ): array {
		$company_priority               = (int) ( $fields['billing_company']['priority'] ?? 30 );
		$fields[ VatProfile::VAT_META ] = array(
			'label'    => __( 'VAT ID', 'linker-commerce' ),
			'required' => false,
			'class'    => array( 'form-row-wide' ),
			'priority' => $company_priority + 1,
		);
		return $fields;
	}

	/**
	 * Shows and edits the field on the inquiry in the admin; runs on woocommerce_admin_billing_fields.
	 *
	 * @param array<string, array<string, mixed>> $fields Admin billing fields (keys without "billing_").
	 * @return array<string, array<string, mixed>>
	 */
	public function admin_billing_fields( array $fields ): array {
		$fields['vat_id'] = array(
			'label' => __( 'VAT ID', 'linker-commerce' ),
			'show'  => true,
		);
		return $fields;
	}

	/**
	 * The VIES verdict under the billing address of an inquiry in the admin;
	 * runs on woocommerce_admin_order_data_after_billing_address.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public function admin_order_verdict( WC_Order $order ): void {
		$status = $order->get_meta( VatProfile::ORDER_STATUS );
		printf(
			'<p class="linker-vat-status"><strong>%1$s</strong> %2$s</p>',
			esc_html__( 'VAT check:', 'linker-commerce' ),
			esc_html( VatProfile::label( is_string( $status ) ? $status : '' ) )
		);
	}

	/**
	 * VAT ID, verdict and business type in WooCommerce's customer section of the
	 * user profile; runs on woocommerce_customer_meta_fields.
	 *
	 * @param array<string, array<string, mixed>> $sections Profile sections.
	 * @return array<string, array<string, mixed>>
	 */
	public function profile_fields( array $sections ): array {
		if ( isset( $sections['billing']['fields'] ) && is_array( $sections['billing']['fields'] ) ) {
			$sections['billing']['fields'][ VatProfile::VAT_META ] = array(
				'label'       => __( 'VAT ID', 'linker-commerce' ),
				'description' => '',
			);
		}
		$sections['linker'] = array(
			'title'  => __( 'Customer check', 'linker-commerce' ),
			'fields' => array(
				CustomerRole::META      => array(
					'label'   => __( 'Business type', 'linker-commerce' ),
					'type'    => 'select',
					'options' => array( '' => '' ) + CustomerRole::options(),
				),
				VatProfile::STATUS_META => array(
					'label'       => __( 'VAT check', 'linker-commerce' ),
					'type'        => 'select',
					'options'     => array(
						''                     => '',
						VatProfile::VALID      => VatProfile::label( VatProfile::VALID ),
						VatProfile::INVALID    => VatProfile::label( VatProfile::INVALID ),
						VatProfile::UNVERIFIED => VatProfile::label( VatProfile::UNVERIFIED ),
						VatProfile::NONE       => VatProfile::label( VatProfile::NONE ),
					),
					'description' => __( 'Set by the VIES check; change it after a manual check.', 'linker-commerce' ),
				),
			),
		);
		return $sections;
	}

	/**
	 * Checks the VAT ID again after the customer saved the company address;
	 * runs on woocommerce_customer_save_address.
	 *
	 * @param int    $user_id      Customer.
	 * @param string $address_type "billing" or "shipping".
	 */
	public function after_address_saved( int $user_id, string $address_type ): void {
		if ( 'billing' === $address_type ) {
			$this->vat->update( $user_id, (string) get_user_meta( $user_id, VatProfile::VAT_META, true ), true );
		}
	}

	/**
	 * Checks the inquiry-specific VAT without changing the saved account profile;
	 * runs on woocommerce_checkout_create_order. Account edits are checked by
	 * after_address_saved(), not by sending an inquiry (#246).
	 *
	 * @param WC_Order $order Inquiry being created.
	 */
	public function on_inquiry( WC_Order $order ): void {
		$this->vat->snapshot( $order );
	}

	/**
	 * Normalizes the VAT ID WooCommerce saves on the customer from the
	 * Proforma request page or the company page.
	 *
	 * @param WC_Customer $customer Customer being saved.
	 */
	public function normalize( WC_Customer $customer ): void {
		$value = $customer->get_meta( VatProfile::VAT_META );
		if ( is_string( $value ) && VatNumber::normalize( $value ) !== $value ) {
			$customer->update_meta_data( VatProfile::VAT_META, VatNumber::normalize( $value ) );
		}
	}
}
