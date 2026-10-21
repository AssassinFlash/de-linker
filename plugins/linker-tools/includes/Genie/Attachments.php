<?php
/**
 * The files a turn carries to Genie, checked before they leave the site.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Error;

/**
 * Checks a turn's attachments (ticket #236, docs/specs/13-genie.md "附件与铭牌").
 *
 * The browser sends each file as base64 in the turn's `attachments`, apart from
 * its messages. Here, before anything reaches the service: at most MAX_FILES
 * files; each a JPEG, PNG, WebP or PDF by its first bytes, or a CSV or Excel
 * parts list (#251), whatever its name or declared type; each under its type's
 * size and the turn under MAX_TURN_BYTES;
 * and every file counts against the caller's hourly allowance (RateLimit, one
 * statement per take), so nobody can spend the site's deepseek-flash budget by
 * uploading in a loop; a refused turn counts too, so nobody can repeat refused
 * uploads for free either. The service checks the same limits again (the numbers are
 * the service's schema.py's; tests/test_attachments.py in services/genie locks
 * them together).
 *
 * Nothing here stores a file: the bytes go to the service with the turn and
 * nowhere else, and only what the service read is kept with the conversation
 * (Thread::READINGS). No file is ever written under the web root or served.
 */
class Attachments {

	/**
	 * Files per turn: a nameplate photo, a second angle of it and a datasheet.
	 */
	public const MAX_FILES = 3;

	/**
	 * Bytes of one image. The shell sends a JPEG of about 1.69 megapixels (a few
	 * hundred kilobytes); six mebibytes hold even an uncompressed image of that
	 * size (5.07 MB of RGB) from another client.
	 */
	public const MAX_IMAGE_BYTES = 6291456;

	/**
	 * Bytes of one PDF: the largest hosted datasheet is 5.09 MB and the median
	 * hosted manual 7.3 MB (uploads of the live snapshot 2026-10-18).
	 */
	public const MAX_PDF_BYTES = 16777216;

	/**
	 * Bytes of one parts list (#251). A 20-row list is two kilobytes; one mebibyte
	 * holds about twenty thousand lines of the shape customers paste, and the
	 * largest list in the research is 61 rows (Taobao, CN.md S32).
	 */
	public const MAX_CSV_BYTES = 1048576;

	/**
	 * Bytes of one Excel list: a workbook may carry images and styles, so it keeps
	 * the image ceiling (Attachments::MAX_IMAGE_BYTES).
	 */
	public const MAX_XLSX_BYTES = 6291456;

	/**
	 * Bytes of one turn's files: well below deepseek-flash's 48 MiB request body
	 * (docs/research/2026-10-17-deepseek-flash-vision/ §3.2).
	 */
	public const MAX_TURN_BYTES = 20971520;

	/**
	 * A file name's length: the longest most file systems allow (255 bytes).
	 */
	public const NAME_LENGTH = 255;

	/**
	 * Files one caller may send per hour. A nameplate session takes one to three
	 * photos and perhaps a datasheet; twenty cover several devices, and cap a
	 * caller's spend at twenty image reads an hour (each at most 1024 image
	 * tokens, research §3.3).
	 */
	public const LIMIT = 20;

	/**
	 * The accepted types and the bytes each starts with; a WebP file also
	 * says WEBP_MARK at byte WEBP_OFFSET (RIFF container). The service's
	 * attachments.MAGIC and the shell's prepare.ts hold the same table
	 * (services/genie/tests/test_attachments.py locks the three).
	 *
	 * @var array<string, string>
	 */
	public const MAGIC = array(
		'image/jpeg'      => "\xFF\xD8\xFF",
		'image/png'       => "\x89PNG\r\n\x1A\n",
		'image/webp'      => 'RIFF',
		'application/pdf' => '%PDF-',
		// A parts list (#251): CSV is text with no first bytes (checked by
		// is_csv), Excel is a zip of XML (the service checks the workbook).
		'text/csv'        => '',
		'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' => "PK\x03\x04",
	);

	/**
	 * Where a WebP file names itself, and how.
	 */
	public const WEBP_OFFSET = 8;

	/**
	 * WebP's mark at WEBP_OFFSET.
	 */
	public const WEBP_MARK = 'WEBP';

	/**
	 * Takes units of a caller's hourly allowance in one statement; false
	 * when they would pass it, and then nothing is taken.
	 *
	 * @var callable(string, int): bool
	 */
	private $take;

	/**
	 * Sets up the check.
	 *
	 * @param (callable(string, int): bool)|null $take The hourly allowance's take; a RateLimit's when omitted.
	 */
	public function __construct( ?callable $take = null ) {
		$this->take = $take ?? array( new RateLimit( 'genie_upload', self::LIMIT, HOUR_IN_SECONDS ), 'take' );
	}

	/**
	 * The turn's files as the service takes them, or why they are refused.
	 *
	 * Every file is checked before any allowance is taken, so a refusal
	 * of the third file spends nothing on the first two. A refused turn
	 * takes one unit itself: a caller who repeats oversized or disguised
	 * uploads runs into the hourly limit like one who uploads, and the
	 * refusal log grows no faster than the allowance (a throttled request
	 * is answered 429 and not logged). An accepted turn takes one unit per
	 * file, all at once.
	 *
	 * @param mixed $raw The request's `attachments`.
	 * @return list<array{name: string, type: string, data: string}>|WP_Error
	 */
	public function check( mixed $raw ) {
		if ( null === $raw || array() === $raw ) {
			return array();
		}
		$who   = is_user_logged_in() ? 'user:' . get_current_user_id() : self::connection();
		$files = $this->files( $raw );
		if ( $files instanceof WP_Error ) {
			if ( ! ( $this->take )( $who, 1 ) ) {
				return $this->throttled();
			}
			$this->log( (string) $files->get_error_code() );
			return $files;
		}
		if ( ! \Linker\Tools\Protection\Resources::verified() && ! ( $this->take )( $who, count( $files ) ) ) {
			return $this->throttled();
		}
		return $files;
	}

