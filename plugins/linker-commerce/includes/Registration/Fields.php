<?php
/**
 * The company fields of the registration form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Inquiry\OrderLocale;
use WC_Customer;
use WP_Error;

/**
 * Adds the registration fields to WooCommerce's own registration form on the
 * account page. The owner's ruling of 2026-10-17 (AGENTS.md §2) and the field
 * research (#224) ask the two steps this form renders: the company with a
 * website or a VAT ID to verify it, and the person with the sign-in details.
 * The street, postcode and city are collected by the Proforma request page
 * (WooCommerce's native billing fields), not here.
 *
 * The account starts pending (Approval); the VAT ID is checked with VIES, and
 * a failed check only flags the account. The team receives a notification.
 */
final class Fields {

	/**
	 * Action fired after a customer registered through the form; WooCommerce
	 * sends the team notification on it (NewCustomerEmail).
	 */
	public const REGISTERED_ACTION = 'linker_commerce_customer_registered';

	/**
	 * Error code of the "website or VAT ID" pair. The two fields are each
	 * optional, one of them is required.
	 */
	public const ONE_OF = 'linker_website_or_vat';

	/**
	 * The fields of the first step; an error in one of them opens step 1 again.
	 *
	 * @var list<string>
	 */
	private const STEP_ONE = array( 'billing_company', CustomerRole::META, 'billing_country', Website::META, VatProfile::VAT_META, self::ONE_OF );

	/**
	 * The step the register card shows after a refused submission, 1 or 2.
	 *
	 * @var int
	 */
	private static int $active_step = 1;

	/**
	 * Values of the current registration, kept between validation and saving.
	 *
	 * @var array<string, string>|null
	 */
	private ?array $values = null;

	/**
	 * Sets up the fields.
	 *
	 * @param VatProfile $vat      The VAT check.
	 * @param Approval   $approval The account approval rule.
	 */
	public function __construct(
		private readonly VatProfile $vat,
		private readonly Approval $approval = new Approval()
	) {}

	/**
	 * The fields, in WooCommerce's form field format. Labels and rules of the
	 * name fields are WooCommerce's own for the chosen country.
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
				// RoleField renders the options, each native input nested inside
				// its own label (#351); WooCommerce's own radio markup keeps the
				// input a sibling of the label, which the pill design could only
				// dress by hiding the input off pointer events.
				'type'     => RoleField::TYPE,
				'label'    => __( 'Business type', 'linker-commerce' ),
				'required' => true,
				'options'  => CustomerRole::options(),
				'class'    => array( 'form-row-wide' ),
			),
			'billing_country'    => array(
				'type'         => 'linker_country',
				'label'        => $address['billing_country']['label'] ?? __( 'Country / Region', 'linker-commerce' ),
				'required'     => true,
				'autocomplete' => 'country',
				'options'      => CountryOptions::all(),
				'class'        => array( 'form-row-wide' ),
			),
			Website::META        => array(
				'type'              => 'text',
				'label'             => __( 'Company website', 'linker-commerce' ),
				'required'          => false,
				'placeholder'       => 'example.com',
				'autocomplete'      => 'url',
				// The accepted values include a bare host (example.com), which a
				// type=url field rejects in the browser before our own check runs.
				// Website::valid() is the validator; inputmode keeps the phone
				// keyboard on the URL layout.
				'custom_attributes' => array( 'inputmode' => 'url' ),
				'class'             => array( 'form-row-wide' ),
			),
			VatProfile::VAT_META => array(
				'label'       => __( 'VAT ID', 'linker-commerce' ),
				'required'    => false,
				'description' => __( 'We check EU VAT IDs in the European Commission\'s VIES system.', 'linker-commerce' ),
				'class'       => array( 'form-row-wide' ),
			),
		);
		foreach ( array( 'billing_first_name', 'billing_last_name' ) as $key ) {
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
		$country = '' !== $country ? $country : CountryOptions::default_country();
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
		if ( '' !== $country && ! array_key_exists( $country, CountryOptions::all() ) ) {
			$errors->add( 'billing_country', __( 'Please choose a country from the list.', 'linker-commerce' ) );
		}
		if ( '' === $values[ Website::META ] && '' === $values[ VatProfile::VAT_META ] ) {
			$errors->add( self::ONE_OF, __( 'Enter your company website or VAT ID, so we can verify your company.', 'linker-commerce' ) );
		} elseif ( '' !== $values[ Website::META ] && ! Website::valid( $values[ Website::META ] ) ) {
			$errors->add( Website::META, __( 'Enter a web address such as example.com.', 'linker-commerce' ) );
		}
		$this->values      = $errors->has_errors() ? null : $values;
		self::$active_step = $this->step( $errors );
		return $errors;
	}

	/**
	 * The step the card reopens on. A company error returns to step 1; any
	 * other refused post stays on the sign-in step.
	 *
	 * @param WP_Error $errors Errors of this submission.
	 */
	private function step( WP_Error $errors ): int {
		foreach ( self::STEP_ONE as $key ) {
			if ( $errors->get_error_message( $key ) ) {
				return 1;
			}
		}
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- WooCommerce verified the registration nonce before this runs; the value is a UI hint.
		return isset( $_POST['register'] ) ? 2 : 1;
	}

	/**
	 * The step the register card shows, 1 after a fresh page view.
	 */
	public static function active_step(): int {
		return self::$active_step;
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
		$values  += array_fill_keys( array( 'billing_first_name', 'billing_last_name', 'billing_country' ), '' );
		$customer->set_first_name( $values['billing_first_name'] );
		$customer->set_last_name( $values['billing_last_name'] );
		// WooCommerce greets with the display name, otherwise the username made from the email address.
		$customer->set_display_name( trim( $values['billing_first_name'] . ' ' . $values['billing_last_name'] ) );
		$customer->set_billing_first_name( $values['billing_first_name'] );
		$customer->set_billing_last_name( $values['billing_last_name'] );
		$customer->set_billing_company( $values['billing_company'] );
		$customer->set_billing_country( $values['billing_country'] );
		$customer->set_billing_email( $customer->get_email() );
		$customer->update_meta_data( Website::META, Website::normalize( $values[ Website::META ] ) );
		$customer->update_meta_data( VatProfile::VAT_META, VatNumber::normalize( $values[ VatProfile::VAT_META ] ) );
		$customer->update_meta_data( CustomerRole::META, $values[ CustomerRole::META ] );
		$customer->save();

		// Every account starts pending (ticket 73): the team approves it, and
		// until then it reads the site like a guest. Written through the rule
		// (Approval), the one writer of the approval state, so the state and its
		// audit row have one owner; the state a fresh customer already defaults
		// to is no change, so nothing is mailed from here.
		if ( $this->approval->is_subject( $customer_id ) ) {
			$this->approval->set( $customer_id, Approval::PENDING );
		}
		// The customer's own language, for every later email: WordPress's user
		// locale, recorded the same way the inquiry records its language.
		update_user_meta( $customer_id, 'locale', OrderLocale::current() );

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
