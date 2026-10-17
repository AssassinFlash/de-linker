<?php
/**
 * Where translation state is stored.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * The translation state of an English object and its German version, in
 * post meta or term meta.
 *
 * On the English object: its status (pending, synced, failed, structure_mismatch) and a
 * note. On the German object: the fingerprint of the English it was made
 * from (`_linker_i18n_source_hash`), per field the fingerprints of the
 * English and German segments last written (`_linker_i18n_units`), and historical conflict flags. The existing `_linker_i18n_reviewed` record
 * is retained as history; it never forces a rewrite or an approval step.
 */
final class State {

	public const STATUS = '_linker_i18n_status';

	public const NOTE = '_linker_i18n_note';

	public const SOURCE_HASH = '_linker_i18n_source_hash';

	public const UNITS = '_linker_i18n_units';

	public const REVIEWED = '_linker_i18n_reviewed';

	/**
	 * Waiting for the translator: queued or a transient retry is scheduled.
	 */
	public const PENDING = 'pending';

	/**
	 * The German version matches the English.
	 */
	public const SYNCED = 'synced';

	/**
	 * A lasting failure, or transient retries exhausted. The previous German stays.
	 */
	public const FAILED = 'failed';

	/**
	 * English changed, but its sentences cannot be aligned with existing German.
	 */
	public const STRUCTURE_MISMATCH = 'structure_mismatch';

	/**
	 * Shared, localised exception reason for the list and the daily digest.
	 */
	public static function structure_reason(): string {
		return __( 'German out of date: structure differs', 'linker-i18n' );
	}

	/**
	 * Historical status, read only to recover objects into automatic translation.
	 */
	public const NEEDS_REVIEW = 'needs_review';

	/**
	 * Object kinds.
	 */
	public const POST = 'post';

	public const TERM = 'term';

	/**
	 * The status of an English object; empty when it never went through the translator.
	 *
	 * @param string $kind State::POST or State::TERM.
	 * @param int    $id   Object ID.
	 */
	public function status( string $kind, int $id ): string {
		return (string) get_metadata( $kind, $id, self::STATUS, true );
	}

	/**
	 * The note that goes with the status.
	 *
	 * @param string $kind State::POST or State::TERM.
	 * @param int    $id   Object ID.
	 */
	public function note( string $kind, int $id ): string {
		return (string) get_metadata( $kind, $id, self::NOTE, true );
	}

	/**
	 * Sets the status of an English object.
	 *
	 * @param string $kind   State::POST or State::TERM.
	 * @param int    $id     Object ID.
	 * @param string $status One of the status constants.
	 * @param string $note   Why, for the admin screens.
	 */
	public function set_status( string $kind, int $id, string $status, string $note = '' ): void {
		update_metadata( $kind, $id, self::STATUS, $status );
		if ( '' === $note ) {
			delete_metadata( $kind, $id, self::NOTE );
		} else {
			update_metadata( $kind, $id, self::NOTE, wp_slash( $note ) );
		}
	}

	/**
	 * The fingerprint of the English the German version was made from.
	 *
	 * @param string $kind State::POST or State::TERM.
	 * @param int    $twin German object ID.
	 */
	public function source_hash( string $kind, int $twin ): string {
		return (string) get_metadata( $kind, $twin, self::SOURCE_HASH, true );
	}

	/**
	 * Per field, the fingerprints of the English segments and of the German
	 * segments last written, including historical conflict flags to recover.
	 *
	 * @param string $kind State::POST or State::TERM.
	 * @param int    $twin German object ID.
	 * @return array<string, array{src: list<string>, out: list<string>, conflict: bool}>
	 */
	public function units( string $kind, int $twin ): array {
		$units = array();
		foreach ( $this->read( $kind, $twin, self::UNITS ) as $field => $unit ) {
			if ( is_string( $field ) && is_array( $unit ) ) {
				$units[ $field ] = array(
					'src'      => array_values( array_map( 'strval', (array) ( $unit['src'] ?? array() ) ) ),
					'out'      => array_values( array_map( 'strval', (array) ( $unit['out'] ?? array() ) ) ),
					'conflict' => true === ( $unit['conflict'] ?? false ),
				);
			}
		}
		return $units;
	}

	/**
	 * Stores the state of a German object.
	 *
	 * @param string                                                                     $kind        State::POST or State::TERM.
	 * @param int                                                                        $twin        German object ID.
	 * @param string                                                                     $source_hash Fingerprint of the English.
	 * @param array<string, array{src: list<string>, out: list<string>, conflict: bool}> $units    Segment fingerprints per field.
	 */
	public function save( string $kind, int $twin, string $source_hash, array $units ): void {
		update_metadata( $kind, $twin, self::SOURCE_HASH, $source_hash );
		update_metadata( $kind, $twin, self::UNITS, wp_slash( (string) wp_json_encode( $units ) ) );
	}

	/**
	 * A JSON meta value as an array.
	 *
	 * @param string $kind State::POST or State::TERM.
	 * @param int    $id   Object ID.
	 * @param string $key  Meta key.
	 * @return array<mixed>
	 */
	private function read( string $kind, int $id, string $key ): array {
		$value = json_decode( (string) get_metadata( $kind, $id, $key, true ), true );
		return is_array( $value ) ? $value : array();
	}
}
