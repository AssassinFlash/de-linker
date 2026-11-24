<?php
/**
 * Native Woo cart sharing transfers products between principals.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use WC_Session_Handler;

/** Keep private report snapshots and transfer receipts out of the cloned session row. */
final class SharedCartSession extends WC_Session_Handler {
	/** Only the initial save can contain the source cart's project data.
	 *
	 * @var bool
	 */
	private bool $opening_shared_cart = true;

	/** Woo calls this branch instead of cloning on an ordinary or repeated visit. */
	public function init_session_cookie(): void {
		$this->opening_shared_cart = false;
		parent::init_session_cookie();
	}

	/**
	 * Woo saves a new shared cart during init, before exposing it to cart consumers.
	 *
	 * @param string $old_session_key Previous session for a native login migration.
	 */
	public function save_data( $old_session_key = '' ): void {
		if ( $this->opening_shared_cart && null !== $this->get( 'previous_customer_id' ) ) {
			$this->opening_shared_cart = false;
			$this->set( DraftTransfer::CONTEXTS, null );
			$this->set( DraftTransfer::RECEIPTS, null );
			foreach ( array( 'cart', 'removed_cart_contents' ) as $field ) {
				$lines = $this->get( $field );
				if ( is_array( $lines ) ) {
					foreach ( $lines as &$line ) {
						unset( $line[ DraftTransfer::LINE_META ] );
					}
					unset( $line );
					$this->set( $field, $lines );
				}
			}
		}
		parent::save_data( $old_session_key );
	}
}
