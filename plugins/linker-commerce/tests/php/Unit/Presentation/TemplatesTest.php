<?php
/**
 * Tests for the LiveCanvas dynamic templates.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\Templates;
use Linker\Commerce\Presentation\WindPressVolume;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;
use WP_Post;

/**
 * Tests for Templates.
 *
 * @covers \Linker\Commerce\Presentation\Templates
 */
final class TemplatesTest extends TestCase {

	/** Existing template tests opt into public product taxonomies explicitly. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_object_taxonomies' )->andReturn( array() )->byDefault();
	}

	/**
	 * Every Woo page the presentation layer owns has an exported HTML file and a LiveCanvas meta key.
	 */
	public function test_paths_cover_the_woo_pages_and_the_tool_pages(): void {
		$paths = Templates::paths();

		$this->assertSame(
			array(
				'is_shop_page',
				'is_cart_page',
				'is_checkout_page',
				'is_account_page',
				'is_single_product',
				'is_archive_for_post_type_product',
				'is_single_post',
				'is_blog_posts_index',
				'is_search',
				'is_archive_for_tax_category',
				'linker-compare',
				'linker-compare-de',
				'linker-faq',
				'linker-faq-de',
				'linker-advisor',
				'linker-advisor-de',
				'linker-configurator',
				'linker-configurator-de',
				// The German exports of page types are sources of their own:
				// the product page's, the product archive's, the blog single
				// face's and the three blog faces #175 brought in.
				'is_single_product__de',
				'is_archive_for_post_type_product__de',
				'is_single_post__de',
				'is_blog_posts_index__de',
				'is_search__de',
				'is_archive_for_tax_category__de',
			),
			array_keys( $paths )
		);
		foreach ( $paths as $path ) {
			$this->assertFileExists( $path );
			$html = (string) file_get_contents( $path );
			$this->assertNotSame( '', trim( $html ) );
		}
		$single = (string) file_get_contents( $paths['is_single_product'] );
		$this->assertStringContainsString( 'class="pdp-layout sf-container"', $single );
		$this->assertStringContainsString( '[linker_pdp_gallery_pair]', $single );
		$this->assertStringContainsString( '[linker_pdp_tools]', $single );
		$this->assertStringContainsString( '[lc_if condition="linker_commerce_pdp_has_pairings"]', $single );
		$this->assertStringNotContainsString( '[linker_pdp_buy]', $single );
		$this->assertStringContainsString( '[linker_products_families]', (string) file_get_contents( $paths['is_shop_page'] ) );
		$this->assertStringContainsString( 'id="tv-storefront-pdp"', (string) file_get_contents( $paths['is_single_product'] ) );
		$this->assertStringContainsString( 'id="linker-products"', (string) file_get_contents( $paths['is_shop_page'] ) );
			$cart = (string) file_get_contents( $paths['is_cart_page'] );
			$this->assertStringContainsString( '[linker_draft_empty]', $cart );
			$this->assertStringContainsString( 'linker_commerce_draft_empty', $cart );
			$this->assertStringContainsString( 'linker_commerce_draft_filled', $cart );
			$this->assertStringContainsString( '[woocommerce_cart]', $cart );
		$this->assertStringContainsString( '[linker_checkout]', (string) file_get_contents( $paths['is_checkout_page'] ) );
		$this->assertStringContainsString( '[woocommerce_my_account]', (string) file_get_contents( $paths['is_account_page'] ) );
		$this->assertStringContainsString( '[linker_compare_table]', (string) file_get_contents( $paths['linker-compare'] ) );
		$this->assertStringContainsString( '[linker_compare_table]', (string) file_get_contents( $paths['linker-compare-de'] ) );
		// The library page's two panels: the FAQ tab's fragments and the
		// documents tab's, each language its own template (docs/specs/176-).
		foreach ( array( 'linker-faq', 'linker-faq-de' ) as $slug ) {
			$face = (string) file_get_contents( $paths[ $slug ] );
			$this->assertStringContainsString( '[linker_library_faq]', $face );
			$this->assertStringContainsString( '[linker_library_documents]', $face );
			$this->assertStringContainsString( '[linker_library_rail]', $face );
			$this->assertStringContainsString( '[linker_library_chips]', $face );
			$this->assertStringContainsString( '[linker_library_config]', $face );
			$this->assertStringContainsString( 'data-library-panel="faq"', $face );
			$this->assertStringContainsString( 'data-library-panel="documents"', $face );
		}
		$this->assertStringContainsString( '[linker_genie_workspace]', (string) file_get_contents( $paths['linker-advisor'] ) );
		$this->assertStringContainsString( '[linker_genie_workspace]', (string) file_get_contents( $paths['linker-advisor-de'] ) );
		// The configurator's page is the application's mount point, in both
		// languages: the page must never fall back to markup it held before.
		$this->assertStringContainsString( '[linker_planner]', (string) file_get_contents( $paths['linker-configurator'] ) );
		$this->assertStringContainsString( '[linker_planner]', (string) file_get_contents( $paths['linker-configurator-de'] ) );
		// The German product page's own export: its words are German, so it
		// is not the English file (a shared file would print "Products").
		$german = (string) file_get_contents( $paths['is_single_product__de'] );
		$this->assertStringContainsString( 'id="tv-storefront-pdp"', $german );
		$this->assertStringContainsString( '>Produkte</a>', $german );
		$this->assertStringContainsString( '[linker_pdp_gallery_pair]', $german );
		$this->assertStringNotContainsString( '>Products</a>', $german );

		// The product page's upper half ends with the inquiry rail (#174): the
		// gallery, the intro and the rail are the page's one grid, the sticky
		// section nav and every content block sit after it, and the rail keeps
		// the inquiry copy in its own order. The rail is sticky inside that
		// grid only, which is what keeps it off the blocks below.
		foreach ( array( 'is_single_product', 'is_single_product__de' ) as $page ) {
			$html = (string) file_get_contents( $paths[ $page ] );

			$upper   = strpos( $html, 'class="pdp-layout sf-container"' );
			$gallery = strpos( $html, 'class="pdp-gallery"' );
			$rail    = strpos( $html, 'class="pdp-purchase"' );
			$intro   = strpos( $html, 'class="pdp-intro"' );
			$nav     = strpos( $html, 'class="pdp-section-nav"' );
			$content = strpos( $html, 'class="pdp-content"' );
			$stats   = strpos( $html, 'id="stats"' );

			$this->assertNotFalse( $upper );
			$this->assertNotFalse( $gallery );
			$this->assertNotFalse( $rail );
			$this->assertNotFalse( $intro );
			$this->assertNotFalse( $nav );
			$this->assertNotFalse( $content );
			$this->assertNotFalse( $stats );
			// The three upper children, then the nav and the lower blocks.
			$this->assertLessThan( $rail, $gallery );
			$this->assertLessThan( $intro, $rail );
			$this->assertLessThan( $nav, $intro );
			$this->assertLessThan( $content, $nav );
			$this->assertLessThan( $stats, $content );

			$this->assertStringContainsString( 'class="pdp-rail-fade pdp-rail-fade-top"', $html );
			$this->assertStringContainsString( 'class="pdp-rail-fade pdp-rail-fade-bottom"', $html );

			// The rail's own order: identity, price, key figures, availability,
			// the primary action, the contact action, the tool row, the project
			// entry — unchanged by the redesign, design only.
			$sequence = array(
				'[linker_pdp_price]',
				'[linker_pdp_key_stats]',
				'[linker_pdp_availability]',
				'[linker_pdp_cta]',
				'[linker_pdp_ask]',
				'[linker_pdp_tools]',
				'class="pdp-project-check"',
			);
			$position = strpos( $html, (string) $sequence[0] );
			$this->assertNotFalse( $position );
			foreach ( \array_slice( $sequence, 1 ) as $step ) {
				$next = strpos( $html, (string) $step );
				$this->assertNotFalse( $next );
				$this->assertGreaterThan( $position, $next );
				$position = $next;
			}
			// The project entry closes the rail, before the nav.
			$this->assertLessThan( $nav, $position );
		}

		// The blog single face: the article's two data areas are the plugin's
		// own shortcodes (the live face resolved them with template loops),
		// the band's words are the live band's, and no style block sits in
		// the markup — the face's rules are the WindPress volume file
		// blog.css.
		$blog = (string) file_get_contents( $paths['is_single_post'] );
		$this->assertStringContainsString( 'id="tv-blog-single-v1"', $blog );
		$this->assertStringContainsString( '[linker_blog_post_categories]', $blog );
		$this->assertStringContainsString( '[linker_blog_related_posts]', $blog );
		$this->assertStringContainsString( '[linker_contact_invitation surface="article"]', $blog );
		$this->assertStringContainsString( 'label="Request a project quote →"', $blog );
		$this->assertStringContainsString( 'Back to blog', $blog );
		$this->assertStringNotContainsString( 'Contact Linker</a>', $blog );
		$this->assertStringNotContainsString( '<style', $blog );
		$this->assertStringNotContainsString( 'Zurück zum Blog', $blog );

		// The German twin is the German face, not the English file re-used:
		// its words, its band label and its date format are the ones the
		// German page shows.
		$blog_de = (string) file_get_contents( $paths['is_single_post__de'] );
		$this->assertStringContainsString( 'id="tv-blog-single-v1"', $blog_de );
		$this->assertStringContainsString( '[linker_blog_post_categories]', $blog_de );
		$this->assertStringContainsString( '[linker_blog_related_posts]', $blog_de );
		$this->assertStringContainsString( 'label_de="Projektangebot anfragen →"', $blog_de );
		$this->assertStringContainsString( 'Zurück zum Blog', $blog_de );
		$this->assertStringContainsString( 'date_format="d.m.Y"', $blog_de );
		$this->assertStringNotContainsString( 'Back to blog', $blog_de );
		$this->assertStringNotContainsString( '<style', $blog_de );
	}

