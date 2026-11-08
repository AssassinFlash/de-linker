<?php
/**
 * Tests for the documents page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\Documents;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Quotation\Issuer;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Documents: the design reports of the saved solutions, newest
 * first. Quotations are written and sent offline (owner ruling 2026-11-08)
 * and are not documents of this site.
 *
 * @covers \Linker\Commerce\Account\Documents
 */
final class DocumentsTest extends TestCase {

	/**
	 * Cleanups that remove the temporary report files.
	 *
	 * @var list<callable>
	 */
	private array $cleanups = array();

	/**
	 * Runs the registered cleanups.
	 */
	public function tearDown(): void {
		foreach ( $this->cleanups as $cleanup ) {
			$cleanup();
		}
		$this->cleanups = array();
		parent::tearDown();
	}

	/**
	 * A saved solution's design report is listed with its report link, newest
	 * first; a solution without a report file adds no row.
	 */
	public function test_reports_are_listed_newest_first(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
		$older = self::solution( 61, 'Verification residence 10kW', 1_700_000_000 );
		$newer = self::solution( 62, 'C&I peak shaving', 1_760_002_000 );
		$bare  = self::solution( 63, 'No report yet', 1_760_003_000 );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( $newer, $bare, $older ) ) );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn ( int $id, string $key ): string => SavedSolutions::REPORT_META === $key && 63 !== $id ? $id . '/report.pdf' : '',
			)
		);
		// PrivateFiles::path() answers only for files that exist.
		$uploads = sys_get_temp_dir() . '/linker-documents-test-' . uniqid();
		$reports = $uploads . '/' . SavedSolutions::REPORTS_DIRECTORY;
		mkdir( $reports . '/61', 0777, true );
		mkdir( $reports . '/62', 0777, true );
		file_put_contents( $reports . '/61/report.pdf', 'x' );
		file_put_contents( $reports . '/62/report.pdf', 'x' );
		$this->cleanups[] = static function () use ( $uploads ): void {
			$pdfs = glob( $uploads . '/*/*/*.pdf' );
			if ( is_array( $pdfs ) ) {
				array_map( 'unlink', $pdfs );
			}
			$dirs = glob( $uploads . '/*/*', GLOB_ONLYDIR );
			if ( is_array( $dirs ) ) {
				array_map( 'rmdir', $dirs );
			}
			$roots = glob( $uploads . '/*', GLOB_ONLYDIR );
			if ( is_array( $roots ) ) {
				array_map( 'rmdir', $roots );
			}
			rmdir( $uploads );
		};
		WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => $uploads ) ) );
		WP_Mock::userFunction( 'wc_get_orders', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_post_timestamp' )->andReturnUsing(
			static fn ( \WP_Post $post ): int => (int) strtotime( (string) $post->post_date )
		);

		$solutions = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
		$documents = ( new Documents( $solutions, '/plugin/templates/' ) )->for_customer( 5 );

		$this->assertSame(
			array(
				array(
					'title' => 'Design report: C&I peak shaving',
					'date'  => 1_760_002_000,
					'url'   => 'https://example.test/?linker-document=report&id=62',
					'kind'  => 'report',
				),
				array(
					'title' => 'Design report: Verification residence 10kW',
					'date'  => 1_700_000_000,
					'url'   => 'https://example.test/?linker-document=report&id=61',
					'kind'  => 'report',
				),
			),
			$documents
		);
	}

	/**
	 * A mock saved solution row, carrying its creation moment in post_date.
	 *
	 * @param positive-int $id    Post id.
	 * @param string       $title     Stored title.
	 * @param int          $timestamp Unix time of creation.
	 */
	private static function solution( int $id, string $title, int $timestamp ): \WP_Post {
		$post             = new \WP_Post( new \stdClass() );
		$post->ID         = $id;
		$post->post_title = $title;
		$post->post_date  = gmdate( 'Y-m-d H:i:s', $timestamp );
		return $post;
	}
}
