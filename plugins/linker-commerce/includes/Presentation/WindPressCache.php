<?php
/**
 * Freshness and content checks for the WindPress CSS cache.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * The templates' Tailwind classes only reach the visitor through the WindPress
 * cache (uploads/windpress/cache/tailwind.css), which the WindPress admin
 * compiles in the browser — Tailwind v4 has no server-side compile. This class
 * keeps a stale, absent or hand-assembled cache from posing as a build: the
 * cache must be newer than the templates and tokens it has to reflect, and it
 * must contain the templates' anchor classes.
 */
final class WindPressCache {

	/**
	 * Template classes the compiled CSS must contain, mapped to their compiled
	 * selector prefix (Tailwind escapes [ ] # : ( ) inside class names). Each
	 * class is used by the exported templates; the pair covers every template
	 * file. text-(--proto-accent) exists only inside shortcode attributes, so a
	 * missing rule is also the alarm for a shortcode parser eating the class.
	 *
	 * @var array<string, string>
	 */
	private const ANCHOR_CLASSES = array(
		'py-10'                 => '.py-10',
		'px-4'                  => '.px-4',
		'bg-white'              => '.bg-white',
		'max-w-[1160px]'        => '.max-w-\\[1160px\\]',
		'text-[#0c7f73]'        => '.text-\\[\\#0c7f73\\]',
		'lg:grid-cols-3'        => '.lg\\:grid-cols-3',
		'text-(--proto-accent)' => '.text-\\(--proto-accent\\)',
	);

	/**
	 * Cache file path, injected by tests; resolved from WindPress when null.
	 *
	 * @var string|null
	 */
	private ?string $cache_file;

	/**
	 * Source files the freshness reads, injected by tests; the exported
	 * templates plus tokens when null.
	 *
	 * @var list<string>|null
	 */
	private ?array $source_files;

	/**
	 * Constructor.
	 *
	 * @param string|null       $cache_file   Cache file path override.
	 * @param list<string>|null $source_files Source file list override.
	 */
	public function __construct( ?string $cache_file = null, ?array $source_files = null ) {
		$this->cache_file   = $cache_file;
		$this->source_files = $source_files;
	}

	/**
	 * The files the cache has to reflect.
	 *
	 * @return list<string>
	 */
	private function sources(): array {
		if ( null !== $this->source_files ) {
			return $this->source_files;
		}
		return array_merge( array_values( Templates::catalog() ), array( Tokens::path() ) );
	}

	/**
	 * Absolute path of the compiled CSS cache, or null when WindPress is not active.
	 */
	public function path(): ?string {
		if ( null !== $this->cache_file ) {
			return $this->cache_file;
		}
		if ( ! class_exists( \WindPress\WindPress\Core\Cache::class ) ) {
			return null;
		}
		$path = \WindPress\WindPress\Core\Cache::get_cache_path( \WindPress\WindPress\Core\Cache::CSS_CACHE_FILE );
		return is_string( $path ) && '' !== $path ? $path : null;
	}

	/**
	 * Newest mtime of the files the cache has to reflect: the LiveCanvas
	 * templates and the tokens stylesheet.
	 */
	public function newest_source_mtime(): int {
		$newest = 0;
		foreach ( $this->sources() as $path ) {
			$mtime = filemtime( $path );
			if ( is_int( $mtime ) && $mtime > $newest ) {
				$newest = $mtime;
			}
		}
		return $newest;
	}

	/**
	 * What keeps the cache from serving the templates styled, or null when it
	 * can: kind 'inactive' (WindPress not active, nothing will ever compile),
	 * 'no-cache' (WindPress has never compiled), 'stale' (the cache predates a
	 * template/token change) or 'missing-classes' (compiled without the
	 * templates' anchor classes — a scan or compile silently skipped them).
	 *
	 * @return array{kind: string, detail: string}|null
	 */
	public function defect(): ?array {
		$path = $this->path();
		if ( null === $path ) {
			return array(
				'kind'   => 'inactive',
				'detail' => 'WindPress is not active',
			);
		}
		$newest_source = $this->newest_source_mtime();
		if ( ! is_readable( $path ) ) {
			return array(
				'kind'   => 'no-cache',
				'detail' => 'no compiled cache exists (WindPress has never compiled)',
			);
		}
		$cache_mtime = filemtime( $path );
		$compiled_at = is_int( $cache_mtime ) ? $cache_mtime : null;
		if ( null === $compiled_at || $compiled_at < $newest_source ) {
			return array(
				'kind'   => 'stale',
				'detail' => sprintf(
					'cache compiled %s, newer source files: %s',
					null === $compiled_at ? 'unknown time' : gmdate( 'Y-m-d H:i:s', $compiled_at ) . ' UTC',
					implode( ', ', $this->newer_sources( $compiled_at ) )
				),
			);
		}
		$missing = $this->missing_anchor_classes( (string) file_get_contents( $path ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local cache file on disk, not a remote URL.
		if ( array() !== $missing ) {
			return array(
				'kind'   => 'missing-classes',
				'detail' => sprintf( 'compiled CSS does not contain template classes (%s)', implode( ', ', $missing ) ),
			);
		}
		return null;
	}

	/**
	 * The source files modified after the cache was compiled, newest-change
	 * order by basename: the files a recompile would pick up.
	 *
	 * @param int|null $cache_mtime Cache compile time, null when unknown.
	 * @return list<string>
	 */
	public function newer_sources( ?int $cache_mtime ): array {
		if ( null === $cache_mtime ) {
			return array( 'the cache has no readable compile time' );
		}
		$newer = array();
		foreach ( $this->sources() as $source ) {
			$mtime = filemtime( $source );
			if ( is_int( $mtime ) && $mtime > $cache_mtime ) {
				$newer[] = basename( $source );
			}
		}
		return $newer;
	}

	/**
	 * Anchor classes missing from compiled CSS. A class counts when its
	 * escaped selector appears followed by something that is not part of a
	 * longer class name, so .py-10 does not match a compiled .py-100.
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
}
