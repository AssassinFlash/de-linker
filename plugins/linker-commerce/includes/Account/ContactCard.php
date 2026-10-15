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
	 * The frame is the workspace's own panel (ticket #184, the owner-accepted
	 * prototype's contact card): a heading with its rule, then the line — the
	 * team's mailbox with the prototype's own letter mark, and the stored name
	 * and phone above or below it when an operator set them.
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
			'<section class="linker-account-panel linker-account-contact" aria-labelledby="linker-contact-card-title"><header class="linker-account-panel-heading"><h2 id="linker-contact-card-title">%1$s</h2></header><div class="linker-account-panel-body"><p class="linker-account-contact-line">%2$s<span>%3$s</span></p></div></section>',
			esc_html__( 'Your contact person', 'linker-commerce' ),
			'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>',
			implode( '<br>', $lines ) // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- each line escaped above.
		);
	}
}
