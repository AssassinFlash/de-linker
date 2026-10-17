<?php
/**
 * Internal authentication health in the daily digest (#297).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Health;

use Linker\Commerce\Digest\Block;
use Linker\Commerce\Mail\InternalSmtp;

/**
 * One warning per digest while configuration is absent, invalid or mismatched.
 * No additional alert mail is sent for the fallback itself.
 */
final class InternalMail implements Block {

	/**
	 * Sets up the configuration health check.
	 *
	 * @param InternalSmtp $smtp The same configuration rule as the Outbox.
	 */
	public function __construct( private readonly InternalSmtp $smtp = new InternalSmtp() ) {}

	/**
	 * Stable digest block identifier.
	 */
	public function id(): string {
		return 'internal_mail';
	}

	/**
	 * Heading in the digest's language.
	 */
	public function title(): string {
		return __( 'Internal mail authentication', 'linker-commerce' );
	}

	/**
	 * A single explicit fallback diagnostic, without configuration values.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		if ( $this->smtp->authenticated() ) {
			return array();
		}
		return array(
			array(
				'label'     => __( 'Internal mail not authenticated.', 'linker-commerce' ),
				'url'       => '',
				'link_text' => '',
				'detail'    => __( 'Internal notifications use PHP mail(). Check the SMTP configuration on the server.', 'linker-commerce' ),
			),
		);
	}

	/**
	 * Configured does not claim a successful remote delivery.
	 */
	public function empty_text(): string {
		return __( 'Authenticated SMTP is configured for internal notifications.', 'linker-commerce' );
	}
}
