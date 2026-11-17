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
use Linker\Commerce\Planning\Context;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_DateTime;
use WC_Order;
use WP_Mock;

/**
 * Tests for Documents: design reports from saved solutions and inquiries,
 * newest first.
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
	 * Inquiry reports appear without a quotation or saved solution, using the
	 * stored report route; invalid references add no document.
	 */
	public function test_inquiry_planning_reports_are_listed_newest_first(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( mixed $value, int $flags = 0 ): string|false => json_encode( $value, $flags ) ) );
		WP_Mock::userFunction( 'rest_url', array( 'return' => static fn ( string $path ): string => 'https://example.test/wp-json/' . $path ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( string $key, string $value, string $url ): string => $url . '?' . http_build_query( array( $key => $value ) ) ) );
		$handoff                     = array(
			'id'              => str_repeat( 'a', 32 ),
			'snapshot_sha256' => str_repeat( 'b', 64 ),
			'snapshot'        => array(
				'project_id'           => str_repeat( 'c', 32 ),
				'title'                => 'Workshop roof',
				'revision'             => 2,
				'input_sha256'         => str_repeat( 'd', 64 ),
				'report_run_id'        => str_repeat( 'e', 32 ),
				'report_source_sha256' => str_repeat( 'f', 64 ),
				'report_sha256'        => str_repeat( '1', 64 ),
				'pdf'                  => array(
					'asset_id'   => str_repeat( '2', 32 ),
					'sha256'     => str_repeat( '3', 64 ),
					'media_type' => 'application/pdf',
				),
				'items'                => array(
					array(
						'product_id' => 4107,
						'quantity'   => 1,
						'label'      => 'Inverter',
					),
				),
			),
		);
		$reference                   = Context::reference( $handoff );
		$invalid                     = $reference;
		$invalid['reference_sha256'] = str_repeat( '0', 64 );
		$invalid['handoff_id']       = str_repeat( '4', 32 );
		$orders                      = array();
		foreach ( array(
			81 => 1_700_000_000,
			82 => 1_760_002_000,
		) as $id => $timestamp ) {
			$order = Mockery::mock( WC_Order::class );
			$order->allows( 'get_id' )->andReturn( $id );
			$order->allows( 'get_order_key' )->andReturn( 'wc_order_' . $id );
			$order->allows( 'get_date_created' )->andReturn( new WC_DateTime( '@' . $timestamp ) );
			$order->allows( 'get_meta' )->with( Context::META )->andReturn(
				json_encode(
					array(
						$handoff['id']         => array( 'reference' => $reference ),
						$invalid['handoff_id'] => array( 'reference' => $invalid ),
					)
				)
			);
			$orders[] = $order;
		}
		WP_Mock::userFunction(
			'wc_get_orders',
			array(
				'return' => function ( array $args ) use ( $orders ): array {
					$this->assertSame( 5, $args['customer_id'] );
					if ( Context::META !== ( $args['meta_key'] ?? '' ) ) {
						return array();
					}
					$this->assertSame( 'EXISTS', $args['meta_compare'] );
					$this->assertSame( -1, $args['limit'] );
					return $orders;
				},
			)
		);

		$solutions = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
		$documents = ( new Documents( $solutions, '/plugin/templates/' ) )->for_customer( 5 );

		$this->assertSame(
			array(
				array(
					'title' => 'Design report: Workshop roof',
					'date'  => 1_760_002_000,
					'url'   => 'https://example.test/wp-json/linker/v1/inquiries/82/planning-report/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa?key=wc_order_82',
					'kind'  => 'report',
				),
				array(
					'title' => 'Design report: Workshop roof',
					'date'  => 1_700_000_000,
					'url'   => 'https://example.test/wp-json/linker/v1/inquiries/81/planning-report/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa?key=wc_order_81',
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
