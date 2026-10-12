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
 *
 * That way has to be the wp_mail filter, not only the outbox's own delivery.
 * The review instances still run the legacy plugin, and it fans a business
 * notification out before wp_mail() sends: its wp_mail filter (priority 100)
 * queues a separate message for each owner inbox whenever the business inbox
 * is a recipient. The VAT review mail is one of those. Rewriting only inside
 * the outbox leaves that filter the original recipients, so the copies still
 * go out. The rewrite therefore runs on wp_mail at PHP_INT_MAX, after every
 * such filter, and the copy queue is removed while the switch is on.
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
		return new Message( array( $address ), $message->subject, $message->body, self::without_copies( $message->headers ), $message->attachments );
	}

	/**
	 * The arguments of a wp_mail() call as they go to the mailer; runs on the
	 * wp_mail filter at PHP_INT_MAX, after every other filter has queued its
	 * copies off the original recipients. While test mode is on, the single
	 * address and no visible or blind copy; otherwise the arguments themselves.
	 *
	 * @param array<string, mixed> $args The call's to, subject, message, headers and attachments.
	 * @return array<string, mixed>
	 */
	public function rewrite( array $args ): array {
		$address = $this->address();
		if ( '' === $address ) {
			return $args;
		}
		$args['to']      = array( $address );
		$args['headers'] = self::without_copies( self::lines( $args['headers'] ?? array() ) );
		return $args;
	}

	/**
	 * Removes the legacy plugin's owner-copy queue while test mode is on.
	 *
	 * The queue is a wp_mail filter (mail-identity.php, priority 100): it reads
	 * the recipients and schedules one message per owner inbox before this
	 * class's rewrite runs. Removing it is what stops those copies; the
	 * rewrite still covers a copy that was already queued. The queue is not
	 * registered on its own: it is the last statement of an anonymous filter
	 * at the same priority, so the closure is unhooked by the function it calls.
	 */
	public function silence_copy_queues(): void {
		if ( ! $this->enabled() ) {
			return;
		}
		self::unhook( 'wp_mail', 'tv_b2b_queue_business_mail_copies', 100 );
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

	/**
	 * Header lines of a wp_mail() headers argument.
	 *
	 * @param mixed $headers A header string or a list of header lines.
	 * @return list<string>
	 */
	private static function lines( mixed $headers ): array {
		if ( is_string( $headers ) ) {
			$headers = preg_split( '/\r\n|\r|\n/', $headers );
		}
		if ( ! is_array( $headers ) ) {
			return array();
		}
		$lines = array();
		foreach ( $headers as $header ) {
			if ( is_string( $header ) && '' !== trim( $header ) ) {
				$lines[] = trim( $header );
			}
		}
		return $lines;
	}

	/**
	 * Removes every callback at a priority whose body calls a named function.
	 *
	 * WordPress's own remove_filter() needs the exact callable. The legacy
	 * copy queue is a closure, so the registered callback list is the only
	 * place that names it.
	 *
	 * @param string $hook     Filter name.
	 * @param string $called   Function the callback calls.
	 * @param int    $priority Priority.
	 */
	private static function unhook( string $hook, string $called, int $priority ): void {
		global $wp_filter;
		if ( ! isset( $wp_filter[ $hook ] ) ) {
			return;
		}
		$registered = $wp_filter[ $hook ];
		$callbacks  = self::callbacks_of( $registered );
		if ( ! isset( $callbacks[ $priority ] ) || ! is_array( $callbacks[ $priority ] ) ) {
			return;
		}
		foreach ( $callbacks[ $priority ] as $id => $entry ) {
			$callback = is_array( $entry ) ? ( $entry['function'] ?? null ) : null;
			$named    = is_string( $callback ) && $callback === $called;
			if ( $named || ( $callback instanceof \Closure && self::calls( $callback, $called ) ) ) {
				unset( $callbacks[ $priority ][ $id ] );
			}
		}
		self::write_callbacks( $registered, $callbacks );
	}

	/**
	 * The callback list of a registered filter, however WordPress stores it.
	 *
	 * @param mixed $registered The $wp_filter entry.
	 * @return array<int, mixed>
	 */
	private static function callbacks_of( mixed $registered ): array {
		if ( is_array( $registered ) ) {
			return $registered;
		}
		if ( ! is_object( $registered ) || ! property_exists( $registered, 'callbacks' ) ) {
			return array();
		}
		$callbacks = $registered->callbacks;
		return is_array( $callbacks ) ? $callbacks : array();
	}

	/**
	 * Writes a callback list back onto the registered filter.
	 *
	 * @param mixed             $registered The $wp_filter entry.
	 * @param array<int, mixed> $callbacks  Callbacks by priority.
	 */
	private static function write_callbacks( mixed $registered, array $callbacks ): void {
		if ( is_object( $registered ) && property_exists( $registered, 'callbacks' ) ) {
			$registered->callbacks = $callbacks; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- $registered is the $wp_filter entry; removing a closure needs its callback list, which remove_filter() cannot name.
		}
	}

	/**
	 * Whether a closure's body calls a named function.
	 *
	 * @param \Closure $callback Closure.
	 * @param string   $called   Function name.
	 */
	private static function calls( \Closure $callback, string $called ): bool {
		$reflection = new \ReflectionFunction( $callback );
		$file       = $reflection->getFileName();
		if ( ! is_string( $file ) || ! is_readable( $file ) ) {
			return false;
		}
		$lines = file( $file );
		if ( false === $lines ) {
			return false;
		}
		$body = implode( '', array_slice( $lines, $reflection->getStartLine() - 1, $reflection->getEndLine() - $reflection->getStartLine() + 1 ) );
		return str_contains( $body, $called . '(' );
	}
}
