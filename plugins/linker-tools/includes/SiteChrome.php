<?php
/**
 * The site chrome's scripts.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

/**
 * Two interactions of the site's chrome that the pages themselves do not
 * carry (#12, docs/specs/12-site-chrome.md items 7 and 8):
 *
 * - the marketing pages' content modules also switch on desktop hover
 *   (a hover clicks the module's own trigger, so the click, keyboard and
 *   touch behaviour is the page's own and unchanged);
 * - the header's menu images load when their menu opens (a fallback for
 *   markup that carries them as data-src; the header's thumbnails resolve
 *   through their own src, so the hydrator currently finds nothing — it
 *   stays until an instance proves the visual parity without it).
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
	 * The chrome's scripts: the menu images everywhere the header renders,
	 * the hover switching on the pages that hold the modules.
	 */
	public function assets(): void {
		$base = plugin_dir_path( $this->plugin_file );
		wp_enqueue_script(
			'linker-tools-menu-images',
			plugins_url( 'assets/menu-images.js', $this->plugin_file ),
			array(),
			(string) filemtime( $base . 'assets/menu-images.js' ),
			array( 'in_footer' => true )
		);
		if ( ! is_singular( 'page' ) || ! $this->has_modules() ) {
			return;
		}
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
