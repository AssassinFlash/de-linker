<?php
/** A transaction that cannot nest or commit a caller's transaction.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Mail;

/** MySQL and MariaDB reject SET TRANSACTION inside an active transaction. */
final class BudgetTransaction {
	/** Begin only a new owned transaction, without changing session defaults. */
	public static function begin(): bool {
		global $wpdb;
		$previous = $wpdb->suppress_errors( true );
		try {
			// phpcs:disable WordPress.DB.DirectDatabaseQuery -- SET TRANSACTION applies to the next transaction only and fails before changing an active caller transaction.
			if ( false === $wpdb->query( 'SET TRANSACTION ISOLATION LEVEL READ COMMITTED' ) ) {
				return false;
			}
			return false !== $wpdb->query( 'START TRANSACTION' );
			// phpcs:enable
		} finally {
			$wpdb->suppress_errors( $previous );
		}
	}
}
