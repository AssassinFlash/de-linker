<?php
/**
 * The settings page: WooCommerce → Settings → Inquiries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Settings;

use Linker\Commerce\Mail\JobStore;
use WC_Admin_Settings;

/**
 * One tab in WooCommerce's own settings screen, built with its settings API:
 * team mailbox and blind copies, the customers' contact person, and what the
 * Proforma prints (number prefix, seller, bank account).
 */
final class SettingsTab {

	/**
	 * Tab id, in the URL of the tab (admin.php?page=wc-settings&tab=…).
	 */
	public const TAB = 'linker_inquiries';

	/**
	 * Sets up the tab.
	 *
	 * @param JobStore $jobs The mail queue, for the undelivered count.
	 */
	public function __construct( private readonly JobStore $jobs ) {}

	/**
	 * Adds the tab to the list of WooCommerce settings tabs.
	 *
	 * @param array<string, string> $tabs Tab id → label.
	 * @return array<string, string>
	 */
	public function add_tab( array $tabs ): array {
		$tabs[ self::TAB ] = __( 'Inquiries', 'linker-commerce' );
		return $tabs;
	}

	/**
	 * Prints the tab's fields, and above them the number of emails no retry
	 * could deliver (review 2026-10-10, S3; the retries themselves are in
	 * WooCommerce → Status → Logs, source linker-mail).
	 */
	public function output(): void {
		$failed = $this->jobs->failed_count();
		if ( $failed > 0 ) {
			$notice = sprintf(
				/* translators: %d: number of emails. */
				_n( '%d email could not be delivered. The attempts are in WooCommerce → Status → Logs (linker-mail); the message stays queued under its post id.', '%d emails could not be delivered. The attempts are in WooCommerce → Status → Logs (linker-mail); each message stays queued under its post id.', $failed, 'linker-commerce' ),
				$failed
			);
			WC_Admin_Settings::show_message( $notice ); // @phpstan-ignore-line staticMethod.notFound -- WooCommerce's own method; the test doubles carry it for the unit tests. phpcs:ignore
		}
		WC_Admin_Settings::output_fields( $this->fields() );
	}

	/**
	 * Saves the tab's fields; the sanitize filters below run for each of them.
	 */
	public function save(): void {
		WC_Admin_Settings::save_fields( $this->fields() );
	}

