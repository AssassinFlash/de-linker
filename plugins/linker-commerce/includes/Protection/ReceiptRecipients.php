<?php
/** Short-lived recipient history for native mail delivery.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Mail\ConnectionFence;

/** Indexed, non-autoloaded options expire independently of unrelated recipients and tools. */
final class ReceiptRecipients {
	private const PREFIX   = 'linker_mail_target_v1.';
	private const IMPORTED = 'linker_mail_target_imported_v1';

	/**
	 * Check a receipt before handoff, or charge it before transport.
	 *
	 * @param string[] $owners Recipient pseudonyms.
	 * @param string   $id Original native source.
	 * @param string   $fingerprint Original destination binding.
	 * @param bool     $spend Whether the actual transport is ready.
	 */
	public static function admit( array $owners, string $id, string $fingerprint, bool $spend ): string {
		$result = 'unavailable';
		try {
			Lock::run(
				'recipient-delivery',
				static function () use ( $owners, $id, $fingerprint, $spend, &$result ) {
					$result = ConnectionFence::run( static fn () => self::charge( $owners, $id, $fingerprint, $spend ) );
				},
				1,
				true
			);
		} catch ( \Throwable $error ) {
			return 'unavailable';
		}
		return $result;
	}

	/**
	 * Take one entry for each normalized recipient of an original source.
	 *
	 * @param string[] $owners Recipient pseudonyms.
	 * @param string   $id Source.
	 * @param string   $fingerprint Destination binding.
	 * @param bool     $spend Commit an allowance.
	 */
	private static function charge( array $owners, string $id, string $fingerprint, bool $spend ): string {
		$now = time();
		self::import( $now );
		$day = intdiv( $now, DAY_IN_SECONDS );
		foreach ( array( $day, $day - 1 ) as $when ) {
			$source = self::value( self::key( $when, 's.' . $id ) );
			if ( null !== $source ) {
				[ $until, $bound ] = explode( '|', $source, 2 );
				if ( $now < (int) $until ) {
					return hash_equals( $fingerprint, $bound ) ? '' : 'unavailable';
				}
			}
		}
		$writes = array( self::key( $day, 's.' . $id ) => ( $now + DAY_IN_SECONDS ) . '|' . $fingerprint );
		foreach ( $owners as $owner ) {
			$prefix = self::key( $day, 'r.' . $owner . '.' );
			$rows   = self::rows( $prefix );
			$hour   = intdiv( $now, HOUR_IN_SECONDS );
			$recent = array_filter( $rows, static fn ( $row ) => intdiv( (int) $row['option_value'], HOUR_IN_SECONDS ) === $hour );
			if ( count( $rows ) >= 5 || count( $recent ) >= 2 ) {
				return 'target_cap';
			}
			// The ordinal gives concurrent writers a unique database constraint even inside an outer transaction.
			$writes[ $prefix . count( $rows ) ] = $now . '|' . $id;
		}
		if ( $spend ) {
			self::insert( $writes );
		}
		return '';
	}

	/**
	 * An indexed key within a UTC day.
	 *
	 * @param int    $day UTC day.
	 * @param string $suffix Indexed record key.
	 */
	private static function key( int $day, string $suffix ): string {
		return self::PREFIX . sprintf( '%010d', $day ) . '.' . $suffix;
	}

	/**
	 * Read an original source marker.
	 *
	 * @param string $key Exact source marker.
	 * @throws \RuntimeException A stored source cannot be read.
	 */
	private static function value( string $key ): ?string {
		global $wpdb;
		$value = $wpdb->get_var( $wpdb->prepare( 'SELECT option_value FROM %i WHERE option_name=%s', $wpdb->options, $key ) );
		if ( '' !== $wpdb->last_error ) {
			throw new \RuntimeException( 'recipient_history_read_failed' );
		}
		return $value;
	}

	/**
	 * Read the delivery history for one recipient and day.
	 *
	 * @param string $prefix Exact recipient and UTC day.
	 * @throws \RuntimeException Recipient history cannot be read.
	 * @return list<array{option_name:string,option_value:string}>
	 */
	private static function rows( string $prefix ): array {
		global $wpdb;
		$rows = $wpdb->get_results( $wpdb->prepare( 'SELECT option_name,option_value FROM %i WHERE option_name LIKE %s', $wpdb->options, $wpdb->esc_like( $prefix ) . '%' ), ARRAY_A );
		if ( ! is_array( $rows ) || '' !== $wpdb->last_error ) {
			throw new \RuntimeException( 'recipient_history_read_failed' );
		}
		return $rows;
	}

