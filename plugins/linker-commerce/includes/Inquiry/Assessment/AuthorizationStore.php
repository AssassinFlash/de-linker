<?php
/** Connection-fenced sending decisions, without copying customer content.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Inquiry\Assessment;

use WP_Error;
/** One private native option per source; exact CAS prevents reconnect writers. */
final class AuthorizationStore {
	public const PREFIX = 'linker_inquiry_send_';
	/** Native source identity.
	 *
	 * @param int|string $id Native source identity.
	 * @return array<string,mixed>|WP_Error
	 */
	public static function read( int|string $id ): array|WP_Error {
		global $wpdb;
	 // phpcs:disable WordPress.DB.DirectDatabaseQuery -- Authoritative uncached read; native options caches cannot establish a sending permission.
		$wpdb->flush();
		$raw = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", self::PREFIX . $id ) );
		if ( '' !== $wpdb->last_error ) {
			return new WP_Error( 'authorization_storage' );
		}
		if ( null === $raw ) {
			return array();
		}
		$state = is_string( $raw ) ? json_decode( $raw, true ) : null;
		return is_array( $state ) ? $state : new WP_Error( 'authorization_corrupt' );
	 // phpcs:enable
	}
	/** Native source identity.
	 *
	 * @param int|string $id Native source identity.
	 * @param callable   $work Mutation.
	 * @phpstan-param callable(array<string,mixed>&):void $work
	 * @param bool       $transaction Own a native transaction around the complete publication.
	 */
	public static function edit( int|string $id, callable $work, bool $transaction = false ): bool {
		global $wpdb;
		$name = 'linker-send-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/' . $id );
	 // phpcs:disable WordPress.DB.DirectDatabaseQuery -- Follows the existing Admission ledger's connection-owned lock + exact CAS contract.
		if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s,0)', $name ) ) ) {
			return false;
		}
		$owned      = false;
		$committed  = false;
		$connection = null;
		$fence      = null;
		try {
			if ( $transaction ) {
				$fence = \Linker\Commerce\Mail\ConnectionFence::enter();
			}
			$option = self::PREFIX . $id;
			$wpdb->query( $wpdb->prepare( "INSERT IGNORE INTO {$wpdb->options} (option_name,option_value,autoload) VALUES (%s,'{}','off')", $option ) );
			$raw   = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s AND IS_USED_LOCK(%s)=CONNECTION_ID()", $option, $name ) );
			$state = is_string( $raw ) ? json_decode( $raw, true ) : null;
			if ( ! is_array( $state ) ) {
				return false;
			}
			if ( $transaction ) {
				$connection = $wpdb->get_var( 'SELECT CONNECTION_ID()' );
				$owned      = \Linker\Commerce\Mail\BudgetTransaction::begin();
				if ( ! $owned ) {
					return false;
				}
			}
			$work( $state );
			$encoded = wp_json_encode( $state );
			if ( ! is_string( $encoded ) ) {
				return false;
			}
			$updated = $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value=%s WHERE option_name=%s AND BINARY option_value=BINARY %s AND IS_USED_LOCK(%s)=CONNECTION_ID()", $encoded, $option, $raw, $name ) );
			if ( false === $updated || ( $raw !== $encoded && 1 !== $updated ) ) {
				return false;
			}
			if ( $encoded !== $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s AND IS_USED_LOCK(%s)=CONNECTION_ID()", $option, $name ) ) ) {
				return false;
			}
			if ( $owned ) {
				$fence->assert_current();
				if ( $connection !== $wpdb->get_var( 'SELECT CONNECTION_ID()' ) || false === $wpdb->query( 'COMMIT' ) ) {
					return false;
				}
				$fence->assert_current();
				$committed = true;
			}
			return true;
		} catch ( \Throwable $error ) {
			return false;
		} finally {
			try {
				$fence?->assert_current();
				if ( $owned && ! $committed && $connection === $wpdb->get_var( 'SELECT CONNECTION_ID()' ) ) {
					$wpdb->query( 'ROLLBACK' );
				}
				$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
			} catch ( \Throwable $cleanup_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- Connection loss releases the native lock; cleanup must never reconnect or mask the fail-closed result.
				// A lost connection releases its native lock; never replay cleanup SQL on another one.
			} finally {
				$fence?->close();
				wp_cache_delete( self::PREFIX . $id, 'options' );
				wp_cache_delete( 'notoptions', 'options' );
			}
		}
		// phpcs:enable
	}
}