	/**
	 * The three blog faces #175 brought into the tree: the blog posts index,
	 * the search results and the category archive, each with its German twin.
	 *
	 * The contract of every file: the live face's ids and section markers, no
	 * style block and no inline declaration (styling is the face's WindPress
	 * volume file), the terms of the face's own loops still in place, and
	 * `{Field url}` on every article card — the live templates wrote
	 * `/{Field name}/`, which on a German face is a 404.
	 */
	public function test_the_three_blog_faces_carry_the_live_markup_and_lingual_links(): void {
		$paths = Templates::paths();
		$faces = array(
			'is_blog_posts_index'         => array( 'tv-blog-index-v1', 'blog-index.css' ),
			'is_search'                   => array( 'tv-blog-search-v1', 'blog-search.css' ),
			'is_archive_for_tax_category' => array( 'tv-blog-category-v1', 'blog-category.css' ),
		);
		foreach ( $faces as $meta => $face ) {
			list( $anchor, $stylesheet ) = $face;
			foreach ( array( '', '__de' ) as $suffix ) {
				$html = (string) file_get_contents( $paths[ $meta . $suffix ] );
				$this->assertStringContainsString( 'id="' . $anchor . '"', $html, $meta . $suffix );
				$this->assertStringContainsString( '<tangible class="live-refresh">', $html );
				$pagination_label = '__de' === $suffix ? 'Seitennavigation' : 'Page navigation';
				$this->assertStringContainsString( '[lc_the_pagination screen_reader_text="' . $pagination_label . '"]', $html );
				$this->assertStringNotContainsString( '<style', $html );
				$this->assertStringNotContainsString( ' style="', $html );
				$this->assertStringNotContainsString( '/{Field name}/', $html );
				// Every card of the face links the post's own permalink: the
				// language layer answers a German article with the /de/ address.
				$this->assertStringContainsString( 'href="{Field url}"', $html );
				$this->assertStringNotContainsString( '127.0.0.1', $html, 'a repository file cannot carry an instance host' );
			}
			// The face's rules are the volume file's, scoped to the face's own
			// id, and they are the live rules — not a second design.
			$css = (string) file_get_contents( dirname( __DIR__, 4 ) . '/content/windpress/' . $stylesheet );
			$this->assertStringContainsString( '#' . $anchor . ' ', $css, $stylesheet );
			$this->assertStringContainsString( 'The face\'s own rules.', $css );
			$this->assertStringNotContainsString( '<style', $css );
		}

		// The German files are the German faces, not the English ones re-used.
		$this->assertStringContainsString( 'Weiterlesen', (string) file_get_contents( $paths['is_blog_posts_index__de'] ) );
		$this->assertStringNotContainsString( 'Read article', (string) file_get_contents( $paths['is_blog_posts_index__de'] ) );
		$this->assertStringContainsString( 'Alle Beiträge', (string) file_get_contents( $paths['is_archive_for_tax_category__de'] ) );
		$this->assertStringNotContainsString( 'Read article', (string) file_get_contents( $paths['is_archive_for_tax_category__de'] ) );
		$this->assertStringContainsString( 'Suche', (string) file_get_contents( $paths['is_search__de'] ) );
		$this->assertStringNotContainsString( 'Search articles', (string) file_get_contents( $paths['is_search__de'] ) );

		// The blog index's structured data names the site through the data
		// shortcode, so every instance answers with its own address; the
		// template engine resolves nothing inside a script block, and the live
		// template carried the host it was authored on.
		foreach ( array(
			'is_blog_posts_index'     => 'blog/',
			'is_blog_posts_index__de' => 'de/blog/',
		) as $index => $path ) {
			$html = (string) file_get_contents( $paths[ $index ] );
			$this->assertStringContainsString( '"url": "[linker_site_url]' . $path . '"', $html );
			$this->assertStringContainsString( '"url": "[linker_site_url]"', $html );
			$this->assertStringNotContainsString( '<site url', $html );
		}

		// The redesigned blog index's configurator CTA point at the tool's own
		// addresses, and the German face names it the way the rest of the site
		// does. The live template still carried the retired address on both
		// faces and the retired German name; the owner's rename ruling
		// (2026-10-10 #12, addresses 2026-10-12) is the change this assertion
		// holds — the German label is the pair the product page's button
		// carries (linker-commerce-de_DE_formal.po, "Open the Solution
		// Configurator" → "Lösungskonfigurator öffnen").
		$english = (string) file_get_contents( $paths['is_blog_posts_index'] );
		$this->assertSame( 1, substr_count( $english, 'href="/solution-configurator/"' ) );
		$this->assertStringContainsString( '>Open the Solution Configurator<', $english );
		$this->assertStringNotContainsString( 'linker-planner', $english );
		$german = (string) file_get_contents( $paths['is_blog_posts_index__de'] );
		$this->assertSame( 1, substr_count( $german, 'href="/de/loesungskonfigurator/"' ) );
		$this->assertSame( 1, substr_count( $german, '>Lösungskonfigurator öffnen<' ) );
		$this->assertStringNotContainsString( 'linker-planner', $german );
		$this->assertStringNotContainsString( 'Linker Planer', $german );
		foreach ( array( 'is_search', 'is_search__de', 'is_archive_for_tax_category', 'is_archive_for_tax_category__de' ) as $untouched ) {
			// The rename reaches the blog index only: the other two faces carry
			// no configurator link at all, so nothing of theirs changed.
			$this->assertStringNotContainsString( 'linker-planner', (string) file_get_contents( $paths[ $untouched ] ) );
			$this->assertStringNotContainsString( 'solution-configurator', (string) file_get_contents( $paths[ $untouched ] ) );
		}
	}

