<?php
/**
 * Hidden honeypot shared by inquiry, contact and registration forms.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

/** The submission handler owns its native nonce and guest verification. */
final class PublicGuard {
	/** The reason recorded when a registration fills the hidden field. */
	public const REFUSAL_HONEYPOT = 'honeypot';

	/** Markup inside the native form. */
	public static function fields(): string {
		return '<div hidden aria-hidden="true"><input type="text" name="website" tabindex="-1" autocomplete="off" aria-label="' . esc_attr__( 'Website', 'linker-commerce' ) . '" /></div>';
	}

	/**
	 * Accept the form when its hidden field is empty.
	 *
	 * @param array<string, mixed> $post Unslashed form fields.
	 */
	public static function allows( array $post ): bool {
		return '' === ( $post['website'] ?? '' );
	}
}
