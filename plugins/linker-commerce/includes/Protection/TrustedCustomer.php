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
		$id       = get_current_user_id();
		$approval = new Approval();
		$by       = (int) get_user_meta( $id, Approval::CHANGED_BY_META, true );
		return $id > 0 && $approval->is_subject( $id )
			&& Approval::APPROVED === $approval->status( $id )
			&& (int) get_user_meta( $id, Approval::CHANGED_AT_META, true ) > 0
			&& $by > 0 && $by !== $id && user_can( $by, 'manage_woocommerce' );
	}
}
