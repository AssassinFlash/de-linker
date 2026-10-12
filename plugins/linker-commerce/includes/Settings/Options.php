<?php
/**
 * The plugin's own settings, read with their defaults.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Settings;

/**
 * Reads the values staff enter on WooCommerce → Settings → Inquiries
 * (SettingsTab). Every reader of these settings goes through this class, so a
 * default lives in one place.
 */
final class Options {

	/**
	 * Option names, also the field ids of the settings tab.
	 */
	public const TEAM_TO         = 'linker_commerce_team_to';
	public const TEAM_BCC        = 'linker_commerce_team_bcc';
	public const CONTACT_NAME    = 'linker_commerce_contact_name';
	public const CONTACT_EMAIL   = 'linker_commerce_contact_email';
	public const CONTACT_PHONE   = 'linker_commerce_contact_phone';
	public const SELLER_NAME     = 'linker_commerce_seller_name';
	public const SELLER_VAT_ID   = 'linker_commerce_seller_vat_id';
	public const BANK_HOLDER     = 'linker_commerce_bank_holder';
	public const BANK_NAME       = 'linker_commerce_bank_name';
	public const BANK_IBAN       = 'linker_commerce_bank_iban';
	public const BANK_BIC        = 'linker_commerce_bank_bic';
	public const PROFORMA_PREFIX = 'linker_commerce_proforma_prefix';

	/**
	 * The team mailbox: every company notification goes there, and customers are
	 * pointed to it (owner ruling 2026-10-05, AGENTS.md §2).
	 */
	public const DEFAULT_TEAM_TO = 'sales@de-linker.com';

	/**
	 * Proforma numbers read DLK-PF-YYYY-NNNN when the settings leave the prefix
	 * empty. Live de-linker.com prints DLK-PF-YYYY-<order id>
	 * (tv_b2b_document_reference); this site counts within the year instead of
	 * using the order id, and keeps the same prefix (docs/specs/11-commerce.md).
	 */
	public const DEFAULT_PROFORMA_PREFIX = 'DLK-PF';

	/**
	 * The seller named on the Proforma when the settings leave it empty
	 * (AGENTS.md §1: the site belongs to Linker Technology GmbH).
	 */
	public const DEFAULT_SELLER_NAME = 'Linker Technology GmbH';

	/**
	 * Address of the team mailbox.
	 */
	public function team_to(): string {
		$to = sanitize_email( $this->text( self::TEAM_TO ) );
		return '' === $to ? self::DEFAULT_TEAM_TO : $to;
	}

	/**
	 * The mailboxes that receive a blind copy of each company notification.
	 *
	 * @return list<string> Valid addresses, without duplicates and without the team mailbox itself.
	 */
	public function team_bcc(): array {
		$addresses = preg_split( '/[\s,;]+/', $this->text( self::TEAM_BCC ) );
		$valid     = array();
		foreach ( false === $addresses ? array() : $addresses as $address ) {
			$address = sanitize_email( $address );
			if ( '' !== $address && is_email( $address ) && $address !== $this->team_to() && ! in_array( $address, $valid, true ) ) {
				$valid[] = $address;
			}
		}
		return $valid;
	}

	/**
	 * The customer's contact person; the email falls back to the team mailbox.
	 *
	 * @return array{name: string, email: string, phone: string}
	 */
	public function contact(): array {
		$email = sanitize_email( $this->text( self::CONTACT_EMAIL ) );
		return array(
			'name'  => $this->text( self::CONTACT_NAME ),
			'email' => '' === $email ? $this->team_to() : $email,
			'phone' => $this->text( self::CONTACT_PHONE ),
		);
	}

	/**
	 * The seller as printed on the Proforma: name, VAT ID and the store address of
	 * WooCommerce → Settings → General.
	 *
	 * @return array{name: string, vat_id: string, address: list<string>, email: string}
	 */
	public function seller(): array {
		$name    = $this->text( self::SELLER_NAME );
		$address = array_values(
			array_filter(
				array(
					$this->text( 'woocommerce_store_address' ),
					$this->text( 'woocommerce_store_address_2' ),
					trim( $this->text( 'woocommerce_store_postcode' ) . ' ' . $this->text( 'woocommerce_store_city' ) ),
					$this->country_name( $this->text( 'woocommerce_default_country' ) ),
				),
				static fn ( string $line ): bool => '' !== $line
			)
		);
		return array(
			'name'    => '' === $name ? self::DEFAULT_SELLER_NAME : $name,
			'vat_id'  => $this->text( self::SELLER_VAT_ID ),
			'address' => $address,
			'email'   => $this->team_to(),
		);
	}

	/**
	 * The bank account the Proforma asks customers to transfer to.
	 *
	 * @return array{holder: string, name: string, iban: string, bic: string}
	 */
	public function bank(): array {
		return array(
			'holder' => $this->text( self::BANK_HOLDER ),
			'name'   => $this->text( self::BANK_NAME ),
			'iban'   => $this->text( self::BANK_IBAN ),
			'bic'    => $this->text( self::BANK_BIC ),
		);
	}

	/**
	 * Prefix of the Proforma numbers.
	 */
	public function proforma_prefix(): string {
		$prefix = $this->text( self::PROFORMA_PREFIX );
		return '' === $prefix ? self::DEFAULT_PROFORMA_PREFIX : $prefix;
	}

	/**
	 * An option as trimmed text; anything that is not a string reads as empty.
	 *
	 * @param string $name Option name.
	 */
	private function text( string $name ): string {
		$value = get_option( $name, '' );
		return is_string( $value ) ? trim( $value ) : '';
	}

	/**
	 * The country of a WooCommerce "CC" or "CC:STATE" value, by name.
	 *
	 * @param string $value Option value of woocommerce_default_country.
	 */
	private function country_name( string $value ): string {
		$code = strtoupper( explode( ':', $value )[0] );
		return '' === $code ? '' : (string) ( WC()->countries->get_countries()[ $code ] ?? $code );
	}
}
