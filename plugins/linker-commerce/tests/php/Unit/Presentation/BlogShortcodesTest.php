<?php
/**
 * Tests for the blog single template's data shortcodes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\BlogShortcodes;
use Linker\Commerce\Presentation\JournalTitles;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;
use WP_Term;

/**
 * Tests for BlogShortcodes.
 *
 * The two fragments the blog single template renders are pinned here, where no
 * instance is needed: the meta Category prints links to the archives of the
 * page's language, and the related grid holds exactly the articles that share a
 * category with the one on display. The rendered page itself — the loop, the
 * LiveCanvas stamp, the addresses the permalink layer builds on an instance —
 * is the integration and e2e suites' subject.
 *
 * Polylang's functions are not loaded in the unit process. WP_Mock defines one
 * when a test stubs it and it stays defined for the rest of the run, so every
 * test that stubs `pll_current_language` also stubs what the language guard can
 * reach behind it, whichever test ran first.
 *
 * @covers \Linker\Commerce\Presentation\BlogShortcodes
 */
final class BlogShortcodesTest extends TestCase {

	/**
	 * The translated search heading supplied by the active test.
	 *
	 * @var string
	 */
	private string $search_heading = 'All posts';

	/**
	 * Translation and escaping return their input except the search heading.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( '__' )->with( 'All posts', 'linker-commerce' )->andReturnUsing( fn(): string => $this->search_heading );
		$this->plain_text();
		// These native fragment fixtures have no Polylang source-pair data.
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => false ) );
	}

	/**
	 * The shortcodes this plugin adds for the blog template.
	 */
	public function test_register_adds_the_blog_shortcodes(): void {
		$codes = new BlogShortcodes();
		WP_Mock::userFunction(
			'add_shortcode',
			array(
				'times' => 1,
				'args'  => array( 'linker_blog_post_categories', array( $codes, 'post_categories' ) ),
			)
		);
		WP_Mock::userFunction(
			'add_shortcode',
			array(
				'times' => 1,
				'args'  => array( 'linker_blog_related_posts', array( $codes, 'related_posts' ) ),
			)
		);
		WP_Mock::userFunction(
			'add_shortcode',
			array(
				'times' => 1,
				'args'  => array( 'linker_blog_share', array( $codes, 'share' ) ),
			)
		);

		WP_Mock::expectActionAdded( 'init', array( JournalTitles::class, 'register' ) );
		WP_Mock::expectFilterAdded( 'pre_get_document_title', array( $codes, 'empty_search_title' ), 60 );
		$codes->register();

		$this->assertConditionsMet();
	}

	/**
	 * A cleared journal search gets a useful title without altering other pages.
	 *
	 * @dataProvider search_title_cases
	 * @param bool   $is_search Whether the request is a search.
	 * @param mixed  $type      The search's post type.
	 * @param string $query     The actual search text.
	 * @param string $heading   The translated heading.
	 * @param string $title     The SEOPress title.
	 * @param string $expected  The expected title.
	 */
	public function test_only_empty_journal_search_gets_a_named_title( bool $is_search, mixed $type, string $query, string $heading, string $title, string $expected ): void {
		WP_Mock::userFunction( 'is_search' )->andReturn( $is_search );
		WP_Mock::userFunction( 'get_query_var' )->with( 'post_type' )->andReturn( $type );
		WP_Mock::userFunction( 'get_search_query' )->with( false )->andReturn( $query );
		$this->search_heading = $heading;
		$this->assertSame( $expected, ( new BlogShortcodes() )->empty_search_title( $title ) );
	}

	/**
	 * Search-title cases for both languages and the unaffected requests.
	 *
	 * @return array<string, array{bool, mixed, string, string, string, string}>
	 */
	public static function search_title_cases(): array {
		return array(
			'empty German journal'  => array( true, 'post', '', 'Alle Beiträge', 'Suchergebnisse für „“ | Linker', 'Alle Beiträge | Linker' ),
			'empty English journal' => array( true, 'post', '', 'All posts', '" " | Linker', 'All posts | Linker' ),
			'zero is a query'       => array( true, 'post', '0', 'Alle Beiträge', '0 | Linker', '0 | Linker' ),
			'normal journal'        => array( true, 'post', 'backup', 'All posts', 'backup | Linker', 'backup | Linker' ),
			'general search'        => array( true, array( 'post', 'page', 'product' ), '', 'Alle Beiträge', 'Search | Linker', 'Search | Linker' ),
			'not search'            => array( false, 'post', '', 'All posts', 'Page | Linker', 'Page | Linker' ),
		);
	}

