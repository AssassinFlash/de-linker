<?php
/**
 * Makes and keeps the German version of an English object.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

use Linker\I18n\Languages;
use Linker\I18n\Twins;

/**
 * Brings the German version of an English post or term up to date.
 *
 * Segment by segment: what did not change in the English keeps its German,
 * what changed goes to the translator, and every translation is checked
 * before anything is stored. A segment a person edited in the German is
 * never overwritten: when the English under it changes, the segment stays as
 * it is (the whole field, when its segments no longer line up) and the object
 * is marked needs_review until a person saves the German again. Nothing is
 * stored when a translation is missing or fails a check; the German stays as
 * it was.
 */
final class Translator {

	/**
	 * Characters of English per request: a rejected answer costs one batch
	 * (see DeepSeekClient::MAX_TOKENS for the output budget it fits).
	 */
	public const BATCH_CHARACTERS = 6000;

	/**
	 * Segments per request, for the same reason.
	 */
	public const BATCH_SEGMENTS = 40;

	/**
	 * Sets up the translator.
	 *
	 * @param Languages $languages The site's languages.
	 * @param Planner   $planner   Plans each field from the English and the German.
	 * @param Fields    $fields    The translatable fields.
	 * @param State     $state     Translation state.
	 * @param Client    $client    The machine translator.
	 * @param Validator $validator Checks translations.
	 * @param Twins     $twins     Writes German objects.
	 */
	public function __construct(
		private readonly Languages $languages,
		private readonly Planner $planner,
		private readonly Fields $fields,
		private readonly State $state,
		private readonly Client $client,
		private readonly Validator $validator,
		private readonly Twins $twins
	) {}

	/**
	 * Brings the German version of an English post up to date.
	 *
	 * @param int  $source_id English post ID.
	 * @param bool $force     Translate every segment again, discarding edits.
	 * @return string The status afterwards; empty when the post is not an English translated post.
	 * @throws TranslationFailed When a translation is missing or fails its checks; nothing was stored.
	 */
	public function post( int $source_id, bool $force = false ): string {
		$source = get_post( $source_id );
		if ( ! $source instanceof \WP_Post || ! $this->languages->translates_post_type( $source->post_type ) || Languages::SOURCE !== $this->languages->of_post( $source_id ) ) {
			return '';
		}
		$twin = $this->german_post( $source_id );
		return $this->run(
			State::POST,
			$source_id,
			$this->fields->of_post( $source ),
			$twin,
			fn( array $values ): int => $this->twins->post( $source_id, $values ),
			$force
		);
	}

	/**
	 * Brings the German version of an English term up to date.
	 *
	 * @param int  $term_id English term ID.
	 * @param bool $force   Translate every segment again, discarding edits.
	 * @return string The status afterwards; empty when the term is not an English translated term.
	 * @throws TranslationFailed When a translation is missing or fails its checks; nothing was stored.
	 */
	public function term( int $term_id, bool $force = false ): string {
		$term = get_term( $term_id );
		if ( ! $term instanceof \WP_Term || ! $this->languages->translates_taxonomy( $term->taxonomy ) || Languages::SOURCE !== $this->languages->of_term( $term_id ) ) {
			return '';
		}
		$twin = $this->german_term( $term_id );
		return $this->run(
			State::TERM,
			$term_id,
			$this->fields->of_term( $term ),
			$twin,
			fn( array $values ): int => $this->twins->term( $term_id, $values ),
			$force
		);
	}

