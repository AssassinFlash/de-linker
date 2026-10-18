<?php
/**
 * WindPress scan provider for this plugin's HTML and PHP.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use WP_Post;

/**
 * Registers on f!windpress/core/cache:compile.providers the way picostrap does
 * (inc/windpress-support.php), so Tailwind classes in the new templates and in
 * this plugin's HTML enter the same compile surface; and keeps LiveCanvas's own
 * provider from rendering our dynamic templates into its scan answer (see
 * render_raw()).
 */
final class WindPress {

	/**
	 * Adds the provider, and the dynamic templates' scan rule.
	 */
	public function register(): void {
		add_filter( 'f!windpress/core/cache:compile.providers', array( $this, 'providers' ) );
		add_filter( 'f!windpress/integration/livecanvas/compile:get_contents.render', array( $this, 'render_raw' ), 10, 2 );
	}

	/**
	 * LiveCanvas's provider scans a dynamic template by `do_shortcode()`-rendering
	 * it, which is not what a template's classes need and is actively harmful
	 * here: outside a product context the WooCommerce template tags of the
	 * single-product template print their own markup — `[lc_wc_product_tab_additional_information]`
	 * emits `<h2>Additional information</h2>` — into the scan REST answer,
	 * before its JSON, so the WindPress cache builder fails to parse it and
	 * the whole compile stops ("o.contents is not iterable" in the browser
	 * worker). A template's Tailwind classes are in its own source, so the
	 * provider reads that instead; the classes a shortcode prints at runtime are
	 * covered by this plugin's provider, which scans the PHP that prints them.
	 *
	 * @param bool  $render Whether LiveCanvas's provider renders this post.
	 * @param mixed $post   The post it is about to read.
	 * @return bool False for this plugin's dynamic templates.
	 */
	public function render_raw( $render, $post ): bool {
		if ( $post instanceof WP_Post && Templates::POST_TYPE === $post->post_type ) {
			return false;
		}

		return (bool) $render;
	}

	/**
	 * Appends this plugin to the compile providers.
	 *
	 * @param array<int, array<string, mixed>> $providers Existing providers.
	 * @return array<int, array<string, mixed>>
	 */
	public function providers( array $providers ): array {
		$providers[] = array(
			'id'          => 'linker-commerce',
			'name'        => 'Linker Commerce',
			'description' => 'Scans linker-commerce templates and PHP for Tailwind classes',
			'callback'    => array( $this, 'scan' ),
			'enabled'     => true,
		);
		return $providers;
	}

	/**
	 * Files WindPress should scan: LiveCanvas HTML plus PHP that prints classes.
	 *
	 * @return list<array{name: string, content: string}>
	 */
	public function scan(): array {
		$root     = dirname( __DIR__, 2 );
		$contents = array();
		foreach ( Templates::paths() as $path ) {
			$contents[] = array(
				'name'    => 'livecanvas/' . basename( $path ),
				'content' => Tokens::read( $path ),
			);
		}
		$inquiry   = glob( $root . '/content/livecanvas/inquiry/*.html' );
		$account   = glob( $root . '/content/livecanvas/account/*.html' );
		$fragments = array_merge( false === $inquiry ? array() : $inquiry, false === $account ? array() : $account );
		foreach ( $fragments as $path ) {
			$contents[] = array(
				'name'    => 'livecanvas/' . basename( dirname( $path ) ) . '/' . basename( $path ),
				'content' => Tokens::read( $path ),
			);
		}
		foreach ( $this->php_files( $root . '/includes/Presentation' ) as $path ) {
			$contents[] = array(
				'name'    => 'includes/Presentation/' . basename( $path ),
				'content' => Tokens::read( $path ),
			);
		}
		return $contents;
	}

	/**
	 * PHP files in a directory.
	 *
	 * @param string $dir Directory.
	 * @return list<string>
	 */
	private function php_files( string $dir ): array {
		$files = glob( $dir . '/*.php' );
		return false === $files ? array() : $files;
	}
}