	/**
	 * Every prefixed declaration pair the volume publishes is ordered the way
	 * the compile keeps it: the `-webkit-` one first.
	 *
	 * WindPress compiles the volume with Lightning CSS, which drops the
	 * standard declaration of a pair written the other way round — it ships
	 * `-webkit-backdrop-filter` alone, Chromium computes `backdrop-filter:
	 * none`, and the frosted panel loses its blur. The blog single face hit
	 * this first (its context card), and the three faces #175 brought in hit it
	 * again: measured on the blogs instance 2026-10-16, the blog index rendered
	 * 188 804 pixels differently from the same rules delivered inline, and the
	 * only computed-style difference over the face's 290 elements was
	 * `backdrop-filter: blur(18px)` → `none`.
	 *
	 * Every prefixed declaration is looked at, line by line: a property written
	 * twice in one file (blog-category.css writes backdrop-filter twice) must
	 * have every pair checked, and the guard below is the one that watches the
	 * very file whose first pair is the same shape as the measured accident
	 * (test_the_prefixed_pair_guard_catches_each_reversed_pair proves it by
	 * reversing pairs in the file itself).
	 */
	public function test_volume_stylesheets_order_prefixed_pairs_the_way_the_compile_keeps_them(): void {
		$files = WindPressVolume::files();
		$this->assertNotSame( array(), $files );
		$checked = 0;
		foreach ( $files as $path ) {
			$css      = (string) file_get_contents( $path );
			$faults   = self::reversed_prefixed_pairs( $css );
			$checked += self::prefixed_pairs_with_a_twin( $css );
			$this->assertSame(
				array(),
				$faults,
				sprintf( '%s: %s', basename( $path ), implode( '; ', $faults ) )
			);
		}
		// The guard must see real pairs, while owner-approved design changes
		// can remove a frosted surface without breaking prefix ordering.
		$this->assertGreaterThan( 0, $checked, 'the volume carries pairs the guard reads' );
	}

