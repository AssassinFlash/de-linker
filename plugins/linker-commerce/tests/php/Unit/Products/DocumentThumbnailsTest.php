<?php
/**
 * Tests for the register's page-1 thumbnails.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\DocumentThumbnails;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for DocumentThumbnails: the manifest the thumbnail pipeline ships, what
 * a document URL resolves to, and which malformed rows never reach a URL.
 *
 * @covers \Linker\Commerce\Products\DocumentThumbnails
 */
final class DocumentThumbnailsTest extends TestCase {

	/**
	 * A file name of the pipeline's own shape (sha1 + .webp).
	 */
	private const FILE = '0123456789abcdef0123456789abcdef01234567.webp';

	/**
	 * Paths this test writes and removes.
	 *
	 * @var list<string>
	 */
	private array $paths = array();

	/**
	 * The URL prefix wp_plugins_url is stubbed to answer with.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static function ( string $url, int $component = -1 ) {
					$parsed = -1 === $component ? parse_url( $url ) : parse_url( $url, $component );
					return false === $parsed ? null : $parsed;
				},
			)
		);
		WP_Mock::userFunction(
			'plugins_url',
			array( 'return' => static fn ( string $path ): string => 'https://de-linker.test/wp-content/plugins/linker-commerce/' . $path )
		);
	}

	/**
	 * Removes the fixtures.
	 */
	public function tearDown(): void {
		foreach ( $this->paths as $path ) {
			unlink( $path );
		}
		$this->paths = array();
		parent::tearDown();
	}

	/**
	 * A manifest file with the given payload, as JSON on disk.
	 *
	 * @param mixed $payload Decoded JSON to write.
	 */
	private function manifest_file( mixed $payload ): string {
		$path = sys_get_temp_dir() . '/linker-commerce-thumbs-' . bin2hex( random_bytes( 6 ) ) . '.json';
		file_put_contents( $path, (string) json_encode( $payload ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a temp fixture on this machine.
		$this->paths[] = $path;

		return $path;
	}

	/**
	 * A document's manifest key is its URL's path, so the live host and a local
	 * instance resolve the same file to the same thumbnail.
	 */
	public function test_a_document_is_keyed_by_its_urls_path(): void {
		$this->assertSame( '/wp-content/uploads/2026/07/a.pdf', DocumentThumbnails::key( 'https://de-linker.com/wp-content/uploads/2026/07/a.pdf' ) );
		$this->assertSame( '/wp-content/uploads/2026/07/a.pdf', DocumentThumbnails::key( 'http://127.0.0.1:9018/wp-content/uploads/2026/07/a.pdf' ) );
		$this->assertSame( '/a.pdf', DocumentThumbnails::key( '/a.pdf' ) );
		$this->assertSame( 'nonsense', DocumentThumbnails::key( 'nonsense' ), 'a URL without a path is its own key and matches no entry' );
	}

	/**
	 * A hit: the entry resolves to the shipped file's URL and its size.
	 */
	public function test_a_shipped_entry_resolves_to_the_files_url(): void {
		$thumbs = new DocumentThumbnails(
			$this->manifest_file(
				array(
					'/wp-content/uploads/2026/07/a.pdf' => array(
						'file'   => self::FILE,
						'width'  => 153,
						'height' => 216,
					),
				)
			)
		);

		$this->assertSame(
			array(
				'src'    => 'https://de-linker.test/wp-content/plugins/linker-commerce/assets/faq-thumbs/' . self::FILE,
				'width'  => 153,
				'height' => 216,
			),
			$thumbs->of( 'https://de-linker.com/wp-content/uploads/2026/07/a.pdf' )
		);
		$this->assertNull( $thumbs->of( 'https://de-linker.com/wp-content/uploads/2026/07/b.pdf' ), 'a document the build did not render has no thumbnail' );
	}

	/**
	 * Rows the pipeline never writes — a name that is not `<sha1>.webp`, a row
	 * that is not an object, a key that is not a string, a header or a summary
	 * — are dropped, so nothing but the pipeline's own files can reach a URL.
	 */
	public function test_malformed_rows_never_reach_a_url(): void {
		$thumbs = new DocumentThumbnails(
			$this->manifest_file(
				array(
					'/good.pdf'    => array(
						'file'   => self::FILE,
						'width'  => 153,
						'height' => 216,
					),
					'/escape.pdf'  => array(
						'file'   => '../../wp-config.php',
						'width'  => 1,
						'height' => 1,
					),
					'/png.pdf'     => array(
						'file'   => '0123456789abcdef0123456789abcdef01234567.png',
						'width'  => 1,
						'height' => 1,
					),
					'/short.pdf'   => array(
						'file'   => 'abc.webp',
						'width'  => 1,
						'height' => 1,
					),
					'/object.pdf'  => array(
						'file'   => self::FILE,
						'width'  => 1,
						'height' => 1,
					),
					'/string.pdf'  => 'not an object',
					'/no-file.pdf' => array(
						'width'  => 1,
						'height' => 1,
					),
					0              => array(
						'file'   => self::FILE,
						'width'  => 1,
						'height' => 1,
					),
				)
			)
		);

		$entries = $thumbs->manifest();
		$this->assertArrayHasKey( '/good.pdf', $entries );
		$this->assertSame( array( '/good.pdf', '/object.pdf' ), array_keys( $entries ), 'only rows shaped like the pipeline\'s own survive' );
		$this->assertNull( $thumbs->of( 'https://de-linker.com/escape.pdf' ) );
		$this->assertNull( $thumbs->of( 'https://de-linker.com/png.pdf' ) );
		$this->assertNull( $thumbs->of( 'https://de-linker.com/short.pdf' ) );
		$this->assertNull( $thumbs->of( 'https://de-linker.com/no-file.pdf' ) );
		$this->assertNull( $thumbs->of( 'https://de-linker.com/0' ) );
	}

	/**
	 * Size fields that are missing or not numbers read as 0 rather than
	 * breaking the row: the row's box is CSS's, the numbers are the image's.
	 */
	public function test_a_row_without_sizes_still_resolves(): void {
		$thumbs = new DocumentThumbnails( $this->manifest_file( array( '/a.pdf' => array( 'file' => self::FILE ) ) ) );

		$this->assertSame(
			array(
				'src'    => 'https://de-linker.test/wp-content/plugins/linker-commerce/assets/faq-thumbs/' . self::FILE,
				'width'  => 0,
				'height' => 0,
			),
			$thumbs->of( 'https://de-linker.com/a.pdf' )
		);
	}

	/**
	 * A manifest that is absent, unreadable or not JSON is no entries, not an
	 * error: the rows then show their type tiles.
	 */
	public function test_an_unreadable_manifest_is_no_entries(): void {
		$absent = new DocumentThumbnails( sys_get_temp_dir() . '/linker-commerce-thumbs-absent-' . bin2hex( random_bytes( 6 ) ) . '.json' );
		$this->assertSame( array(), $absent->manifest() );
		$this->assertNull( $absent->of( 'https://de-linker.com/a.pdf' ) );

		$broken = sys_get_temp_dir() . '/linker-commerce-thumbs-broken-' . bin2hex( random_bytes( 6 ) ) . '.json';
		file_put_contents( $broken, '{not json' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a temp fixture on this machine.
		$this->paths[] = $broken;
		$this->assertSame( array(), ( new DocumentThumbnails( $broken ) )->manifest() );

		$list = $this->manifest_file( array( 'a', 'b' ) );
		$this->assertSame( array(), ( new DocumentThumbnails( $list ) )->manifest(), 'a JSON list is not a manifest' );
	}
}
