<?php
/**
 * Authenticated transport for explicitly internal Outbox messages (#297).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

// phpcs:disable WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- PHPMailer defines these public property names.

use Linker\Commerce\Settings\Options;
use PHPMailer\PHPMailer\Exception;
use PHPMailer\PHPMailer\PHPMailer;

/**
 * Reads the owner's server-side file only. Secrets never enter options,
 * queue data or logs. Tests inject a temporary path containing fake values.
 */
final class InternalSmtp {

	/**
	 * Sets up the file boundary; empty means #297's path outside the web root.
	 *
	 * @param string $path Fake env file in tests, otherwise the default path.
	 */
	public function __construct( private readonly string $path = '' ) {}

	/**
	 * Whether internal mail has complete configuration matching its sender.
	 * This checks configuration, not remote connectivity or inbox delivery.
	 */
	public function authenticated(): bool {
		return null !== $this->configuration();
	}

	/**
	 * Configure WordPress's native mailer for this Outbox attempt alone.
	 *
	 * @param PHPMailer $mailer   WordPress's reusable mailer.
	 * @param bool      $internal The queued message's explicit internal marker.
	 * @throws Exception When a queued sender no longer matches the auth identity.
	 */
	public function configure( PHPMailer $mailer, bool $internal ): void {
		$this->reset( $mailer );
		$mailer->clearCustomHeader( 'X-Linker-Internal' );
		$config = $internal ? $this->configuration() : null;
		if ( null === $config ) {
			return;
		}
		if ( $mailer->From !== $config['user'] ) {
			throw new Exception( 'Internal SMTP sender does not match the authenticated identity.' );
		}
		$mailer->isSMTP();
		$mailer->Host     = $config['host'];
		$mailer->Port     = $config['port'];
		$mailer->SMTPAuth = true;
		$mailer->Username = $config['user'];
		$mailer->Password = $config['password'];
		$mailer->Sender   = $config['user'];
		// PHPMailer: implicit TLS on 465, STARTTLS otherwise. Plaintext is only
		// for the test-owned loopback sink required by #297, never a remote host.
		$mailer->SMTPSecure  = '127.0.0.1' === $config['host'] ? '' : ( 465 === $config['port'] ? PHPMailer::ENCRYPTION_SMTPS : PHPMailer::ENCRYPTION_STARTTLS );
		$mailer->SMTPAutoTLS = '127.0.0.1' !== $config['host'];
	}

	/**
	 * Remove authentication state before customer mail and after every attempt.
	 *
	 * @param PHPMailer $mailer WordPress's reusable mailer.
	 */
	public function reset( PHPMailer $mailer ): void {
		$mailer->smtpClose();
		$mailer->isMail();
		$mailer->Host          = '';
		$mailer->Username      = '';
		$mailer->Password      = '';
		$mailer->Sender        = '';
		$mailer->SMTPAuth      = false;
		$mailer->SMTPSecure    = '';
		$mailer->SMTPKeepAlive = false;
		$mailer->SMTPDebug     = 0; // #297: protocol diagnostics must never expose credentials.
		$mailer->ErrorInfo     = '';
	}

	/**
	 * Reads an INI-style env file without interpolation or evaluating shell code.
	 * Parser errors are suppressed because a malformed line could contain a secret.
	 *
	 * @return array{host: string, port: int, user: string, password: string}|null
	 */
	private function configuration(): ?array {
		$home = getenv( 'HOME' );
		$path = '' !== $this->path ? $this->path : ( is_string( $home ) && '' !== $home ? $home . '/.config/terravolt-builder/sunriver-smtp.env' : '' );
		if ( '' === $path || ! is_readable( $path ) ) {
			return null;
		}
		// phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged -- parser diagnostics may expose a secret; health reports configuration failure instead.
		$env = @parse_ini_file( $path, false, INI_SCANNER_RAW );
		if ( ! is_array( $env ) ) {
			return null;
		}
		foreach ( array( 'LINKER_SMTP_HOST', 'LINKER_SMTP_PORT', 'LINKER_SMTP_USER', 'LINKER_SMTP_PASS' ) as $key ) {
			if ( ! isset( $env[ $key ] ) || ! is_string( $env[ $key ] ) || '' === trim( $env[ $key ] ) ) {
				return null;
			}
			// INI strips double quotes; env files also commonly use single quotes.
			if ( str_starts_with( $env[ $key ], "'" ) && str_ends_with( $env[ $key ], "'" ) ) {
				$env[ $key ] = substr( $env[ $key ], 1, -1 );
			}
			if ( '' === trim( $env[ $key ] ) ) {
				return null;
			}
		}
		$port = filter_var( $env['LINKER_SMTP_PORT'], FILTER_VALIDATE_INT );
		// TCP port bounds (IANA); SMTP encryption follows PHPMailer's 465/587 conventions.
		if ( false === $port || $port < 1 || $port > 65535 || ( new Options() )->notify_sender()->email !== $env['LINKER_SMTP_USER'] ) {
			return null;
		}
		// PHPMailer accepts host lists and URI prefixes; this file names one host (#297).
		if ( 1 !== preg_match( '/^[a-zA-Z0-9.-]+$/D', $env['LINKER_SMTP_HOST'] ) ) {
			return null;
		}
		return array(
			'host'     => $env['LINKER_SMTP_HOST'],
			'port'     => $port,
			'user'     => $env['LINKER_SMTP_USER'],
			'password' => $env['LINKER_SMTP_PASS'],
		);
	}
}