	/**
	 * The share row names each network through the catalog (#264 M1): the
	 * template calls this shortcode instead of LiveCanvas's English one, the
	 * link text is what the template's script turns into the accessible name,
	 * and the German catalog carries the German sentence.
	 */
	public function test_the_share_row_carries_the_german_network_labels(): void {
		WP_Mock::userFunction(
			'shortcode_atts',
			array(
				'return' => static fn( array $defaults, array $given ): array => array_merge( $defaults, $given ),
			)
		);
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => 551 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://linker.test/de/beitrag/' ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => 'Ein Beitrag' ) );

		$html = ( new BlogShortcodes() )->share( array( 'class' => 'reader-share-links' ) );

		$this->assertStringContainsString( 'class="lc-sharing-buttons reader-share-links"', $html );
		$this->assertStringContainsString( 'title="Share on Facebook" aria-label="Share on Facebook"', $html );
		$this->assertStringContainsString( 'title="Share on WhatsApp" aria-label="Share on WhatsApp"', $html );
		$this->assertStringContainsString( 'title="Share on Telegram" aria-label="Share on Telegram"', $html );
		$this->assertStringContainsString( 'title="Share on Twitter" aria-label="Share on Twitter"', $html );
		$this->assertStringContainsString( 'https://www.facebook.com/sharer.php?u=https%3A%2F%2Flinker.test%2Fde%2Fbeitrag%2F', $html );
		$this->assertStringContainsString( 'https://twitter.com/share?url=https%3A%2F%2Flinker.test%2Fde%2Fbeitrag%2F&text=Ein%20Beitrag', $html );
		// The unit process renders the English source; the German sentence the
		// instance prints is the catalog's (the coverage gate holds it).
		$catalog = (string) file_get_contents( \dirname( __DIR__, 4 ) . '/languages/linker-commerce-de_DE_formal.po' );
		$this->assertStringContainsString( "msgid \"Share on %s\"\nmsgstr \"Auf %s teilen\"", $catalog );
	}

	/**
	 * An English article's category prints as a link to the English archive —
	 * the shape the face carries, `/category/<slug>/`.
	 */
	public function test_the_category_links_the_english_archive(): void {
		$term = $this->term( 10, 'System Design', 'system-design' );
		$this->on_an_article( 551, array( $term ) );
		$this->language( 'en' );
		WP_Mock::userFunction( 'pll_get_term_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( $term ),
				'return' => 'https://linker.test/category/system-design/',
			)
		);

		$html = ( new BlogShortcodes() )->post_categories();

