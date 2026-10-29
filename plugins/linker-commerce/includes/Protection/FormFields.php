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
	 * @param bool   $individual Preserve an explicit individual-review retry.
	 * @param bool   $recover Whether the last native result may still need recovery.
	 */
	public static function render( string $action, string $id = '', bool $individual = false, bool $recover = true ): string {
		if ( ! Business::enabled() ) {
			return '';
		}
		do_action( 'linker_commerce_public_protection_assets' ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Shared native verification client, documented in Protection\Module.
		$recovery = $recover && in_array( $action, array( 'contact', 'inquiry' ), true ) && wp_is_uuid( $id, 4 ) ? ' data-linker-protection-recovery="true"' : '';
		$id       = wp_is_uuid( $id, 4 ) ? $id : wp_generate_uuid4();
		$fallback = 'enforce' === Configuration::current()->mode && Configuration::verification_required( $action ) ? '<noscript><p>' . esc_html__( 'Please enable JavaScript to verify this request, or email sales@de-linker.com.', 'linker-commerce' ) . '</p></noscript>' : '';
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Controls display only; no action is taken from the query state.
		$grouped = 'grouped' === ( isset( $_GET['contact'] ) && is_string( $_GET['contact'] ) ? sanitize_key( wp_unslash( $_GET['contact'] ) ) : '' ) || WC()->session->get( 'linker_intake_grouped', false );
		$review  = ( $grouped || $individual ) && in_array( $action, array( 'contact', 'inquiry' ), true ) ? '<p><label><input type="checkbox" name="linker_individual_review" value="1"' . checked( $individual, true, false ) . ' /> ' . esc_html__( 'Request individual review of this message', 'linker-commerce' ) . '</label></p>' : '';
		return $review . '<input type="hidden" name="linker_request_id" value="' . esc_attr( $id ) . '" data-linker-protected-action="' . esc_attr( $action ) . '"' . $recovery . ' /><input type="hidden" name="linker_proof" value="" /><div data-linker-protection-widget hidden></div><p role="status" aria-live="polite" data-linker-protection-status hidden></p>' . $fallback;
	}
}
