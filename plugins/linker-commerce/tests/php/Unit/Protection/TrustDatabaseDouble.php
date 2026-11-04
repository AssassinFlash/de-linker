<?php
/**
 * An in-memory options table for the trust store's SQL.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

/**
 * The options table as the trust's SQL sees it.
 */
final class TrustDatabaseDouble {

	/**
	 * The table name the SQL interpolates.
	 *
	 * @var string
	 */
	public string $options = 'wp_options';

	/**
	 * Every query() made (purges and inserts).
	 *
	 * @var list<string>
	 */
	public array $queries = array();

	/**
	 * The rows the options API serves, by name.
	 *
	 * @var array<string, mixed>
	 */
	public $rows = array();

	/**
	 * Escapes LIKE wildcards, as wpdb does.
	 *
	 * @param string $text Raw text.
	 */
	public function esc_like( string $text ): string {
		return str_replace( array( '\\', '%', '_' ), array( '\\\\', '\\%', '\\_' ), $text );
	}

	/**
	 * Substitutes the placeholders, as wpdb does.
	 *
	 * @param string $query SQL text.
	 * @param mixed  ...$args Bound values.
	 */
	public function prepare( string $query, mixed ...$args ): string {
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.serialize_serialize -- no serialization; quoting only.
		$query = str_replace( '%s', "'%s'", $query );
		return vsprintf( $query, array_map( static fn( mixed $value ): string => (string) $value, array_values( $args ) ) );
	}

	/**
	 * The purge and the insert, applied to the store the options API reads.
	 *
	 * @param string $query SQL text.
	 */
	public function query( string $query ): int {
		$this->queries[] = $query;
		if ( 1 === preg_match( '/VALUES \(\'([^\']+)\', \'([^\']+)\', \'off\'\)/', $query, $insert ) ) {
			$this->rows[ $insert[1] ] = unserialize( $insert[2], array( 'allowed_classes' => false ) ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.serialize_unserialize -- the double mirrors wpdb's option storage, never live data.
			return 1;
		}
		if ( 1 === preg_match( '/RIGHT\(option_name, 10\) < \'([0-9]{10})\'/', $query, $purge ) && 1 === preg_match( '/LIKE \'([^\']+)\'/', $query, $prefix ) ) {
			$prefix = str_replace( array( '\\%', '\\_' ), array( '%', '_' ), $prefix[1] );
			$gone   = 0;
			foreach ( $this->rows as $name => $ignored ) {
				if ( str_starts_with( $name, $prefix ) && substr_compare( $name, $purge[1], -10 ) < 0 ) {
					unset( $this->rows[ $name ] );
					++$gone;
				}
			}
			return $gone;
		}
		return 1;
	}
}