	/**
	 * The guard behind the test above catches every reversed pair, not only the
	 * last one of a property.
	 *
	 * Repeating the same property across two surfaces catches a scanner that
	 * only examines the last pair. The fixture is independent of how many
	 * frosted surfaces the current page design happens to contain.
	 */
	public function test_the_prefixed_pair_guard_catches_each_reversed_pair(): void {
		// Independent two-surface fixture: the journal redesign may remove
		// glass panels while this compiler regression still covers repeated pairs.
		$css = ".first {\n -webkit-backdrop-filter: blur(18px);\n backdrop-filter: blur(18px);\n}\n.second {\n -webkit-backdrop-filter: blur(14px);\n backdrop-filter: blur(14px);\n}";
		$this->assertSame( array(), self::reversed_prefixed_pairs( $css ), 'the fixture starts with correct pairs' );

		$pairs = self::prefixed_pairs_with_a_twin( $css );
		$this->assertGreaterThan( 1, $pairs, 'the fixture covers more than the last pair' );
		for ( $reversed = 0; $reversed < $pairs; $reversed++ ) {
			$mutated = self::reverse_prefixed_pair( $css, $reversed );
			$this->assertNotSame( $css, $mutated, sprintf( 'pair %d was reversed', $reversed ) );
			$faults = self::reversed_prefixed_pairs( $mutated );
			$this->assertNotSame(
				array(),
				$faults,
				sprintf( 'the guard must catch pair %d when it is reversed', $reversed )
			);
			$this->assertCount( 1, $faults, sprintf( 'reversing pair %d is the file\'s only fault', $reversed ) );
		}
	}

	/**
	 * The prefixed declarations whose standard twin stands before them inside
	 * the same rule block: the order Lightning CSS punishes.
	 *
	 * A prefixed declaration without any twin is not a fault — the compiler
	 * adds the standard declaration itself. The search runs over the rule block
	 * the declaration belongs to, so a twin in a neighbouring rule cannot stand
	 * in for one.
	 *
	 * @param string $css The stylesheet.
	 * @return list<string> One line per fault, in file order.
	 */
	private static function reversed_prefixed_pairs( string $css ): array {
		$lines  = explode( "\n", $css );
		$faults = array();
		$count  = count( $lines );
		foreach ( $lines as $index => $line ) {
			$trimmed = trim( $line );
			if ( ! str_starts_with( $trimmed, '-webkit-' ) ) {
				continue;
			}
			$twin_declaration    = substr( $trimmed, strlen( '-webkit-' ) );
			list( $start, $end ) = self::rule_block( $lines, $index, $count );
			for ( $candidate = $start; $candidate <= $end; $candidate++ ) {
				if ( $candidate !== $index && trim( $lines[ $candidate ] ) === $twin_declaration ) {
					if ( $candidate < $index ) {
						$faults[] = sprintf(
							'line %d: -webkit-%s is preceded by its standard twin at line %d',
							$index + 1,
							$twin_declaration,
							$candidate + 1
						);
					}
					break;
				}
			}
		}
		return $faults;
	}

	/**
	 * How many prefixed declarations in the stylesheet have a standard twin in
	 * their own rule block — the pairs `reversed_prefixed_pairs()` judges.
	 *
	 * @param string $css The stylesheet.
	 */
	private static function prefixed_pairs_with_a_twin( string $css ): int {
		$lines = explode( "\n", $css );
		$count = count( $lines );
		$pairs = 0;
		foreach ( $lines as $index => $line ) {
			$trimmed = trim( $line );
			if ( ! str_starts_with( $trimmed, '-webkit-' ) ) {
				continue;
			}
			$twin_declaration    = substr( $trimmed, strlen( '-webkit-' ) );
			list( $start, $end ) = self::rule_block( $lines, $index, $count );
			for ( $candidate = $start; $candidate <= $end; $candidate++ ) {
				if ( $candidate !== $index && trim( $lines[ $candidate ] ) === $twin_declaration ) {
					++$pairs;
					break;
				}
			}
		}
		return $pairs;
	}

	/**
	 * The given declaration's rule block: the lines between the braces around
	 * it. Both ends are inclusive and bounded by the file.
	 *
	 * @param array<int, string> $lines The stylesheet's lines.
	 * @param int                $index The declaration's line.
	 * @param int                $count Line count.
	 * @return array{int, int} First and last line of the block.
	 */
	private static function rule_block( array $lines, int $index, int $count ): array {
		$start = 0;
		for ( $candidate = $index - 1; $candidate >= 0; $candidate-- ) {
			if ( str_contains( $lines[ $candidate ], '{' ) || str_contains( $lines[ $candidate ], '}' ) ) {
				$start = $candidate + 1;
				break;
			}
		}
		$end = $count - 1;
		for ( $candidate = $index + 1; $candidate < $count; $candidate++ ) {
			if ( str_contains( $lines[ $candidate ], '}' ) ) {
				$end = $candidate;
				break;
			}
		}
		return array( $start, $end );
	}

