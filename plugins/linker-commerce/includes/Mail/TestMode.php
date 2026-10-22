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
 * the rewrite happens on the way out of the outbox alone (Outbox calls
 * redirect() on the copy it sends, after the queue has stored the original).
 *
 * A wp_mail filter cannot do that rewrite. WordPress applies the wp_mail filter
 * before pre_wp_mail (wp-includes/pluggable.php), and the outbox records the
 * queue from the arguments pre_wp_mail is handed. Rewriting on wp_mail would
 * replace those arguments first, and the queue would name the tester address
 * instead of the routing data.
 *
 * The review instances still run the legacy plugin. Its wp_mail filter (priority
 * 100, mail-identity.php) schedules one later message per owner inbox whenever
 * the business inbox is a recipient, and that later message is itself a
 * wp_mail() call. The outbox takes every such call, so while the switch is on
 * the copy is rewritten to the tester address on the way out the same way the
 * original is. A rerun with the switch on (t109, 2026-10-12) queued the three
 * owner addresses and then wrote each copy to the tester address alone; it did
 * not show a copy leaving for a real recipient. That is why this class does not
 * also rewrite wp_mail() arguments or unhook the copy queue.
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
		return new Message( array( $address ), $message->subject, $message->body, self::without_copies( $message->headers ), $message->attachments, $message->critical );
	}

	/**
	 * Header lines without a visible or blind copy.
	 *
	 * @param string[] $headers Header lines.
	 * @return list<string>
	 */
	private static function without_copies( array $headers ): array {
		$kept = array();
		foreach ( $headers as $header ) {
			$name = strtolower( ltrim( $header ) );
			if ( ! str_starts_with( $name, 'cc:' ) && ! str_starts_with( $name, 'bcc:' ) ) {
				$kept[] = $header;
			}
		}
		return $kept;
	}
}
