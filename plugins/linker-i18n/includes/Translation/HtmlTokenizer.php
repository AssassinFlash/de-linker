<?php
/**
 * Splits HTML into tokens that put back together to the same bytes.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * A tokenizer for the HTML the site stores: page and product bodies, many of
 * them LiveCanvas sections with inline scripts and styles.
 *
 * Concatenating the tokens' bytes gives the input back unchanged, whatever
 * the input: a `<` that starts no tag is text, an unterminated comment runs to
 * the end. The content of script, style and the other raw-text elements of
 * the HTML standard is one OTHER token, never text, so code never reaches the
 * translator.
 */
final class HtmlTokenizer {

	/**
	 * Elements whose content is not markup (HTML Living Standard §13.1.2,
	 * raw text and escapable raw text elements, plus the legacy ones parsed
	 * the same way).
	 */
	private const RAW_TEXT = array( 'script', 'style', 'textarea', 'title', 'xmp', 'iframe', 'noembed', 'noframes', 'noscript' );

	/**
	 * A start or end tag: name, attributes (quoted values may hold `>`), optional `/`.
	 */
	private const TAG = '/\G<(\/?)([a-zA-Z][a-zA-Z0-9:-]*)((?:\s+[^\s"\'>\/=]+(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s"\'=<>`]+))?|\s*\/(?!>))*\s*)(\/?)>/';

	/**
	 * The tokens of an HTML string.
	 *
	 * @param string $html HTML.
	 * @return list<HtmlToken>
	 */
	public function tokens( string $html ): array {
		$tokens = array();
		$length = strlen( $html );
		$at     = 0;
		while ( $at < $length ) {
			$open = strpos( $html, '<', $at );
			if ( false === $open ) {
				$tokens[] = new HtmlToken( HtmlToken::TEXT, substr( $html, $at ) );
				break;
			}
			if ( $open > $at ) {
				$tokens[] = new HtmlToken( HtmlToken::TEXT, substr( $html, $at, $open - $at ) );
				$at       = $open;
			}
			if ( 0 === substr_compare( $html, '<!--', $at, 4 ) ) {
				$end      = strpos( $html, '-->', $at + 4 );
				$end      = false === $end ? $length : $end + 3;
				$tokens[] = new HtmlToken( HtmlToken::COMMENT, substr( $html, $at, $end - $at ) );
				$at       = $end;
				continue;
			}
			if ( 1 === preg_match( '/\G<[!?]/', $html, $unused, 0, $at ) ) {
				$end      = strpos( $html, '>', $at );
				$end      = false === $end ? $length : $end + 1;
				$tokens[] = new HtmlToken( HtmlToken::OTHER, substr( $html, $at, $end - $at ) );
				$at       = $end;
				continue;
			}
			if ( 1 !== preg_match( self::TAG, $html, $match, 0, $at ) ) {
				$tokens[] = new HtmlToken( HtmlToken::TEXT, '<' );
				++$at;
				continue;
			}
			$name     = strtolower( $match[2] );
			$closing  = '/' === $match[1];
			$tokens[] = new HtmlToken( HtmlToken::TAG, $match[0], $name, $closing );
			$at      += strlen( $match[0] );
			if ( ! $closing && '/' !== $match[4] && in_array( $name, self::RAW_TEXT, true ) ) {
				$at = $this->raw_text( $html, $at, $name, $tokens );
			}
		}
		return $tokens;
	}

	/**
	 * Adds the content and the end tag of a raw-text element.
	 *
	 * @param string                $html   HTML.
	 * @param int                   $at     Offset after the start tag.
	 * @param string                $name   Element name.
	 * @param array<int, HtmlToken> $tokens Tokens so far.
	 * @return int Offset after the element.
	 *
	 * @phpstan-param list<HtmlToken> $tokens
	 */
	private function raw_text( string $html, int $at, string $name, array &$tokens ): int {
		if ( 1 !== preg_match( '/<\/' . preg_quote( $name, '/' ) . '\s*>/i', $html, $end, PREG_OFFSET_CAPTURE, $at ) ) {
			$tokens[] = new HtmlToken( HtmlToken::OTHER, substr( $html, $at ) );
			return strlen( $html );
		}
		$close = (int) $end[0][1];
		if ( $close > $at ) {
			$tokens[] = new HtmlToken( HtmlToken::OTHER, substr( $html, $at, $close - $at ) );
		}
		$tokens[] = new HtmlToken( HtmlToken::TAG, $end[0][0], $name, true );
		return $close + strlen( $end[0][0] );
	}
}
