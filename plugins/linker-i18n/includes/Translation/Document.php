<?php
/**
 * A value split into what the translator sees and what it does not.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * A title, a description or an HTML body as a sequence of parts: markup kept
 * byte for byte, segments to translate, and tags with translatable
 * attributes. Printing it with no translations gives the value back.
 */
final class Document {

	/** Sentence containers can move with a sentence; layout containers stay put. */
	private const CONTAINERS = array( 'p', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'abbr', 'b', 'bdi', 'bdo', 'cite', 'data', 'del', 'dfn', 'em', 'font', 'i', 'ins', 'label', 'mark', 'q', 's', 'small', 'span', 'strong', 'sub', 'sup', 'time', 'u' );

	private const BLOCKS = array( 'p', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6' );

	/** HTML Living Standard void elements do not open a container. */
	private const VOID_TAGS = array( 'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr' );

	/**
	 * Sets up the document.
	 *
	 * @param array<int, string|int|TagPart> $parts    Markup to keep (string), a segment (its index) or a tag with segment attributes.
	 * @param array<int, Segment>            $segments The segments, in reading order.
	 *
	 * @phpstan-param list<Segment> $segments
	 */
	public function __construct( public readonly array $parts, public readonly array $segments ) {}

	/**
	 * The segments' fingerprints, in order.
	 *
	 * @return list<string>
	 */
	public function hashes(): array {
		return array_map( static fn( Segment $segment ): string => $segment->hash(), $this->segments );
	}

	/**
	 * Text and attribute slots must align before an incremental replacement.
	 *
	 * @return list<string>
	 */
	public function segment_roles(): array {
		$roles = array_fill( 0, count( $this->segments ), 'text' );
		$parts = $this->parts;
		foreach ( $this->segments as $segment ) {
			array_push( $parts, ...array_values( $segment->map ) );
		}
		foreach ( $parts as $part ) {
			if ( $part instanceof TagPart ) {
				foreach ( $part->attributes as $attribute => $index ) {
					$roles[ $index ] = 'attribute:' . $attribute;
				}
			}
		}
		return array_values( $roles );
	}

	/**
	 * The value with segments replaced by translations; a segment without a
	 * translation keeps its own bytes.
	 *
	 * @param array<int, string> $translations Segment index => translated text (with placeholders).
	 * @param array<int, string> $verbatim     Segment index => bytes to print as they are.
	 */
	public function render( array $translations, array $verbatim = array() ): string {
		return implode( '', $this->render_parts( $translations, $verbatim ) );
	}

	/**
	 * Renders without losing the original part coordinates used by splices.
	 *
	 * @param array<int, string> $translations Translations.
	 * @param array<int, string> $verbatim Exact replacements.
	 * @return list<string>
	 */
	public function render_parts( array $translations, array $verbatim = array() ): array {
		$out = array();
		foreach ( $this->parts as $part ) {
			if ( is_int( $part ) ) {
				$segment = $this->segments[ $part ];
				if ( isset( $verbatim[ $part ] ) ) {
					$out[] = $verbatim[ $part ];
				} else {
					$out[] = isset( $translations[ $part ] ) ? $segment->render( $translations[ $part ], $translations ) : $segment->raw;
				}
			} elseif ( $part instanceof TagPart ) {
				$out[] = $part->render( $translations, $verbatim );
			} else {
				$out[] = $part;
			}
		}
		return $out;
	}

	/**
	 * A separable sentence range, in part coordinates (end exclusive).
	 * Layout and media do not belong to sentence edits.
	 *
	 * @param int  $start First segment.
	 * @param int  $end After last segment.
	 * @param bool $blocks Include complete sentence containers.
	 * @param bool $space Include one whitespace separator.
	 * @return array{start: int, end: int, block: bool}|null
	 */
	public function span( int $start, int $end, bool $blocks = true, bool $space = true ): ?array {
		$owners    = $this->owners();
		$positions = array();
		foreach ( $owners as $position => $indexes ) {
			$selected = array_filter( $indexes, static fn( int $index ): bool => $index >= $start && $index < $end );
			if ( array() !== $selected ) {
				if ( count( $selected ) !== count( $indexes ) ) {
					return null;
				}
				$positions[] = $position;
			}
		}
		if ( array() === $positions ) {
			return null;
		}
		$first = min( $positions );
		$last  = max( $positions ) + 1;
		$block = false;
		foreach ( $this->frames() as $frame ) {
			$is_block = in_array( $frame['name'], self::BLOCKS, true );
			if ( ! in_array( $frame['name'], self::CONTAINERS, true ) || ( $is_block && ! $blocks ) || $frame['end'] <= $first || $frame['start'] >= $last ) {
				continue;
			}
			$outside = false;
			for ( $part = $frame['start']; $part < $frame['end']; $part++ ) {
				foreach ( $owners[ $part ] as $index ) {
					$outside = $outside || $index < $start || $index >= $end;
				}
			}
			if ( ! $outside ) {
				$first = min( $first, $frame['start'] );
				$last  = max( $last, $frame['end'] );
				$block = $block || $is_block;
			}
		}
		if ( $space ) {
			if ( $this->whitespace( $last ) ) {
				++$last;
			} elseif ( $first > 0 && $this->whitespace( $first - 1 ) ) {
				--$first;
			}
		}
		$stack = array();
		foreach ( ( new HtmlTokenizer() )->tokens( $this->slice( $first, $last )->render( array() ) ) as $token ) {
			if ( HtmlToken::TEXT === $token->type ) {
				continue;
			}
			// Never remove an intervening image, script, comment or layout container.
			if ( HtmlToken::TAG !== $token->type || ! in_array( $token->name, self::CONTAINERS, true ) ) {
				return null;
			}
			if ( $token->closing ) {
				if ( array_pop( $stack ) !== $token->name ) {
					return null;
				}
			} else {
				$stack[] = $token->name;
			}
		}
		return array() === $stack ? array(
			'start' => $first,
			'end'   => $last,
			'block' => $block,
		) : null;
	}

	/**
	 * Deletions split around media and layout that must survive the edit.
	 *
	 * @param int $start First deleted segment.
	 * @param int $end After last deleted segment.
	 * @return list<array{start: int, end: int, source: Document|null}>|null
	 */
	public function deletions( int $start, int $end ): ?array {
		$ranges = array();
		while ( $start < $end ) {
			$span = null;
			for ( $next = $end; $next > $start; --$next ) {
				$span = $this->span( $start, $next );
				if ( null !== $span ) {
					break;
				}
			}
			if ( null === $span ) {
				return null;
			}
			$ranges[] = array(
				'start'  => $span['start'],
				'end'    => $span['end'],
				'source' => null,
			);
			$start    = $next;
		}
		return $ranges;
	}

	/**
	 * A fragment retaining global segment indexes.
	 *
	 * @param int $start First part.
	 * @param int $end After last part.
	 */
	public function slice( int $start, int $end ): self {
		return new self( array_slice( $this->parts, $start, $end - $start ), $this->segments );
	}

	/**
	 * An insertion point beside an unchanged sentence or its block container.
	 *
	 * @param int  $index Anchor segment.
	 * @param bool $after Insert after it.
	 * @param bool $block Insert a complete block.
	 */
	public function boundary( int $index, bool $after, bool $block ): ?int {
		if ( ! $block ) {
			$span = $this->span( $index, $index + 1, false, false );
			return null === $span ? null : $span[ $after ? 'end' : 'start' ];
		}
		$owners = $this->owners();
		foreach ( $this->frames() as $frame ) {
			if ( ! in_array( $frame['name'], self::BLOCKS, true ) ) {
				continue;
			}
			$indexes = array();
			for ( $part = $frame['start']; $part < $frame['end']; ++$part ) {
				array_push( $indexes, ...$owners[ $part ] );
			}
			if ( array() !== $indexes && ( $after ? max( $indexes ) : min( $indexes ) ) === $index ) {
				return $frame[ $after ? 'end' : 'start' ];
			}
		}
		return null;
	}

	/**
	 * Parent elements at a part boundary, to keep inserted lists/phrasing valid.
	 *
	 * @param int $position Part boundary.
	 * @return list<string>
	 */
	public function context( int $position ): array {
		return array_values( array_map( static fn( array $frame ): string => $frame['name'], array_filter( $this->frames(), static fn( array $frame ): bool => $frame['start'] < $position && $frame['end'] > $position ) ) );
	}

	/**
	 * Part ownership includes attributes nested inside a sentence placeholder.
	 *
	 * @return array<int, list<int>>
	 */
	private function owners(): array {
		$owners = array();
		foreach ( $this->parts as $position => $part ) {
			$indexes = $part instanceof TagPart ? array_values( $part->attributes ) : array();
			if ( is_int( $part ) ) {
				$indexes[] = $part;
				foreach ( $this->segments[ $part ]->map as $tag ) {
					if ( $tag instanceof TagPart ) {
						array_push( $indexes, ...array_values( $tag->attributes ) );
					}
				}
			}
			$owners[ $position ] = $indexes;
		}
		return $owners;
	}

	/**
	 * Balanced containers in original part coordinates, inner containers first.
	 *
	 * @return list<array{start: int, end: int, name: string}>
	 */
	private function frames(): array {
		$frames = array();
		$stack  = array();
		foreach ( $this->parts as $position => $part ) {
			$raw = $part instanceof TagPart ? $part->tag->raw : $part;
			if ( ! is_string( $raw ) ) {
				continue;
			}
			foreach ( ( new HtmlTokenizer() )->tokens( $raw ) as $token ) {
				if ( HtmlToken::TAG !== $token->type || in_array( $token->name, self::VOID_TAGS, true ) || str_ends_with( $token->raw, '/>' ) ) {
					continue;
				}
				if ( $token->closing ) {
					$open = array_pop( $stack );
					if ( null !== $open && $open['name'] === $token->name ) {
						$frames[] = array(
							'start' => $open['start'],
							'end'   => $position + 1,
							'name'  => $token->name,
						);
					}
				} else {
					$stack[] = array(
						'start' => $position,
						'name'  => $token->name,
					);
				}
			}
		}
		return $frames;
	}

	/**
	 * Whether a part is a sentence separator.
	 *
	 * @param int $index Part index.
	 */
	private function whitespace( int $index ): bool {
		$part = $this->parts[ $index ] ?? null;
		return is_string( $part ) && '' === trim( $part );
	}
}
