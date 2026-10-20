<?php
/**
 * Splits titles and bodies into segments for the translator.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Turns a value into a {@see Document}.
 *
 * A segment is the text between two block boundaries: a paragraph, a list
 * item, a heading, a button. Inline elements inside it become placeholders,
 * so the translator may move them with the words but cannot change them;
 * what must not change at all (model names, figures with units written
 * together, shortcodes, code, e-mail and web addresses) becomes a `<kN/>`
 * placeholder. Script, style, SVG, code and elements marked
 * translate="no" or class="notranslate" are never sent.
 */
final class Segmenter {

	/**
	 * Inline (phrasing) elements that may sit inside a segment.
	 */
	private const INLINE = array( 'a', 'abbr', 'b', 'bdi', 'bdo', 'cite', 'data', 'del', 'dfn', 'em', 'font', 'i', 'ins', 'label', 'mark', 'q', 's', 'small', 'span', 'strong', 'sub', 'sup', 'time', 'u' );

	/**
	 * Inline elements without content.
	 */
	private const VOID_INLINE = array( 'br', 'img', 'wbr' );

	/**
	 * Inline elements whose content is kept as it is, as one placeholder.
	 */
	private const OPAQUE_INLINE = array( 'code', 'kbd', 'samp', 'var', 'svg', 'math' );

	/**
	 * Block elements whose content is kept as it is. The element's own start
	 * tag is still dispatched like any other: its text attributes (alt,
	 * title, aria-label, placeholder) are text for people and become
	 * segments, while everything from the content to the end tag stays the
	 * source's bytes. Reading the whole element as one raw part swallowed
	 * those attributes too — measured 2026-10-16 on the live content: the
	 * services page's two stage videos carry `aria-label`, and a German page
	 * rebuilt from its English source came back with the English labels
	 * while every visible line stayed German.
	 */
	private const OPAQUE_BLOCK = array( 'pre', 'template', 'select', 'object', 'video', 'audio', 'canvas' );

	/**
	 * Attributes whose values are text for people.
	 */
	private const TEXT_ATTRIBUTES = array( 'alt', 'title', 'aria-label', 'placeholder' );

	/**
	 * What must come back unchanged inside text: shortcodes, SEO variables
	 * (%%sitetitle%%), e-mail and web addresses, and model names, the tokens
	 * with a digit and an upper-case letter (GW10K-EHA-G20, CHS2-29.9K-T4-X,
	 * IP65, LiFePO4); see keep() for compounds such as B2B-PARTNER.
	 */
	private const KEEP = '/\[\/?[A-Za-z][\w-]*(?:\s[^\[\]]*)?\]|%%[a-z_]+%%|[\w.+-]+@[\w-]+(?:\.[\w-]+)+|https?:\/\/[^\s<>"]+|(?<model>\b(?=[\w.\/-]*\d)(?=[\w.\/-]*[A-Z])[A-Za-z0-9]+(?:[-.\/][A-Za-z0-9]+)*\b)/';

	/**
	 * A part of a hyphenated model name longer than this, without a digit,
	 * is a word (PARTNER in B2B-PARTNER), not part of the name. The parts of
	 * the live model names are at most four letters (EHA, BAT, LCD, HCA, STS).
	 */
	private const MODEL_PART = 5;

	/**
	 * Sets up the segmenter.
	 *
	 * @param HtmlTokenizer $tokenizer The HTML tokenizer.
	 */
	public function __construct( private readonly HtmlTokenizer $tokenizer ) {}

	/**
	 * A plain-text value (a title, an SEO field, a term name) as a document
	 * of at most one segment.
	 *
	 * @param string $text Text.
	 */
	public function text( string $text ): Document {
		$parts    = array();
		$segments = array();
		foreach ( $this->sentences( array( new HtmlToken( HtmlToken::TEXT, $text ) ) ) as $tokens ) {
			$document = $this->plain( implode( '', array_map( static fn( HtmlToken $token ): string => $token->raw, $tokens ) ) );
			$offset   = count( $segments );
			foreach ( $document->parts as $part ) {
				$parts[] = is_int( $part ) ? $part + $offset : $part;
			}
			array_push( $segments, ...$document->segments );
		}
		return new Document( $parts, $segments );
	}

	/**
	 * Fingerprints from before sentence splitting: one per plain field or paragraph.
	 *
	 * A stored baseline that still matches these hashes describes the same text.
	 * Sentence hashes of that text differ, and must not be read as an edit.
	 *
	 * @param string $value Field value.
	 * @param bool   $html  Whether the field is HTML.
	 * @return list<string>
	 */
	public function block_hashes( string $value, bool $html ): array {
		return ( $html ? $this->paragraphs( $value ) : $this->plain( $value ) )->hashes();
	}

