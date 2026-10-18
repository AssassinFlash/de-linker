<?php
/**
 * The blog single face, as the instance's own front end renders it.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use WP_Post;
use WP_Term;

/**
 * The article page's two data areas and its band, read over HTTP from the
 * instance: the meta Category links the article's own archive, the related grid
 * holds an article that shares a category, and the band carries the live words
 * rather than the shortcode's default.
 *
 * Run conditions, both of them instance state rather than code:
 *
 * - The suite runs against a local instance with LINKER_WP_ROOT and
 *   LINKER_INTEGRATION=1 (`just test`, or `LINKER_WP_ROOT=<instance>/wordpress
 *   php vendor/bin/phpunit -c phpunit.integration.xml.dist`); the unit suite
 *   skips it.
 * - The instance has the blog single template installed (`just present
 *   <instance>`) and the live snapshot loaded (`just pull load`), which is
 *   where the article, its categories and its related article come from. An
 *   instance without them skips test by test — a red assertion would say
 *   nothing about this face.
 *
 * @covers \Linker\Commerce\Presentation\BlogShortcodes
 */
final class BlogSingleFaceTest extends IntegrationTestCase {

	/**
	 * The live snapshot's article, the one the closure round reproduced the
	 * face against (post 551 of the snapshot).
	 */
	private const ARTICLE_SLUG = 'hybrid-inverter-vs-ac-coupled-storage';

	/**
	 * The instance's front end.
	 */
	private function front(): string {
		$home = home_url( '/' );
		$this->assertNotSame( '', $home );
		return rtrim( $home, '/' );
	}

	/**
	 * The snapshot article, or a skip.
	 */
	private function article_or_skip(): WP_Post {
		$post = get_page_by_path( self::ARTICLE_SLUG, OBJECT, 'post' );
		if ( ! $post instanceof WP_Post ) {
			self::markTestSkipped( 'the instance has no post at ' . self::ARTICLE_SLUG . '; load the live snapshot first (just pull load)' );
		}
		return $post;
	}

	/**
	 * The categories the article carries, or a skip: an article whose relations
	 * are missing (a snapshot loaded without the repair) has nothing to link.
	 *
	 * @param WP_Post $post The article.
	 * @return list<WP_Term>
	 */
	private function categories_or_skip( WP_Post $post ): array {
		$terms = get_the_terms( $post, 'category' );
		if ( ! \is_array( $terms ) || array() === $terms ) {
			self::markTestSkipped( 'the instance article carries no category; run `wp linker-i18n repair-post-categories` after the load' );
		}
		return array_values( $terms );
	}

	/**
	 * The article that shares a category with the one on display, or a skip:
	 * without a neighbour there is no grid to assert.
	 *
	 * @param WP_Post             $post       The article on display.
	 * @param array<int, WP_Term> $categories The categories it carries.
	 */
	private function related_or_skip( WP_Post $post, array $categories ): WP_Post {
		$ids   = array_map( static fn( WP_Term $term ): int => (int) $term->term_id, $categories );
		$found = get_posts(
			array(
				'post_type'      => 'post',
				'post_status'    => 'publish',
				'category__in'   => $ids,
				'post__not_in'   => array( (int) $post->ID ),
				'posts_per_page' => 1,
			)
		);
		if ( ! isset( $found[0] ) ) {
			self::markTestSkipped( 'no instance article shares the category of ' . self::ARTICLE_SLUG );
		}
		return $found[0];
	}

	/**
	 * One front-end GET. A non-200 is a failed test, not a skip: the instance
	 * this suite runs against is supposed to be serving.
	 *
	 * @param string $path Path on the instance.
	 */
	private function get( string $path ): string {
		$response = wp_remote_get( $this->front() . $path );
		$this->assertIsArray( $response, $response instanceof \WP_Error ? $response->get_error_message() : 'the request did not return a response' );
		$this->assertSame( 200, (int) wp_remote_retrieve_response_code( $response ) );
		return (string) wp_remote_retrieve_body( $response );
	}

	/**
	 * The page the article is served at.
	 *
	 * @param WP_Post $post The article.
	 */
	private function page( WP_Post $post ): string {
		$path = (string) wp_parse_url( (string) get_permalink( $post ), PHP_URL_PATH );
		$this->assertNotSame( '', $path );
		return $path;
	}

	/**
	 * The block between two markers, which is where an assertion belongs: the
	 * band's words and the meta's links are also carried by the site chrome.
	 *
	 * @param string $html  The page.
	 * @param string $start Opening marker.
	 * @param string $end   Closing marker.
	 */
	private function block( string $html, string $start, string $end ): string {
		$from = strpos( $html, $start );
		$this->assertNotFalse( $from, "the page has no {$start}" );
		$to = strpos( $html, $end, (int) $from );
		$this->assertNotFalse( $to, "the page has no {$end} after {$start}" );
		return substr( $html, (int) $from, (int) $to - (int) $from );
	}

	/**
	 * The meta Category prints the article's own archive as a link — the shape
	 * the live face carries — not the shortcode text and not a bare label.
	 */
	public function test_the_meta_category_links_the_archive(): void {
		$post       = $this->article_or_skip();
		$categories = $this->categories_or_skip( $post );
		$archive    = get_term_link( $categories[0] );
		$this->assertIsString( $archive );

		$html = $this->get( $this->page( $post ) );

		$meta = $this->block( $html, '<div class="tv-blog-single-meta-cats">', '</div>' );
		$this->assertStringContainsString( 'href="' . esc_url( $archive ) . '"', $meta );
		$this->assertStringContainsString( esc_html( $categories[0]->name ), $meta );
		$this->assertStringNotContainsString( '[linker_blog_post_categories]', $html, 'the shortcode is expanded, not left as text' );
	}

	/**
	 * The related grid holds an article that shares a category with the one on
	 * display, and never the article itself.
	 */
	public function test_the_related_grid_holds_an_article_sharing_the_category(): void {
		$post       = $this->article_or_skip();
		$categories = $this->categories_or_skip( $post );
		$related    = $this->related_or_skip( $post, $categories );

		$html = $this->get( $this->page( $post ) );

		$grid = $this->block( $html, '<div class="tv-blog-single-related-grid">', '</section>' );
		$this->assertStringContainsString( 'href="' . esc_url( (string) get_permalink( $related ) ) . '"', $grid );
		$this->assertStringNotContainsString( 'href="' . esc_url( (string) get_permalink( $post ) ) . '"', $grid );
		$this->assertStringNotContainsString( '[linker_blog_related_posts]', $html, 'the shortcode is expanded, not left as text' );
	}

	/**
	 * The band prints the live words, not the contact shortcode's default.
	 */
	public function test_the_band_prints_the_live_words(): void {
		$post = $this->article_or_skip();

		$html = $this->get( $this->page( $post ) );

		$band = $this->block( $html, 'id="tv-blog-single-cta"', '</section>' );
		$this->assertStringContainsString( 'Request a project quote →', $band );
		$this->assertStringContainsString( 'Back to blog', $band );
		$this->assertStringNotContainsString( '>Contact Linker</a>', $band, 'the band carries its own words, not the chrome\'s' );
	}
}
