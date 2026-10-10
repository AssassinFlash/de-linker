<?php
/**
 * The company fields of the registration form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WC_Customer;
use WP_Error;

/**
 * Adds company, business type, VAT ID, name and address to WooCommerce's own
 * registration form on the account page (docs/specs/11-commerce.md, journey
 * step 2). The account is usable at once; the VAT ID is checked with VIES, and
 * a failed check only flags the account. The team receives a notification.
 */
final class Fields {

	/**
	 * Action fired after a customer registered through the form; WooCommerce
	 * sends the team notification on it (NewCustomerEmail).
	 */
	public const REGISTERED_ACTION = 'linker_commerce_customer_registered';

	/**
	 * Values of the current registration, kept between validation and saving.
	 *
	 * @var array<string, string>|null
	 */
	private ?array $values = null;

	/**
	 * Sets up the fields.
	 *
	 * @param VatProfile $vat The VAT check.
	 */
	public function __construct( private readonly VatProfile $vat ) {}

	/**
	 * The fields, in WooCommerce's form field format. Labels and rules of the
	 * name and address fields are WooCommerce's own for the chosen country.
	 *
	 * @param string $country Country whose address rules apply.
	 * @return array<string, array<string, mixed>>
	 */
	public function fields( string $country ): array {
		$address = WC()->countries->get_address_fields( $country, 'billing_' );
		$fields  = array(
			'billing_company'    => array(
				'label'        => __( 'Company name', 'linker-commerce' ),
				'required'     => true,
				'autocomplete' => 'organization',
				'class'        => array( 'form-row-wide' ),
			),
			CustomerRole::META   => array(
				'type'     => 'select',
				'label'    => __( 'Business type', 'linker-commerce' ),
				'required' => true,
				'options'  => array( '' => __( 'Please choose', 'linker-commerce' ) ) + CustomerRole::options(),
				'class'    => array( 'form-row-wide' ),
			),
			VatProfile::VAT_META => array(
				'label'       => __( 'VAT ID', 'linker-commerce' ),
				'required'    => false,
				'description' => __( 'We check EU VAT IDs in the European Commission\'s VIES system. You can register without one.', 'linker-commerce' ),
				'class'       => array( 'form-row-wide' ),
			),
		);
		foreach ( array( 'billing_first_name', 'billing_last_name', 'billing_country', 'billing_address_1', 'billing_postcode', 'billing_city' ) as $key ) {
			if ( isset( $address[ $key ] ) && is_array( $address[ $key ] ) ) {
				$fields[ $key ] = $address[ $key ];
			}
		}
		return $fields;
	}

	/**
	 * Prints the fields; runs on woocommerce_register_form_start.
	 */
	public function render(): void {
		$country = $this->posted( 'billing_country' );
		$country = '' !== $country ? $country : WC()->countries->get_base_country();
		foreach ( $this->fields( $country ) as $key => $field ) {
			woocommerce_form_field( $key, $field, 'billing_country' === $key ? $country : $this->posted( $key ) );
		}
	}

	/**
	 * Checks the fields; runs on woocommerce_process_registration_errors, which
	 * WooCommerce applies only to its registration form, after checking its nonce.
	 *
	 * @param WP_Error $errors Errors so far.
	 */
	public function validate( WP_Error $errors ): WP_Error {
		$country = $this->posted( 'billing_country' );
		$values  = array();
		foreach ( $this->fields( $country ) as $key => $field ) {
			$value          = $this->posted( $key );
			$values[ $key ] = $value;
			if ( ! empty( $field['required'] ) && '' === $value ) {
				/* translators: %s: field name. */
				$errors->add( $key, sprintf( __( '%s is a required field.', 'linker-commerce' ), '<strong>' . esc_html( (string) ( $field['label'] ?? $key ) ) . '</strong>' ) );
			}
		}
		if ( '' !== $values[ CustomerRole::META ] && '' === CustomerRole::label( $values[ CustomerRole::META ] ) ) {
			$errors->add( CustomerRole::META, __( 'Please choose a business type.', 'linker-commerce' ) );
		}
		if ( '' !== $country && ! array_key_exists( $country, WC()->countries->get_allowed_countries() ) ) {
			$errors->add( 'billing_country', __( 'Please choose a country from the list.', 'linker-commerce' ) );
		}
		$postcode = $values['billing_postcode'] ?? '';
		if ( '' !== $postcode && '' !== $country && ! \WC_Validation::is_postcode( $postcode, $country ) ) {
			$errors->add( 'billing_postcode', __( 'Please enter a valid postcode.', 'linker-commerce' ) );
		}
		$this->values = $errors->has_errors() ? null : $values;
		return $errors;
	}

	/**
	 * Saves the fields on the new customer, checks the VAT ID and announces the
	 * registration; runs on woocommerce_created_customer, before WooCommerce's
	 * welcome email (which greets the customer by the first name saved here).
	 *
	 * @param int $customer_id New customer.
	 */
	public function save( int $customer_id ): void {
		if ( null === $this->values ) {
			return;
		}
		$values       = $this->values;
		$this->values = null;

		$customer = new WC_Customer( $customer_id );
		$values  += array_fill_keys( array( 'billing_first_name', 'billing_last_name', 'billing_country', 'billing_address_1', 'billing_postcode', 'billing_city' ), '' );
		$customer->set_first_name( $values['billing_first_name'] );
		$customer->set_last_name( $values['billing_last_name'] );
		// WooCommerce greets with the display name, otherwise the username made from the email address.
		$customer->set_display_name( trim( $values['billing_first_name'] . ' ' . $values['billing_last_name'] ) );
		$customer->set_billing_first_name( $values['billing_first_name'] );
		$customer->set_billing_last_name( $values['billing_last_name'] );
		$customer->set_billing_company( $values['billing_company'] );
		$customer->set_billing_country( $values['billing_country'] );
		$customer->set_billing_address_1( $values['billing_address_1'] );
		$customer->set_billing_postcode( wc_format_postcode( $values['billing_postcode'], $values['billing_country'] ) );
		$customer->set_billing_city( $values['billing_city'] );
		$customer->set_billing_email( $customer->get_email() );
		$customer->update_meta_data( VatProfile::VAT_META, VatNumber::normalize( $values[ VatProfile::VAT_META ] ) );
		$customer->update_meta_data( CustomerRole::META, $values[ CustomerRole::META ] );
		$customer->save();

		$this->vat->update( $customer_id, $values[ VatProfile::VAT_META ], false );

		/**
		 * Fires after a customer registered through the account page's form;
		 * WooCommerce sends the team notification on it (NewCustomerEmail).
		 *
		 * @since 0.1.0
		 *
		 * @param int $customer_id New customer.
		 */
		do_action( 'linker_commerce_customer_registered', $customer_id );
	}

	/**
	 * A posted value, sanitized as text.
	 *
	 * @param string $key Field name.
	 */
	private function posted( string $key ): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- WooCommerce verified the registration nonce before validate() and save() run; render() only refills the form.
		return isset( $_POST[ $key ] ) && is_string( $_POST[ $key ] ) ? trim( sanitize_text_field( wp_unslash( $_POST[ $key ] ) ) ) : '';
	}
}
