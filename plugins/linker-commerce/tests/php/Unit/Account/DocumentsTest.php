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
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;
use WP_Post;

/**
 * Tests for Documents.
 *
 * @covers \Linker\Commerce\Account\Documents
 */
final class DocumentsTest extends TestCase {

	/**
	 * Proforma invoices and design reports of the customer, newest first.
	 */
	public function test_for_customer(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( 'PI-2026-0001' );
		$order->allows( 'get_meta' )->with( Issuer::ISSUED_META )->andReturn( '1760000000' );
		$order->allows( 'has_status' )->andReturn( false );
		WP_Mock::userFunction( 'wc_get_orders' )->andReturnUsing(
			static function ( array $args ) use ( $order ): array {
				if ( 5 !== $args['customer_id'] ) {
					return array();
				}
				if ( Issuer::NUMBER_META === ( $args['meta_key'] ?? '' ) ) {
					return array( $order );
				}
				return array();
			}
		);
		$uploads = sys_get_temp_dir() . '/linker-documents-' . bin2hex( random_bytes( 4 ) );
		mkdir( $uploads . '/solution-reports/5', 0777, true );
		file_put_contents( $uploads . '/solution-reports/5/house-barleben-0123456789abcdef.pdf', '%PDF-1.4' );
		$with    = new WP_Post(
			(object) array(
				'ID'          => 45,
				'post_title'  => 'House Barleben',
				'post_status' => 'private',
			)
		);
		$without = new WP_Post(
			(object) array(
				'ID'          => 46,
				'post_title'  => 'Without report',
				'post_status' => 'private',
			)
		);
		WP_Mock::userFunction( 'get_posts', array( 'return' => array( $with, $without ) ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => static fn ( int $id ): string => 45 === $id ? '5/house-barleben-0123456789abcdef.pdf' : '' ) );
		WP_Mock::userFunction( 'get_post_timestamp', array( 'return' => 1770000000 ) );
		WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => $uploads ) ) );

		$documents = ( new Documents( new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' ), '/plugin/templates/' ) )->for_customer( 5 );
		unlink( $uploads . '/solution-reports/5/house-barleben-0123456789abcdef.pdf' );
		rmdir( $uploads . '/solution-reports/5' );
		rmdir( $uploads . '/solution-reports' );
		rmdir( $uploads );

		$this->assertSame(
			array(
				array(
					'title' => 'Design report: House Barleben',
					'date'  => 1770000000,
					'url'   => 'https://example.test/?linker-document=report&id=45',
				),
				array(
					'title' => 'Proforma invoice PI-2026-0001 (inquiry #20)',
					'date'  => 1760000000,
					'url'   => 'https://example.test/?linker-document=proforma&id=20',
				),
			),
			$documents,
			'Newest first; the private post\'s stored name without "Private:"; a saved solution without a design report adds no document.'
		);
	}


	/**
	 * A Proforma issued by a status change is found through the issued status,
	 * not only through the number meta query. An issued inquiry without a number adds no row.
	 */
	public function test_issued_status_with_a_number_is_listed_once(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
		$issued = Mockery::mock( WC_Order::class );
		$issued->allows( 'get_id' )->andReturn( 21 );
		$issued->allows( 'get_order_number' )->andReturn( '21' );
		$issued->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( 'PI-2026-0009' );
		$issued->allows( 'get_meta' )->with( Issuer::ISSUED_META )->andReturn( '1760001000' );
		$issued->allows( 'has_status' )->with( Statuses::PROFORMA )->andReturn( true );
		$bare = Mockery::mock( WC_Order::class );
		$bare->allows( 'get_id' )->andReturn( 22 );
		$bare->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( '' );
		$bare->allows( 'has_status' )->with( Statuses::PROFORMA )->andReturn( true );
		WP_Mock::userFunction( 'wc_get_orders' )->andReturnUsing(
			static function ( array $args ) use ( $issued, $bare ): array {
				return isset( $args['status'] ) ? array( $issued, $bare ) : array();
			}
		);
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );

		$documents = ( new Documents( new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' ), '/plugin/templates/' ) )->for_customer( 5 );

			$this->assertSame(
				array(
					array(
						'title' => 'Proforma invoice PI-2026-0009 (inquiry #21)',
						'date'  => 1760001000,
						'url'   => 'https://example.test/?linker-document=proforma&id=21',
					),
				),
				$documents
			);
		}

		/**
		 * Completed keeps the download. The number meta, not the status word, is what the page reads.
		 */
		public function test_completed_inquiry_keeps_the_download(): void {
			WP_Mock::passthruFunction( '__' );
			WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
			WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
			$done = Mockery::mock( WC_Order::class );
			$done->allows( 'get_id' )->andReturn( 23 );
			$done->allows( 'get_order_number' )->andReturn( '23' );
			$done->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( 'DLK-PF-2026-0002' );
			$done->allows( 'get_meta' )->with( Issuer::ISSUED_META )->andReturn( '1760002000' );
			$done->allows( 'has_status' )->with( Statuses::PROFORMA )->andReturn( false );
			WP_Mock::userFunction( 'wc_get_orders' )->andReturnUsing(
				static function ( array $args ) use ( $done ): array {
					return Issuer::NUMBER_META === ( $args['meta_key'] ?? '' ) ? array( $done ) : array();
				}
			);
			WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );

			$documents = ( new Documents( new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' ), '/plugin/templates/' ) )->for_customer( 5 );

			$this->assertSame(
				array(
					array(
						'title' => 'Proforma invoice DLK-PF-2026-0002 (inquiry #23)',
						'date'  => 1760002000,
						'url'   => 'https://example.test/?linker-document=proforma&id=23',
					),
				),
				$documents
			);
		}
	}
