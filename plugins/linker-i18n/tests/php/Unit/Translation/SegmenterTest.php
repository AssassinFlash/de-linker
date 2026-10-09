<?php
/**
 * Tests for the segmenter.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Translation\Segment;
use Linker\I18n\Translation\Segmenter;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Segmenter, Document and Segment with real content of the live site.
 *
 * @covers \Linker\I18n\Translation\Segmenter
 * @covers \Linker\I18n\Translation\Document
 * @covers \Linker\I18n\Translation\Segment
 * @covers \Linker\I18n\Translation\TagPart
 */
final class SegmenterTest extends TestCase {

	/**
	 * The segmenter.
	 *
	 * @var Segmenter
	 */
	private Segmenter $segmenter;

	/**
	 * Sets up the segmenter.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->segmenter = new Segmenter( new HtmlTokenizer() );
	}

	/**
	 * A paragraph's text is one segment; its inline markup becomes paired
	 * placeholders, the model name a kept one.
	 */
	public function test_inline_markup_becomes_placeholders(): void {
		$document = $this->segmenter->html( "<p>The <strong>GW10K-ET</strong> pairs with the <a href=\"/product/lynx/\">Lynx Home F</a>.</p>\n" );

		$this->assertCount( 1, $document->segments );
		$this->assertSame( 'The <t1><k2/></t1> pairs with the <t3>Lynx Home F</t3>.', $document->segments[0]->text );
	}

	/**
	 * A list item and a heading are segments of their own; white space and
	 * block tags stay markup.
	 */
	public function test_blocks_split_segments(): void {
		$document = $this->segmenter->html( "<h3>Specifications</h3>\n<ul>\n<li><strong>Rated AC power:</strong> 10 kW</li>\n<li>Ingress protection: IP66</li>\n</ul>" );

		$this->assertSame(
			array( 'Specifications', '<t1>Rated AC power:</t1> 10 kW', 'Ingress protection: <k1/>' ),
			array_map( static fn( Segment $segment ): string => $segment->text, $document->segments )
		);
	}

	/**
	 * An inline tag that wraps the whole text stays outside the segment.
	 */
	public function test_wrapping_inline_tag_stays_markup(): void {
		$document = $this->segmenter->html( '<div class="cta"> <a class="btn" href="/contact/">Contact the team</a> </div>' );

		$this->assertSame( 'Contact the team', $document->segments[0]->text );
		$this->assertSame( array( '<div class="cta">', ' ', '<a class="btn" href="/contact/">', 0, '</a>', ' ', '</div>' ), $document->parts );
	}

	/**
	 * Code, inline SVG and elements marked translate="no" or notranslate are never sent.
	 */
	public function test_untranslatable_content_is_kept(): void {
		$document = $this->segmenter->html( '<p>Run <code>wp linker-i18n setup</code> now <span translate="no">Linker GmbH</span>.</p><svg><text>Chart</text></svg><div class="notranslate">Keep me</div><script>var x = "Hello";</script>' );

		$this->assertSame( array( 'Run <k1/> now <k2/>.' ), array_map( static fn( Segment $segment ): string => $segment->text, $document->segments ) );
	}

	/**
	 * Text that is only kept names or a shortcode is not a segment.
	 */
	public function test_shortcode_only_is_not_a_segment(): void {
		$this->assertSame( array(), $this->segmenter->html( '<!-- wp:shortcode -->[woocommerce_my_account]<!-- /wp:shortcode -->' )->segments );
		$this->assertSame( array(), $this->segmenter->text( 'GW10K-EHA-G20' )->segments );
		$this->assertSame( array(), $this->segmenter->html( '<p>10 / 20</p>' )->segments );
	}

	/**
	 * Alt and title attributes are segments of their own.
	 */
	public function test_text_attributes_are_segments(): void {
		$document = $this->segmenter->html( '<figure><img src="/a.png" alt="Battery cabinet front"><figcaption>Front view</figcaption></figure>' );

		$this->assertSame(
			array( 'Battery cabinet front', 'Front view' ),
			array_map( static fn( Segment $segment ): string => $segment->text, $document->segments )
		);
		$this->assertSame(
			'<figure><img src="/a.png" alt="Batterieschrank, Vorderseite"><figcaption>Vorderansicht</figcaption></figure>',
			$document->render(
				array(
					0 => 'Batterieschrank, Vorderseite',
					1 => 'Vorderansicht',
				)
			)
		);
	}

	/**
	 * A translation keeps the markup: placeholders come back as the tags,
	 * text is encoded, kept names are put back.
	 */
	public function test_render_puts_markup_back(): void {
		$document = $this->segmenter->html( '<p>The <strong>GW10K-ET</strong> &amp; battery</p>' );

		$this->assertSame( '<p>Der <strong>GW10K-ET</strong> &amp; Speicher &lt;neu&gt;</p>', $document->render( array( 0 => 'Der <t1><k2/></t1> & Speicher <neu>' ) ) );
	}

	/**
	 * A plain-text value: decoded for the translator, a model name kept.
	 */
	public function test_text_value(): void {
		$document = $this->segmenter->text( '  GoodWe GW60K-STS-G10 | Linker ' );

		$this->assertSame( 'GoodWe <k1/> | Linker', $document->segments[0]->text );
		$this->assertSame( '  GoodWe GW60K-STS-G10 – Notstrom | Linker ', $document->render( array( 0 => 'GoodWe <k1/> – Notstrom | Linker' ) ) );
	}

	/**
	 * Link targets are not part of a segment's fingerprint; text and markup are.
	 */
	public function test_hash_ignores_link_targets(): void {
		$english = $this->segmenter->html( '<p>See the <a href="/product/x/">datasheet</a>.</p>' )->segments[0];
		$german  = $this->segmenter->html( '<p>See the <a href="/de/produkt/x/">datasheet</a>.</p>' )->segments[0];
		$changed = $this->segmenter->html( '<p>See the <a href="/product/x/" class="b">datasheet</a>.</p>' )->segments[0];

		$this->assertSame( $english->hash(), $german->hash() );
		$this->assertNotSame( $english->hash(), $changed->hash() );
	}

	/**
	 * The English and German bodies of the live site, unchanged when no
	 * segment is translated; and the old German lines up with the English
	 * segment for segment.
	 */
	public function test_live_content_round_trips_and_aligns(): void {
		$live     = dirname( __DIR__, 3 ) . '/fixtures/live';
		$products = json_decode( (string) file_get_contents( $live . '/products.json' ), true ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a fixture.
		$pages    = json_decode( (string) file_get_contents( $live . '/pages.json' ), true ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a fixture.
		$this->assertIsArray( $products );
		$this->assertIsArray( $pages );

		$pairs = array();
		foreach ( $products as $product ) {
			$pairs[] = array( $product['description'], $product['meta']['_linker_de_content'] );
			$pairs[] = array( $product['short_description'], $product['meta']['_linker_de_excerpt'] );
		}
		foreach ( $pages as $page ) {
			if ( null !== $page['de']['content_rendered'] ) {
				$pairs[] = array( $page['content'], $page['de']['content_rendered'] );
			}
		}
		$this->assertGreaterThan( 20, count( $pairs ) );
		foreach ( $pairs as list( $english, $german ) ) {
			$english_document = $this->segmenter->html( $english );
			$german_document  = $this->segmenter->html( $german );
			$this->assertSame( $english, $english_document->render( array() ) );
			$this->assertSame( $german, $german_document->render( array() ) );
			$this->assertCount( count( $english_document->segments ), $german_document->segments );
		}
	}
}
