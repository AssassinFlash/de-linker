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
	public const NOTIFY_TO       = 'linker_commerce_notify_to';
	public const NOTIFY_FROM     = 'linker_commerce_notify_from';
	public const ENVELOPE_SENDER = 'linker_commerce_envelope_sender';
	public const NOTIFY_BCC      = 'linker_commerce_team_bcc';
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
	 * The team mailbox customers see and write to: the seller address of the
	 * Proforma, the mailto links of the pages, Genie's hand-off sentence and
	 * the contact person's fallback (owner rulings 2026-10-05 and 2026-10-17,
	 * AGENTS.md §2). Internal notifications do not go here; see
	 * DEFAULT_NOTIFY_TO.
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
	 * Ticket #288, SPF evidence 2026-10-18: sunriverinverter.com publishes
	 * v=spf1 include:_spf.mlsend.com include:_spf.mail.hostinger.com ~all.
	 * de-linker.com authorizes only Tencent; the envelope therefore defaults
	 * to the Hostinger-authorized address, independently of the visible From.
	 */
	public const DEFAULT_ENVELOPE_SENDER = self::DEFAULT_NOTIFY_FROM;

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
	 * The sender address of internal notifications, independent of their recipient.
	 */
	public function notify_from(): string {
		$from = sanitize_email( $this->text( self::NOTIFY_FROM ) );
		return is_email( $from ) ? $from : self::DEFAULT_NOTIFY_FROM;
	}

	/**
	 * One identity for Woo internal notifications and plain wp_mail alerts.
	 *
	 * @return array{name: string, email: string}
	 */
	public function notify_sender(): array {
		return array(
			'name'  => 'Linker',
			'email' => $this->notify_from(),
		);
	}

	/**
	 * PHPMailer's Sender for every delivery, including Outbox retries.
	 */
	public function envelope_sender(): string {
		$sender = sanitize_email( $this->text( self::ENVELOPE_SENDER ) );
		return is_email( $sender ) ? $sender : self::DEFAULT_ENVELOPE_SENDER;
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
			'email'   => $this->team_mailbox(),
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