	/**
	 * The fields of the tab, in WooCommerce's settings API format.
	 *
	 * @return list<array<string, mixed>>
	 */
	public function fields(): array {
		return array(
			array(
				'title' => __( 'Team mailbox', 'linker-commerce' ),
				'type'  => 'title',
				'desc'  => __( 'The address customers see: on the Proforma, on the website and in Genie\'s answers. Internal notifications do not go here.', 'linker-commerce' ),
				'id'    => 'linker_commerce_team',
			),
			array(
				'title'       => __( 'Team mailbox', 'linker-commerce' ),
				'id'          => Options::TEAM_TO,
				'type'        => 'email',
				'default'     => Options::DEFAULT_TEAM_TO,
				'placeholder' => Options::DEFAULT_TEAM_TO,
				'autoload'    => false,
			),
			array(
				'type' => 'sectionend',
				'id'   => 'linker_commerce_team',
			),
			array(
				'title' => __( 'Internal notifications', 'linker-commerce' ),
				'type'  => 'title',
				'desc'  => __( 'Every internal notification (new customer, VAT check, new inquiry, contact form message, daily digest, health check) is one message to this address, with a blind copy to each address below.', 'linker-commerce' ),
				'id'    => 'linker_commerce_notify',
			),
			array(
				'title'       => __( 'Recipient', 'linker-commerce' ),
				'id'          => Options::NOTIFY_TO,
				'type'        => 'email',
				'default'     => Options::DEFAULT_NOTIFY_TO,
				'placeholder' => Options::DEFAULT_NOTIFY_TO,
				'autoload'    => false,
			),
			array(
				'title'       => __( 'Sender email', 'linker-commerce' ),
				'desc'        => __( 'Internal notifications use this address with the sender name Linker. Customer emails use the WooCommerce sender settings.', 'linker-commerce' ),
				'id'          => Options::NOTIFY_FROM,
				'type'        => 'email',
				'default'     => Options::DEFAULT_NOTIFY_FROM,
				'placeholder' => Options::DEFAULT_NOTIFY_FROM,
				'autoload'    => false,
			),
			array(
				'title'    => __( 'Blind copies', 'linker-commerce' ),
				'desc'     => __( 'One address per line.', 'linker-commerce' ),
				'id'       => Options::NOTIFY_BCC,
				'type'     => 'textarea',
				'css'      => 'min-width: 300px; min-height: 80px;',
				'autoload' => false,
			),
			array(
				'type' => 'sectionend',
				'id'   => 'linker_commerce_notify',
			),
			array(
				'title' => __( 'Contact person', 'linker-commerce' ),
				'type'  => 'title',
				'desc'  => __( 'Shown to customers at the top of their account. Without an email address the team mailbox is shown.', 'linker-commerce' ),
				'id'    => 'linker_commerce_contact',
			),
			array(
				'title'    => __( 'Name', 'linker-commerce' ),
				'id'       => Options::CONTACT_NAME,
				'type'     => 'text',
				'autoload' => false,
			),
			array(
				'title'    => __( 'Email', 'linker-commerce' ),
				'id'       => Options::CONTACT_EMAIL,
				'type'     => 'email',
				'autoload' => false,
			),
			array(
				'title'    => __( 'Phone', 'linker-commerce' ),
				'id'       => Options::CONTACT_PHONE,
				'type'     => 'text',
				'autoload' => false,
			),
			array(
				'type' => 'sectionend',
				'id'   => 'linker_commerce_contact',
			),
			array(
				'title' => __( 'Proforma invoice', 'linker-commerce' ),
				'type'  => 'title',
				'desc'  => __( 'Printed on every Proforma invoice. The seller address is the store address under General.', 'linker-commerce' ),
				'id'    => 'linker_commerce_proforma',
			),
			array(
				'title'       => __( 'Number prefix', 'linker-commerce' ),
				'desc'        => __( 'Numbers read PREFIX-YEAR-NNNN and count from 1 each calendar year. Empty uses DLK-PF, the prefix on de-linker.com.', 'linker-commerce' ),
				'id'          => Options::PROFORMA_PREFIX,
				'type'        => 'text',
				'default'     => Options::DEFAULT_PROFORMA_PREFIX,
				'placeholder' => Options::DEFAULT_PROFORMA_PREFIX,
				'autoload'    => false,
			),
			array(
				'title'       => __( 'Seller', 'linker-commerce' ),
				'id'          => Options::SELLER_NAME,
				'type'        => 'text',
				'placeholder' => Options::DEFAULT_SELLER_NAME,
				'autoload'    => false,
			),
			array(
				'title'    => __( 'Seller VAT ID', 'linker-commerce' ),
				'id'       => Options::SELLER_VAT_ID,
				'type'     => 'text',
				'autoload' => false,
			),
			array(
				'title'    => __( 'Account holder', 'linker-commerce' ),
				'id'       => Options::BANK_HOLDER,
				'type'     => 'text',
				'autoload' => false,
			),
			array(
				'title'    => __( 'Bank', 'linker-commerce' ),
				'id'       => Options::BANK_NAME,
				'type'     => 'text',
				'autoload' => false,
			),
			array(
				'title'    => __( 'IBAN', 'linker-commerce' ),
				'id'       => Options::BANK_IBAN,
				'type'     => 'text',
				'autoload' => false,
			),
			array(
				'title'    => __( 'BIC', 'linker-commerce' ),
				'id'       => Options::BANK_BIC,
				'type'     => 'text',
				'autoload' => false,
			),
			array(
				'type' => 'sectionend',
				'id'   => 'linker_commerce_proforma',
			),
		);
	}

