<?php
/**
 * The site search's result set, in a real WordPress.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Products\SearchScope;

/**
 * An unspecified `?s=` search returns blog posts of the current language and
 * nothing else. Products stay in the catalogue search. English and German are
 * both covered: Polylang filters the same scoped query by language
 * (2026-10-14 live recheck, families 17 and 23).
 *
 * @covers \Linker\Commerce\Products\SearchScope
 */
final class SearchScopeTest extends IntegrationTestCase {

	/**
	 * A token shared by the fixtures of one test, so the search hits them and
	 * nothing already in the instance.
	 *
	 * @var string
	 */
	private string $token = '';

	/**
	 * Builds a fresh token.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->token = 'sscope' . self::tag();
	}

	/**
	 * English and German searches each return that language's post and neither
	 * returns the product, the page, or the other language's post.
	 */
	public function test_implicit_search_returns_posts_in_each_language(): void {
		if ( ! $this->languages_ready() ) {
			$this->markTestSkipped( 'Polylang has no en/de languages; run wp linker-i18n setup on the instance.' );
		}

		$english = $this->entry( 'post', 'en', "English article about {$this->token}" );
		$german  = $this->entry( 'post', 'de', "Deutscher Artikel über {$this->token}" );
		$product = $this->entry( 'product', 'en', "English product about {$this->token}" );
		// A German product too: the live defect (families 17 and 23) paginated
		// products on both languages' search pages, so the German search needs
		// its own leak for the one-page assertion below to guard it.
		$german_product = $this->entry( 'product', 'de', "Deutsches Produkt über {$this->token}" );
		$page           = $this->entry( 'page', 'en', "English page about {$this->token}" );

		// The live defect paginated the leaked products (1 2 3 … 8 »). A page
		// size of one turns every leaked entry into its own page, so the
		// one-page assertion in search() can only hold when nothing leaks.
		$per_page = (int) get_option( 'posts_per_page' );
		update_option( 'posts_per_page', 1 );
		$this->later(
			static function () use ( $per_page ): void {
				update_option( 'posts_per_page', $per_page );
			}
		);

		$english_hits = $this->search( 'en' );
		$german_hits  = $this->search( 'de' );

		$this->assertContains( $english, $english_hits, 'The English search includes the English article.' );
		$this->assertNotContains( $german, $english_hits, 'The English search does not include the German article.' );
		$this->assertContains( $german, $german_hits, 'The German search includes the German article.' );
		$this->assertNotContains( $english, $german_hits, 'The German search does not include the English article.' );
		$this->assertNotContains( $product, $english_hits, 'A product never enters the implicit search.' );
		$this->assertNotContains( $product, $german_hits, 'A product never enters the German search either.' );
		$this->assertNotContains( $german_product, $english_hits, 'The German product never enters the English search.' );
		$this->assertNotContains( $german_product, $german_hits, 'The German product never enters the German search.' );
		$this->assertNotContains( $page, $english_hits, 'A page never enters the implicit search.' );
		$this->assertNotContains( $page, $german_hits, 'A page never enters the German search.' );
		$this->assertLessThanOrEqual( (int) get_option( 'posts_per_page' ), count( $english_hits ), 'The search uses the blog page size, not a product pager of its own.' );
	}

	/**
	 * A request that names product keeps that type. The scope only rewrites
	 * the implicit case.
	 */
	public function test_explicit_product_search_keeps_its_type(): void {
		if ( ! $this->languages_ready() ) {
			$this->markTestSkipped( 'Polylang has no en/de languages; run wp linker-i18n setup on the instance.' );
		}
		$product = $this->entry( 'product', 'en', "Named product search {$this->token}" );
		$this->entry( 'post', 'en', "Named post search {$this->token}" );

		$this->as_language( 'en' );
		$GLOBALS['wp']->query_vars = array(
			's'         => $this->token,
			'post_type' => 'product',
		);
		$GLOBALS['wp']->query_posts();
		$query = $GLOBALS['wp_query'];
		$this->assertInstanceOf( \WP_Query::class, $query );
		$this->assertSame( 'product', $query->get( 'post_type' ), 'An explicit product search is not rewritten to posts.' );
		$this->assertContains( $product, $this->ids_of( $query ), 'The named product search still finds the product.' );
	}