		$this->assertSame( '<a href="https://linker.test/category/system-design/">System Design</a>', $html );
	}

	/**
	 * A German article's category prints as a link to the German archive —
	 * `/de/category/<slug>/`, the address the German classifier answers.
	 */
	public function test_the_category_links_the_german_archive(): void {
		$english = $this->term( 10, 'System Design', 'system-design' );
		$german  = $this->term( 15, 'Systemauslegung', 'system-design' );
		$this->on_an_article( 6893, array( $english ) );
		$this->language( 'de' );
		WP_Mock::userFunction( 'pll_get_term_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_get_term',
			array(
				'args'   => array( 10, 'de' ),
				'return' => 15,
			)
		);
		WP_Mock::userFunction(
			'get_term',
			array(
				'args'   => array( 15, 'category' ),
				'return' => $german,
			)
		);
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( $german ),
				'return' => 'https://linker.test/de/category/system-design/',
			)
		);

		$html = ( new BlogShortcodes() )->post_categories();

		$this->assertSame( '<a href="https://linker.test/de/category/system-design/">Systemauslegung</a>', $html );
	}

	/**
	 * A German page never links an English archive: a term without a German
	 * twin prints nothing.
	 */
	public function test_a_category_without_a_twin_is_not_linked_on_the_german_page(): void {
		$this->on_an_article( 6893, array( $this->term( 10, 'System Design', 'system-design' ) ) );
		$this->language( 'de' );
		WP_Mock::userFunction( 'pll_get_term_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_get_term',
			array(
				'args'   => array( 10, 'de' ),
				'return' => 0,
			)
		);

		$this->assertSame( '', ( new BlogShortcodes() )->post_categories() );
	}

	/**
	 * An article with no category prints no link — and no link either when the
	 * taxonomy query fails.
	 */
	public function test_an_article_without_categories_prints_no_link(): void {
		$this->on_an_article( 551, false );

		$this->assertSame( '', ( new BlogShortcodes() )->post_categories() );
	}

	/**
	 * The related grid holds the articles that share a category with the one
	 * on display: same taxonomy terms, the article itself excluded, newest
	 * first, at most three.
	 */
	public function test_related_posts_are_the_articles_sharing_a_category(): void {
		$related = $this->post( 552, 'What Installers Should Check', 'installer-checklist' );
		$term    = $this->term( 10, 'System Design', 'system-design' );
		$this->on_an_article( 551, array( $term ) );
		$this->language( 'en' );
		WP_Mock::userFunction( 'pll_get_term_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'args'   => array(
					array(
						'post_type'           => 'post',
						'post_status'         => 'publish',
						'category__in'        => array( 10 ),
						'post__not_in'        => array( 551 ),
						'posts_per_page'      => BlogShortcodes::RELATED_LIMIT,
						'orderby'             => 'date',
						'order'               => 'DESC',
						'ignore_sticky_posts' => true,
						'no_found_rows'       => true,
					),
				),
				'return' => array( $related ),
			)
		);
		WP_Mock::userFunction(
			'get_post_thumbnail_id',
			array(
				'args'   => array( $related ),
				'return' => 0,
			)
		);
		$this->card_reads( $related, 'M j, Y', 'May 29, 2026' );

		$html = ( new BlogShortcodes() )->related_posts();

		$this->assertSame( 1, substr_count( $html, '<article class="lc-block">' ) );
		$this->assertStringContainsString( 'href="https://linker.test/installer-checklist/"', $html );
		$this->assertStringContainsString( 'What Installers Should Check', $html );
		$this->assertConditionsMet();
	}

	/**
	 * An article without a category shares nothing: the grid stays empty and
	 * no query runs — never a fallback to the newest articles.
	 */
	public function test_an_article_without_a_category_prints_no_grid(): void {
		$this->on_an_article( 551, array() );

		$this->assertSame( '', ( new BlogShortcodes() )->related_posts() );
	}

	/**
	 * The card is the live card's anatomy — its classes, its image attributes,
	 * its excerpt and its own words — and carries no inline style, because
	 * every rule of the face lives in the WindPress volume.
	 */
	public function test_the_card_carries_the_live_anatomy(): void {
		$related = $this->post( 552, 'What Installers Should Check', 'installer-checklist' );
		$this->on_an_article( 551, array( $this->term( 10, 'System Design', 'system-design' ) ) );
		$this->language( 'en' );
		WP_Mock::userFunction( 'pll_get_term_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( $related ) ) );
		$this->card_reads( $related, 'M j, Y', 'May 29, 2026' );
		WP_Mock::userFunction(
			'get_post_thumbnail_id',
			array(
				'args'   => array( $related ),
				'return' => 700,
			)
		);
		WP_Mock::userFunction(
			'wp_get_attachment_image_url',
			array(
				'args'   => array( 700, 'medium_large' ),
				'return' => 'https://linker.test/up/card.jpg',
			)
		);
		WP_Mock::userFunction(
			'wp_get_attachment_image_srcset',
			array(
				'args'   => array( 700, 'medium_large' ),
				'return' => 'https://linker.test/up/card-300x200.jpg 300w, https://linker.test/up/card.jpg 600w',
			)
		);

		$html = ( new BlogShortcodes() )->related_posts();

		$this->assertStringContainsString( '<article class="lc-block"><a href="https://linker.test/installer-checklist/" class="tv-blog-single-related-card">', $html );
		$this->assertStringContainsString( '<div class="tv-blog-single-related-img">', $html );
		$this->assertStringContainsString(
			'<img src="https://linker.test/up/card.jpg" srcset="https://linker.test/up/card-300x200.jpg 300w, https://linker.test/up/card.jpg 600w" sizes="(max-width: 300px) 100vw, 300px" loading="lazy" alt="">',
			$html
		);
		$this->assertStringContainsString( '<time datetime="2026-05-29T00:00:00+00:00">May 29, 2026</time>', $html );
		$this->assertStringContainsString( '<span aria-hidden="true">&middot;</span>', $html );
		$this->assertStringContainsString( '<h3 class="tv-blog-single-related-card-title">What Installers Should Check</h3>', $html );
		$this->assertStringContainsString( '<div class="tv-blog-single-related-excerpt">A pre-installation checklist.</div>', $html );
		$this->assertStringContainsString( '<span class="tv-blog-single-related-arrow">Read article<svg', $html );
		$this->assertStringNotContainsString( 'style="', $html );
	}

	/**
	 * Without an image the card prints the live face's placeholder figure.
	 */
	public function test_the_card_prints_the_placeholder_without_an_image(): void {
		$related = $this->post( 552, 'What Installers Should Check', 'installer-checklist' );
		$this->on_an_article( 551, array( $this->term( 10, 'System Design', 'system-design' ) ) );
		$this->language( 'en' );
		WP_Mock::userFunction( 'pll_get_term_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( $related ) ) );
		WP_Mock::userFunction(
			'get_post_thumbnail_id',
			array(
				'args'   => array( $related ),
				'return' => 0,
			)
		);
		$this->card_reads( $related, 'M j, Y', 'May 29, 2026' );

		$html = ( new BlogShortcodes() )->related_posts();

		$this->assertStringContainsString( '<div class="tv-blog-single-img-fallback">', $html );
		$this->assertStringNotContainsString( '<img', $html );
	}

	/**
	 * The card's date is the page's date: the English format in English, the
	 * German one in German, the way the live face prints them.
	 */
	public function test_the_card_date_follows_the_page_language(): void {
		$related = $this->post( 552, 'Was Installateure prüfen sollten', 'hybridwechselrichter-pruefen' );
		$this->on_an_article( 6893, array( $this->term( 15, 'Systemauslegung', 'system-design' ) ) );
		$this->language( 'de' );
		WP_Mock::userFunction( 'pll_get_term_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( $related ) ) );
		WP_Mock::userFunction(
			'get_post_thumbnail_id',
			array(
				'args'   => array( $related ),
				'return' => 0,
			)
		);
		$this->card_reads( $related, 'd.m.Y', '29.05.2026' );

		$html = ( new BlogShortcodes() )->related_posts();

		$this->assertStringContainsString( '<time datetime="2026-05-29T00:00:00+00:00">29.05.2026</time>', $html );
		$this->assertConditionsMet();
	}

	/**
	 * The article on display and the categories it carries, or the taxonomy
	 * query's failure.
	 *
	 * @param int                 $id    The article's id.
	 * @param list<WP_Term>|false $terms The categories.
	 */
	private function on_an_article( int $id, array|false $terms ): void {
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => $id ) );
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'args'   => array( $id, 'category' ),
				'return' => $terms,
			)
		);
	}

	/**
	 * The request's language.
	 *
	 * @param string $language `en` or `de`.
	 */
	private function language( string $language ): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => $language ) );
	}

	/**
	 * Everything the card reads off the related article: its date in the given
	 * format, and the words and link that do not depend on the language.
	 *
	 * @param WP_Post $related The related article.
	 * @param string  $format  The page language's date format.
	 * @param string  $date    The date that format produces.
	 */
	private function card_reads( WP_Post $related, string $format, string $date ): void {
		WP_Mock::userFunction(
			'get_the_date',
			array(
				'args'   => array( 'c', $related ),
				'return' => '2026-05-29T00:00:00+00:00',
			)
		);
		WP_Mock::userFunction(
			'get_the_date',
			array(
				'args'   => array( $format, $related ),
				'return' => $date,
			)
		);
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'args'   => array( $related ),
				'return' => $related->post_title,
			)
		);
		WP_Mock::userFunction(
			'get_the_excerpt',
			array(
				'args'   => array( $related ),
				'return' => 'A pre-installation checklist.',
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $related ),
				'return' => 'https://linker.test/installer-checklist/',
			)
		);
	}

	/**
	 * A category as WordPress hands it over.
	 *
	 * @param int    $id   Term id.
	 * @param string $name Term name.
	 * @param string $slug Term slug.
	 */
	private function term( int $id, string $name, string $slug ): WP_Term {
		return new WP_Term(
			(object) array(
				'term_id'  => $id,
				'name'     => $name,
				'slug'     => $slug,
				'taxonomy' => 'category',
			)
		);
	}

	/**
	 * An article as WordPress hands it over.
	 *
	 * @param int    $id    Post id.
	 * @param string $title Post title.
	 * @param string $name  Post name.
	 */
	private function post( int $id, string $title, string $name ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'         => $id,
				'post_title' => $title,
				'post_name'  => $name,
				'post_type'  => 'post',
			)
		);
	}
}
