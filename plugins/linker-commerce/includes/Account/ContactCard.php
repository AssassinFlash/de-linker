<?php
/**
 * The customer's contact person.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Settings\Options;

/**
 * Names the customer's contact person in the main column of every account page,
 * (docs/specs/11-commerce.md, journey step 6; every distributor in the
 * account-workspace mapping names one, §2.3).
 */
final class ContactCard {

	/**
	 * Sets up the card.
	 *
	 * @param Options $options The plugin settings.
	 */
	public function __construct( private readonly Options $options ) {}

	/**
	 * Prints the card; runs on linker_account_after_content, after the page's content.
	 */
	public function render(): void {
		$contact = $this->options->contact();
		$lines   = array();
		if ( '' !== $contact['name'] ) {
			$lines[] = '<strong>' . esc_html( $contact['name'] ) . '</strong>';
		}
		$lines[] = sprintf( '<a href="mailto:%1$s">%2$s</a>', esc_attr( $contact['email'] ), esc_html( $contact['email'] ) );
		if ( '' !== $contact['phone'] ) {
			$lines[] = sprintf( '<a href="tel:%1$s">%2$s</a>', esc_attr( (string) preg_replace( '/[^0-9+]/', '', $contact['phone'] ) ), esc_html( $contact['phone'] ) );
		}
		printf(
			'<section class="linker-contact-card" aria-labelledby="linker-contact-card-title"><h2 id="linker-contact-card-title">%1$s</h2><p>%2$s</p></section>',
			esc_html__( 'Your contact person', 'linker-commerce' ),
			implode( '<br>', $lines ) // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- each line escaped above.
		);
	}
}