	/**
	 * One plain-text sentence, retaining its surrounding whitespace.
	 *
	 * @param string $text Sentence bytes.
	 */
	private function plain( string $text ): Document {
		$core = trim( $text );
		if ( ! self::has_letters( $core ) ) {
			return new Document( array( $text ), array() );
		}
		$map     = array();
		$counter = 0;
		$masked  = $this->keep( self::collapse( $core ), $map, $counter, false );
		if ( ! self::has_letters( self::without_placeholders( $masked ) ) ) {
			return new Document( array( $text ), array() );
		}
		$start = (int) strpos( $text, $core );
		return new Document(
			array_values( array_filter( array( substr( $text, 0, $start ), 0, substr( $text, $start + strlen( $core ) ) ), static fn( $part ): bool => '' !== $part ) ),
			array( new Segment( $masked, $core, $map, false ) )
		);
	}

	/**
	 * An HTML value (a body, an excerpt) as a document.
	 *
	 * @param string $html HTML.
	 */
	public function html( string $html ): Document {
		return $this->markup( $html, true );
	}

	/**
	 * One segment per paragraph, the fingerprints stored before sentences were split.
	 *
	 * @param string $html HTML.
	 */
	private function paragraphs( string $html ): Document {
		return $this->markup( $html, false );
	}

	/**
	 * An HTML value as a document.
	 *
	 * @param string $html      HTML.
	 * @param bool   $sentences Whether to split paragraphs into sentences.
	 */
	private function markup( string $html, bool $sentences ): Document {
		$tokens   = $this->tokenizer->tokens( $html );
		$parts    = array();
		$segments = array();
		$run      = array();
		$count    = count( $tokens );
		for ( $i = 0; $i < $count; $i++ ) {
			$token = $tokens[ $i ];
			if ( HtmlToken::TEXT === $token->type ) {
				$run[] = $token;
				continue;
			}
			if ( HtmlToken::TAG !== $token->type ) {
				$this->flush( $run, $parts, $segments, $sentences );
				$parts[] = $token->raw;
				continue;
			}
			$opaque = ! $token->closing && ( in_array( $token->name, self::OPAQUE_INLINE, true ) || in_array( $token->name, self::OPAQUE_BLOCK, true ) || self::untranslatable( $token ) );
			if ( $opaque ) {
				$element = $this->element( $tokens, $i );
				if ( in_array( $token->name, self::OPAQUE_INLINE, true ) || ( self::untranslatable( $token ) && in_array( $token->name, array_merge( self::INLINE, self::VOID_INLINE ), true ) ) ) {
					$run[] = new HtmlToken( HtmlToken::OTHER, $element );
				} elseif ( self::untranslatable( $token ) ) {
					// translate="no" on a block element: nothing of it is touched.
					$this->flush( $run, $parts, $segments, $sentences );
					$parts[] = $element;
				} else {
					// An opaque block: the content stays the source's bytes, the
					// element's own start tag is dispatched like any other so its
					// text attributes (video's aria-label) are segments too.
					$this->flush( $run, $parts, $segments, $sentences );
					$parts[] = $this->tag( $token, $segments );
					$rest    = substr( $element, strlen( $token->raw ) );
					if ( '' !== $rest ) {
						$parts[] = $rest;
					}
				}
				continue;
			}
			if ( in_array( $token->name, self::INLINE, true ) || in_array( $token->name, self::VOID_INLINE, true ) ) {
				$run[] = $token;
				continue;
			}
			$this->flush( $run, $parts, $segments, $sentences );
			$parts[] = $this->tag( $token, $segments );
		}
		$this->flush( $run, $parts, $segments, $sentences );
		return new Document( $parts, $segments );
	}

	/**
	 * The bytes of an element from its start tag to its matching end tag,
	 * advancing the cursor to that end tag.
	 *
	 * @param array<int, HtmlToken> $tokens Tokens.
	 * @param int                   $i      Index of the start tag; set to the index of the end tag.
	 */
	private function element( array $tokens, int &$i ): string {
		$name  = $tokens[ $i ]->name;
		$raw   = $tokens[ $i ]->raw;
		$depth = 1;
		if ( str_ends_with( rtrim( $raw ), '/>' ) || in_array( $name, self::VOID_INLINE, true ) ) {
			return $raw;
		}
		$count = count( $tokens );
		while ( $depth > 0 && $i + 1 < $count ) {
			$next = $tokens[ ++$i ];
			$raw .= $next->raw;
			if ( HtmlToken::TAG === $next->type && $next->name === $name && ! str_ends_with( rtrim( $next->raw ), '/>' ) ) {
				$depth += $next->closing ? -1 : 1;
			}
		}
		return $raw;
	}

