<?php
/**
 * Tests for the WindPress cache freshness and content checks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\Templates;
use Linker\Commerce\Presentation\Tokens;
use Linker\Commerce\Presentation\WindPressCache;
use Linker\Commerce\Tests\TestCase;

/**
 * Tests for WindPressCache.
 *
 * @covers \Linker\Commerce\Presentation\WindPressCache
 */
final class WindPressCacheTest extends TestCase {

	/**
	 * The compiled selectors of every anchor class, as Tailwind emits them.
	 */
	private const COMPILED_ALL = '.py-10{padding-block:2.5rem}.px-4{padding-inline:1rem}.bg-white{background-color:#fff}'
		. '.max-w-\\[1160px\\]{max-width:1160px}.text-\\[\\#0c7f73\\]{color:#0c7f73}'
		. '.text-\\(--proto-accent\\){color:var(--proto-accent)}.overflow-x-auto{overflow-x:auto}'
		. '.object-contain{object-fit:contain}'
		. '.sf-products{}.product-grid{}.sf-card{}.wb-strip{}'
		. '.pdp-layout{}.pdp-purchase{}.pdp-scene-reel{}.pdp-disclose{}'
		. '#tv-blog-single-v1{}'
		. '.linker-library-tabbar{}.linker-library-card{}.linker-library-thumb{}';

	/**
	 * The per-test compiled-cache file.
	 *
	 * @var string
	 */
	private string $cache_path;

	/** Removes a previous test's cache file. */
	public function setUp(): void {
		parent::setUp();
		$this->cache_path = sys_get_temp_dir() . '/linker-commerce-windpress-cache-test.css';
		if ( file_exists( $this->cache_path ) ) {
			unlink( $this->cache_path );
		}
	}

	/** Deletes the test's cache file. */
	public function tearDown(): void {
		if ( file_exists( $this->cache_path ) ) {
			unlink( $this->cache_path );
		}
		parent::tearDown();
	}

	/**
	 * WindPress is not loaded in the test process, so the cache path is unknown.
	 */
	public function test_path_is_null_when_windpress_is_not_active(): void {
		$this->assertNull( ( new WindPressCache() )->path() );
	}

	/**
	 * An injected path wins over the WindPress lookup.
	 */
	public function test_path_returns_the_injected_file(): void {
		$this->assertSame( $this->cache_path, ( new WindPressCache( $this->cache_path ) )->path() );
	}

	/**
	 * The sources the cache has to reflect are the real exported files: the
	 * newest mtime is at least the tokens stylesheet's.
	 */
	public function test_newest_source_mtime_covers_tokens_and_templates(): void {
		$newest = ( new WindPressCache() )->newest_source_mtime();

		$this->assertGreaterThan( 0, $newest );
		$tokens_mtime = filemtime( Tokens::path() );
		$this->assertIsInt( $tokens_mtime );
		$this->assertGreaterThanOrEqual( $tokens_mtime, $newest );
		foreach ( Templates::paths() as $path ) {
			$mtime = filemtime( $path );
			$this->assertIsInt( $mtime );
			$this->assertGreaterThanOrEqual( $mtime, $newest );
		}
	}

	/**
	 * A cache newer than every source and containing the anchor classes is defect-free.
	 */
	public function test_fresh_complete_cache_has_no_defect(): void {
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() + 60 );

		$this->assertNull( ( new WindPressCache( $this->cache_path ) )->defect() );
	}

	/**
	 * WindPress not active: nothing will ever compile, defect of its own kind.
	 */
	public function test_inactive_windpress_is_a_defect(): void {
		$defect = ( new WindPressCache() )->defect();

		$this->assertNotNull( $defect );
		$this->assertSame( 'inactive', $defect['kind'] );
	}

	/**
	 * A never-compiled cache is a defect of its own kind.
	 */
	public function test_absent_cache_is_a_defect(): void {
		$defect = ( new WindPressCache( $this->cache_path ) )->defect();

		$this->assertNotNull( $defect );
		$this->assertSame( 'no-cache', $defect['kind'] );
		$this->assertStringContainsString( 'never compiled', $defect['detail'] );
	}

	/**
	 * A cache older than the sources is stale, even when complete.
	 */
	public function test_cache_older_than_the_sources_is_stale(): void {
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() - 3600 );
		$source = $this->cache_path . '.source.html';
		file_put_contents( $source, '<section>template</section>' );

		$defect = ( new WindPressCache( $this->cache_path, array( $source ) ) )->defect();

		unlink( $source );
		$this->assertNotNull( $defect );
		$this->assertSame( 'stale', $defect['kind'] );
		$this->assertStringContainsString( 'newer source files:', $defect['detail'] );
		$this->assertStringContainsString( basename( $source ), $defect['detail'] );
	}

	/**
	 * A fresh cache without the templates' classes is reported class by class,
	 * and a longer compiled class name does not stand in for its prefix.
	 */
	public function test_missing_anchor_classes_are_listed(): void {
		file_put_contents( $this->cache_path, '.py-100{padding-block:25rem}.px-4{padding-inline:1rem}' );
		touch( $this->cache_path, time() + 60 );

		$defect = ( new WindPressCache( $this->cache_path ) )->defect();

		$this->assertNotNull( $defect );
		$this->assertSame( 'missing-classes', $defect['kind'] );
		$this->assertStringContainsString( 'py-10, ', $defect['detail'] );
		$this->assertStringContainsString( 'max-w-[1160px]', $defect['detail'] );
		$this->assertStringNotContainsString( 'px-4', $defect['detail'] );
	}

	/**
	 * The class matcher matches the compiled selectors and rejects near names.
	 */
	public function test_missing_anchor_classes_matching(): void {
		$cache = new WindPressCache( $this->cache_path );

		$this->assertSame( array( 'py-10', 'px-4', 'bg-white', 'max-w-[1160px]', 'text-[#0c7f73]', 'text-(--proto-accent)', 'overflow-x-auto', 'object-contain', 'sf-products', 'product-grid', 'sf-card', 'wb-strip', 'pdp-layout', 'pdp-purchase', 'pdp-scene-reel', 'pdp-disclose', 'tv-blog-single-v1', 'linker-library-tabbar', 'linker-library-card', 'linker-library-thumb' ), $cache->missing_anchor_classes( '' ) );
		// .py-100 does not stand in for .py-10; the other classes are absent.
		$this->assertSame( array( 'py-10', 'bg-white', 'max-w-[1160px]', 'text-[#0c7f73]', 'text-(--proto-accent)', 'overflow-x-auto', 'object-contain', 'sf-products', 'product-grid', 'sf-card', 'wb-strip', 'pdp-layout', 'pdp-purchase', 'pdp-scene-reel', 'pdp-disclose', 'tv-blog-single-v1', 'linker-library-tabbar', 'linker-library-card', 'linker-library-thumb' ), $cache->missing_anchor_classes( '.py-100{padding-block:25rem}.px-4{padding-inline:1rem}' ) );
		$this->assertSame( array(), $cache->missing_anchor_classes( self::COMPILED_ALL ) );
	}
}
