<?php
/**
 * An in-memory options table for the browser-claim lifecycle tests.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

/**
 * The options table behind both the options API and the claim SQL.
 */
final class ClaimOptionsDouble {

	/**
	 * The table name the SQL interpolates.
	 *
	 * @var string
	 */
	public string $options = 'wp_options';

	/**
	 * Rows of the in-memory store.
	 *
	 * @var array<string, mixed>
	 */
	private array $rows = array();

	/**
	 * The queries query() saw (inserts, deletes).
	 *
	 * @var list<string>
	 */
	public array $queries = array();

	/**
	 * Rows update_option() wrote, by name.
	 *
	 * @var array<string, mixed>
	 */
	public array $updated = array();

	/**
	 * INSERT answers, in order (0: ignored; 1: inserted).
	 *
	 * @var list<int>
	 */
	public array $insert_answers = array();

	/**
	 * UPDATE answers, in order (1: the take matched; 0: the allowance was spent).
	 *
	 * @var array<int, int>
	 */
	public array $update_answers = array();

	/**
	 * The row a concurrent winner commits as this request's insert is
	 * ignored, keyed by the claim's option name; models a commit racing the
	 * loser's read-back.
	 *
	 * @var array<string, mixed>|null
	 */
	public ?array $committed_on_ignored_insert = null;

	/**
	 * GET_LOCK answers, in order.
	 *
	 * @var list<string>
	 */
	public array $lock_answers = array();

	/**
	 * One stored option.
	 *
	 * @param string $name     Option name.
	 * @param mixed  $fallback What to answer when it is not stored.
	 */
	public function get( string $name, mixed $fallback ): mixed {
		return array_key_exists( $name, $this->rows ) ? $this->rows[ $name ] : $fallback;
	}

	/**
	 * Stores one option.
	 *
	 * @param string $name  Option name.
	 * @param mixed  $value The value.
	 */
	public function set( string $name, mixed $value ): void {
		$this->rows[ $name ] = $value;
	}

	/**
	 * Deletes one option.
	 *
	 * @param string $name Option name.
	 */
	public function delete( string $name ): bool {
		unset( $this->rows[ $name ] );
		return true;
	}

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
	 * GET_LOCK and RELEASE_LOCK.
	 *
	 * @param string $query SQL text.
	 */
	public function get_var( string $query ): string {
		if ( str_contains( $query, 'GET_LOCK' ) ) {
			return (string) ( array_shift( $this->lock_answers ) ?? '0' );
		}
		return '1';
	}

	/**
	 * INSERT IGNORE and DELETE by name.
	 *
	 * @param string $query SQL text.
	 */
	public function query( string $query ): int {
		$this->queries[] = $query;
		if ( str_contains( $query, 'INSERT IGNORE' ) ) {
			$ignored = 0 === ( array_shift( $this->insert_answers ) ?? 1 );
			if ( $ignored && null !== $this->committed_on_ignored_insert ) {
				preg_match( "/VALUES \('([^']+)'/", $query, $name );
				if ( isset( $name[1] ) ) {
					$this->rows[ $name[1] ] = $this->committed_on_ignored_insert;
				}
			}
			return $ignored ? 0 : 1;
		}
		if ( str_contains( $query, 'UPDATE' ) ) {
			return array_shift( $this->update_answers ) ?? 1;
		}
		if ( str_contains( $query, 'DELETE FROM' ) ) {
			preg_match( "/'([^']+)'/", $query, $name );
			if ( isset( $name[1] ) ) {
				$this->delete( $name[1] );
				return 1;
			}
		}
		return 1;
	}
}