	/**
	 * Ends the current inline run: its text becomes a segment, the white
	 * space around it and inline tags that wrap all of it stay markup.
	 *
	 * @param array<int, HtmlToken>          $run       Tokens of the run; emptied.
	 * @param array<int, string|int|TagPart> $parts     Parts of the document.
	 * @param array<int, Segment>            $segments  Segments of the document.
	 * @param bool                           $sentences Whether to split the run into sentences.
	 *
	 * @phpstan-param list<HtmlToken> $run
	 * @phpstan-param list<string|int|TagPart> $parts
	 * @phpstan-param-out list<string|int|TagPart> $parts
	 * @phpstan-param list<Segment> $segments
	 * @phpstan-param-out list<Segment> $segments
	 */
	private function flush( array &$run, array &$parts, array &$segments, bool $sentences = true ): void {
		if ( array() === $run ) {
			return;
		}
		$tokens = $run;
		$run    = array();

		// Words left for the translator, token by token as segment() masks them.
		$words   = '';
		$unused  = array();
		$counter = 0;
		foreach ( $tokens as $token ) {
			if ( HtmlToken::TEXT === $token->type ) {
				$words .= ' ' . self::without_placeholders( $this->keep( html_entity_decode( $token->raw, ENT_QUOTES | ENT_HTML5, 'UTF-8' ), $unused, $counter, true ) );
			}
		}
		if ( ! self::has_letters( $words ) ) {
			foreach ( $tokens as $token ) {
				$parts[] = HtmlToken::TAG === $token->type ? $this->tag( $token, $segments ) : $token->raw;
			}
			return;
		}

		$before = array();
		$after  = array();
		while ( true ) {
			list( $lead, $trail ) = self::trim_space( $tokens );
			if ( '' !== $lead ) {
				$before[] = $lead;
			}
			if ( '' !== $trail ) {
				array_unshift( $after, $trail );
			}
			if ( count( $tokens ) < 2 || ! self::wraps( $tokens ) ) {
				break;
			}
			$before[] = $this->tag( $tokens[0], $segments );
			array_unshift( $after, $this->tag( $tokens[ count( $tokens ) - 1 ], $segments ) );
			$tokens = array_slice( $tokens, 1, -1 );
		}
		array_push( $parts, ...$before );
		if ( ! $sentences ) {
			$parts[] = $this->segment( $tokens, $segments );
			array_push( $parts, ...$after );
			return;
		}
		foreach ( $this->sentences( array_values( $tokens ) ) as $sentence ) {
			list( $lead, $trail ) = self::trim_space( $sentence );
			if ( '' !== $lead ) {
				$parts[] = $lead;
			}
			if ( array() !== $sentence ) {
				$parts[] = $this->segment( $sentence, $segments );
			}
			if ( '' !== $trail ) {
				$parts[] = $trail;
			}
		}
		array_push( $parts, ...$after );
	}

	/**
	 * Splits at sentence punctuation plus whitespace before an uppercase letter.
	 * An inline element spanning a boundary stays together, so placeholders stay
	 * balanced. Paragraph/list/heading boundaries remain independent as before.
	 *
	 * @param array<int, HtmlToken> $tokens Inline run.
	 * @return list<list<HtmlToken>>
	 * @phpstan-param list<HtmlToken> $tokens
	 */
	private function sentences( array $tokens ): array {
		$sentences = array();
		$sentence  = array();
		$depth     = 0;
		foreach ( $tokens as $token ) {
			if ( HtmlToken::TAG === $token->type && in_array( $token->name, self::INLINE, true ) ) {
				$depth += $token->closing ? -1 : 1;
			}
			$pieces = HtmlToken::TEXT === $token->type && 0 === $depth ? preg_split( '/(?<=[.!?])([ \t\r\n]+)(?=[\p{Lu}])/u', $token->raw, -1, PREG_SPLIT_DELIM_CAPTURE ) : false;
			if ( false === $pieces ) {
				$sentence[] = $token;
				continue;
			}
			foreach ( $pieces as $index => $piece ) {
				$sentence[] = new HtmlToken( HtmlToken::TEXT, $piece );
				if ( 1 === $index % 2 ) {
					$sentences[] = $sentence;
					$sentence    = array();
				}
			}
		}
		if ( array() !== $sentence ) {
			$sentences[] = $sentence;
		}
		return $sentences;
	}

