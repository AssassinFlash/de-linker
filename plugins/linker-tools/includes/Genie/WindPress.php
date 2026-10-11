<?php
/**
 * WindPress scan provider for the entries' markup.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Registers on f!windpress/core/cache:compile.providers the way Linker
 * Commerce's provider does, so the Tailwind classes of this plugin's PHP
 * markup enter the same compile surface.
 *
 * The ask chip of the catalogue search box (Entries::ask_chip) is printed by
 * this plugin, not by a LiveCanvas template, and WindPress's scan of rendered
 * pages does not reach it (the dynamic template rendering scan is off; the
 * page carries the chip only through the [linker_genie_ask] mount). Without a
 * file provider the chip's utility classes — min-h-11, rounded-xl,
 * border-neutral-200 and the rest of ask_chip() — never reach the compiled
 * cache and the chip renders unstyled (ticket #68 review).
 */
final class WindPress {

	/**
	 * Template classes the compiled CSS must contain, mapped to their compiled
	 * selector prefix (Tailwind escapes [ ] # : ( ) inside class names): the
	 * ask chip's own utilities, the classes no LiveCanvas template prints.
	 *
	 * @var array<string, string>
	 */
	private const ANCHOR_CLASSES = array(
		'min-h-11'           => '.min-h-11',
		'rounded-xl'         => '.rounded-xl',
		'border-neutral-200' => '.border-neutral-200',
	);

	/**
	 * Adds the provider.
	 */
	public function register(): void {
		add_filter( 'f!windpress/core/cache:compile.providers', array( $this, 'providers' ) );
	}

	/**
	 * Appends this plugin to the compile providers.
	 *
	 * @param array<int, array<string, mixed>> $providers Existing providers.
	 * @return array<int, array<string, mixed>>
	 */
	public function providers( array $providers ): array {
		$providers[] = array(
			'id'          => 'linker-tools',
			'name'        => 'Linker Tools',
			'description' => 'Scans the Genie entries for Tailwind classes',
			'callback'    => array( $this, 'scan' ),
			'enabled'     => true,
		);
		return $providers;
	}

	/**
	 * What WindPress should scan: the entries, the only file of this plugin
	 * that prints utility classes (the ask chip and the dock; the React apps
	 * carry their own stylesheets).
	 *
	 * @return list<array{name: string, content: string}>
	 */
	public function scan(): array {
		return array(
			array(
				'name'    => 'includes/Genie/Entries.php',
				'content' => $this->read( __DIR__ . '/Entries.php' ),
			),
		);
	}

	/**
	 * Anchor classes missing from compiled CSS. A class counts when its
	 * escaped selector appears followed by something that is not part of a
	 * longer class name, so .min-h-11 does not match a compiled .min-h-110.
	 *
	 * @param string $css Compiled CSS.
	 * @return list<string>
	 */
	public function missing_anchor_classes( string $css ): array {
		$missing = array();
		foreach ( self::ANCHOR_CLASSES as $class => $selector ) {
			$pattern = '/' . preg_quote( $selector, '/' ) . '(?![a-zA-Z0-9_-])/';
			if ( 1 !== preg_match( $pattern, $css ) ) {
				$missing[] = $class;
			}
		}
		return $missing;
	}

	/**
	 * A file of this plugin on disk.
	 *
	 * @param string $path Absolute path.
	 */
	private function read( string $path ): string {
		if ( ! is_readable( $path ) ) {
			return '';
		}
		$contents = file_get_contents( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- plugin file on disk, not a remote URL.
		return false === $contents ? '' : $contents;
	}
}