	/**
	 * Keeps only valid addresses in the blind copy list, one per line.
	 *
	 * @param mixed $value Value WooCommerce sanitized as text.
	 */
	public function sanitize_bcc( $value ): string {
		$lines   = preg_split( '/[\s,;]+/', is_string( $value ) ? $value : '' );
		$valid   = array();
		$invalid = array();
		foreach ( false === $lines ? array() : $lines as $line ) {
			if ( '' === $line ) {
				continue;
			}
			if ( is_email( $line ) ) {
				$valid[] = sanitize_email( $line );
			} else {
				$invalid[] = $line;
			}
		}
		if ( array() !== $invalid ) {
			/* translators: %s: the addresses that were left out, comma-separated. */
			WC_Admin_Settings::add_error( sprintf( __( 'Not an email address, left out: %s', 'linker-commerce' ), implode( ', ', $invalid ) ) );
		}
		return implode( "\n", array_unique( $valid ) );
	}

	/**
	 * Accepts an IBAN only when its ISO 13616 check digits are right, so a typo
	 * never reaches a Proforma; otherwise the saved value stays.
	 *
	 * @param mixed $value Value WooCommerce sanitized as text.
	 */
	public function sanitize_iban( $value ): string {
		$iban = strtoupper( (string) preg_replace( '/\s+/', '', is_string( $value ) ? $value : '' ) );
		if ( '' === $iban || self::is_valid_iban( $iban ) ) {
			return $iban;
		}
		WC_Admin_Settings::add_error( __( 'The IBAN is not valid (check digits do not match); the previous IBAN is kept.', 'linker-commerce' ) );
		return $this->saved( Options::BANK_IBAN );
	}

	/**
	 * Accepts a BIC only in the ISO 9362 form (4 letters bank, 2 letters country,
	 * 2 characters location, optional 3 characters branch); otherwise the saved value stays.
	 *
	 * @param mixed $value Value WooCommerce sanitized as text.
	 */
	public function sanitize_bic( $value ): string {
		$bic = strtoupper( (string) preg_replace( '/\s+/', '', is_string( $value ) ? $value : '' ) );
		if ( '' === $bic || 1 === preg_match( '/^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$/', $bic ) ) {
			return $bic;
		}
		WC_Admin_Settings::add_error( __( 'The BIC is not valid (8 or 11 characters); the previous BIC is kept.', 'linker-commerce' ) );
		return $this->saved( Options::BANK_BIC );
	}

	/**
	 * Keeps letters and digits of the number prefix, upper case.
	 *
	 * @param mixed $value Value WooCommerce sanitized as text.
	 */
	public function sanitize_prefix( $value ): string {
		return strtoupper( (string) preg_replace( '/[^A-Za-z0-9]/', '', is_string( $value ) ? $value : '' ) );
	}

	/**
	 * Whether an IBAN's check digits are right: move the first four characters to
	 * the end, letters to numbers (A = 10 … Z = 35), and the remainder of the
	 * division by 97 is 1 (ISO 13616-1 / ISO 7064 MOD 97-10).
	 *
	 * @param string $iban IBAN without spaces, upper case.
	 */
	public static function is_valid_iban( string $iban ): bool {
		if ( 1 !== preg_match( '/^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$/', $iban ) ) {
			return false;
		}
		$digits = '';
		foreach ( str_split( substr( $iban, 4 ) . substr( $iban, 0, 4 ) ) as $char ) {
			$digits .= ctype_alpha( $char ) ? (string) ( ord( $char ) - 55 ) : $char;
		}
		$remainder = 0;
		foreach ( str_split( $digits, 7 ) as $chunk ) {
			$remainder = (int) ( (string) $remainder . $chunk ) % 97;
		}
		return 1 === $remainder;
	}

	/**
	 * The value an option has now.
	 *
	 * @param string $name Option name.
	 */
	private function saved( string $name ): string {
		$value = get_option( $name, '' );
		return is_string( $value ) ? $value : '';
	}
}
