<?php
/**
 * Failed contact input uses the same native Woo session as inquiry recovery.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** No password, proof, nonce or full transport body is kept. */
final class FormRecovery {
	/**
	 * Recover only this browser's editable contact fields, once.
	 *
	 * @param string              $action Native form name.
	 * @param array<string,mixed> $post Unslashed posted fields.
	 */
	public static function save( string $action, array $post ): void {
		wc_load_cart();
		$fields = array();
		foreach ( array( 'name', 'email', 'company', 'message', 'intent', 'consent', 'linker_request_id', 'linker_individual_review' ) as $key ) {
			$fields[ $key ] = isset( $post[ $key ] ) && is_string( $post[ $key ] ) ? mb_substr( sanitize_textarea_field( $post[ $key ] ), 0, 5000 ) : '';
		}
		// Five-minute retry lifetime follows the shared proof window (#519).
		WC()->session->set(
			'linker_form_recovery_' . $action,
			array(
				'until'  => time() + 300,
				'fields' => $fields,
			)
		);
		if ( WC()->session instanceof \WC_Session_Handler ) {
			WC()->session->set_customer_session_cookie( true );
		}
	}

	/**
	 * Read once from the current Woo session, never from URL query text.
	 *
	 * @param string $action Native form name.
	 * @return array<string,string>
	 */
	public static function consume( string $action ): array {
		// A fresh page needs no Woo session access. A failed POST explicitly
		// sets Woo's signed session cookie before redirecting back to this form.
		$has_session = false;
		foreach ( array_keys( $_COOKIE ) as $key ) {
			if ( is_string( $key ) && str_starts_with( $key, 'wp_woocommerce_session_' ) ) {
				$has_session = true;
				break; }
		}
		if ( ! $has_session ) {
			return array(); }
		$value = WC()->session->get( 'linker_form_recovery_' . $action );
		WC()->session->set( 'linker_form_recovery_' . $action, null );
		return is_array( $value ) && (int) ( $value['until'] ?? 0 ) > time() && is_array( $value['fields'] ?? null ) ? $value['fields'] : array();
	}
}
