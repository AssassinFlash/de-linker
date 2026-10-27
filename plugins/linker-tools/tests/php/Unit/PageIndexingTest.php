<?php
/**
 * The workspace page's robots decision and its sitemap exclusion.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\PageIndexing;
use WP_Post;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for PageIndexing.
 *
 * @covers \Linker\Tools\Genie\PageIndexing
 */
final class PageIndexingTest extends TestCase {

	/**
	 * The indexing rule under test.
	 */
	private function rule(): PageIndexing {
		return new PageIndexing();
	}

	/**
	 * A page post as WordPress hands it to the head and the sitemap.
	 *
	 * @param string $slug      The page's post name.
	 * @param int    $parent_id The page's parent id.
	 */
	private function page( string $slug = 'genie', int $parent_id = 0 ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'          => 60,
				'post_type'   => 'page',
				'post_status' => 'publish',
				'post_name'   => $slug,
				'post_parent' => $parent_id,
			)
		);
	}

	/**
	 * Both SEOPress extension points are hooked.
	 */
	public function test_register_adds_the_two_seopress_filters(): void {
		$rule = $this->rule();

		WP_Mock::expectFilterAdded( 'seopress_titles_noindex_bypass', array( $rule, 'noindex' ) );
		WP_Mock::expectFilterAdded( 'seopress_sitemaps_single_url', array( $rule, 'drop_from_sitemap' ), 10, 2 );

		$rule->register();

		$this->assertConditionsMet();
	}

	/**
	 * A request for the page named `genie` answers noindex. The English page
	 * and its German twin are both named `genie` (Polylang only prefixes the
	 * path), so one check covers both addresses.
	 */
	public function test_the_workspace_page_answers_noindex(): void {
		WP_Mock::userFunction(
			'is_page',
			array(
				'times'  => 1,
				'return' => true,
			)
		);
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'times'  => 1,
				'return' => $this->page(),
			)
		);

		$this->assertSame( '1', $this->rule()->noindex( '' ) );
	}

	/**
	 * Every other page keeps SEOPress's own decision — the rule only adds a
	 * verdict where the native chain found none.
	 */
	public function test_another_page_keeps_its_decision(): void {
		WP_Mock::userFunction(
			'is_page',
			array(
				'times'  => 1,
				'return' => true,
			)
		);
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'times'  => 1,
				'return' => $this->page( 'about' ),
			)
		);

		$this->assertSame( '', $this->rule()->noindex( '' ) );
	}

	/**
	 * A native noindex verdict is never replaced, so a stronger setting (the
	 * per-post option, a global toggle) survives this filter unchanged.
	 */
	public function test_a_native_noindex_decision_is_not_replaced(): void {
		$this->assertSame( 'yes', $this->rule()->noindex( 'yes' ) );
		$this->assertSame( '1', $this->rule()->noindex( '1' ) );
	}

	/**
	 * A page under another parent that happens to end in /genie/ is not the
	 * workspace.
	 */
	public function test_a_nested_page_named_genie_is_not_the_workspace(): void {
		WP_Mock::userFunction(
			'is_page',
			array(
				'times'  => 1,
				'return' => true,
			)
		);
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'times'  => 1,
				'return' => $this->page( 'genie', 12 ),
			)
		);

		$this->assertSame( '', $this->rule()->noindex( '' ) );
	}

	/**
	 * A blog post named `genie` is not the page.
	 */
	public function test_a_post_named_genie_is_not_the_workspace(): void {
		$post            = $this->page();
		$post->post_type = 'post';

		WP_Mock::userFunction(
			'is_page',
			array(
				'times'  => 1,
				'return' => false,
			)
		);

		$this->assertSame( '', $this->rule()->noindex( '' ) );
	}

	/**
	 * A request that is not a single page never asks for the queried object.
	 */
	public function test_a_non_page_request_keeps_its_decision(): void {
		WP_Mock::userFunction(
			'is_page',
			array(
				'times'  => 1,
				'return' => false,
			)
		);

		$this->assertSame( '', $this->rule()->noindex( '' ) );
	}

	/**
	 * The XML sitemap drops the workspace page in both languages.
	 */
	public function test_the_workspace_page_leaves_the_sitemap(): void {
		$entry = array(
			'loc'    => 'https://linker.test/genie/',
			'mod'    => '2026-10-26T00:00:00+00:00',
			'images' => array(),
		);

		$this->assertNull( $this->rule()->drop_from_sitemap( $entry, $this->page() ) );
		$this->assertNull( $this->rule()->drop_from_sitemap( $entry, $this->page() ) );
	}

	/**
	 * Every other entry is left exactly as SEOPress built it.
	 */
	public function test_other_entries_stay_in_the_sitemap(): void {
		$entry = array(
			'loc'    => 'https://linker.test/about/',
			'mod'    => '2026-10-26T00:00:00+00:00',
			'images' => array(),
		);

		$this->assertSame( $entry, $this->rule()->drop_from_sitemap( $entry, $this->page( 'about' ) ) );
		$this->assertSame( $entry, $this->rule()->drop_from_sitemap( $entry, $this->page( 'genie', 12 ) ) );

		$post            = $this->page();
		$post->post_type = 'post';
		$this->assertSame( $entry, $this->rule()->drop_from_sitemap( $entry, $post ) );
	}

	/**
	 * An entry another filter already dropped stays dropped.
	 */
	public function test_an_entry_already_dropped_stays_dropped(): void {
		$this->assertNull( $this->rule()->drop_from_sitemap( null, $this->page( 'about' ) ) );
	}
}
