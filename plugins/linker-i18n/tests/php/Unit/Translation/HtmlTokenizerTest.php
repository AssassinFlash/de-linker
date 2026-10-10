<?php
/**
 * Tests for the HTML tokenizer.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Translation\HtmlToken;
use Linker\I18n\Translation\HtmlTokenizer;
use WP_Mock\Tools\TestCase;

/**
 * Tests for HtmlTokenizer.
 *
 * @covers \Linker\I18n\Translation\HtmlTokenizer
 * @covers \Linker\I18n\Translation\HtmlToken
 */
final class HtmlTokenizerTest extends TestCase {

	/**
	 * Markup the site stores: LiveCanvas sections with inline scripts and
	 * styles, attributes holding ">", comments, stray "<".
	 *
	 * @return array<string, array{string}>
	 */
	public function provide_markup(): array {
		return array(
			'paragraph'           => array( '<p class="lead">Hybrid <strong>inverter</strong> &amp; battery.</p>' ),
			'script with <'       => array( '<script>if (a < b && c > d) { document.body.setAttribute("data-page","about"); }</script><p>Text</p>' ),
			'style'               => array( "<style>.a > .b{color:red}</style>\n<div>Ok</div>" ),
			'attribute with >'    => array( '<a data-x="a>b" href="/x/">Link</a>' ),
			'comment'             => array( '<!-- wp:paragraph --><p>A</p><!-- /wp:paragraph -->' ),
			'unterminated'        => array( '<p>Open <!-- never closed' ),
			'stray less-than'     => array( '<p>5 < 10 and 3<4</p>' ),
			'doctype and cdata'   => array( '<!DOCTYPE html><![CDATA[x]]><p>y</p>' ),
			'void and self-close' => array( '<br><img src="a.png" alt="Alt"/><wbr>' ),
			'unclosed script'     => array( '<p>a</p><script>var x = 1;' ),
		);
	}

	/**
	 * Joining the tokens gives the input back byte for byte.
	 *
	 * @dataProvider provide_markup
	 *
	 * @param string $html Markup.
	 */
	public function test_tokens_join_to_the_input( string $html ): void {
		$tokens = ( new HtmlTokenizer() )->tokens( $html );

		$this->assertSame( $html, implode( '', array_map( static fn( HtmlToken $token ): string => $token->raw, $tokens ) ) );
	}

	/**
	 * Script content is one OTHER token, never text, so code is never translated.
	 */
	public function test_script_content_is_not_text(): void {
		$tokens = ( new HtmlTokenizer() )->tokens( '<script>var text = "<p>hello</p>";</script>' );

		$this->assertSame( array( HtmlToken::TAG, HtmlToken::OTHER, HtmlToken::TAG ), array_map( static fn( HtmlToken $token ): string => $token->type, $tokens ) );
		$this->assertSame( 'script', $tokens[2]->name );
		$this->assertTrue( $tokens[2]->closing );
	}

	/**
	 * Tag names are lower case and closing tags are marked.
	 */
	public function test_tag_names_and_closers(): void {
		$tokens = ( new HtmlTokenizer() )->tokens( '<DIV id="a">x</DIV>' );

		$this->assertSame( 'div', $tokens[0]->name );
		$this->assertFalse( $tokens[0]->closing );
		$this->assertSame( HtmlToken::TEXT, $tokens[1]->type );
		$this->assertTrue( $tokens[2]->closing );
	}

	/**
	 * An attribute is read decoded and replaced encoded, the rest of the tag untouched.
	 */
	public function test_attribute_read_and_replace(): void {
		$tag = ( new HtmlTokenizer() )->tokens( '<img class="x" alt="Batterie &amp; Wechselrichter" src="/a.png">' )[0];

		$this->assertSame( 'Batterie & Wechselrichter', $tag->attribute( 'alt' ) );
		$this->assertNull( $tag->attribute( 'title' ) );
		$this->assertSame( '<img class="x" alt="Speicher &amp; &quot;Hybrid&quot;" src="/a.png">', $tag->with_attribute( 'alt', 'Speicher & "Hybrid"' ) );
		$this->assertSame( $tag->raw, $tag->with_attribute( 'title', 'x' ) );
	}
}