	/**
	 * Stores German values made elsewhere (the migration of the old
	 * plugin's German, an import) as the German version, and records them
	 * as the machine's baseline: later English edits update them segment by
	 * segment. Fields with English text and no German are left to the
	 * translator, and the object is pending.
	 *
	 * @param string                $kind      State::POST or State::TERM.
	 * @param int                   $source_id English object ID.
	 * @param array<string, string> $german    German values by field.
	 * @param string|null           $slug      Slug for a new German object.
	 * @return string The status afterwards.
	 */
	public function adopt( string $kind, int $source_id, array $german, ?string $slug = null ): string {
		$source = State::POST === $kind ? get_post( $source_id ) : get_term( $source_id );
		if ( $source instanceof \WP_Post ) {
			$fields = $this->fields->of_post( $source );
		} elseif ( $source instanceof \WP_Term ) {
			$fields = $this->fields->of_term( $source );
		} else {
			return '';
		}
		$missing = array();
		$values  = array();
		foreach ( $fields as $field => list( $value, $html ) ) {
			$english = $this->planner->split( $value, $html );
			if ( isset( $german[ $field ] ) && '' !== trim( $german[ $field ] ) ) {
				$values[ $field ] = $german[ $field ];
			} elseif ( array() === $english->segments ) {
				$values[ $field ] = $value;
			} else {
				$values[ $field ] = '';
				$missing[]        = $field;
			}
		}
		$twin = State::POST === $kind ? $this->twins->post( $source_id, $values, $slug ) : $this->twins->term( $source_id, $values, $slug );
		$this->record( $kind, $twin, $fields, array(), array(), $missing );
		$status = array() === $missing ? State::SYNCED : State::PENDING;
		$this->state->set_status( $kind, $source_id, $status, array() === $missing ? '' : 'no German for ' . implode( ', ', $missing ) );
		return $status;
	}

	/**
	 * Takes in what a person changed in a German object: the changed segments
	 * become reviewed and are never overwritten. When the object waited for a
	 * review, the person's German is accepted for the English as it is now
	 * and the object is queued again.
	 *
	 * @param string $kind State::POST or State::TERM.
	 * @param int    $twin German object ID.
	 * @return bool Whether the object waited for a review and was accepted.
	 */
	public function record_edit( string $kind, int $twin ): bool {
		$source_id = State::POST === $kind ? $this->languages->post_translation( $twin, Languages::SOURCE ) : $this->languages->term_translation( $twin, Languages::SOURCE );
		if ( null === $source_id ) {
			return false;
		}
		$source = State::POST === $kind ? get_post( $source_id ) : get_term( $source_id );
		$german = State::POST === $kind ? get_post( $twin ) : get_term( $twin );
		if ( $source instanceof \WP_Post && $german instanceof \WP_Post ) {
			$english_fields = $this->fields->of_post( $source );
			$german_fields  = $this->fields->of_post( $german );
		} elseif ( $source instanceof \WP_Term && $german instanceof \WP_Term ) {
			$english_fields = $this->fields->of_term( $source );
			$german_fields  = $this->fields->of_term( $german );
		} else {
			return false;
		}
		$units    = $this->state->units( $kind, $twin );
		$reviewed = $this->state->reviewed( $kind, $twin );
		$accepted = State::NEEDS_REVIEW === $this->state->status( $kind, $source_id );
		foreach ( $units as $field => $unit ) {
			$current                = $this->planner->split( $german_fields[ $field ][0] ?? '', $german_fields[ $field ][1] ?? true );
			$reviewed[ $field ]     = $this->planner->absorb( $unit['out'], $current, $reviewed[ $field ] ?? array() );
			$units[ $field ]['out'] = $current->hashes();
			if ( $accepted && $unit['conflict'] && isset( $english_fields[ $field ] ) ) {
				$units[ $field ]['src']      = $this->planner->split( $english_fields[ $field ][0], $english_fields[ $field ][1] )->hashes();
				$units[ $field ]['conflict'] = false;
			}
		}
		$this->state->save( $kind, $twin, $this->state->source_hash( $kind, $twin ), $units, $reviewed );
		return $accepted;
	}

	/**
	 * Whether the German version was made from the English as it is now.
	 *
	 * @param string $kind      State::POST or State::TERM.
	 * @param int    $source_id English object ID.
	 */
	public function current( string $kind, int $source_id ): bool {
		$twin   = State::POST === $kind ? $this->german_post( $source_id ) : $this->german_term( $source_id );
		$source = State::POST === $kind ? get_post( $source_id ) : get_term( $source_id );
		if ( null === $twin || ! ( $source instanceof \WP_Post || $source instanceof \WP_Term ) ) {
			return false;
		}
		$fields = $source instanceof \WP_Post ? $this->fields->of_post( $source ) : $this->fields->of_term( $source );
		return $this->state->source_hash( $kind, $twin ) === self::fingerprint( $fields );
	}

