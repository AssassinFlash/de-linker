<?php
/**
 * The site chrome's scripts.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

/**
 * The site chrome's script (#12, docs/specs/12-site-chrome.md item 7):
 * the marketing pages' content modules also switch on desktop hover (a
 * hover clicks the module's own trigger, so the click, keyboard and touch
 * behaviour is the page's own and unchanged).
 *
 * The header menu images carry no script of their own anymore: they
 * resolve through their own src, the browser's loading attribute decides
 * when they are fetched, and menu-images.js retired with its enqueue
 * (closure decision 8 of 2026-10-15: the review harness proved the plain
 * src resolves at load time — 13/13 loaded — and the script was inert
 * without data-src).
 */
final class SiteChrome {

	/**
	 * The selectors of the content modules' own triggers — the single list:
	 * the script receives it as an inline variable, and the enqueue decision
	 * reads the bare marker of each (the selector's first word without its
	 * . or [ sigil) out of the same entries.
	 */
	private const MODULE_TRIGGERS = array(
		'.lk-serve-tab',
		'.ss-stage-tab',
		'.lk-bstage-pill',
		'.lk-sstage-pill',
		'.lk-testi-pill',
		'.lk-story-card',
		'[data-capability-card]',
		'.home-stor-dot',
		'.sol-scale-tabs button',
	);

	/**
	 * Sets up the plugin's hooks.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action( 'wp_enqueue_scripts', array( $this, 'assets' ) );
	}

	/**
	 * The chrome's script: the hover switching on the pages that hold the
	 * modules. The header menu images need no script (see the class note).
	 */
	public function assets(): void {
		if ( ! is_singular( 'page' ) || ! $this->has_modules() ) {
			return;
		}
		$base = plugin_dir_path( $this->plugin_file );
		wp_enqueue_script(
			'linker-tools-marketing-hover',
			plugins_url( 'assets/marketing-hover.js', $this->plugin_file ),
			array(),
			(string) filemtime( $base . 'assets/marketing-hover.js' ),
			array( 'in_footer' => true )
		);
		wp_add_inline_script(
			'linker-tools-marketing-hover',
			'window.linkerHoverTriggers = ' . wp_json_encode( implode( ', ', self::MODULE_TRIGGERS ) ) . ';',
			'before'
		);
	}

	/**
	 * Whether this page's content holds the switchable modules.
	 */
	private function has_modules(): bool {
		$post = get_post();
		if ( ! $post instanceof \WP_Post ) {
			return false;
		}
		foreach ( self::MODULE_TRIGGERS as $selector ) {
			// The bare marker the content carries: the selector's class or
			// attribute name, without its sigils and scope.
			$first  = explode( ' ', $selector )[0];
			$marker = trim( (string) preg_replace( '/^([.\[]|[a-z.-]+ )/', '', $first ), ']' );
			if ( '' !== $marker && str_contains( $post->post_content, $marker ) ) {
				return true;
			}
		}
		return false;
	}
}
