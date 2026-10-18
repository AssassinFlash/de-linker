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
	 * Who asked for how many units of the allowance, as "who×units".
	 *
	 * @var list<string>
	 */
	private array $taken = array();

	/**
	 * Units left after the last check.
	 *
	 * @var int
	 */
	private int $left = 0;

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
		$this->left = $left;
		return new Attachments(
			function ( string $who, int $units ): bool {
				$this->taken[] = $who . '×' . $units;
				if ( $units > $this->left ) {
					return false;
				}
				$this->left -= $units;
				return true;
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
	 * JPEG, PNG, WebP and PDF pass by their first bytes; the turn takes one
	 * unit of the connection's allowance per file, in one take; a name loses
	 * its path.
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
		$this->assertSame( array( '203.0.113.7×3' ), $this->taken );
		$pdf = $this->attachments()->check( array( self::file( '%PDF-1.7 ...', 'application/pdf', 'ds.pdf' ) ) );
		$this->assertIsArray( $pdf );
		$this->assertSame( 'application/pdf', $pdf[0]['type'] );
	}

	/**
	 * A file that is not what it says, or a type not taken, is a 415, and the
	 * refused turn takes one unit.
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
		$this->assertSame( array( '203.0.113.7×1' ), $this->taken );
	}

	/**
	 * Every file is checked before allowance is taken: a refused third file
	 * spends one unit for the refusal, nothing for the two good ones.
	 */
	public function test_a_later_refusal_spends_nothing_on_earlier_files(): void {
		$jpeg   = self::file( "\xFF\xD8\xFFjpeg", 'image/jpeg' );
		$result = $this->attachments( 20 )->check( array( $jpeg, $jpeg, self::file( 'MZ', 'image/png' ) ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_type', $result->get_error_code() );
		$this->assertSame( array( '203.0.113.7×1' ), $this->taken );
		$this->assertSame( 19, $this->left );
	}

	/**
	 * Refusals count against the allowance: once it is spent, a refused
	 * upload is answered 429 like any other, so repeating it is not free.
	 */
	public function test_repeated_refusals_run_into_the_allowance(): void {
		$bad   = array( self::file( 'MZ', 'image/jpeg' ) );
		$check = $this->attachments( 2 );

		foreach ( array( 1, 2 ) as $attempt ) {
			$refused = $check->check( $bad );
			$this->assertInstanceOf( WP_Error::class, $refused, "attempt $attempt" );
			$this->assertSame( 'linker_genie_attachment_type', $refused->get_error_code() );
		}
		$third = $check->check( $bad );
		$this->assertInstanceOf( WP_Error::class, $third );
		$this->assertSame( 'linker_genie_attachment_throttled', $third->get_error_code() );
		$this->assertSame( 429, $third->get_error_data()['status'] );
	}

	/**
	 * A file's size is read from its base64 length before it is decoded: an
	 * oversize body that is not even base64 is a 413, not a decode.
	 */
	public function test_an_oversize_file_is_refused_before_it_is_decoded(): void {
		$result = $this->attachments()->check(
			array(
				array(
					'name' => 'x.jpg',
					'type' => 'image/jpeg',
					'data' => str_repeat( '!', Attachments::encoded( Attachments::MAX_IMAGE_BYTES ) + 4 ),
				),
			)
		);

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_size', $result->get_error_code() );
		$this->assertSame( 8388608, Attachments::encoded( Attachments::MAX_IMAGE_BYTES ) );
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
	 * Past the hourly allowance the turn is a 429 and takes nothing: two
	 * files do not fit in one unit.
	 */
	public function test_past_the_allowance_the_turn_is_refused(): void {
		$jpeg   = self::file( "\xFF\xD8\xFFjpeg", 'image/jpeg' );
		$result = $this->attachments( 1 )->check( array( $jpeg, $jpeg ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_throttled', $result->get_error_code() );
		$this->assertSame( 429, $result->get_error_data()['status'] );
		$this->assertSame( Attachments::LIMIT, $result->get_error_data()['limit'] );
		$this->assertSame( array( '203.0.113.7×2' ), $this->taken );
		$this->assertSame( 1, $this->left );
	}

	/**
	 * A signed-in customer's uploads count against their account.
	 */
	public function test_a_signed_in_customer_counts_by_account(): void {
		$this->attachments( 100, 42 )->check( array( self::file( "\xFF\xD8\xFFjpeg", 'image/jpeg' ) ) );

		$this->assertSame( array( 'user:42×1' ), $this->taken );
	}

	/**
	 * A parts list passes (#251): CSV as text, Excel as the zip it is; the
	 * workbook itself is checked by the service, which reads the rows.
	 */
	public function test_parts_lists_pass_as_text_and_workbook(): void {
		$files = $this->attachments()->check(
			array(
				self::file( "Produkt;Menge\nSAJ H2-10K-T3;2\n", 'text/csv', 'list.csv' ),
				self::file( "PK\x03\x04workbook", 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'list.xlsx' ),
			)
		);

		$this->assertIsArray( $files );
		$this->assertSame(
			array( 'text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ),
			array_column( $files, 'type' )
		);
	}

	/**
	 * A binary file renamed to .csv is a 415: the text is checked, not only the
	 * extension.
	 */
	public function test_a_binary_file_sent_as_csv_is_refused(): void {
		$result = $this->attachments()->check(
			array( self::file( "\x00\x01binary", 'text/csv', 'list.csv' ) )
		);

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_type', $result->get_error_code() );
		$this->assertSame( 415, $result->get_error_data()['status'] );
	}

	/**
	 * A CSV is refused past its own ceiling (the image's would let a 6 MB text
	 * file through).
	 */
	public function test_a_csv_over_its_limit_is_refused(): void {
		$csv    = self::file( 'a' . str_repeat( '0', Attachments::MAX_CSV_BYTES ), 'text/csv', 'list.csv' );
		$result = $this->attachments()->check( array( $csv ) );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_genie_attachment_size', $result->get_error_code() );
		$this->assertSame( 413, $result->get_error_data()['status'] );
	}
}
