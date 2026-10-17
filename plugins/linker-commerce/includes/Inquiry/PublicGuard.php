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
	 * Signed start time; no script is needed to submit the form.
	 */
	public function fields(): string {
		$stamp = (string) time();
		return '<input type="hidden" name="linker_started" value="' . esc_attr( $stamp ) . '" /><input type="hidden" name="linker_started_nonce" value="' . esc_attr( wp_create_nonce( 'linker_inquiry_started_' . $stamp ) ) . '" />';
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
		&& false !== wp_verify_nonce( $nonce, 'linker_inquiry_started_' . $stamp );
	}
}
