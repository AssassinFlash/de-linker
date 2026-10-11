<?php
/**
 * The shared secret of the stock push channel.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Stock;

/**
 * The key an ERP sends with every stock push (ticket #69). It is set from
 * WP-CLI and stored as its SHA-256 hash, so an option-table export is not
 * the credential; comparison is constant time on the hashes. Without a key
 * the channel is closed: every request is rejected, which is how the
 * endpoint ships at the switchover (dormant until an ERP is connected).
 */
final class PushKey {

	/**
	 * Option holding the key's SHA-256 hash (lowercase hex), not autoloaded.
	 */
	public const OPTION = 'linker_stock_push_key_hash';

	/**
	 * The HTTP header that carries the key.
	 */
	public const HEADER = 'X-Linker-Stock-Key';

	/**
	 * Whether a key is set: the channel is open.
	 */
	public static function is_set(): bool {
		return '' !== self::stored_hash();
	}

	/**
	 * Whether a provided key is the stored one. Constant time (hash_equals
	 * on the two hashes); no key set, or no key sent, rejects everything.
	 *
	 * @param string $provided The key the caller sent.
	 */
	public static function verify( string $provided ): bool {
		$stored = self::stored_hash();
		if ( '' === $stored || '' === $provided ) {
			return false;
		}
		return hash_equals( $stored, hash( 'sha256', $provided ) );
	}

	/**
	 * Stores (or replaces) the key. The key itself is not persisted; only
	 * its hash is.
	 *
	 * @param string $key The new key.
	 * @return string The stored hash, for the caller's log line.
	 */
	public static function set( string $key ): string {
		$hash = hash( 'sha256', $key );
		update_option( self::OPTION, $hash, false );
		return $hash;
	}

	/**
	 * Removes the key: the channel is closed again.
	 */
	public static function clear(): void {
		delete_option( self::OPTION );
	}

	/**
	 * A fresh key: 64 lowercase hex characters (256 bits).
	 */
	public static function generate(): string {
		return bin2hex( random_bytes( 32 ) );
	}

	/**
	 * The fingerprint the audit rows record: the first characters of the
	 * stored hash identify which key pushed, without holding the key.
	 */
	public static function fingerprint(): string {
		$stored = self::stored_hash();
		return '' === $stored ? '' : substr( $stored, 0, 12 );
	}

	/**
	 * The stored hash, '' when no key is set.
	 */
	private static function stored_hash(): string {
		$stored = get_option( self::OPTION, '' );
		return \is_string( $stored ) ? $stored : '';
	}
}
