<?php
/**
 * Design tokens in Additional CSS.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * The design-token stylesheet. The single source is the WindPress volume
 * export `content/windpress/tokens.css`: `present` copies that directory into
 * the volume the compiler reads, and `Tokens::path()` points at the same file
 * so a run cannot require one copy and publish another. Additional CSS is not
 * a second home for it — `uninstall()` only removes a block an earlier run
 * left there.
 */
final class Tokens {

	/**
	 * Marks the managed block inside custom CSS so a second install replaces it.
	 */
	public const MARKER = '/* linker-commerce-tokens */';

	/**
	 * End of the managed block.
	 */
	private const END = '/* /linker-commerce-tokens */';

	/**
	 * Absolute path of the exported stylesheet.
	 *
	 * This is the only copy. WindPressVolume publishes `content/windpress/*.css`,
	 * so the tokens file lives in that directory rather than beside it.
	 */
	public static function path(): string {
		return dirname( __DIR__, 2 ) . '/content/windpress/tokens.css';
	}

	/**
	 * The font files the stylesheet serves, read from its @font-face src()
	 * URLs: the stylesheet owns which fonts exist, so a font added there is
	 * guarded without touching this class. Urls outside this plugin (none
	 * today) are skipped — they are not files a run installs.
	 *
	 * @return list<string> Absolute paths.
	 */
	public static function fonts(): array {
		$plugin_dir = dirname( __DIR__, 2 );
		$prefix     = '/wp-content/plugins/linker-commerce/';
		$fonts      = array();
		if ( preg_match_all( '/src:url\("([^"]+)"\)/', self::css(), $urls ) ) {
			foreach ( array_unique( $urls[1] ) as $url ) {
				if ( str_starts_with( $url, $prefix ) ) {
					$fonts[] = $plugin_dir . '/' . substr( $url, strlen( $prefix ) );
				}
			}
		}
		return $fonts;
	}

	/**
	 * The exported stylesheet.
	 */
	public static function css(): string {
		return (string) self::read( self::path() );
	}

	/**
	 * Removes the marked tokens block from Additional CSS. The live site does
	 * not serve tokens from Additional CSS: the WindPress volume's tokens.css
	 * is the copy the compiler reads. This only takes out a block an earlier
	 * presentation run wrote there.
	 *
	 * @return bool Whether Additional CSS changed.
	 */
	public function uninstall(): bool {
		$current = (string) wp_get_custom_css();
		if ( ! \str_contains( $current, self::MARKER ) ) {
			return false;
		}
		$stripped = (string) \preg_replace(
			'/' . \preg_quote( self::MARKER, '/' ) . '.*?' . \preg_quote( self::END, '/' ) . '/s',
			'',
			$current
		);
		$stripped = \trim( $stripped );
		if ( $stripped === $current ) {
			return false;
		}
		wp_update_custom_css_post( $stripped );
		return true;
	}

	/**
	 * Removes the inlined tokens.css style block from LiveCanvas header/footer partials.
	 *
	 * @return int Partials rewritten.
	 */
	public function detach_from_partials(): int {
		$partials = get_posts(
			array(
				'post_type'      => 'lc_partial',
				'post_status'    => 'any',
				'posts_per_page' => -1,
			)
		);
		$changed  = 0;
		foreach ( $partials as $partial ) {
			$stripped = (string) preg_replace( '/<style[^>]*data-site-css="tokens\.css"[^>]*>.*?<\/style>/s', '', $partial->post_content );
			if ( $stripped === $partial->post_content ) {
				continue;
			}
			wp_update_post(
				array(
					'ID'           => $partial->ID,
					'post_content' => wp_slash( $stripped ),
				)
			);
			++$changed;
		}
		return $changed;
	}

	/**
	 * Local file contents; empty when the file cannot be read.
	 *
	 * @param string $path Absolute path.
	 */
	public static function read( string $path ): string {
		if ( ! is_readable( $path ) ) {
			return '';
		}
		$handle = fopen( $path, 'r' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- plugin file on disk, not a remote URL.
		if ( false === $handle ) {
			return '';
		}
		$contents = stream_get_contents( $handle );
		fclose( $handle ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- pair of fopen above.
		return false === $contents ? '' : $contents;
	}
}
