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
 * files; each a JPEG, PNG, WebP or PDF by its first bytes, whatever its name or
 * declared type; each under its type's size and the turn under MAX_TURN_BYTES;
 * and every file counts against the caller's hourly allowance (RateLimit, one
 * statement per take), so nobody can spend the site's deepseek-flash budget by
 * uploading in a loop. The service checks the same limits again (the numbers are
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
	 * The accepted types and the bytes each starts with.
	 *
	 * @var array<string, string>
	 */
	private const MAGIC = array(
		'image/jpeg'      => "\xFF\xD8\xFF",
		'image/png'       => "\x89PNG\r\n\x1A\n",
		'image/webp'      => 'RIFF',
		'application/pdf' => '%PDF-',
	);

	/**
	 * Takes one unit of a caller's hourly allowance; false past it.
	 *
	 * @var callable(string): bool
	 */
	private $take;

	/**
	 * Sets up the check.
	 *
	 * @param (callable(string): bool)|null $take The hourly allowance's take; a RateLimit's when omitted.
	 */
	public function __construct( ?callable $take = null ) {
		$this->take = $take ?? array( new RateLimit( 'genie_upload', self::LIMIT, HOUR_IN_SECONDS ), 'take' );
	}

	/**
	 * The turn's files as the service takes them, or why they are refused.
	 *
	 * @param mixed $raw The request's `attachments`.
	 * @return list<array{name: string, type: string, data: string}>|WP_Error
	 */
	public function check( mixed $raw ) {
		if ( null === $raw || array() === $raw ) {
			return array();
		}
		if ( ! is_array( $raw ) || count( $raw ) > self::MAX_FILES ) {
			return $this->refuse( 'count', 400 );
		}
		$files = array();
		$total = 0;
		foreach ( $raw as $item ) {
			if ( ! is_array( $item ) ) {
				return $this->refuse( 'type', 415 );
			}
			$type = is_string( $item['type'] ?? null ) ? $item['type'] : '';
			$data = is_string( $item['data'] ?? null ) ? $item['data'] : '';
			if ( ! isset( self::MAGIC[ $type ] ) ) {
				return $this->refuse( 'type', 415 );
			}
			$bytes = base64_decode( $data, true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- the file travels as base64; decoding is how its type and size are checked.
			if ( false === $bytes || '' === $bytes ) {
				return $this->refuse( 'unreadable', 400 );
			}
			if ( ! self::is( $bytes, $type ) ) {
				return $this->refuse( 'type', 415 );
			}
			$size   = strlen( $bytes );
			$total += $size;
			$max    = 'application/pdf' === $type ? self::MAX_PDF_BYTES : self::MAX_IMAGE_BYTES;
			if ( $size > $max || $total > self::MAX_TURN_BYTES ) {
				return $this->refuse( 'size', 413 );
			}
			$files[] = array(
				'name' => self::name( $item['name'] ?? '' ),
				'type' => $type,
				'data' => $data,
			);
		}
		$who = is_user_logged_in() ? 'user:' . get_current_user_id() : self::connection();
		foreach ( $files as $unused ) {
			unset( $unused );
			if ( ! ( $this->take )( $who ) ) {
				return $this->refuse( 'throttled', 429 );
			}
		}
		return $files;
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
		return 'image/webp' !== $type || 'WEBP' === substr( $bytes, 8, 4 );
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
	 * The refusal the shell shows, logged where staff can see it.
	 *
	 * @param string $reason Reason code: count, type, unreadable, size, throttled.
	 * @param int    $status HTTP status.
	 */
	private function refuse( string $reason, int $status ): WP_Error {
		if ( function_exists( 'wc_get_logger' ) ) {
			wc_get_logger()->warning(
				sprintf( 'Genie attachment refused: %s', $reason ),
				array( 'source' => 'linker-genie' )
			);
		}
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
	 * The address this connection came from, never a forwarded header a
	 * client could write itself.
	 */
	private static function connection(): string {
		return isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( (string) $_SERVER['REMOTE_ADDR'] ) ) : '';
	}
}
