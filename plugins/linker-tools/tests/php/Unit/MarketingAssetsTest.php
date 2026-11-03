<?php
/**
 * The marketing binder loads on exactly the pages that carry its editors.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Entries;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Post;

/**
 * Page content decides whether the binder is enqueued.
 *
 * @covers \Linker\Tools\Genie\Entries::marketing_assets
 */
final class MarketingAssetsTest extends TestCase {

	/**
	 * Content of the page under test.
	 *
	 * @var string
	 */
	private string $content = '';

	/**
	 * Whether the page under test is the front page.
	 *
	 * @var bool
	 */
	private bool $front = false;

	/**
	 * Whether the binder was enqueued.
	 *
	 * @var bool
	 */
	private bool $enqueued = false;

	/** One stub set serves every case; each case only changes the page. */
	public function setUp(): void {
		parent::setUp();
		$this->content  = '';
		$this->front    = false;
		$this->enqueued = false;
		$case           = $this;
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => function () use ( $case ): WP_Post {
					$post               = new WP_Post( (object) array( 'ID' => 1 ) );
					$post->post_content = $case->content_for_test();
					return $post;
				},
			)
		);
		WP_Mock::userFunction(
			'is_front_page',
			array(
				'return' => function () use ( $case ): bool {
					return $case->front_for_test();
				},
			)
		);
		WP_Mock::userFunction(
			'wp_enqueue_script',
			array(
				'args'   => array( 'linker-tools-marketing' ),
				'return' => function () use ( $case ): void {
					$case->mark_enqueued_for_test();
				},
			)
		);
	}

	/**
	 * Current page content.
	 *
	 * @return string
	 */
	public function content_for_test(): string {
		return $this->content;
	}

	/**
	 * Current front-page flag.
	 *
	 * @return bool
	 */
	public function front_for_test(): bool {
		return $this->front;
	}

	/**
	 * Record that the binder was enqueued.
	 */
	public function mark_enqueued_for_test(): void {
		$this->enqueued = true;
	}

	/**
	 * Run marketing_assets() for one page.
	 *
	 * @param string $content Published page content.
	 * @param bool   $front   Whether this page is the front page.
	 */
	private function loads( string $content, bool $front = false ): bool {
		$this->content  = $content;
		$this->front    = $front;
		$this->enqueued = false;
		( new Entries( '/srv/linker-tools.php' ) )->marketing_assets();
		return $this->enqueued;
	}

	/** Each of the three editor markup families loads the binder. */
	public function test_every_editor_markup_family_loads_the_binder(): void {
		$this->assertTrue( $this->loads( '<div id="system-search"><textarea class="lk-dialog-prompt"></textarea></div>' ) );
		$this->assertTrue( $this->loads( '<div class="installer-mobile-assistant"><textarea id="installer-mobile-query"></textarea></div>' ) );
		// The desktop Installer console carries only the Plan input and its link.
		$this->assertTrue( $this->loads( '<div class="lk-console-input-row"><input id="lki-hero-query" /><a class="lk-btn-query" href="/solution-configurator/">Plan</a></div>' ) );
	}

	/** A page without an editor, and the front page, do not load it. */
	public function test_pages_without_an_editor_and_the_front_page_do_not_load_the_binder(): void {
		$this->assertFalse( $this->loads( '<h1>About</h1><p>No editor here.</p>' ) );
		$this->assertFalse( $this->loads( '<div id="system-search"><textarea class="lk-dialog-prompt"></textarea></div>', true ) );
	}
}
