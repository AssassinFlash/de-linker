<?php
/**
 * Restore report links on the native inquiry form after Woo merges carts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use WP_Error;

/** Woo migrates the guest session and its receipts; its persistent cart stores only lines. */
final class DraftRecovery {
	public const FIELD = 'linker_detach_planning_links';

	/**
	 * Resolve each linked report against the current owner before showing its details.
	 *
	 * @return list<string>|WP_Error Cart keys with inaccessible links, or an inconclusive lookup.
	 */
	public static function review(): array|WP_Error {
		$stored   = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
		$reviewed = array();
		$missing  = array();
		foreach ( WC()->cart->get_cart() as $key => $line ) {
			$id = $line[ DraftTransfer::LINE_META ] ?? null;
			if ( null === $id ) {
				continue;
			}
			if ( ! is_string( $id ) || ! preg_match( '/\A[a-f0-9]{32}\z/', $id ) ) {
				$missing[] = $key;
				continue;
			}
			if ( ! array_key_exists( $id, $reviewed ) ) {
				/** This private Tools reader authorizes the current account or signed guest.
				 *
				 * @since 0.3.0
				 */
				$owned = apply_filters( 'linker_tools_planning_inquiry_handoff', null, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Private linker-tools seam.
				if ( $owned instanceof WP_Error && 'linker_planner_handoff_not_found' === $owned->get_error_code() && 404 === ( $owned->get_error_data()['status'] ?? null ) ) {
					$reviewed[ $id ] = false;
					unset( $stored[ $id ] );
				} elseif ( DraftTransfer::envelope_valid( $owned ) && $owned['id'] === $id && ! DraftTransfer::report_only( $owned['snapshot'] ) ) {
					$reviewed[ $id ] = true;
					$stored[ $id ]   = DraftTransfer::native_context( $owned );
				} else {
					return Context::admission_unavailable();
				}
			}
			if ( ! $reviewed[ $id ] ) {
				$missing[] = $key;
			}
		}
		if ( array() !== $reviewed ) {
			WC()->session->set( DraftTransfer::CONTEXTS, $stored );
		}
		return $missing;
	}

	/**
	 * Bind the choice to the Woo lines shown in this customer's draft.
	 *
	 * @param string[] $missing Unavailable cart line keys.
	 */
	public static function nonce_action( array $missing ): string {
		return self::FIELD . ':' . implode( ',', $missing );
	}

	/** Remove only the links the buyer reviewed and the server still cannot resolve.
	 *
	 * @param string $nonce Confirmation from the inquiry form.
	 */
	public static function detach( string $nonce ): bool {
		$missing = self::review();
		if ( $missing instanceof WP_Error || array() === $missing || ! wp_verify_nonce( $nonce, self::nonce_action( $missing ) ) ) {
			return false;
		}
		$cart  = WC()->cart;
		$lines = $cart->get_cart();
		foreach ( $missing as $key ) {
			unset( $lines[ $key ][ DraftTransfer::LINE_META ] );
		}
		$cart->set_cart_contents( $lines );
		$session = new \WC_Cart_Session( $cart );
		$session->set_session();
		$session->persistent_cart_update();
		return true;
	}
}
