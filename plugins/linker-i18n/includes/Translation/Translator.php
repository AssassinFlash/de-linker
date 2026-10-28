<?php
/**
 * Makes and keeps the German version of an English object.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Twins;

/**
 * Brings the German version of an English post or term up to date.
 *
 * Segment by segment: what did not change in the English keeps its German,
 * what changed goes to the translator, and every translation is checked
 * before anything is stored. Existing German without a baseline is adopted as-is. Unalignable changes
 * preserve it with a visible exception (owner ruling in PR #277). Nothing is
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
	 * @param Languages     $languages The site's languages.
	 * @param Planner       $planner   Plans each field from the English and the German.
	 * @param Fields        $fields    The translatable fields.
	 * @param State         $state     Translation state.
	 * @param Client        $client    The machine translator.
	 * @param Validator     $validator Checks translations.
	 * @param Twins         $twins     Writes German objects.
	 * @param LinkLocalizer $links Localises newly translated fragments only.
	 */
	public function __construct(
		private readonly Languages $languages,
		private readonly Planner $planner,
		private readonly Fields $fields,
		private readonly State $state,
		private readonly Client $client,
		private readonly Validator $validator,
		private readonly Twins $twins,
		private readonly LinkLocalizer $links
	) {}

	/**
	 * Brings the German version of an English post up to date.
	 *
	 * @param int  $source_id English post ID.
	 * @param bool $force     Legacy argument; existing German is always preserved.
	 * @return string The status afterwards; empty when the post is not an English translated post.
	 * @throws TranslationFailed When a translation is missing or fails its checks; nothing was stored.
	 */
	public function post( int $source_id, bool $force = false ): string {
		$source = get_post( $source_id );
		if ( ! $source instanceof \WP_Post || ! $this->accepts( State::POST, $source_id ) ) {
			return '';
		}
		$twin = $this->german_post( $source_id );
		return $this->run(
			State::POST,
			$source_id,
			$this->fields->of_post( $source ),
			$twin,
			function ( array $values, array $changed ) use ( $source_id, $twin ): int {
				if ( null !== $twin && array( Fields::META . Fields::COVER_ALT ) === array_keys( $changed ) ) {
					return $this->twins->translated_post_meta( $twin, $changed );
				}
				return $this->twins->post( $source_id, $values, null, false );
			},
			$force
		);
	}

	/**
	 * The shared guard for saves, explicit commands and previously queued jobs.
	 *
	 * @param string $kind State::POST or State::TERM.
	 * @param int    $id English object ID.
	 */
	public function accepts( string $kind, int $id ): bool {
		if ( State::POST === $kind ) {
			$post = get_post( $id );
			return $post instanceof \WP_Post && $this->languages->automatically_translates_post_type( $post->post_type ) && Languages::SOURCE === $this->languages->of_post( $id );
		}
		if ( State::TERM === $kind ) {
			$term = get_term( $id );
			return $term instanceof \WP_Term && $this->languages->translates_taxonomy( $term->taxonomy ) && Languages::SOURCE === $this->languages->of_term( $id );
		}
		return false;
	}

	/**
	 * Captures the old English before its first edit when German has no baseline.
	 * This writes metadata only, so the first saved change can translate by sentence.
	 *
	 * @param string $kind State::POST or State::TERM.
	 * @param int    $id English object ID.
	 */
	public function prime( string $kind, int $id ): void {
		if ( ! $this->accepts( $kind, $id ) ) {
			return;
		}
		$twin = State::POST === $kind ? $this->german_post( $id ) : $this->german_term( $id );
		if ( null === $twin || array() !== $this->state->units( $kind, $twin ) ) {
			return;
		}
		$source = State::POST === $kind ? get_post( $id ) : get_term( $id );
		if ( $source instanceof \WP_Post || $source instanceof \WP_Term ) {
			$this->record( $kind, $twin, $source instanceof \WP_Post ? $this->fields->of_post( $source ) : $this->fields->of_term( $source ) );
		}
	}

	/**
	 * Brings the German version of an English term up to date.
	 *
	 * @param int  $term_id English term ID.
	 * @param bool $force   Legacy argument; existing German is always preserved.
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
			fn( array $values ): int => $this->twins->term( $term_id, $values, null, false ),
			$force
		);
	}

	/**
	 * Records the German already in place as the machine's baseline, without
	 * rewriting it (ticket #264: reviewed German copy is written by the
	 * German-copy migration, then adopted here). Fields whose English carries
	 * text but whose German is empty stay out of the baseline and the object
	 * is pending, so the next translation run fills only those fields.
	 *
	 * @param string $kind      State::POST or State::TERM.
	 * @param int    $source_id English object ID.
	 * @return string The status afterwards; empty when the object is not an English translated object.
	 */
	public function adopt_current( string $kind, int $source_id ): string {
		$source = State::POST === $kind ? get_post( $source_id ) : get_term( $source_id );
		if ( $source instanceof \WP_Post ) {
			$fields = $this->fields->of_post( $source );
			$twin   = $this->german_post( $source_id );
		} elseif ( $source instanceof \WP_Term ) {
			$fields = $this->fields->of_term( $source );
			$twin   = $this->german_term( $source_id );
		} else {
			return '';
		}
		if ( null === $twin ) {
			return '';
		}
		$german  = $this->german_fields( $kind, $twin );
		$missing = array();
		foreach ( $fields as $field => list( $value, $html ) ) {
			if ( array() !== $this->planner->split( $value, $html )->segments && '' === trim( $german[ $field ][0] ?? '' ) ) {
				$missing[] = $field;
			}
		}
		$this->record( $kind, $twin, $fields, $missing );
		$status = array() === $missing ? State::SYNCED : State::PENDING;
		$this->state->set_status( $kind, $source_id, $status, array() === $missing ? '' : 'no German for ' . implode( ', ', $missing ) );
		return $status;
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
		$this->record( $kind, $twin, $fields, $missing );
		$status = array() === $missing ? State::SYNCED : State::PENDING;
		$this->state->set_status( $kind, $source_id, $status, array() === $missing ? '' : 'no German for ' . implode( ', ', $missing ) );
		return $status;
	}

	/**
	 * Whether the German version was made from the English as it is now.
	 *
	 * @param string $kind      State::POST or State::TERM.
	 * @param int    $source_id English object ID.
	 */
	public function current( string $kind, int $source_id ): bool {
		// Another PHP request can invalidate Redis while this worker retains an
		// old object in its runtime cache. Re-read the source before claiming sync.
		if ( State::POST === $kind ) {
			clean_post_cache( $source_id );
			$post = get_post( $source_id );
			if ( $post instanceof \WP_Post && 'post' === $post->post_type ) {
				$image = (int) get_post_thumbnail_id( $source_id );
				if ( $image ) {
					clean_post_cache( $image );
				}
			}
		} else {
			$term = get_term( $source_id );
			if ( $term instanceof \WP_Term ) {
				// Without the taxonomy WordPress treats these as term_taxonomy_ids.
				clean_term_cache( $source_id, $term->taxonomy );
			}
		}
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
	 * @param bool                               $force     Legacy argument; cannot discard existing German.
	 * @return string The status afterwards.
	 * @throws TranslationFailed When a translation is missing or fails its checks.
	 *
	 * @phpstan-param callable(array<string, string>, array<string, string>): int $write
	 */
	private function run( string $kind, int $source_id, array $source, ?int $twin, callable $write, bool $force = false ): string {
		// Legacy forced actions must obey the owner's German-preservation ruling.
		unset( $force );
		$fingerprint = self::fingerprint( $source );
		$units       = null === $twin ? array() : $this->state->units( $kind, $twin );
		if ( null !== $twin && ( array() === $units || $this->state->source_hash( $kind, $twin ) === $fingerprint ) ) {
			// Refresh old paragraph-level fingerprints without rewriting German.
			$this->record( $kind, $twin, $source );
			$status = State::SYNCED;
			$this->state->set_status( $kind, $source_id, $status );
			return $status;
		}

		$current = $this->german_fields( $kind, $twin );
		$plans   = array();
		foreach ( $source as $field => list( $value, $html ) ) {
			$unit = $units[ $field ] ?? null;
			if ( Fields::META . Fields::COVER_ALT === $field ) {
				$english = $this->planner->split( $value, false );
				$german  = $current[ $field ][0] ?? '';
				$changed = isset( $unit['src_raw'] ) && ! hash_equals( $unit['src_raw'], hash( 'sha256', $value ) );
				if ( '' === trim( $value ) || ( array() === $english->segments && ( $changed || ( ! isset( $unit['src_raw'] ) && '' === trim( $german ) ) ) ) ) {
					$plans[ $field ] = FieldPlan::keep( $english, $value );
					continue;
				}
				// Sentence hashes omit pure model/number-only pieces. Do not
				// certify a translation if such a piece changed inside prose.
				if ( array() !== $english->segments && isset( $unit['src_literals'] ) && ! hash_equals( $unit['src_literals'], $this->planner->literal_hash( $english ) ) ) {
					$plans[ $field ] = FieldPlan::blocked( $english, $german );
					continue;
				}
			}
			$plans[ $field ] = $this->planner->plan( $value, $html, $current[ $field ] ?? null, $unit, false );
		}
		if ( array() !== array_filter( $plans, static fn( FieldPlan $plan ): bool => $plan->mismatch ) ) {
			$this->state->set_status( $kind, $source_id, State::STRUCTURE_MISMATCH, State::structure_reason() );
			return State::STRUCTURE_MISMATCH;
		}
		$translations = $this->translate( $plans );

		$values = array();
		foreach ( $plans as $field => $plan ) {
			$values[ $field ] = $plan->render( $translations[ $field ] ?? array(), $source[ $field ][1] ? $this->links->localize( ... ) : null );
		}
		foreach ( array_keys( $current ) as $field ) {
			if ( ! isset( $values[ $field ] ) ) {
				$values[ $field ] = $current[ $field ][0];
			}
		}
		// Baseline adoption must not pass preserved markup through a content writer.
		$before   = array_map( static fn( array $field ): string => $field[0], $current );
		$changed  = array_diff_assoc( $values, $before );
		$changed += array_fill_keys( array_keys( array_diff_key( $before, $values ) ), '' );
		if ( null === $twin || array() !== $changed ) {
			$twin = $write( $values, $changed );
		}

		$this->record( $kind, $twin, $source, array(), $values );
		$status = State::SYNCED;
		$this->state->set_status( $kind, $source_id, $status );
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
	 * Records the English and German segment fingerprints after a successful write.
	 *
	 * @param string                             $kind State::POST or State::TERM.
	 * @param int                                $twin German object ID.
	 * @param array<string, array{string, bool}> $source English fields.
	 * @param array<int, string>                 $missing Fields left without German during import.
	 * @param array<string, string>|null         $expected Values produced by this run, before concurrent writes.
	 */
	private function record( string $kind, int $twin, array $source, array $missing = array(), ?array $expected = null ): void {
		$stored = $this->german_fields( $kind, $twin );
		$units  = array();
		foreach ( $source as $field => list( $value, $html ) ) {
			if ( in_array( $field, $missing, true ) ) {
				continue;
			}
			$units[ $field ] = array(
				'src'      => $this->planner->split( $value, $html )->hashes(),
				'out'      => $this->planner->split( $stored[ $field ][0] ?? '', $html )->hashes(),
				'conflict' => false,
			);
			if ( Fields::META . Fields::COVER_ALT === $field ) {
				$units[ $field ]['src_raw']      = hash( 'sha256', $value );
				$units[ $field ]['out_raw']      = hash( 'sha256', $expected[ $field ] ?? $stored[ $field ][0] ?? '' );
				$units[ $field ]['src_literals'] = $this->planner->literal_hash( $this->planner->split( $value, false ) );
			}
		}
		$this->state->save( $kind, $twin, array() === $missing ? self::fingerprint( $source ) : '', $units );
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
			return $this->fields->of_post( $object, true );
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