	/**
	 * The stylesheet with its nth (0-based) prefixed pair written the way the
	 * compiler punishes: the standard declaration first.
	 *
	 * @param string $css The stylesheet.
	 * @param int    $index Which pair to reverse, in file order.
	 * @throws \RuntimeException When the file carries fewer pairs than asked for.
	 */
	private static function reverse_prefixed_pair( string $css, int $index ): string {
		$lines       = explode( "\n", $css );
		$count       = count( $lines );
		$seen        = 0;
		$prefixed_at = -1;
		$twin_at     = -1;
		foreach ( $lines as $line_index => $line ) {
			$trimmed = trim( $line );
			if ( ! str_starts_with( $trimmed, '-webkit-' ) ) {
				continue;
			}
			$twin_declaration    = substr( $trimmed, strlen( '-webkit-' ) );
			list( $start, $end ) = self::rule_block( $lines, $line_index, $count );
			for ( $candidate = $start; $candidate <= $end; $candidate++ ) {
				if ( $candidate !== $line_index && trim( $lines[ $candidate ] ) === $twin_declaration ) {
					if ( $seen === $index ) {
						$prefixed_at = $line_index;
						$twin_at     = $candidate;
					}
					++$seen;
					break;
				}
			}
			if ( -1 !== $prefixed_at ) {
				break;
			}
		}
		if ( -1 === $prefixed_at || -1 === $twin_at || $twin_at < $prefixed_at ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- a test failure message, not page output.
			throw new \RuntimeException( sprintf( 'pair %d is not a reversed-able pair of this stylesheet', $index ) );
		}
		// Swap the two lines' contents, keeping each line's own indentation.
		$prefixed_line         = $lines[ $prefixed_at ];
		$twin_line             = $lines[ $twin_at ];
		$lines[ $prefixed_at ] = preg_replace( '/\S/', '', $prefixed_line ) . ltrim( $twin_line );
		$lines[ $twin_at ]     = preg_replace( '/\S/', '', $twin_line ) . ltrim( $prefixed_line );
		return implode( "\n", $lines );
	}

