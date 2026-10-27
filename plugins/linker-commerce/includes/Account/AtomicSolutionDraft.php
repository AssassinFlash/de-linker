<?php
/**
 * All-or-nothing solution writes through WooCommerce's own cart.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Products\Publication;
use Throwable;
use WC_Cart;
use WP_Error;

/**
 * Preflight the whole design; restore the prior cart if any native Woo write or
 * the final current-authority check fails. Existing quantities are preserved.
 */
final class AtomicSolutionDraft {
	/**
	 * Uses the same current authority at every stage of the write.
	 *
	 * @param DesignProof $proof Current publication checks.
	 */
	public function __construct( private readonly DesignProof $proof = new DesignProof() ) {}

	/**
	 * Tops up every BOM line as one operation, never duplicating an existing set.
	 *
	 * @param array<string, mixed> $result Trusted complete design.
	 * @param array<string,mixed>  $item_data Trusted native context, when supplied by a server integration.
	 * @param string[]             $replace_keys Only the reviewed native project group, when supplied.
	 * @return list<array{id:int,quantity:int}>|WP_Error Read-back quantities.
	 */
	public function add( array $result, array $item_data = array(), array $replace_keys = array() ): array|WP_Error {
		$items = DesignProof::items( $result );
		if ( array() === $items ) {
			return DesignProof::unavailable();
		}
		$current_error = $this->proof->current_error( $result );
		if ( $current_error instanceof WP_Error ) {
			return $current_error;
		}
		wc_load_cart();
		$cart = WC()->cart;
		try {
			foreach ( $items as $item ) {
				$permit  = Publication::product( $item['product_id'] );
				$product = null !== $permit ? wc_get_product( $item['product_id'] ) : false;
				if ( ! $product instanceof \WC_Product ) {
					return DesignProof::unavailable();
				}
			}
		} catch ( \RuntimeException $error ) {
			return DesignProof::verification_failed();
		}
		$before  = $cart->get_cart();
		$notices = wc_get_notices();
		try {
			foreach ( $replace_keys as $key ) {
				if ( false === $cart->remove_cart_item( $key ) ) {
					return $this->rollback( $cart, $before, $notices );
				}
			}
			foreach ( $items as $item ) {
				$held = 0;
				foreach ( $cart->get_cart() as $line ) {
					if ( (int) $line['product_id'] === $item['product_id'] && $this->matches( $line, $item_data ) ) {
						$held += (int) $line['quantity'];
					}
				}
				$needed = max( 0, $item['quantity'] - $held );
				if ( $needed > 0 ) {
					// WC_Form_Handler validates this hook before WC_Cart::add_to_cart;
					// the cart method does not run it for trusted server-side callers.
					/** This filter is documented in woocommerce/includes/class-wc-form-handler.php. */
					$valid = apply_filters( 'woocommerce_add_to_cart_validation', true, $item['product_id'], $needed ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce's native validation hook.
					$added = $valid ? ( array() === $item_data ? $cart->add_to_cart( $item['product_id'], $needed ) : $cart->add_to_cart( $item['product_id'], $needed, 0, array(), $item_data ) ) : false;
					if ( false === $added ) {
						return $this->rollback( $cart, $before, $notices );
					}
				}
			}
			$current_error = $this->proof->current_error( $result );
			if ( $current_error instanceof WP_Error ) {
				return $this->rollback( $cart, $before, $notices, $current_error );
			}
			$quantities = array();
			foreach ( $cart->get_cart() as $line ) {
				if ( ! $this->matches( $line, $item_data ) ) {
					continue;
				}
				$id                = (int) $line['product_id'];
				$quantities[ $id ] = ( $quantities[ $id ] ?? 0 ) + (int) $line['quantity'];
			}
			foreach ( $items as $item ) {
				if ( ( $quantities[ $item['product_id'] ] ?? 0 ) < $item['quantity'] || ( array() !== $item_data && ( $quantities[ $item['product_id'] ] ?? 0 ) != $item['quantity'] ) ) { // phpcs:ignore Universal.Operators.StrictComparisons.LooseNotEqual -- Woo may return an integral float; fractional pieces do not satisfy the frozen quantity.
					return $this->rollback( $cart, $before, $notices );
				}
			}
			$cart->calculate_totals();
			$current_error = $this->proof->current_error( $result );
			if ( $current_error instanceof WP_Error ) {
				return $this->rollback( $cart, $before, $notices, $current_error );
			}
			return array_map(
				static fn ( array $item ): array => array(
					'id'       => $item['product_id'],
					'quantity' => $quantities[ $item['product_id'] ],
				),
				$items
			);
		} catch ( Throwable $error ) {
			return $this->rollback( $cart, $before, $notices );
		}
	}

	/**
	 * Keep independent project transfers separate while preserving ordinary adds.
	 *
	 * @param array<string,mixed> $line Native Woo line.
	 * @param array<string,mixed> $data Trusted server metadata.
	 */
	private function matches( array $line, array $data ): bool {
		foreach ( $data as $key => $value ) {
			if ( ( $line[ $key ] ?? null ) !== $value ) {
				return false;
			}
		}
		return true;
	}

	/**
	 * Restores only this operation's writes, preserving the existing draft.
	 *
	 * @param WC_Cart              $cart    Woo native draft.
	 * @param array<string, mixed> $before  Exact previous contents.
	 * @param array<string, mixed> $notices Previous native notices.
	 * @param WP_Error|null        $error   Current-authority failure when known.
	 */
	private function rollback( WC_Cart $cart, array $before, array $notices, ?WP_Error $error = null ): WP_Error {
		$cart->set_cart_contents( $before );
		$cart->calculate_totals();
		wc_set_notices( $notices );
		return $error ?? DesignProof::unavailable();
	}
}
