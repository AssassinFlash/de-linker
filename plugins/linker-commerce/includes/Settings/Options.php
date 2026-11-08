<?php
/**
 * The plugin's own settings, read with their defaults.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Settings;

use Linker\Commerce\Mail\Identity;

/**
 * Reads the values staff enter on WooCommerce → Settings → Inquiries
 * (SettingsTab). Every reader of these settings goes through this class, so a
 * default lives in one place.
 */
final class Options {

	/**
	 * Option names, also the field ids of the settings tab.
	 */
	public const TEAM_TO          = 'linker_commerce_team_to';
	public const NOTIFY_TO        = 'linker_commerce_notify_to';
	public const NOTIFY_FROM      = 'linker_commerce_notify_from';
	public const NOTIFY_BCC       = 'linker_commerce_team_bcc';
	public const CONTACT_NAME     = 'linker_commerce_contact_name';
	public const CONTACT_EMAIL    = 'linker_commerce_contact_email';
	public const CONTACT_PHONE    = 'linker_commerce_contact_phone';
	public const SELLER_NAME      = 'linker_commerce_seller_name';
	public const SELLER_VAT_ID    = 'linker_commerce_seller_vat_id';
	public const QUOTATION_PREFIX = 'linker_commerce_quotation_prefix';

	/**
	 * The team mailbox customers see and write to: the mailto links of the
	 * pages, Genie's hand-off sentence and the contact person's fallback
	 * (owner rulings 2026-10-05 and 2026-10-17, AGENTS.md §2). Internal
	 * notifications do not go here; see DEFAULT_NOTIFY_TO.
	 */
	public const DEFAULT_TEAM_TO = 'sales@de-linker.com';

	/**
	 * Where every internal notification goes — new customer, VAT check, new
	 * inquiry, contact form message, daily digest, health alert — until the
	 * owner names another mailbox (owner ruling 2026-10-17, AGENTS.md §2:
	 * not sales@de-linker.com, which is the owner's own mailbox).
	 */
	public const DEFAULT_NOTIFY_TO = 'sales@sunriverinverter.com';

	/**
	 * Internal mail uses the Hostinger-authorized sender (ticket #286).
	 * Customer mail keeps WooCommerce's own sender settings.
	 */
	public const DEFAULT_NOTIFY_FROM = 'sales@sunriverinverter.com';

	/**
	 * Quotation numbers read DLK-QT-YYYY-NNNN when the settings leave the
	 * prefix empty (owner ruling 2026-11-08: a quotation, not an invoice).
	 */
	public const DEFAULT_QUOTATION_PREFIX = 'DLK-QT';

	/**
	 * The seller named on the Quotation when the settings leave it empty
	 * (AGENTS.md §1: the site belongs to Linker Technology GmbH).
	 */
	public const DEFAULT_SELLER_NAME = 'Linker Technology GmbH';

	/**
	 * Address of the team mailbox customers see (DEFAULT_TEAM_TO). Nothing
	 * internal is sent here.
	 */
	public function team_mailbox(): string {
		$to = sanitize_email( $this->text( self::TEAM_TO ) );
		return '' === $to ? self::DEFAULT_TEAM_TO : $to;
	}

	/**
	 * The recipient of every internal notification (DEFAULT_NOTIFY_TO). Send
	 * an internal notification through Mail\TeamEmail, which reads this and
	 * notify_bcc(); a plain wp_mail() reads both directly.
	 */
	public function notify_to(): string {
		$to = sanitize_email( $this->text( self::NOTIFY_TO ) );
		return '' === $to ? self::DEFAULT_NOTIFY_TO : $to;
	}

	/**
	 * One identity for Woo internal notifications and plain wp_mail alerts.
	 */
	public function notify_sender(): Identity {
		$from = sanitize_email( $this->text( self::NOTIFY_FROM ) );
		return new Identity( 'Linker', is_email( $from ) ? $from : self::DEFAULT_NOTIFY_FROM );
	}

	/**
	 * The mailboxes that receive a blind copy of each internal notification.
	 *
	 * @return list<string> Valid addresses, without duplicates and without notify_to() itself.
	 */
	public function notify_bcc(): array {
		$addresses = preg_split( '/[\s,;]+/', $this->text( self::NOTIFY_BCC ) );
		$valid     = array();
		foreach ( false === $addresses ? array() : $addresses as $address ) {
			$address = sanitize_email( $address );
			if ( '' !== $address && is_email( $address ) && $address !== $this->notify_to() && ! in_array( $address, $valid, true ) ) {
				$valid[] = $address;
			}
		}
		return $valid;
	}

	/**
	 * The customer's contact person; the email falls back to the team mailbox
	 * customers see.
	 *
	 * @return array{name: string, email: string, phone: string}
	 */
	public function contact(): array {
		$email = sanitize_email( $this->text( self::CONTACT_EMAIL ) );
		return array(
			'name'  => $this->text( self::CONTACT_NAME ),
			'email' => '' === $email ? $this->team_mailbox() : $email,
			'phone' => $this->text( self::CONTACT_PHONE ),
		);
	}




	/**
	 * The seller as printed on the Quotation: name, VAT ID and the store
	 * address of WooCommerce → Settings → General. A quotation names no bank
	 * account (owner ruling 2026-11-08).
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
			'email'   => $this->team_mailbox(),
		);
	}

	/**
	 * The country name of WooCommerce's country:state value, or the raw value.
	 *
	 * @param string $value Country setting.
	 */
	private function country_name( string $value ): string {
		$parts     = explode( ':', $value );
		$countries = \WC()->countries->get_countries();
		return isset( $countries[ $parts[0] ] ) ? (string) $countries[ $parts[0] ] : $value;
	}

	/**
	 * Prefix of the Quotation numbers.
	 */
	public function quotation_prefix(): string {
		$prefix = $this->text( self::QUOTATION_PREFIX );
		return '' === $prefix ? self::DEFAULT_QUOTATION_PREFIX : $prefix;
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
}
