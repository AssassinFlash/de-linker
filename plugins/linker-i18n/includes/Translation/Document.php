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
	private const CONTAINERS = array( 'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'span', 'strong', 'em', 'b', 'i', 'small', 'u', 's', 'mark', 'q' );

	private const BLOCKS = array( 'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6' );

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
	 * Shared attribute/text owners and unbalanced markup cannot be spliced.
	 * Wrappers and separators move with the sentence, never layout or media.
	 *
	 * @param int  $start First segment.
	 * @param int  $end After the last segment.
	 * @param bool $blocks Include a complete paragraph/list item/heading.
	 * @param bool $space Include one adjacent whitespace separator.
	 * @return array{int, int, bool}|null Part bounds and whether they include a block.
	 */
	public function span( int $start, int $end, bool $blocks = true, bool $space = true ): ?array {
		$positions = array();
		foreach ( $this->parts as $position => $part ) {
			$owners = $part instanceof TagPart ? array_values( $part->attributes ) : array();
			if ( is_int( $part ) ) {
				$owners[] = $part;
				foreach ( $this->segments[ $part ]->map as $tag ) {
					if ( $tag instanceof TagPart ) {
						array_push( $owners, ...array_values( $tag->attributes ) );
					}
				}
			}
			$selected = array_filter( $owners, static fn( int $index ): bool => $index >= $start && $index < $end );
			if ( array() !== $selected ) {
				if ( count( $selected ) !== count( $owners ) ) {
					return null;
				}
				$positions[] = $position;
			}
		}
		if ( array() === $positions ) {
			return null;
		}
		$first      = min( $positions );
		$last       = max( $positions ) + 1;
		$block      = false;
		$part_count = count( $this->parts );
		while ( true ) {
			$left  = $first;
			$right = $last;
			while ( $left > 0 && $this->whitespace( $left - 1 ) ) {
				--$left;
			}
			while ( $right < $part_count && $this->whitespace( $right ) ) {
				++$right;
			}
			$open  = $this->parts[ $left - 1 ] ?? null;
			$close = $this->parts[ $right ] ?? null;
			if ( ! is_string( $open ) || ! is_string( $close ) || 1 !== preg_match( '/^<([a-z0-9]+)(?:\s[^<>]*)?>$/i', $open, $match ) ) {
				break;
			}
			$name     = strtolower( $match[1] );
			$is_block = in_array( $name, self::BLOCKS, true );
			if ( ! in_array( $name, self::CONTAINERS, true ) || ( $is_block && ! $blocks ) || 1 !== preg_match( '/^<\/' . $name . '\s*>$/i', $close ) ) {
				break;
			}
			$first = $left - 1;
			$last  = $right + 1;
			$block = $block || $is_block;
		}
		if ( $space ) {
			if ( $this->whitespace( $last ) ) {
				++$last;
			} elseif ( $first > 0 && $this->whitespace( $first - 1 ) ) {
				--$first;
			}
		}
		// A sentence inside a shared wrapper is balanced; a range crossing
		// separate containers or owning only an opening attribute tag is not.
		$stack = array();
		foreach ( ( new HtmlTokenizer() )->tokens( $this->slice( $first, $last )->render( array() ) ) as $token ) {
			if ( HtmlToken::TAG !== $token->type || in_array( $token->name, array( 'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr' ), true ) || str_ends_with( $token->raw, '/>' ) ) {
				continue;
			}
			if ( $token->closing ) {
				if ( array_pop( $stack ) !== $token->name ) {
					return null;
				}
			} else {
				$stack[] = $token->name;
			}
		}
		return array() === $stack ? array( $first, $last, $block ) : null;
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
	 * An insertion point beside an unchanged sentence, inside or outside its block.
	 *
	 * @param int  $index Anchor segment.
	 * @param bool $after Insert after the anchor.
	 * @param bool $block Insert a complete block.
	 */
	public function boundary( int $index, bool $after, bool $block ): ?int {
		$span = $this->span( $index, $index + 1, false, false );
		if ( null === $span ) {
			return null;
		}
		$position = $after ? $span[1] : $span[0];
		if ( ! $block ) {
			return $position;
		}
		while ( $this->whitespace( $after ? $position : $position - 1 ) ) {
			$position += $after ? 1 : -1;
		}
		$part    = $this->parts[ $after ? $position : $position - 1 ] ?? null;
		$pattern = $after ? '/^<\/([a-z0-9]+)\s*>$/i' : '/^<([a-z0-9]+)(?:\s[^<>]*)?>$/i';
		if ( ! is_string( $part ) || 1 !== preg_match( $pattern, $part, $match ) || ! in_array( strtolower( $match[1] ), self::BLOCKS, true ) ) {
			return null;
		}
		return $after ? $position + 1 : $position - 1;
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