	/**
	 * Moves white space at the ends of a run out of it.
	 *
	 * @param array<int, HtmlToken> $tokens Tokens of the run.
	 * @return array{string, string} The white space before and after.
	 */
	private static function trim_space( array &$tokens ): array {
		$lead  = '';
		$trail = '';
		while ( array() !== $tokens && HtmlToken::TEXT === $tokens[0]->type ) {
			$raw     = $tokens[0]->raw;
			$trimmed = ltrim( $raw, " \t\n\r\f" );
			$lead   .= substr( $raw, 0, strlen( $raw ) - strlen( $trimmed ) );
			if ( '' !== $trimmed ) {
				$tokens[0] = new HtmlToken( HtmlToken::TEXT, $trimmed );
				break;
			}
			array_shift( $tokens );
		}
		while ( array() !== $tokens && HtmlToken::TEXT === $tokens[ (int) array_key_last( $tokens ) ]->type ) {
			$last    = (int) array_key_last( $tokens );
			$raw     = $tokens[ $last ]->raw;
			$trimmed = rtrim( $raw, " \t\n\r\f" );
			$trail   = substr( $raw, strlen( $trimmed ) ) . $trail;
			if ( '' !== $trimmed ) {
				$tokens[ $last ] = new HtmlToken( HtmlToken::TEXT, $trimmed );
				break;
			}
			array_pop( $tokens );
		}
		return array( $lead, $trail );
	}

	/**
	 * Whether the run's first token opens an inline element that its last
	 * token closes, and nothing in between closes it.
	 *
	 * @param array<int, HtmlToken> $tokens Tokens of the run.
	 */
	private static function wraps( array $tokens ): bool {
		$first = $tokens[0];
		$last  = $tokens[ count( $tokens ) - 1 ];
		if ( HtmlToken::TAG !== $first->type || $first->closing || HtmlToken::TAG !== $last->type || ! $last->closing || $first->name !== $last->name || ! in_array( $first->name, self::INLINE, true ) ) {
			return false;
		}
		$depth = 0;
		$last  = count( $tokens ) - 1;
		for ( $i = 0; $i < $last; $i++ ) {
			$token = $tokens[ $i ];
			if ( HtmlToken::TAG === $token->type && $token->name === $first->name ) {
				$depth += $token->closing ? -1 : 1;
				if ( 0 === $depth ) {
					return false;
				}
			}
		}
		return 1 === $depth;
	}

	/**
	 * A segment made of the run's tokens.
	 *
	 * @param array<int, HtmlToken> $tokens   Tokens; text at both ends is not white space.
	 * @param array<int, Segment>   $segments Segments of the document; the new one is added.
	 * @return int Index of the segment.
	 *
	 * @phpstan-param list<Segment> $segments
	 * @phpstan-param-out list<Segment> $segments
	 */
	private function segment( array $tokens, array &$segments ): int {
		$map     = array();
		$counter = 0;
		$text    = '';
		$raw     = '';
		$open    = array();
		$pairs   = $this->pairs( $tokens );
		foreach ( $tokens as $position => $token ) {
			$raw .= $token->raw;
			if ( HtmlToken::TEXT === $token->type ) {
				$text .= $this->keep( html_entity_decode( $token->raw, ENT_QUOTES | ENT_HTML5, 'UTF-8' ), $map, $counter, true );
				continue;
			}
			if ( HtmlToken::OTHER === $token->type ) {
				$key         = 'k' . ( ++$counter ) . '/';
				$map[ $key ] = $token->raw;
				$text       .= '<' . $key . '>';
				continue;
			}
			$part = $this->tag( $token, $segments );
			if ( isset( $pairs[ $position ] ) && ! $token->closing ) {
				$number                      = ++$counter;
				$open[ $pairs[ $position ] ] = $number;
				$map[ 't' . $number ]        = $part;
				$text                       .= '<t' . $number . '>';
			} elseif ( isset( $open[ $position ] ) ) {
				$map[ '/t' . $open[ $position ] ] = $part;
				$text                            .= '</t' . $open[ $position ] . '>';
			} else {
				$key         = 't' . ( ++$counter ) . '/';
				$map[ $key ] = $part;
				$text       .= '<' . $key . '>';
			}
		}
		// After the attribute segments of the run's tags, which tag() added.
		$segments[] = new Segment( trim( self::collapse( $text ) ), $raw, $map, true );
		return count( $segments ) - 1;
	}