	/**
	 * One run for an object.
	 *
	 * @param string                             $kind      State::POST or State::TERM.
	 * @param int                                $source_id English object ID.
	 * @param array<string, array{string, bool}> $source    English fields.
	 * @param int|null                           $twin      German object ID, null when there is none.
	 * @param callable                           $write     Writes the German values and returns the German object ID.
	 * @param bool                               $force     Translate every segment again.
	 * @return string The status afterwards.
	 * @throws TranslationFailed When a translation is missing or fails its checks.
	 *
	 * @phpstan-param callable(array<string, string>): int $write
	 */
	private function run( string $kind, int $source_id, array $source, ?int $twin, callable $write, bool $force = false ): string {
		$fingerprint = self::fingerprint( $source );
		$units       = null === $twin || $force ? array() : $this->state->units( $kind, $twin );
		$reviewed    = null === $twin || $force ? array() : $this->state->reviewed( $kind, $twin );
		if ( ! $force && null !== $twin && $this->state->source_hash( $kind, $twin ) === $fingerprint ) {
			$status = array() === array_filter( $units, static fn( array $unit ): bool => $unit['conflict'] ) ? State::SYNCED : State::NEEDS_REVIEW;
			$this->state->set_status( $kind, $source_id, $status );
			return $status;
		}

		$current = $this->german_fields( $kind, $twin );
		$plans   = array();
		foreach ( $source as $field => list( $value, $html ) ) {
			$plans[ $field ] = $this->planner->plan( $value, $html, $current[ $field ] ?? null, $units[ $field ] ?? null, $reviewed[ $field ] ?? array(), $force );
		}
		$translations = $this->translate( $plans );

		$values = array();
		foreach ( $plans as $field => $plan ) {
			$values[ $field ] = $plan->render( $translations[ $field ] ?? array() );
		}
		foreach ( array_keys( $current ) as $field ) {
			if ( ! isset( $values[ $field ] ) ) {
				$values[ $field ] = '';
			}
		}
		$twin = $write( $values );

		$this->record( $kind, $twin, $source, array_map( static fn( FieldPlan $plan ): array|string => $plan->reviewed, $plans ), $plans );
		$conflicts = array_keys( array_filter( $plans, static fn( FieldPlan $plan ): bool => $plan->conflict ) );
		$status    = array() === $conflicts ? State::SYNCED : State::NEEDS_REVIEW;
		$this->state->set_status( $kind, $source_id, $status, array() === $conflicts ? '' : 'English changed where the German was edited: ' . implode( ', ', $conflicts ) );
		return $status;
	}

	/**
	 * Translates the missing segments of all fields, in batches, each checked;
	 * a rejected segment gets one more try with the reasons.
	 *
	 * @param array<string, FieldPlan> $plans Plans by field.
	 * @return array<string, array<int, string>> Field => segment index => German.
	 * @throws TranslationFailed When a segment has no acceptable translation.
	 */
	private function translate( array $plans ): array {
		$wanted = array();
		foreach ( $plans as $field => $plan ) {
			foreach ( $plan->missing() as $index ) {
				$segment                    = $plan->english->segments[ $index ];
				$wanted[ $segment->text ][] = array( $field, $index, $segment );
			}
		}
		if ( array() === $wanted ) {
			return array();
		}
		if ( ! $this->client->available() ) {
			throw new TranslationFailed( 'DEEPSEEK_API_KEY is not set', false );
		}
		$german = array();
		$retry  = array();
		foreach ( $this->batches( array_keys( $wanted ) ) as $batch ) {
			foreach ( $this->client->translate( $batch ) as $position => $translation ) {
				$text     = $batch[ $position ];
				$problems = $this->validator->problems( $wanted[ $text ][0][2], $translation );
				if ( array() === $problems ) {
					$german[ $text ] = $translation;
				} else {
					$retry[ $text ] = implode( '; ', $problems );
				}
			}
		}
		foreach ( $retry as $text => $problems ) {
			$translation = $this->client->translate( array( (string) $text ), $problems )[0];
			$left        = $this->validator->problems( $wanted[ $text ][0][2], $translation );
			if ( array() !== $left ) {
				throw new TranslationFailed( esc_html( sprintf( 'translation rejected (%s): %s', implode( '; ', $left ), mb_substr( (string) $text, 0, 80 ) ) ), false );
			}
			$german[ $text ] = $translation;
		}
		$out = array();
		foreach ( $wanted as $text => $uses ) {
			foreach ( $uses as list( $field, $index ) ) {
				$out[ $field ][ $index ] = $german[ $text ];
			}
		}
		return $out;
	}