	/** One native statement commits the source and every destination together.
	 *
	 * @param array<string,string> $records Option names and values.
	 * @param bool                 $import Existing rows from a previous migration batch are retained.
	 * @throws \RuntimeException A grouped write failed.
	 */
	private static function insert( array $records, bool $import = false ): void {
		global $wpdb;
		if ( array() === $records ) {
			return;
		}
		$values = array();
		foreach ( $records as $name => $value ) {
			$values[] = $wpdb->prepare( "(%s,%s,'off')", $name, $value );
		}
		$query = $wpdb->prepare( 'INSERT INTO %i (option_name,option_value,autoload) VALUES ', $wpdb->options ) . implode( ',', $values );
		if ( $import ) {
			$query .= ' ON DUPLICATE KEY UPDATE option_name=option_name';
		}
		// phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared -- Each value and the options table have already been prepared above.
		if ( false === $wpdb->query( $query ) ) {
			throw new \RuntimeException( 'recipient_history_write_failed' );
		}
	}

	/** Copy unexpired source bindings once, including a previously full tools journal.
	 *
	 * @param int $now Current Unix time.
	 * @throws \RuntimeException The migration cannot be saved.
	 */
	private static function import( int $now ): void {
		if ( get_option( self::IMPORTED ) ) {
			return;
		}
		$legacy = json_decode( self::value( Ledger::OPTION ) ?? '', true );
		$writes = array();
		$counts = array();
		foreach ( (array) ( $legacy['receipts'] ?? array() ) as $id => $entry ) {
			if ( 'customer_receipt' !== ( $entry['purpose'] ?? '' ) || ( $entry['retry_until'] ?? 0 ) <= $now || in_array( $entry['status'], array( 'cancelled', 'expired' ), true ) ) {
				continue;
			}
			$at                                      = (int) $entry['created_at'];
			$day                                     = intdiv( $at, DAY_IN_SECONDS );
			$writes[ self::key( $day, 's.' . $id ) ] = $entry['retry_until'] . '|' . ( 'erased' === $entry['status'] ? 'erased' : $entry['fingerprint'] );
			if ( 'erased' === $entry['status'] ) {
				continue;
			}
			foreach ( array_diff( $entry['owners'], array( Allowance::owner_for( 'site' ) ) ) as $owner ) {
				$prefix                    = self::key( $day, 'r.' . $owner . '.' );
				$slot                      = $counts[ $prefix ] ?? 0;
				$writes[ $prefix . $slot ] = $at . '|' . $id;
				$counts[ $prefix ]         = $slot + 1;
			}
		}
		foreach ( array_chunk( $writes, 250, true ) as $batch ) {
			self::insert( $batch, true );
		}
		if ( ! add_option( self::IMPORTED, '1', '', false ) && ! get_option( self::IMPORTED ) ) {
			throw new \RuntimeException( 'recipient_history_migration_failed' );
		}
	}

	/** Export or erase contributions belonging to the verified email address.
	 *
	 * @param string $email Native verified email.
	 * @param bool   $erase Whether the requester asked for erasure.
	 * @return list<array{id:string,purpose:string,created_at:int}>
	 * @throws \RuntimeException The privacy operation cannot be completed.
	 */
	public static function privacy( string $email, bool $erase ): array {
		global $wpdb;
		$records = array();
		$read    = static function () use ( $email, $erase, &$records, $wpdb ) {
			$now = time();
			self::import( $now );
			$today = intdiv( $now, DAY_IN_SECONDS );
			$owner = Allowance::owner_for( Identity::recipient( $email ) );
			foreach ( array( $today, $today - 1 ) as $day ) {
				foreach ( self::rows( self::key( $day, 'r.' . $owner . '.' ) ) as $row ) {
					[ $at, $id ] = explode( '|', $row['option_value'], 2 );
					if ( $now - (int) $at < DAY_IN_SECONDS ) {
						$records[] = array(
							'id'         => $id,
							'purpose'    => 'customer_receipt',
							'created_at' => (int) $at,
						);
					}
					if ( $erase ) {
						if ( false === $wpdb->update( $wpdb->options, array( 'option_value' => ( (int) $at + DAY_IN_SECONDS ) . '|erased' ), array( 'option_name' => self::key( $day, 's.' . $id ) ) ) || false === $wpdb->delete( $wpdb->options, array( 'option_name' => $row['option_name'] ) ) ) {
							throw new \RuntimeException( 'recipient_history_erasure_failed' );
						}
					}
				}
			}
		};
		if ( ! Lock::run( 'recipient-delivery', static fn () => ConnectionFence::run( $read ), 1, true ) ) {
			throw new \RuntimeException( 'recipient_history_busy' );
		}
		return $records;
	}

	/** The daily native maintenance job removes days outside the replay window. */
	public static function expire(): void {
		global $wpdb;
		$cutoff = self::key( intdiv( time(), DAY_IN_SECONDS ) - 1, '' );
		$wpdb->query( $wpdb->prepare( 'DELETE FROM %i WHERE option_name >= %s AND option_name < %s', $wpdb->options, self::PREFIX, $cutoff ) );
	}
}