	/**
	 * The start tags of the run whose end tag is also in the run.
	 *
	 * @param array<int, HtmlToken> $tokens Tokens.
	 * @return array<int, int> Position of a start tag => position of its end tag.
	 */
	private function pairs( array $tokens ): array {
		$pairs = array();
		$stack = array();
		foreach ( $tokens as $position => $token ) {
			if ( HtmlToken::TAG !== $token->type || in_array( $token->name, self::VOID_INLINE, true ) ) {
				continue;
			}
			if ( ! $token->closing ) {
				$stack[] = $position;
				continue;
			}
			for ( $j = count( $stack ) - 1; $j >= 0; $j-- ) {
				if ( $tokens[ $stack[ $j ] ]->name === $token->name ) {
					$pairs[ $stack[ $j ] ] = $position;
					array_splice( $stack, $j );
					break;
				}
			}
		}
		return $pairs;
	}

	/**
	 * A tag as a part: as it is, or with its text attributes as segments.
	 *
	 * @param HtmlToken           $tag      The tag.
	 * @param array<int, Segment> $segments Segments of the document; attribute segments are added.
	 * @return string|TagPart
	 *
	 * @phpstan-param list<Segment> $segments
	 * @phpstan-param-out list<Segment> $segments
	 */
	private function tag( HtmlToken $tag, array &$segments ) {
		$attributes = array();
		foreach ( self::TEXT_ATTRIBUTES as $attribute ) {
			$value = $tag->attribute( $attribute );
			if ( null === $value || ! self::has_letters( $value ) ) {
				continue;
			}
			$map                      = array();
			$counter                  = 0;
			$attributes[ $attribute ] = count( $segments );
			$segments[]               = new Segment( $this->keep( self::collapse( trim( $value ) ), $map, $counter, false ), $value, $map, false );
		}
		return array() === $attributes ? $tag->raw : new TagPart( $tag, $attributes );
	}

	/**
	 * Replaces what must come back unchanged with `<kN/>` placeholders.
	 *
	 * @param string                        $text    Decoded text.
	 * @param array<string, string|TagPart> $map     Placeholder map; entries are added.
	 * @param int                           $counter Last placeholder number; advanced.
	 * @param bool                          $html    Whether the kept text goes back into HTML (and is encoded).
	 */
	private function keep( string $text, array &$map, int &$counter, bool $html ): string {
		$placeholder = static function ( string $kept ) use ( &$map, &$counter, $html ): string {
			$key         = 'k' . ( ++$counter ) . '/';
			$map[ $key ] = $html ? Segment::encode( $kept ) : $kept;
			return '<' . $key . '>';
		};
		return (string) preg_replace_callback(
			self::KEEP,
			static function ( array $found ) use ( $placeholder ): string {
				if ( '' === ( $found['model'] ?? '' ) ) {
					return $placeholder( $found[0] );
				}
				$parts = preg_split( '/([-.\/])/', $found[0], -1, PREG_SPLIT_DELIM_CAPTURE );
				$word  = static fn( string $part ): bool => strlen( $part ) > self::MODEL_PART && 1 !== preg_match( '/\d/', $part );
				if ( ! is_array( $parts ) || array() === array_filter( $parts, $word ) ) {
					return $placeholder( $found[0] );
				}
				// A compound of a model name and words: only the parts with a digit are kept.
				$out = '';
				foreach ( $parts as $part ) {
					$out .= 1 === preg_match( '/\d/', $part ) && 1 === preg_match( '/[A-Z]/', $part ) ? $placeholder( $part ) : $part;
				}
				return $out;
			},
			$text
		);
	}

	/**
	 * Whether a tag is marked as not to be translated (HTML's translate
	 * attribute, or the notranslate class translation tools honour).
	 *
	 * @param HtmlToken $tag The tag.
	 */
	private static function untranslatable( HtmlToken $tag ): bool {
		if ( 'no' === strtolower( (string) $tag->attribute( 'translate' ) ) ) {
			return true;
		}
		$classes = preg_split( '/\s+/', (string) $tag->attribute( 'class' ) );
		return is_array( $classes ) && in_array( 'notranslate', $classes, true );
	}

	/**
	 * Collapses runs of ASCII white space to one space (a no-break space stays).
	 *
	 * @param string $text Text.
	 */
	private static function collapse( string $text ): string {
		return (string) preg_replace( '/[ \t\n\r\f]+/', ' ', $text );
	}

	/**
	 * Text without placeholders: what is left for the translator.
	 *
	 * @param string $text Text with placeholders.
	 */
	private static function without_placeholders( string $text ): string {
		return (string) preg_replace( Segment::PLACEHOLDER, '', $text );
	}

	/**
	 * Whether a text has a letter in it.
	 *
	 * @param string $text Text.
	 */
	private static function has_letters( string $text ): bool {
		return 1 === preg_match( '/\p{L}/u', $text );
	}
}
