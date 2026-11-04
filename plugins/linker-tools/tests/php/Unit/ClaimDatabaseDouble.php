<?php
/**
 * An in-memory options table for the browser-claim scan tests.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

/**
 * The options table as the browser-claim scan sees it.
 */
final class ClaimDatabaseDouble {

	/**
	 * The table name the SQL interpolates.
	 *
	 * @var string
	 */
	public string $options = 'wp_options';

	/**
	 * The claim rows, as a SELECT would return them.
	 *
	 * @var array<int, \stdClass>
	 */
	public array $rows = array();

	/**
	 * Every SELECT the scan made.
	 *
	 * @var list<string>
	 */
	public array $selects = array();

	/**
	 * Every other query (the deletes).
	 *
	 * @var list<string>
	 */
	public array $queries = array();

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
		if ( array() === $args ) {
			return $query;
		}
		// wpdb quotes %s values in place; %d stays bare.
		$query = str_replace( '%s', "'%s'", $query );
		return vsprintf( $query, array_map( static fn( mixed $value ): string => (string) $value, array_values( $args ) ) );
	}

	/**
	 * One bounded page of claim rows past the cursor.
	 *
	 * @param string $sql Prepared SQL text.
	 * @return array<int, \stdClass>
	 */
	public function get_results( string $sql ): array {
		$this->selects[] = $sql;
		preg_match( '/option_id > (\d+)/', $sql, $cursor );
		preg_match( '/LIMIT (\d+)/', $sql, $limit );
		$after = (int) ( $cursor[1] ?? 0 );
		$rows  = array_values(
			array_filter(
				$this->rows,
				static fn( \stdClass $row ): bool => (int) $row->option_id > $after
			)
		);
		return array_slice( $rows, 0, (int) ( $limit[1] ?? 0 ) );
	}

	/**
	 * Deletes the named rows, as the scan's DELETE … IN would.
	 *
	 * @param string $sql Prepared SQL text.
	 */
	public function query( string $sql ): int {
		$this->queries[] = $sql;
		if ( 1 !== preg_match( '/^DELETE FROM .* WHERE option_name IN \( (.+) \)$/', trim( $sql ), $names ) ) {
			return 1;
		}
		preg_match_all( "/'([^']+)'/", $names[1], $quoted );
		$gone = array();
		foreach ( $this->rows as $index => $row ) {
			if ( in_array( $row->option_name, $quoted[1], true ) ) {
				$gone[] = $index;
			}
		}
		foreach ( $gone as $index ) {
			unset( $this->rows[ $index ] );
		}
		$this->rows = array_values( $this->rows );
		return count( $gone );
	}
}
