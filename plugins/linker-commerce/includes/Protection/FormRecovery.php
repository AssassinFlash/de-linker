<?php
/**
 * Failed contact input uses the same native Woo session as inquiry recovery.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** No password, proof, nonce or full transport body is kept. */
final class FormRecovery {
	/**
	 * Known native pre-dispatch refusals need a fresh check; every other outcome
	 * keeps the original UUID recoverable.
	 *
	 * @param WP_Error $error Native result, never a client-supplied state.
	 */
	public static function after_error( WP_Error $error ): bool {
		return Outcome::REFUSED !== Outcome::of( (string) $error->get_error_code() );
	}

	/**
	 * The journal already holds this UUID for different input, so the form must
	 * not offer it again: every resubmit would be refused as changed input.
	 *
	 * @param WP_Error|null $error Native result, never a client-supplied state.
	 */
	public static function superseded( ?WP_Error $error ): bool {
		return null !== $error && 'linker_admission_payload_changed' === $error->get_error_code();
	}

	/**
	 * Recover only this browser's editable contact fields, once.
	 *
	 * @phpstan-impure
	 *
	 * @param string              $action Native form name.
	 * @param array<string,mixed> $post Unslashed posted fields.
	 * @param WP_Error|null       $error Native result of this attempt, if it failed.
	 */
	public static function save( string $action, array $post, ?WP_Error $error = null ): void {
		$recover = null === $error || self::after_error( $error );
		if ( 'enforce' === Configuration::active_mode() && Campaign::recovery_matches( $post ) ) {
			return;
		}
		$fields = array();
		foreach ( array( 'name', 'email', 'company', 'message', 'intent', 'consent', 'linker_request_id', 'linker_individual_review', \Linker\Commerce\Contact\SelectionContext::FIELD, \Linker\Commerce\Contact\SelectionContext::INCLUDE_FIELD ) as $key ) {
			$value = isset( $post[ $key ] ) && is_string( $post[ $key ] ) ? $post[ $key ] : '';
			if ( \Linker\Commerce\Contact\SelectionContext::FIELD === $key && '' !== $value ) {
				$context = \Linker\Commerce\Contact\SelectionContext::normalize( json_decode( $value, true ) );
				if ( array() !== $context ) {
					// Re-encode the validated transport: unknown keys never consume the native recovery bound.
					$fields[ $key ] = (string) wp_json_encode(
						array(
							'source'    => $context['source'],
							'selection' => $context['selection'],
						)
					);
					// URL percent escapes and JSON backslashes are structural, not textarea prose.
					continue;
				}
			}
			$fields[ $key ] = mb_substr( sanitize_textarea_field( $value ), 0, 5000 );
		}
		// Server-owned outcome only. A client flag cannot create this context.
		$fields['linker_recovery_available'] = $recover ? '1' : '0';
		if ( self::superseded( $error ) ) {
			// The journal holds this UUID under other input and refuses it on every
			// retry. Clearing it lets the native form mint a new one, which is what
			// the refusal asks the customer to do.
			$fields['linker_request_id'] = '';
		}
		wc_load_cart();
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
