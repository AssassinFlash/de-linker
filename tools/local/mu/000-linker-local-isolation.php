<?php
/**
 * Plugin Name: Linker local isolation
 * Description: Keeps a local instance to itself: mail is written to files, WordPress's outbound HTTP may reach 127.0.0.1 only, pages may load resources from this machine only, and search engines are asked not to index.
 *
 * Copied into wp-content/mu-plugins by linker-local (tools/local); never deployed.
 *
 * @package Linker\Local
 */

declare( strict_types = 1 );

defined( 'ABSPATH' ) || exit;

// The instance directory, defined in wp-config.php by linker-local. Without it
// there is nowhere to put mail, so the site stops instead of sending any.
if ( ! defined( 'LINKER_LOCAL_DIR' ) ) {
	throw new RuntimeException( 'LINKER_LOCAL_DIR is not defined; this mu-plugin belongs to an instance made by linker-local.' );
}

add_filter( 'pre_wp_mail', 'linker_local_capture_mail', PHP_INT_MAX );
add_filter( 'wp_mail_from', 'linker_local_mail_from' );
add_filter( 'pre_http_request', 'linker_local_filter_http', PHP_INT_MAX, 3 );

if ( 'cli' !== PHP_SAPI && ! headers_sent() ) {
	// The browser may fetch from this machine only (any port: the instance, its engine and Genie).
	header( "Content-Security-Policy: default-src 'self' http://127.0.0.1:* data: blob: 'unsafe-inline' 'unsafe-eval'; form-action 'self'" );
	header( 'X-Robots-Tag: noindex, nofollow' );
}

/**
 * Lets wp_mail() build the message as usual, then hands it a mailer that writes
 * the message to LINKER_LOCAL_DIR/mail/*.eml instead of sending it.
 *
 * @param null|bool $pre Short-circuit value from an earlier filter; null to send.
 * @return null|bool The value unchanged.
 */
function linker_local_capture_mail( $pre ) {
	if ( null === $pre ) {
		// phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- wp_mail() sends through this global; replacing it is how mail stays local.
		$GLOBALS['phpmailer'] = linker_local_mailer( LINKER_LOCAL_DIR . '/mail' );
	}
	return $pre;
}

/**
 * WordPress's default sender is wordpress@<site host>. With the host 127.0.0.1
 * PHPMailer rejects it ("Invalid address: (From)") and every such mail fails
 * here while it is sent from a domain in production; .test is reserved and
 * never delivered (RFC 6761 §6.2).
 *
 * @param string $from Sender address.
 * @return string
 */
function linker_local_mail_from( string $from ): string {
	return 'wordpress@127.0.0.1' === $from ? 'wordpress@example.test' : $from;
}

/**
 * A WordPress mailer whose sending step writes the finished message to a file:
 * the same bytes mail() would receive, with To, Subject, Cc and Bcc headers.
 *
 * @param string $directory Directory of the .eml files.
 * @return PHPMailer\PHPMailer\PHPMailer
 */
function linker_local_mailer( string $directory ) {
	require_once ABSPATH . WPINC . '/PHPMailer/PHPMailer.php';
	require_once ABSPATH . WPINC . '/PHPMailer/SMTP.php';
	require_once ABSPATH . WPINC . '/PHPMailer/Exception.php';
	require_once ABSPATH . WPINC . '/class-wp-phpmailer.php';

	return new class( $directory ) extends WP_PHPMailer {

		/**
		 * Directory of the .eml files.
		 *
		 * @var string
		 */
		private string $directory;

		/**
		 * Constructor.
		 *
		 * @param string $directory Directory of the .eml files.
		 */
		public function __construct( string $directory ) {
			// Exceptions on, as wp_mail() creates its mailer.
			parent::__construct( true );
			$this->directory = $directory;
		}

		/**
		 * Writes the message instead of sending it.
		 *
		 * @return bool Whether the file was written.
		 */
		public function postSend(): bool {
			$file = sprintf( '%s/%s-%s.eml', $this->directory, gmdate( 'Ymd-His' ), bin2hex( random_bytes( 4 ) ) );
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a local file outside WP_Filesystem's scope.
			return false !== file_put_contents( $file, $this->getSentMIMEMessage() );
		}
	};
}

/**
 * Lets WordPress's HTTP API reach 127.0.0.1 only; anything else is refused and
 * written to LINKER_LOCAL_DIR/logs/isolation.log.
 *
 * @param false|array<string, mixed>|WP_Error $response Answer from an earlier filter, false to send.
 * @param array<string, mixed>                $args     Request arguments.
 * @param string                              $url      Request URL.
 * @return false|array<string, mixed>|WP_Error
 */
function linker_local_filter_http( $response, array $args, string $url ) {
	if ( false !== $response ) {
		return $response;
	}
	if ( '127.0.0.1' === wp_parse_url( $url, PHP_URL_HOST ) ) {
		return false;
	}
	$method = isset( $args['method'] ) && is_string( $args['method'] ) ? $args['method'] : 'GET';
	$line   = sprintf( "%s\t%s\t%s\n", gmdate( 'c' ), $method, $url );
	// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a local log outside WP_Filesystem's scope.
	file_put_contents( LINKER_LOCAL_DIR . '/logs/isolation.log', $line, FILE_APPEND | LOCK_EX );
	return new WP_Error( 'linker_local_blocked', sprintf( 'Blocked by the local isolation: %s', $url ) );
}