	/**
	 * A missing template is created with its meta key — its content slashed
	 * like every write — and an insert WordPress refuses stops the run.
	 */
	public function test_sync_inserts_slashed_and_raises_on_a_refused_insert(): void {
		$slashed = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'wp_slash',
			array(
				'return' => static function ( string $value ) use ( &$slashed ): string {
					++$slashed;
					return $value;
				},
			)
		);
		$error = Mockery::mock( \WP_Error::class );
		$error->allows( 'get_error_message' )->andReturn( 'Invalid post type' );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => $error,
			)
		);

		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'wp_insert_post refused the is_shop_page template: Invalid post type' );
		try {
			( new Templates() )->sync();
		} finally {
			Mockery::close();
		}
		$this->assertSame( 1, $slashed );
	}

	/**
	 * A missing template is created with its meta key; a second run updates the same posts and does not create another.
	 */
	public function test_sync_is_idempotent(): void {
		/**
		 * Published templates already assigned, keyed by LiveCanvas meta.
		 *
		 * @var array<string, WP_Post>
		 */
		$existing = array();
		$created  = 0;
		$updated  = 0;
		$slashes  = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$existing ): array {
					if ( in_array( $args['post_type'], array( 'page', 'lc_partial' ), true ) ) {
						return array();
					}
					$key = (string) ( $args['name'] ?? $args['meta_key'] ?? '' );
					return isset( $existing[ $key ] ) ? array( $existing[ $key ] ) : array();
				},
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function ( array $data ) use ( &$created, &$existing ): int {
					++$created;
					if ( isset( $data['post_name'] ) ) {
						$existing[ (string) $data['post_name'] ] = self::post( 500 + $created, 'created', (string) ( $data['post_title'] ?? '' ) );
					}
					return 500 + $created;
				},
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => static function ( int $id, string $key ) use ( &$existing ): bool {
					$existing[ $key ] = self::post( $id, 'from-file' );
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static function ( int $id ): WP_Post {
					return self::post( $id, 'stale' );
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function () use ( &$updated ): int {
					++$updated;
					return 1;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_slash',
			array(
				'return' => static function ( string $value ) use ( &$slashes ): string {
					++$slashes;
					return $value;
				},
			)
		);

		$templates = new Templates();
		$first     = $templates->sync();
		$second    = $templates->sync();

			$this->assertSame( 18, $created, 'the ten templates and the eight tool-page templates' );
			$this->assertSame( 18, $first['created'] );
		$this->assertSame( 0, $first['updated'] );
		$this->assertSame( 0, $second['created'] );
			$this->assertSame( 18, $second['updated'] );
			$this->assertSame( 18, $updated );
			// Every insert and every update slashes its content — both write paths.
			$this->assertSame( 36, $slashes );
	}

	/**
	 * Templates whose post content already matches the file are left alone:
	 * counted unchanged, never written.
	 */
	public function test_sync_counts_unchanged_templates_and_writes_nothing(): void {
		$paths   = Templates::paths();
		$keys    = array_keys( $paths );
		$titles  = array(
			'linker-compare'         => 'Compare products',
			'linker-compare-de'      => 'Produkte vergleichen',
			'linker-faq'             => 'FAQ & documents',
			'linker-faq-de'          => 'FAQ & Dokumente',
			'linker-advisor'         => 'Genie',
			'linker-advisor-de'      => 'Genie',
			'linker-configurator'    => 'Solution Configurator',
			'linker-configurator-de' => 'Lösungskonfigurator',
		);
		$updated = 0;
		$inserts = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $paths, $keys, $titles ): array {
					if ( in_array( $args['post_type'], array( 'page', 'lc_partial' ), true ) ) {
						return array();
					}
					$key = (string) ( $args['name'] ?? $args['meta_key'] ?? '' );
					$id  = 600 + array_search( $key, $keys, true );
					return array( self::post( $id, (string) file_get_contents( $paths[ $key ] ), $titles[ $key ] ?? 'Template' ) );
				},
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static function ( int $id ) use ( $paths, $keys, $titles ): WP_Post {
					$key = (string) $keys[ $id - 600 ];
					return self::post( $id, (string) file_get_contents( $paths[ $key ] ), $titles[ $key ] ?? 'Template' );
				},
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 0,
				'return' => static function () use ( &$inserts ): int {
					++$inserts;
					return 1;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times'  => 0,
				'return' => static function () use ( &$updated ): int {
					++$updated;
					return 1;
				},
			)
		);

		$report = ( new Templates() )->sync();

		$this->assertSame( 0, $report['created'] );
		$this->assertSame( 0, $report['updated'] );
			$this->assertSame( 18, $report['unchanged'] );
		$this->assertSame( 0, $inserts + $updated );
	}

	/**
	 * The product page's German export is written into the German twin of the
	 * English template — the post LiveCanvas renders on /de/produkt/<slug>/
	 * once the assignment is looked up in the request's language. Measured
	 * 2026-10-13 on the review instance before this: /product/<slug>/ rendered
	 * the export through template 234 while /de/produkt/<slug>/ rendered the
	 * legacy template the snapshot carried through its German twin.
	 */
	public function test_the_german_product_export_is_written_into_the_templates_german_twin(): void {
		$paths  = Templates::paths();
		$writes = array();
		$this->mock_templates( 234, 6913, $writes );

		$report = ( new Templates() )->sync();

		$this->assertArrayHasKey( 6913, $writes, 'the German twin carries the German export' );
		$this->assertSame( (string) file_get_contents( $paths['is_single_product__de'] ), $writes[6913]['post_content'] );
		$this->assertNotSame( (string) file_get_contents( $paths['is_single_product'] ), $writes[6913]['post_content'] );
		$this->assertSame( 1, $report['de_twins_updated'] );
		$this->assertSame( array(), $report['de_twins_missing'] );
	}

	/**
	 * A German twin that already holds the export is left alone: sync is
	 * idempotent, and a second run writes nothing.
	 */
	public function test_a_current_german_twin_is_not_written_again(): void {
		$paths  = Templates::paths();
		$writes = array();
		$this->mock_templates( 234, 6913, $writes, (string) file_get_contents( $paths['is_single_product__de'] ) );

		$report = ( new Templates() )->sync();

		$this->assertSame( array(), $writes );
		$this->assertSame( 0, $report['de_twins_updated'] );
		$this->assertSame( array(), $report['de_twins_missing'] );
	}

	/**
	 * A page type whose anchor has no German twin is reported, and no template
	 * is invented for it: the twin is a translation decision this class does
	 * not own, and present() prints the list.
	 */
	public function test_a_page_type_without_a_german_twin_is_reported_and_not_invented(): void {
		$writes = array();
		$this->mock_templates( 234, 0, $writes );

		$report = ( new Templates() )->sync();

		$this->assertSame( array(), $writes );
		$this->assertSame( 0, $report['de_twins_updated'] );
		$this->assertSame( array( 'is_single_product' ), $report['de_twins_missing'] );
	}

	/**
	 * A template created while Polylang runs gets the site's source language
	 * when it has none, and one that already carries a language keeps it (#11's
	 * LiveCanvas forensics: a languageless source is silently skipped when its
	 * German twin is paired).
	 */
	public function test_sync_assigns_the_source_language_to_languageless_templates(): void {
		$assigned = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static fn(): array => array(), // Nothing existing: sync creates all ten.
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function () {
					static $id = 700;
					return ++$id;
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_get_post_language',
			array(
				'return' => static fn(): bool => false, // The API answers false for a post without a language.
			)
		);
		WP_Mock::userFunction(
			'pll_set_post_language',
			array(
				'return' => static function ( int $id, string $slug ) use ( &$assigned ): bool {
					$assigned[ $id ] = $slug;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );

		( new Templates() )->sync();

			$this->assertCount( 18, $assigned, 'the ten templates and the eight tool-page templates' );
			$this->assertSame( array_fill( 0, 18, 'en' ), array_values( $assigned ) );
	}

	/**
	 * Polylang without configured languages has no source language to name:
	 * the templates stay languageless and a later `wp linker-i18n setup
	 * --assign` covers them.
	 */
	public function test_sync_skips_the_language_when_no_language_is_configured(): void {
		$assigned = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static fn(): array => array(),
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function () {
					static $id = 800;
					return ++$id;
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => false ) ); // Polylang's answer without languages.
		WP_Mock::userFunction(
			'pll_set_post_language',
			array(
				'return' => static function ( int $id, string $slug ) use ( &$assigned ): bool {
					$assigned[ $id ] = $slug;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );

		$report = ( new Templates() )->sync();

		$this->assertSame( array(), $assigned );
			$this->assertSame( 18, $report['created'] );
	}

	/**
	 * Each tool page carries the LiveCanvas per-post choice of its own
	 * language's template: the page's template loader reads the choice from
	 * the queried post, so the English page and the German page name
	 * different templates.
	 */
	public function test_tool_pages_get_their_template_choice(): void {
		$assigned = array();
		$pages    = array(
			array(
				'ID'        => 5385,
				'post_name' => 'compare-products',
				'post_type' => 'page',
			),
			array(
				'ID'        => 6608,
				'post_name' => 'compare-products',
				'post_type' => 'page',
			),
			array(
				'ID'        => 932,
				'post_name' => 'faq-download',
				'post_type' => 'page',
			),
			array(
				'ID'        => 6871,
				'post_name' => 'faq-download',
				'post_type' => 'page',
			),
			array(
				'ID'        => 4101,
				'post_name' => 'genie',
				'post_type' => 'page',
			),
			array(
				'ID'        => 4102,
				'post_name' => 'genie',
				'post_type' => 'page',
			),
		);
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $pages ): array {
					if ( 'page' !== $args['post_type'] ) {
						return array();
					}
					return array_values(
						array_filter(
							self::wp_posts( $pages ),
							static fn( WP_Post $post ): bool => $post->post_name === $args['name']
						)
					);
				},
			)
		);
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
		WP_Mock::userFunction(
			'wp_slash',
			array(
				'return' => static fn( $value ) => $value,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static fn(): int => 700,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'is_wp_error',
			array(
				'return' => false,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'times'  => '0+',
				'return' => static function ( int $id, string $key, $value ) use ( &$assigned ): bool {
					$assigned[ $id ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'pll_get_post_language',
			array(
				'return' => static fn ( int $id ): string => in_array( $id, array( 6608, 6871, 4102 ), true ) ? 'de' : 'en',
				'times'  => '0+',
			)
		);
		// sync() also gives every template it creates or updates the site's
		// source language (assign_source_language()).
		WP_Mock::userFunction(
			'pll_default_language',
			array(
				'return' => 'en',
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'pll_set_post_language',
			array(
				'return' => true,
				'times'  => '0+',
			)
		);

		( new Templates() )->sync();

		$this->assertSame( 'linker-compare', $assigned[5385] );
		$this->assertSame( 'linker-compare-de', $assigned[6608] );
			$this->assertSame( 'linker-faq', $assigned[932] );
			$this->assertSame( 'linker-faq-de', $assigned[6871] );
			$this->assertSame( 'linker-advisor', $assigned[4101] );
			$this->assertSame( 'linker-advisor-de', $assigned[4102] );
	}

	/**
	 * A missing or empty header export stops sync() before any write: the
	 * Woo templates and the header partials keep what they had.
	 */
	public function test_sync_refuses_a_missing_header_before_writing_templates(): void {
		$dir     = sys_get_temp_dir() . '/linker-commerce-missing-header-' . getmypid();
		$partial = $dir . '/partials';
		mkdir( $partial . '/de', 0777, true );
		$english = $partial . '/header.html';
		$german  = $partial . '/de/header.html';
		file_put_contents( $english, '<header>english</header>' );
		file_put_contents( $german, '<header>deutsch</header>' );

		$templates_written = 0;
		$partials_written  = 0;
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function () use ( &$templates_written ): int {
					++$templates_written;
					return 1;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$templates_written, &$partials_written ): int {
					if ( isset( $data['post_title'] ) ) {
						++$templates_written;
					} else {
						++$partials_written;
					}
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );

		$templates = new Templates();
		try {
			try {
				$templates->sync( array( $english, $dir . '/partials/missing-header.html' ) );
				$this->fail( 'A missing header source should stop sync() before any write' );
			} catch ( \RuntimeException $e ) {
				$this->assertStringContainsString( 'missing or empty', $e->getMessage() );
				$this->assertStringContainsString( 'missing-header.html', $e->getMessage() );
			}
			$this->assertSame( 0, $templates_written, 'templates must not be written when a header source is missing' );
			$this->assertSame( 0, $partials_written, 'partials must not be written when a header source is missing' );

			$templates_written = 0;
			file_put_contents( $german, "   \n" );
			try {
				$templates->sync( array( $english, $german ) );
				$this->fail( 'An empty header source should stop sync() before any write' );
			} catch ( \RuntimeException $e ) {
				$this->assertStringContainsString( 'missing or empty', $e->getMessage() );
				$this->assertStringContainsString( 'de/header.html', $e->getMessage() );
			}
			$this->assertSame( 0, $templates_written );
			$this->assertSame( 0, $partials_written );
		} finally {
			foreach ( array( $english, $german ) as $path ) {
				if ( file_exists( $path ) ) {
					unlink( $path );
				}
			}
			rmdir( $partial . '/de' );
			rmdir( $partial );
			rmdir( $dir );
		}
	}

		/**
		 * The installed English header and its Polylang twin are written from
		 * the two exports. The twin's slug is kopfzeile, the live German slug,
		 * not header. The German export is already localized, so a repeat
		 * present keeps the German addresses.
		 */
	public function test_sync_writes_the_localized_header_partials(): void {
		$files   = Templates::header_partials();
		$written = array();
		$twins   = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ): array {
					if ( 'lc_partial' === ( $args['post_type'] ?? '' ) && 'header' === ( $args['name'] ?? '' ) ) {
						return array( self::header_partial( 17, '2026-10-01 09:00:00', 'stale header', 'header' ) );
					}
					return array();
				},
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static function ( int $id, string $language ) use ( &$twins ): int {
					$twins[] = array( $id, $language );
					return 17 === $id && 'de' === $language ? 6919 : 0;
				},
			)
		);
		WP_Mock::userFunction( 'get_post', array( 'return' => static fn( int $id ): WP_Post => self::header_partial( $id, 'stale', 'stale header', 6919 === $id ? 'kopfzeile' : 'header' ) ) );
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$written ): int {
					$written[ (int) $data['ID'] ] = (string) $data['post_content'];
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );

		( new Templates() )->sync();

		$this->assertSame( array( array( 17, 'de' ) ), $twins );
		$this->assertSame( (string) file_get_contents( $files[0] ), $written[17] );
		$this->assertSame( (string) file_get_contents( $files[1] ), $written[6919] );
		$this->assertStringContainsString( 'href="/de/loesung/heimspeicher/"', $written[6919] );
		$this->assertStringNotContainsString( 'href="/solution/', $written[6919] );
			$this->assertSame( 35, substr_count( $written[17], '<rect x=' ) );
	}

		/**
		 * The footer exports name the account route in the site's words.
		 * present() writes these files onto the English footer and its twin.
		 */
	public function test_footer_exports_name_the_solution_draft(): void {
		$files = Templates::footer_partials();

		$english = (string) file_get_contents( $files[0] );
		$german  = (string) file_get_contents( $files[1] );

		$this->assertStringContainsString( '<span>Solution draft</span>', $english );
		$this->assertStringContainsString( '<span>Lösungsentwurf</span>', $german );
		$this->assertStringNotContainsString( '>Cart<', $english );
		$this->assertStringNotContainsString( 'Warenkorb', $german );
		$this->assertNotSame( '', trim( $english ) );
		$this->assertNotSame( '', trim( $german ) );
	}

		/**
		 * The German partial is not the same slug. A date-ordered same-slug
		 * lookup would return the newer kopfzeile row if it were queried as
		 * header; the write still follows pll_get_post from the English anchor.
		 */
	public function test_header_twin_is_resolved_from_the_english_partial_not_the_slug(): void {
		$files   = Templates::header_partials();
		$english = (string) file_get_contents( $files[0] );
		$german  = (string) file_get_contents( $files[1] );
		$written = array();
		$queried = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$queried ): array {
					if ( 'lc_partial' !== ( $args['post_type'] ?? '' ) ) {
						return array();
					}
					$queried[] = $args;
					// A same-slug query is the failure under test: the newer
					// German row would come back, and its slug is not header.
					if ( array( 'header' ) === ( $args['post_name__in'] ?? null ) ) {
						return array( self::header_partial( 6919, '2026-10-12 09:00:00', 'stale', 'kopfzeile' ) );
					}
					if ( 'header' === ( $args['name'] ?? '' ) ) {
						return array( self::header_partial( 17, '2026-10-01 09:00:00', 'stale', 'header' ) );
					}
					return array();
				},
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static fn( int $id, string $language ): int => 17 === $id && 'de' === $language ? 6919 : 0,
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static fn( int $id ): WP_Post => self::header_partial( $id, 'stale', 'stale', 6919 === $id ? 'kopfzeile' : 'header' ),
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$written ): int {
					$written[ (int) $data['ID'] ] = (string) $data['post_content'];
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );

		( new Templates() )->sync();

		$this->assertSame( array(), array_values( array_filter( $queried, static fn( array $args ): bool => isset( $args['post_name__in'] ) ) ) );
		$this->assertSame( $english, $written[17] );
		$this->assertSame( $german, $written[6919] );
		$this->assertNotSame( $written[17], $written[6919] );
	}

		/**
		 * An English header whose German twin cannot be resolved stops the
		 * sync. Neither language is written, and the run does not report the
		 * skipped language as a success.
		 */
	public function test_a_missing_german_header_twin_refuses_before_any_partial_write(): void {
		$written = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ): array {
					if ( 'lc_partial' === ( $args['post_type'] ?? '' ) && 'header' === ( $args['name'] ?? '' ) ) {
						return array( self::header_partial( 17, '2026-10-01 09:00:00', 'stale', 'header' ) );
					}
					return array();
				},
			)
		);
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function () use ( &$written ): int {
					++$written;
					return 1;
				},
			)
		);
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );

		try {
			( new Templates() )->sync();
			$this->fail( 'A missing German header twin should stop sync()' );
		} catch ( \RuntimeException $e ) {
			$this->assertStringContainsString( 'German header partial could not be resolved', $e->getMessage() );
			$this->assertStringContainsString( '17', $e->getMessage() );
		}
		$this->assertSame( 0, $written, 'neither language is written when the twin is missing' );
	}

	/**
	 * The page's rows as WP_Post objects.
	 *
	 * @param array<int, array<string, mixed>> $rows Rows.
	 * @return list<WP_Post>
	 */
	private static function wp_posts( array $rows ): array {
		$posts = array();
		foreach ( $rows as $row ) {
			$posts[] = new WP_Post(
				(object) array(
					'ID'           => (int) $row['ID'],
					'post_name'    => (string) $row['post_name'],
					'post_type'    => (string) $row['post_type'],
					'post_status'  => 'publish',
					'post_title'   => 'Page',
					'post_content' => '',
				)
			);
		}
		return $posts;
	}

	/**
	 * A published header partial. post_date is the trap: the German twin is newer.
	 *
	 * @param int    $id      Post id.
	 * @param string $date    post_date, MySQL datetime.
	 * @param string $content Body.
	 * @param string $slug    post_name. Live German header is kopfzeile, not header.
	 */
	private static function header_partial( int $id, string $date, string $content = 'stale header', string $slug = 'header' ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'           => $id,
				'post_type'    => 'lc_partial',
				'post_status'  => 'publish',
				'post_name'    => $slug,
				'post_date'    => $date,
				'post_content' => $content,
				'post_title'   => 'kopfzeile' === $slug ? 'Kopfzeile' : 'Header',
			)
		);
	}

	/**
	 * A site whose product page type already has an English template — the
	 * anchor in the German-twin logic — with the German twin (or 0 for a site
	 * that has none). Records every post write in $writes.
	 *
	 * The site has no header partial and no tool page: those paths are covered
	 * by their own tests, and an empty answer keeps this one's writes to the
	 * twin the test is about.
	 *
	 * @param int                              $anchor          English template post id.
	 * @param int                              $twin            Its German twin, 0 when the site has none.
	 * @param array<int, array<string, mixed>> $writes Post writes, by id, filled in by the mock.
	 * @param string                           $twin_content    The twin's current body.
	 */
	private function mock_templates( int $anchor, int $twin, array &$writes, string $twin_content = 'stale legacy template' ): void {
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		// phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.FoundAfterLastUsed -- pll_get_post's $language, mirrored for the call shape.
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn( int $id, string $lang ): int => $id === $anchor ? $twin : 0 ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_set_post_language', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $anchor ): array {
					if ( in_array( $args['post_type'], array( 'page', 'lc_partial' ), true ) ) {
						return array();
					}
					if ( 'is_single_product' === (string) ( $args['meta_key'] ?? '' ) ) {
						return array( self::post( $anchor, 'stale export', 'Single product' ) );
					}
					return array();
				},
			)
		);
		$english = (string) file_get_contents( Templates::paths()['is_single_product'] );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static function ( int $id ) use ( $anchor, $twin, $twin_content, $english ): WP_Post {
					if ( $id === $twin ) {
						return self::post( $id, $twin_content, 'Vorlage für einzelnes Produkt' );
					}
					// The English anchor already holds its export: the only post
					// this sync has left to write is the German twin.
					return self::post( $id, $id === $anchor ? $english : 'stale export' );
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function (): int {
					static $id = 700;
					return ++$id;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$writes ): int {
					$writes[ (int) $data['ID'] ] = $data;
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );
	}

	/**
	 * A published LiveCanvas template post.
	 *
	 * @param int    $id      Post id.
	 * @param string $content Body.
	 * @param string $title   Post title, the tool templates' own words.
	 */
	private static function post( int $id, string $content = '', string $title = 'Template' ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'           => $id,
				'post_type'    => 'lc_dynamic_template',
				'post_status'  => 'publish',
				'post_content' => $content,
				'post_title'   => $title,
			)
		);
	}
}
