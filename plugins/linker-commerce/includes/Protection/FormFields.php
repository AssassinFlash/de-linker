<?php
/**
 * Native business-form verification and inquiry retry identity.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Anonymous visitors verify when they send a message or register. */
final class FormFields {
	/**
	 * The request ID connects an inquiry retry to its original submission.
	 *
	 * @param string $action Native form action.
	 * @param string $id     Previous inquiry or contact request ID.
	 */
	public static function render( string $action, string $id = '' ): string {
		if ( ! Configuration::verification_required( $action ) ) {
			return '';
		}
		$html = '';
		if ( in_array( $action, array( 'contact', 'inquiry' ), true ) ) {
			$id   = wp_is_uuid( $id, 4 ) ? $id : wp_generate_uuid4();
			$html = '<input type="hidden" name="linker_request_id" value="' . esc_attr( $id ) . '" />';
		}
		if ( is_user_logged_in() ) {
			return $html;
		}
		do_action( 'linker_commerce_public_protection_assets' ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Shared native client registered by Protection\Module.
		return $html . '<div data-linker-turnstile="' . esc_attr( $action ) . '"></div><noscript><p>' . esc_html__( 'Please enable JavaScript to verify this request, or email sales@de-linker.com.', 'linker-commerce' ) . '</p></noscript>';
	}
}