	/**
	 * The registered hook is SearchScope, and the constant no longer names product.
	 */
	public function test_scope_is_registered_as_posts_only(): void {
		$this->assertGreaterThan( 0, has_action( 'pre_get_posts', array( $this->scope(), 'scope' ) ), 'SearchScope is registered on the instance.' );
		$this->assertSame( array( 'post' ), SearchScope::POST_TYPES, 'The constant itself no longer names product.' );
		$this->assertNotContains( 'product', SearchScope::POST_TYPES );
	}

	/**
	 * Whether Polylang is loaded with the site's two languages. A clean
	 * instance has the plugin but no languages until setup runs.
	 */
	private function languages_ready(): bool {
		return function_exists( 'pll_set_post_language' )
			&& function_exists( 'PLL' )
			&& PLL()->model->get_language( 'en' )
			&& PLL()->model->get_language( 'de' );
	}

	/**
	 * A published entry of one language, removed after the test.
	 *
	 * @param string $post_type Post type.
	 * @param string $language  Polylang language slug.
	 * @param string $title     Title, which also carries the search token.
	 */
	private function entry( string $post_type, string $language, string $title ): int {
		$id = wp_insert_post(
			array(
				'post_type'    => $post_type,
				'post_status'  => 'publish',
				'post_title'   => $title,
				'post_content' => "Fixture body {$this->token}",
				'post_name'    => sanitize_title( $title ),
			),
			true
		);
		$this->assertIsInt( $id );
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		pll_set_post_language( $id, $language );
		return $id;
	}

	/**
	 * The main search of one language, as the results page runs it: no
	 * post_type in the request, so SearchScope decides. SearchScope only
	 * rewrites the main query (`$wp_the_query`), so this goes through
	 * `WP::query_posts()`, which is what `?s=` runs.
	 *
	 * @param string $language Polylang language slug.
	 * @return list<int>
	 */
	private function search( string $language ): array {
		$this->as_language( $language );
		$GLOBALS['wp']->query_vars = array(
			's' => $this->token,
		);
		$GLOBALS['wp']->query_posts();
		$query = $GLOBALS['wp_query'];
		$this->assertInstanceOf( \WP_Query::class, $query );
		$this->assertTrue( $query->is_main_query(), 'The results page query is the main query.' );
		$this->assertTrue( $query->is_search(), 'The fixture query is a search.' );
		$this->assertSame( array( 'post' ), (array) $query->get( 'post_type' ), "The {$language} search was scoped to posts." );
		$this->assertSame( 1, (int) $query->max_num_pages, "The {$language} search is one page at a page size of one: nothing leaked to paginate it." );
		$ids = $this->ids_of( $query );
		sort( $ids );
		return $ids;
	}

	/**
	 * Post IDs of a query. The main query returns posts, not IDs.
	 *
	 * @param \WP_Query $query The query that just ran.
	 * @return list<int>
	 */
	private function ids_of( \WP_Query $query ): array {
		$posts = is_array( $query->posts ) ? $query->posts : array();
		$ids   = array();
		foreach ( $posts as $post ) {
			$ids[] = $post instanceof \WP_Post ? (int) $post->ID : (int) $post;
		}
		return $ids;
	}

	/**
	 * Points Polylang at one language for the next main query. The results
	 * page is a front-end request; these tests run as CLI.
	 *
	 * @param string $language Polylang language slug.
	 */
	private function as_language( string $language ): void {
		PLL()->curlang = PLL()->model->get_language( $language );
	}

	/**
	 * The scope the plugin registered.
	 */
	private function scope(): SearchScope {
		// The bootstrap constructs SearchScope once and registers it; a second
		// instance would double the hook. Read the registered callback.
		$hook = $GLOBALS['wp_filter']['pre_get_posts'] ?? null;
		if ( $hook instanceof \WP_Hook ) {
			foreach ( $hook->callbacks as $callbacks ) {
				foreach ( $callbacks as $callback ) {
					$function = $callback['function'];
					if ( is_array( $function ) && $function[0] instanceof SearchScope && 'scope' === $function[1] ) {
						return $function[0];
					}
				}
			}
		}
		$this->fail( 'SearchScope is not registered on pre_get_posts.' );
	}
}
