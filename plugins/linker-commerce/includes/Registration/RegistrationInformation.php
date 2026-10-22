<?php
/**
 * Reads saved registration information from the registration/Woo field definitions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WC_Customer;
use WP_User;

/** One field reader for the review cards; adding a registration field adds a row. */
final class RegistrationInformation {

	/**
	 * Uses the actual form's definitions, not a second list of registration fields.
	 *
	 * @param Fields $fields Registration form.
	 */
	public function __construct( private readonly Fields $fields ) {}

	/**
	 * Saved public registration/billing values, never arbitrary user meta.
	 *
	 * @param WP_User $user Customer.
	 * @return list<array{key: string, label: string, value: string, website: bool}>
	 */
	public function rows( WP_User $user ): array {
		$customer = new WC_Customer( $user->ID );
		return $this->customer_rows( $customer, $user );
	}

	/**
	 * Render prospective native fields without creating a user or checking VIES.
	 *
	 * @param array<string,string> $values Validated public business fields.
	 * @param WP_User              $user Prospective public identity, without a password.
	 * @return list<array{key:string,label:string,value:string,website:bool}>
	 */
	public function prospective( array $values, WP_User $user ): array {
		$customer = new WC_Customer();
		foreach ( array( 'billing_company', 'billing_first_name', 'billing_last_name', 'billing_country' ) as $property ) {
			$setter = 'set_' . $property;
			$customer->$setter( $values[ $property ] ?? '' );
		}
		$customer->update_meta_data( Website::META, Website::normalize( $values[ Website::META ] ?? '' ) );
		$customer->update_meta_data( VatProfile::VAT_META, VatNumber::normalize( $values[ VatProfile::VAT_META ] ?? '' ) );
		$customer->update_meta_data( CustomerRole::META, $values[ CustomerRole::META ] ?? '' );
		return $this->customer_rows( $customer, $user );
	}

	/**
	 * Both native saved and prospective messages use the same field definitions.
	 *
	 * @param WC_Customer $customer Native customer values; never saved here.
	 * @param WP_User     $user Public identity.
	 * @return list<array{key:string,label:string,value:string,website:bool}>
	 */
	private function customer_rows( WC_Customer $customer, WP_User $user ): array {
		$country = $customer->get_billing_country();
		$billing = $customer->get_billing();
		$fields  = $this->fields->fields( $country ) + WC()->countries->get_address_fields( $country, 'billing_' );
		$rows    = array();
		foreach ( $fields as $key => $field ) {
			if ( in_array( $field['type'] ?? '', array( 'password', 'hidden' ), true ) ) {
				continue;
			}
			$property = str_starts_with( $key, 'billing_' ) ? substr( $key, strlen( 'billing_' ) ) : '';
			$value    = '' !== $property && array_key_exists( $property, $billing ) ? $billing[ $property ] : $customer->get_meta( $key );
			if ( ! is_scalar( $value ) || '' === (string) $value ) {
				continue;
			}
			$value = (string) $value;
			if ( CustomerRole::META === $key ) {
				$value = CustomerRole::label( $value );
			} elseif ( 'billing_country' === $key ) {
				$value = WC()->countries->get_countries()[ $value ] ?? $value;
			} elseif ( isset( $field['options'] ) && is_array( $field['options'] ) && isset( $field['options'][ $value ] ) && is_scalar( $field['options'][ $value ] ) ) {
				$value = (string) $field['options'][ $value ];
			}
			$rows[] = array(
				'key'     => $key,
				'label'   => wp_strip_all_tags( (string) ( $field['label'] ?? $key ) ),
				'value'   => $value,
				'website' => ( 'url' === ( $field['type'] ?? '' ) || str_contains( $key, 'website' ) ) && in_array( wp_parse_url( $value, PHP_URL_SCHEME ), array( 'http', 'https' ), true ),
			);
		}
		$rows[] = array(
			'key'     => 'user_email',
			'label'   => __( 'Login email', 'linker-commerce' ),
			'value'   => $user->user_email,
			'website' => false,
		);
		$rows[] = array(
			'key'     => 'user_registered',
			'label'   => __( 'Registered', 'linker-commerce' ),
			'value'   => get_date_from_gmt( $user->user_registered, 'Y-m-d H:i' ),
			'website' => false,
		);
		return $rows;
	}
}