	/**
	 * The files, each checked, or the first refusal (not yet logged).
	 *
	 * @param mixed $raw The request's `attachments`.
	 * @return list<array{name: string, type: string, data: string}>|WP_Error
	 */
	private function files( mixed $raw ) {
		if ( ! is_array( $raw ) || count( $raw ) > self::MAX_FILES ) {
			return $this->refusal( 'count', 400 );
		}
		$files = array();
		$total = 0;
		foreach ( $raw as $item ) {
			if ( ! is_array( $item ) ) {
				return $this->refusal( 'type', 415 );
			}
			$type = is_string( $item['type'] ?? null ) ? $item['type'] : '';
			$data = is_string( $item['data'] ?? null ) ? $item['data'] : '';
			if ( ! isset( self::MAGIC[ $type ] ) ) {
				return $this->refusal( 'type', 415 );
			}
			$max = match ( $type ) {
				'application/pdf' => self::MAX_PDF_BYTES,
				'text/csv' => self::MAX_CSV_BYTES,
				'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' => self::MAX_XLSX_BYTES,
				default => self::MAX_IMAGE_BYTES,
			};
			// The size is known from the base64 length: a file past its cap is
			// refused before anything is decoded.
			if ( strlen( $data ) > self::encoded( $max ) ) {
				return $this->refusal( 'size', 413 );
			}
			$bytes = base64_decode( $data, true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- the file travels as base64; decoding is how its type and size are checked.
			if ( false === $bytes || '' === $bytes ) {
				return $this->refusal( 'unreadable', 400 );
			}
			if ( ! self::is( $bytes, $type ) ) {
				return $this->refusal( 'type', 415 );
			}
			$size   = strlen( $bytes );
			$total += $size;
			if ( $size > $max || $total > self::MAX_TURN_BYTES ) {
				return $this->refusal( 'size', 413 );
			}
			$files[] = array(
				'name' => self::name( $item['name'] ?? '' ),
				'type' => $type,
				'data' => $data,
			);
		}
		return $files;
	}

	/**
	 * Characters of `$bytes` bytes in base64: three bytes are four characters.
	 *
	 * @param int $bytes A size in bytes.
	 */
	public static function encoded( int $bytes ): int {
		return intdiv( $bytes + 2, 3 ) * 4;
	}

	/**
	 * Whether the bytes are the type they were sent as.
	 *
	 * @param string $bytes The file.
	 * @param string $type  Its declared type.
	 */
	private static function is( string $bytes, string $type ): bool {
		if ( ! str_starts_with( $bytes, self::MAGIC[ $type ] ) ) {
			return false;
		}
		if ( 'text/csv' === $type ) {
			// Text, not a binary file renamed: no NUL byte and at least one letter
			// (the service decodes UTF-8 or Windows-1252 and parses the rows).
			return false === strpos( $bytes, "\0" ) && 1 === preg_match( '/[A-Za-z]/', $bytes );
		}
		return 'image/webp' !== $type || self::WEBP_MARK === substr( $bytes, self::WEBP_OFFSET, strlen( self::WEBP_MARK ) );
	}

	/**
	 * A file name as the thread shows it: no path, no control characters, cut.
	 *
	 * @param mixed $name The name as sent.
	 */
	private static function name( mixed $name ): string {
		$name = is_string( $name ) ? $name : '';
		$name = (string) preg_replace( '/[\x00-\x1F\x7F]/u', '', wp_basename( str_replace( '\\', '/', $name ) ) );
		$name = mb_substr( trim( $name ), 0, self::NAME_LENGTH );
		return '' !== $name ? $name : 'file';
	}

	/**
	 * A refusal the shell shows; `check` logs it once its unit is taken.
	 *
	 * @param string $reason Reason code: count, type, unreadable, size.
	 * @param int    $status HTTP status.
	 */
	private function refusal( string $reason, int $status ): WP_Error {
		return new WP_Error(
			'linker_genie_attachment_' . $reason,
			'The attachment was not accepted.',
			array(
				'status'    => $status,
				'max_files' => self::MAX_FILES,
				'limit'     => self::LIMIT,
			)
		);
	}

	/**
	 * The answer past the hourly allowance: explicit (429), not logged, so a
	 * flood of requests cannot flood the log.
	 */
	private function throttled(): WP_Error {
		return $this->refusal( 'throttled', 429 );
	}

	/**
	 * Logs a refusal where staff can see it.
	 *
	 * @param string $code The refusal's error code.
	 */
	private function log( string $code ): void {
		if ( function_exists( 'wc_get_logger' ) ) {
			wc_get_logger()->warning(
				sprintf( 'Genie attachment refused: %s', str_replace( 'linker_genie_attachment_', '', $code ) ),
				array( 'source' => 'linker-genie' )
			);
		}
	}

	/**
	 * The address this connection came from, never a forwarded header a
	 * client could write itself.
	 */
	private static function connection(): string {
		return isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( (string) $_SERVER['REMOTE_ADDR'] ) ) : '';
	}
}
