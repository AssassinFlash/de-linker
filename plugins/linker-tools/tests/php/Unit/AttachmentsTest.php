<?php
/**
 * The files a turn carries, checked before they leave the site (#236).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Attachments;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Attachments.
 *
 * @covers \Linker\Tools\Genie\Attachments
 */
final class AttachmentsTest extends TestCase {

	/**
	 * Who took what from the allowance.
	 *
	 * @var list<string>
	 */
	private array $taken = array();

	/**
	 * Common WordPress doubles.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->taken = array();
		WP_Mock::passthruFunction( 'sanitize_text_field' );
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::userFunction( 'wp_basename', array( 'return' => static fn( string $path ): string => basename( $path ) ) );
		$_SERVER['REMOTE_ADDR'] = '203.0.113.7';
	}

	/**
	 * A check whose allowance has `$left` units.
	 *
	 * @param int $left Units left.
	 * @param int $user The signed-in customer, 0 for a guest.
	 */
	private function attachments( int $left = 100, int $user = 0 ): Attachments {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $user > 0 ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => $user ) );
		return new Attachments(
			function ( string $who ) use ( &$left ): bool {
				$this->taken[] = $who;
				--$left;
				return $left >= 0;
			}
		);
	}

	/**
	 * One file as the shell sends it.
	 *
	 * @param string $bytes The file.
	 * @param string $type  Its declared type.
	 * @param string $name  Its name.
	 * @return array{name: string, type: string, data: string}
	 */
	private static function file( string $bytes, string $type, string $name = 'plate.jpg' ): array {
		return array(
			'name' => $name,
			'type' => $type,
			'data' => base64_encode( $bytes ), // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- the wire format.
		);
	}

	/**
	 * No files is no check and no allowance taken.
	 */
	public function test_a_turn_without_files_passes_untouched(): void {
		$this->assertSame( array(), $this->attachments()->check( null ) );
		$this->assertSame( array(), $this->attachments()->check( array() ) );
		$this->assertSame( array(), $this->taken );
	}

	/**
	 * JPEG, PNG, WebP and PDF pass by their first bytes; each file takes one
	 * unit of the connection's allowance; a name loses its path.
	 */
	public function test_the_four_types_pass_and_each_file_counts(): void {
		$files = $this->attachments()->check(
			array(
				self::file( "\xFF\xD8\xFF\xE0jpeg", 'image/jpeg', 'C:\\Users\\me\\IMG_0001.jpg' ),
				self::file( "\x89PNG\r\n\x1A\npng", 'image/png', '../../etc/passwd' ),
				self::file( 'RIFF____WEBPVP8 ', 'image/webp', "bad\x00name.webp" ),
			)
		);

		$this->assertIsArray( $files );
		$this->assertSame( array( 'IMG_0001.jpg', 'passwd', 'badname.webp' ), array_column( $files, 'name' ) );
		$this->assertSame( array( '203.0.113.7', '203.0.113.7', '203.0.113.7' ), $this->taken );
		$pdf = $this->attachments()->check( array( self::file( '%PDF-1.7 ...', 'application/pdf', 'ds.pdf' ) ) );
		$this->assertIsArray( $pdf );
		$this->assertSame( 'application/pdf', $pdf[0]['type'] );
	}

	/**
	 * A file that is not what it says, or a type not taken, is a 415.
	 *
	 * @testWith ["MZ\u0090\u0000program", "image/jpeg"]
	 *           ["<svg xmlns=\"http://www.w3.org/2000/svg\"/>", "image/svg+xml"]
	 *           ["%PDF-1.4 sent as a photo", "image/png"]
	 *           ["RIFF____WAVEfmt ", "image/webp"]
	 *           ["\u00ff\u00d8\u00ff heic sent raw", "image/heic"]
	 *
	 * @param string $bytes The file.
	 * @param string $type  Its declared type.
	 */
	public function test_a_file_that_is_not_what_it_says_is_refused( string $bytes, string $type ): void {
		$result = $this->attachments()->check( array( self::file( $bytes, $type ) ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_type', $result->get_error_code() );
		$this->assertSame( 415, $result->get_error_data()['status'] );
		$this->assertSame( array(), $this->taken );
	}

	/**
	 * More than three files, or base64 that is not, is a 400.
	 */
	public function test_too_many_files_or_broken_data_is_refused(): void {
		$jpeg   = self::file( "\xFF\xD8\xFFjpeg", 'image/jpeg' );
		$result = $this->attachments()->check( array( $jpeg, $jpeg, $jpeg, $jpeg ) );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_count', $result->get_error_code() );

		$broken = $this->attachments()->check(
			array(
				array(
					'name' => 'x.jpg',
					'type' => 'image/jpeg',
					'data' => '!!not base64!!',
				),
			)
		);
		$this->assertInstanceOf( WP_Error::class, $broken );
		$this->assertSame( 'linker_genie_attachment_unreadable', $broken->get_error_code() );
	}

	/**
	 * An image over its size, or a turn over its total, is a 413.
	 */
	public function test_an_oversize_file_or_turn_is_refused(): void {
		$image  = self::file( "\xFF\xD8\xFF" . str_repeat( '0', Attachments::MAX_IMAGE_BYTES ), 'image/jpeg' );
		$result = $this->attachments()->check( array( $image ) );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_size', $result->get_error_code() );
		$this->assertSame( 413, $result->get_error_data()['status'] );

		$pdf   = self::file( '%PDF-' . str_repeat( '0', 11 * 1024 * 1024 ), 'application/pdf' );
		$total = $this->attachments()->check( array( $pdf, $pdf ) );
		$this->assertInstanceOf( WP_Error::class, $total );
		$this->assertSame( 'linker_genie_attachment_size', $total->get_error_code() );
	}

	/**
	 * Past the hourly allowance the turn is a 429; a signed-in customer
	 * counts by account, a guest by connection.
	 */
	public function test_past_the_allowance_the_turn_is_refused(): void {
		$jpeg   = self::file( "\xFF\xD8\xFFjpeg", 'image/jpeg' );
		$result = $this->attachments( 1 )->check( array( $jpeg, $jpeg ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_throttled', $result->get_error_code() );
		$this->assertSame( 429, $result->get_error_data()['status'] );
		$this->assertSame( Attachments::LIMIT, $result->get_error_data()['limit'] );
	}

	/**
	 * A signed-in customer's uploads count against their account.
	 */
	public function test_a_signed_in_customer_counts_by_account(): void {
		$this->attachments( 100, 42 )->check( array( self::file( "\xFF\xD8\xFFjpeg", 'image/jpeg' ) ) );

		$this->assertSame( array( 'user:42' ), $this->taken );
	}
}
