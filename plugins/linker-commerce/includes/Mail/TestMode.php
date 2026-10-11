<?php
/**
 * Test mode: every outgoing email goes to one address.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * The sending discipline of test scenarios (AGENTS.md §5, owner 2026-10-11):
 * while the switch is on, every message goes to a single address, so a test run
 * proves the delivery path once and reaches no customer, team or Bcc mailbox.
 * The switch is an option that the command line sets and removes
 * (`wp linker-commerce test-mail on|off`); the queue keeps the recipients the
 * message was handed over with — the routing data every assertion reads — and
 * the rewrite happens on the way to wp_mail() alone.
 */
final class TestMode {

	/**
	 * Option holding the single address mail goes to while test mode is on; an
	 * absent or empty option means the switch is off.
	 */
	public const OPTION = 'linker_commerce_test_mail_to';

	/**
	 * The address test mode sends to unless the option names another one
	 * (owner ruling 2026-10-11).
	 */
	public const DEFAULT_TO = 'chester@de-linker.com';

	/**
	 * The address every message goes to; '' while test mode is off. The option
	 * is read through WordPress's own address rule: a stored value that is not
	 * an address is not a switch (review 2026-10-11) — whatever wrote the
	 * option, a corrupt value must not route mail anywhere.
	 */
	public function address(): string {
		$address = get_option( self::OPTION, '' );
		if ( ! is_string( $address ) ) {
			return '';
		}
		$address = (string) sanitize_email( $address );
		return is_email( $address ) ? $address : '';
	}

	/**
	 * Whether test mode is on.
	 */
	public function enabled(): bool {
		return '' !== $this->address();
	}

	/**
	 * Turns test mode on and reads the switch back: what the option holds is
	 * the truth, not what the write answered.
	 *
	 * @param string $address The single address, the default one when empty.
	 * @return bool Whether test mode is on afterwards.
	 */
	public function enable( string $address = self::DEFAULT_TO ): bool {
		$address = (string) sanitize_email( $address );
		if ( '' === $address ) {
			return false;
		}
		update_option( self::OPTION, $address, false );
		return $this->address() === $address;
	}

	/**
	 * Turns test mode off by removing the option, so nothing is left behind.
	 *
	 * @return bool Whether test mode is off afterwards.
	 */
	public function disable(): bool {
		return ! $this->enabled() || delete_option( self::OPTION );
	}

	/**
	 * The message as it goes to the mailer: while test mode is on, the single
	 * address and no visible or blind copy; otherwise the message itself. The
	 * caller keeps the message it queued, so a retry and the queue data still
	 * name the real recipients.
	 *
	 * @param Message $message Message.
	 */
	public function redirect( Message $message ): Message {
		$address = $this->address();
		if ( '' === $address ) {
			return $message;
		}
		$headers = array();
		foreach ( $message->headers as $header ) {
			$name = strtolower( ltrim( $header ) );
			if ( ! str_starts_with( $name, 'cc:' ) && ! str_starts_with( $name, 'bcc:' ) ) {
				$headers[] = $header;
			}
		}
		return new Message( array( $address ), $message->subject, $message->body, $headers, $message->attachments );
	}
}
