<?php
/**
 * A message as wp_mail() would send it.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * The arguments of one wp_mail() call, with the sender and content type
 * settled at the time of the call. WooCommerce sets them through filters that
 * exist only while it sends; a message sent again later from the queue keeps
 * them in its headers.
 */
final class Message {


	/**
	 * Explicit internal routing marker, persisted by Outbox (#297).
	 */
	public const INTERNAL_HEADER = 'X-Linker-Internal: yes';
	/** Trusted server producer categories; never parsed from public mail headers. */
	public const STANDARD        = 'standard';
	public const REVIEW_REMINDER = 'review_reminder';

	/**
	 * Marks either native wp_mail header form as an internal notification.
	 *
	 * @param  string|string[] $headers Original headers.
	 * @return ($headers is string ? string : string[])
	 */
	public static function mark_internal( array|string $headers ): array|string {
		if ( is_string( $headers ) ) {
			return rtrim( $headers, "\r\n" ) . "\r\n" . self::INTERNAL_HEADER . "\r\n";
		}
		$headers[] = self::INTERNAL_HEADER;
		return $headers;
	}

	/**
	 * Sets up the message.
	 *
	 * @param string[] $to          Recipients.
	 * @param string   $subject     Subject.
	 * @param string   $body        Body.
	 * @param string[] $headers     Header lines, "Name: value".
	 * @param string[] $attachments Paths of attached files.
	 * @param bool     $critical    Server-owned producer priority.
	 * @param string   $category    Trusted native producer category.
	 */
	public function __construct(
		public readonly array $to,
		public readonly string $subject,
		public readonly string $body,
		public readonly array $headers,
		public readonly array $attachments,
		public readonly bool $critical = false,
		public readonly string $category = self::STANDARD
	) {
	}

	/**
	 * Whether the producer marked this as an internal notification.
	 */
	public function is_internal(): bool {
		foreach ( $this->headers as $header ) {
			if ( 0 === strcasecmp( trim( $header ), self::INTERNAL_HEADER ) ) {
				return true;
			}
		}
		return false;
	}

	/**
	 * The message of a wp_mail() call, read on pre_wp_mail.
	 *
	 * @param array<string, mixed> $atts The call's to, subject, message, headers and attachments.
	 */
	public static function from_wp_mail( array $atts ): self {
		$headers      = array();
		$from_email   = '';
		$from_name    = '';
		$content_type = '';
		$charset      = '';
		foreach ( self::lines( $atts['headers'] ?? array() ) as $line ) {
			if ( ! str_contains( $line, ':' ) ) {
				continue;
			}
			[ $name, $value ] = array_map( 'trim', explode( ':', $line, 2 ) );
			$lower            = strtolower( $name );
			if ( 'from' === $lower ) {
				if ( 1 === preg_match( '/^(.*)<(.+)>$/', $value, $parts ) ) {
					$from_name  = trim( $parts[1], " \t\"" );
					$from_email = trim( $parts[2] );
				} else {
					$from_email = $value;
				}
			} elseif ( 'content-type' === $lower ) {
				$pieces       = array_map( 'trim', explode( ';', $value ) );
				$content_type = (string) array_shift( $pieces );
				foreach ( $pieces as $piece ) {
					if ( str_starts_with( strtolower( $piece ), 'charset=' ) ) {
						$charset = trim( substr( $piece, 8 ), '"' );
					}
				}
			} else {
				$headers[] = $name . ': ' . $value;
			}
		}

		// The same defaults and filters as wp_mail() (wp-includes/pluggable.php), applied now.
     // phpcs:disable WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own filters, applied as wp_mail() applies them.
		/**
	* This filter is documented in wp-includes/pluggable.php
*/
		$from_email = (string) apply_filters( 'wp_mail_from', '' !== $from_email ? $from_email : self::default_from() );
		/**
	* This filter is documented in wp-includes/pluggable.php
*/
		$from_name = (string) apply_filters( 'wp_mail_from_name', '' !== $from_name ? $from_name : 'WordPress' );
		/**
	* This filter is documented in wp-includes/pluggable.php
*/
		$content_type = (string) apply_filters( 'wp_mail_content_type', '' !== $content_type ? $content_type : 'text/plain' );
		/**
	* This filter is documented in wp-includes/pluggable.php
*/
		$charset = (string) apply_filters( 'wp_mail_charset', '' !== $charset ? $charset : get_bloginfo( 'charset' ) );
     // phpcs:enable

		$headers[] = sprintf( 'From: %s <%s>', $from_name, $from_email );
		$headers[] = sprintf( 'Content-Type: %s; charset=%s', $content_type, $charset );

		$subject = $atts['subject'] ?? '';
		$body    = $atts['message'] ?? '';
		return new self(
			self::lines( $atts['to'] ?? array(), ',' ),
			is_string( $subject ) ? $subject : '',
			is_string( $body ) ? $body : '',
			$headers,
			self::lines( $atts['attachments'] ?? array() ),
			Producer::priority( $atts )
		);
	}

	/**
	 * The message as a JSON-ready array, for the queue.
	 *
	 * @return array{to: string[], subject: string, body: string, headers: string[], attachments: string[], critical: bool, category: string}
	 */
	public function to_array(): array {
		return array(
			'to'          => $this->to,
			'subject'     => $this->subject,
			'body'        => $this->body,
			'headers'     => $this->headers,
			'attachments' => $this->attachments,
			'critical'    => $this->critical,
			'category'    => $this->category,
		);
	}

	/**
	 * A message stored with to_array().
	 *
	 * @param array<string, mixed> $data Stored message.
	 */
	public static function from_array( array $data ): self {
		$subject = $data['subject'] ?? '';
		$body    = $data['body'] ?? '';
		return new self(
			self::lines( $data['to'] ?? array() ),
			is_string( $subject ) ? $subject : '',
			is_string( $body ) ? $body : '',
			self::lines( $data['headers'] ?? array() ),
			self::lines( $data['attachments'] ?? array() ),
			true === ( $data['critical'] ?? false ),
			self::REVIEW_REMINDER === ( $data['category'] ?? '' ) ? self::REVIEW_REMINDER : self::STANDARD
		);
	}

	/**
	 * A string or list of strings as a list of non-empty strings.
	 *
	 * @param  mixed            $value     Value.
	 * @param  non-empty-string $separator Separator of a string value ("\n" for headers, "," for recipients).
	 * @return list<string>
	 */
	private static function lines( $value, string $separator = "\n" ): array {
		$items = is_array( $value ) ? $value : explode( $separator, is_string( $value ) ? str_replace( "\r\n", "\n", $value ) : '' );
		$lines = array();
		foreach ( $items as $item ) {
			if ( is_string( $item ) && '' !== trim( $item ) ) {
				$lines[] = trim( $item );
			}
		}
		return $lines;
	}

	/**
	 * WordPress's default sender: wordpress@ and the site's host without "www.".
	 */
	private static function default_from(): string {
		$host = (string) wp_parse_url( network_home_url(), PHP_URL_HOST );
		return 'wordpress@' . ( str_starts_with( $host, 'www.' ) ? substr( $host, 4 ) : $host );
	}
}
