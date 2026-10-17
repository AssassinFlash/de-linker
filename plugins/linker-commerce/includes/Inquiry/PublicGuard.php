<?php
/**
 * Public form bot checks shared by both inquiry doors.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

/**
 * The request's own nonce is checked by its handler before these checks.
 */
final class PublicGuard {


	/**
	 * Initial minimum for the owner-required fill-time check (#246).
	 */
	public const MIN_SECONDS = 3;

	/**
	 * PR #290 round 1 retains contact's three accepted messages per connection
	 * per hour, shared by both doors to protect the host's 100-mail daily quota.
	 */
	public const LIMIT = 3;

	/**
	 * Length of the window, in seconds.
	 */
	public const WINDOW = HOUR_IN_SECONDS;


	/**
	 * Signed start time; no script is needed to submit the form.
	 */
	public function fields(): string {
		$stamp = (string) time();
		return '<input type="hidden" name="linker_started" value="' . esc_attr( $stamp ) . '" /><input type="hidden" name="linker_started_nonce" value="' . esc_attr( wp_create_nonce( 'linker_inquiry_started_' . $stamp ) ) . '" /><div hidden aria-hidden="true"><input type="text" name="website" tabindex="-1" autocomplete="off" aria-label="' . esc_attr__( 'Website', 'linker-commerce' ) . '" /></div>';
	}

	/**
	 * Reject filled traps, missing/forged clocks, and submissions too soon.
	 *
	 * @param array<string, mixed> $post Unslashed request.
	 */
	public function allows( array $post ): bool {
		$stamp = $post['linker_started'] ?? '';
		$nonce = $post['linker_started_nonce'] ?? '';
		$trap  = $post['website'] ?? '';
		return is_string( $stamp ) && ctype_digit( $stamp ) && is_string( $nonce ) && '' === $trap
		&& time() - (int) $stamp >= self::MIN_SECONDS
		&& false !== wp_verify_nonce( $nonce, 'linker_inquiry_started_' . $stamp ) && ! $this->is_limited();
	}
	/**
	 * Whether this connection has reached the shared submission limit.
	 */
	public function is_limited(): bool {
		return \count( $this->recent() ) >= self::LIMIT;
	}

	/**
	 * Records an accepted submission.
	 */
	public function record(): void {
		$recent   = $this->recent();
		$recent[] = time();
		set_transient( $this->key(), $recent, self::WINDOW );
	}

	/**
	 * The times of this connection's messages within the window.
	 *
	 * @return list<int>
	 */
	private function recent(): array {
		$stored = get_transient( $this->key() );
		$times  = array();
		foreach ( \is_array( $stored ) ? $stored : array() as $time ) {
			if ( \is_int( $time ) && $time > time() - self::WINDOW ) {
				$times[] = $time;
			}
		}
		return $times;
	}

	/**
	 * The transient of this connection. The address is the one the connection
	 * came from — never a forwarded header, which a sender could set freely.
	 */
	private function key(): string {
		$address = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( (string) $_SERVER['REMOTE_ADDR'] ) ) : '';
		return 'linker_contact_' . md5( $address );
	}
}
