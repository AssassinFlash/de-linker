<?php
/**
 * Semantic proof fields shared by native forms; no presentation CSS.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** A normal page visit loads no third-party verification script. */
final class FormFields {
	/**
	 * One logical UUID survives a validation retry in the native session.
	 *
	 * @param string $action Native action.
	 * @param string $id Optional original logical request.
	 */
	public static function render( string $action, string $id = '' ): string {
		if ( ! Business::enabled() ) {
			return '';
		}
		do_action( 'linker_commerce_public_protection_assets' ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Shared native verification client, documented in Protection\Module.
		$id       = wp_is_uuid( $id, 4 ) ? $id : wp_generate_uuid4();
		$fallback = 'enforce' === Configuration::current()->mode ? '<noscript><p>' . esc_html__( 'Please enable JavaScript to verify this request, or email sales@de-linker.com.', 'linker-commerce' ) . '</p></noscript>' : '';
		return '<input type="hidden" name="linker_request_id" value="' . esc_attr( $id ) . '" data-linker-protected-action="' . esc_attr( $action ) . '" /><input type="hidden" name="linker_proof" value="" /><div data-linker-protection-widget hidden></div><p role="status" aria-live="polite" data-linker-protection-status hidden></p>' . $fallback;
	}
}
