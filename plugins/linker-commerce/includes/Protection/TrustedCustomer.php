<?php
/**
 * A staff decision, rather than login or the default approval status (#568).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Registration\Approval;

/** The protected pool is available only to a customer actually approved by staff. */
final class TrustedCustomer {
	/** Check the native role, recorded decision and its still-authorized author. */
	public static function current(): bool {
		$id = get_current_user_id();
		clean_user_cache( $id );
		wp_cache_delete( $id, 'user_meta' );
		$approval = new Approval();
		$by       = (int) get_user_meta( $id, Approval::CHANGED_BY_META, true );
		if ( $by > 0 ) {
			clean_user_cache( $by );
			wp_cache_delete( $by, 'user_meta' );
		}
		return $id > 0 && $approval->is_subject( $id )
			&& Approval::APPROVED === $approval->status( $id )
			&& (int) get_user_meta( $id, Approval::CHANGED_AT_META, true ) > 0
			&& $by > 0 && $by !== $id && user_can( $by, 'manage_woocommerce' );
	}
}
