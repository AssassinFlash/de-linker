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
	 * PR #290 round 1 retains contact's three send attempts per connection
	 * per hour, shared by both doors to protect the host's 100-mail daily quota.
	 */
	public const LIMIT = 3;

	/**
	 * Length of the window, in seconds.
	 */
	public const WINDOW = HOUR_IN_SECONDS;

	/**
	 * Refusal reasons, observable to the registration counter (#225).
	 */
	public const REFUSAL_HONEYPOT = 'honeypot';
	public const REFUSAL_CLOCK    = 'clock';
	public const REFUSAL_TOO_FAST = 'too_fast';

	/**
	 * Signed start time; no script is needed to submit the form.
	 */
	public function fields(): string {
		$stamp = (string) time();
		return '<input type="hidden" name="linker_started" value="' . esc_attr( $stamp ) . '" /><input type="hidden" name="linker_started_nonce" value="' . esc_attr( wp_create_nonce( 'linker_inquiry_started_' . $stamp ) ) . '" /><div hidden aria-hidden="true"><input type="text" name="website" tabindex="-1" autocomplete="off" aria-label="' . esc_attr__( 'Website', 'linker-commerce' ) . '" /></div>';
	}

	/**
	 * Why the request is refused, '' when it passes. The reasons let a refusal
	 * be counted (#225) without a second copy of these checks.
	 *
	 * @param array<string, mixed> $post Unslashed request.
	 */
	public function refusal( array $post ): string {
		$trap = $post['website'] ?? '';
		if ( ! is_string( $trap ) || '' !== $trap ) {
			return self::REFUSAL_HONEYPOT;
		}
		$stamp = $post['linker_started'] ?? '';
		$nonce = $post['linker_started_nonce'] ?? '';
		if ( ! is_string( $stamp ) || ! ctype_digit( $stamp ) || ! is_string( $nonce ) || false === wp_verify_nonce( $nonce, 'linker_inquiry_started_' . $stamp ) ) {
			return self::REFUSAL_CLOCK;
		}
		return time() - (int) $stamp < self::MIN_SECONDS ? self::REFUSAL_TOO_FAST : '';
	}

	/**
	 * Reject filled traps, missing/forged clocks, and submissions too soon.
	 *
	 * @param array<string, mixed> $post Unslashed request.
	 */
	public function allows( array $post ): bool {
		return '' === $this->refusal( $post );
	}
	/**
	 * Atomically reserves one submission before either door writes an inquiry.
	 * Hourly fixed windows use #235's conditional UPDATE technique, kept inside
	 * commerce so the public forms have no dependency on linker-tools.
	 */
	public function take(): bool {
		return ( new RateLimit( 'public_connection', self::LIMIT, self::WINDOW ) )->take( $this->connection() );
	}

	/**
	 * The direct connection address. The address is the one the connection
	 * came from — never a forwarded header, which a sender could set freely.
	 */
	private function connection(): string {
		$address = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( (string) $_SERVER['REMOTE_ADDR'] ) ) : '';
		return $address;
	}
}