	/**
	 * Splits texts into request-sized batches.
	 *
	 * @param array<int, string> $texts Texts.
	 * @return list<list<string>>
	 */
	private function batches( array $texts ): array {
		$batches = array();
		$batch   = array();
		$size    = 0;
		foreach ( $texts as $text ) {
			if ( array() !== $batch && ( count( $batch ) >= self::BATCH_SEGMENTS || $size + strlen( $text ) > self::BATCH_CHARACTERS ) ) {
				$batches[] = $batch;
				$batch     = array();
				$size      = 0;
			}
			$batch[] = (string) $text;
			$size   += strlen( $text );
		}
		$batches[] = $batch;
		return $batches;
	}

	/**
	 * Stores the state of a German object after a write: per field the
	 * fingerprints of the English segments its German was made from and of
	 * the German as stored, and whether German a person edited waits for a
	 * review; and the fingerprint of the English when no field is missing.
	 *
	 * @param string                                $kind     State::POST or State::TERM.
	 * @param int                                   $twin     German object ID.
	 * @param array<string, array{string, bool}>    $source   English fields.
	 * @param array<string, array<int, int>|string> $reviewed Edited segments by field.
	 * @param array<string, FieldPlan>              $plans    This run's plans by field; none for German made elsewhere.
	 * @param array<int, string>                    $missing  Fields left without German.
	 */
	private function record( string $kind, int $twin, array $source, array $reviewed, array $plans, array $missing = array() ): void {
		$stored = $this->german_fields( $kind, $twin );
		$units  = array();
		foreach ( $source as $field => list( $value, $html ) ) {
			if ( in_array( $field, $missing, true ) ) {
				continue;
			}
			$plan            = $plans[ $field ] ?? null;
			$units[ $field ] = $plan->unit ?? array(
				// Held segments keep the English their German was made from.
				'src'      => array_values( array_replace( $this->planner->split( $value, $html )->hashes(), $plan->held ?? array() ) ),
				'out'      => $this->planner->split( $stored[ $field ][0] ?? '', $html )->hashes(),
				'conflict' => null !== $plan && $plan->conflict,
			);
		}
		$this->state->save( $kind, $twin, array() === $missing ? self::fingerprint( $source ) : '', $units, $reviewed );
	}

	/**
	 * The fields of a German object.
	 *
	 * @param string   $kind State::POST or State::TERM.
	 * @param int|null $twin German object ID.
	 * @return array<string, array{string, bool}>
	 */
	private function german_fields( string $kind, ?int $twin ): array {
		if ( null === $twin ) {
			return array();
		}
		$object = State::POST === $kind ? get_post( $twin ) : get_term( $twin );
		if ( $object instanceof \WP_Post ) {
			return $this->fields->of_post( $object );
		}
		return $object instanceof \WP_Term ? $this->fields->of_term( $object ) : array();
	}

	/**
	 * The German post of an English post.
	 *
	 * @param int $source_id English post ID.
	 */
	private function german_post( int $source_id ): ?int {
		return $this->languages->post_translation( $source_id, Languages::TARGET );
	}

	/**
	 * The German term of an English term.
	 *
	 * @param int $term_id English term ID.
	 */
	private function german_term( int $term_id ): ?int {
		return $this->languages->term_translation( $term_id, Languages::TARGET );
	}

	/**
	 * A fingerprint of an object's English fields.
	 *
	 * @param array<string, array{string, bool}> $fields Fields.
	 */
	private static function fingerprint( array $fields ): string {
		$parts = array();
		foreach ( $fields as $field => list( $value ) ) {
			$parts[] = $field . "\0" . $value;
		}
		return sha1( implode( "\1", $parts ) );
	}
}
