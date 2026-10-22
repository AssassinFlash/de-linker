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
use Linker\Commerce\Settings\PrivateConfigDirectory;
use PHPMailer\PHPMailer\Exception;
use PHPMailer\PHPMailer\PHPMailer;

/**
 * Reads the owner's server-side file only. Secrets never enter options,
 * queue data or logs. Tests inject a temporary path containing fake values.
 */
final class InternalSmtp {


	/**
	 * Fixed public diagnostic; server responses must never enter logs or jobs.
	 */
	public const FAILURE_MESSAGE = 'Internal notification delivery failed.';

	/**
	 * Reason of the active attempt, reset before each configuration.
	 *
	 * @var string
	 */
	private string $failure_reason = SmtpOutcome::SMTP_FAILURE;

	/**
	 * Sets up the file boundary; empty means #297's path outside the web root.
	 *
	 * @param string  $path    Fake env file in tests, otherwise the default path.
	 * @param Options $options Internal sender settings.
	 */
	public function __construct( private readonly string $path = '', private readonly Options $options = new Options() ) {
	}

	/**
	 * Whether internal mail has complete configuration matching its sender.
	 * This checks configuration, not remote connectivity or inbox delivery.
	 */
	public function authenticated(): bool {
		$config = $this->configuration();
		return null !== $config && $this->options->notify_sender()->email === $config['user'];
	}

	/**
	 * Configuration exists; identity is still enforced in configure() before sending.
	 */
	public function available(): bool {
		return null !== $this->configuration();
	}

	/**
	 * Fixed category of an unsuccessful SMTP attempt.
	 */
	public function failure_reason(): string {
		return $this->failure_reason;
	}

	/**
	 * Configure WordPress's native mailer for this Outbox attempt alone.
	 *
	 * @param  PHPMailer $mailer   WordPress's reusable mailer.
	 * @param  bool      $internal The queued message's explicit internal marker.
	 * @throws Exception When a queued sender no longer matches the auth identity.
	 */
	public function configure( PHPMailer $mailer, bool $internal ): bool {
		$this->reset( $mailer );
		$this->failure_reason = SmtpOutcome::SMTP_FAILURE;
		$mailer->clearCustomHeader( explode( ':', Message::INTERNAL_HEADER, 2 )[0] );
		$config = $internal ? $this->configuration() : null;
		if ( null === $config ) {
			return false;
		}
		if ( $mailer->From !== $config['user'] || $this->options->notify_sender()->email !== $config['user'] ) {
			$this->failure_reason = SmtpOutcome::IDENTITY_MISMATCH;
			throw new Exception( esc_html( self::FAILURE_MESSAGE ) );
		}
		$mailer->isSMTP();
		$mailer->Host        = $config['host'];
		$mailer->Port        = $config['port'];
		$mailer->SMTPAuth    = true;
		$mailer->Username    = $config['user'];
		$mailer->Password    = $config['password'];
		$mailer->Sender      = $config['user'];
		$mailer->SMTPSecure  = $config['secure'];
		$mailer->SMTPAutoTLS = '' !== $config['secure'];
		return true;
	}

	/**
	 * Remove authentication state before customer mail and after every attempt.
	 *
	 * @param PHPMailer $mailer WordPress's reusable mailer.
	 */
	public function reset( PHPMailer $mailer ): void {
		$mailer->smtpClose();
		$mailer->isMail();
		// PHPMailer declares Port=25 and SMTPAutoTLS=true as its native defaults.
		$mailer->Port          = 25;
		$mailer->SMTPAutoTLS   = true;
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
	 * Reads literal KEY=VALUE lines without interpolation or INI comment rules.
	 *
	 * @return array{host: string, port: int, user: string, password: string, secure: string}|null
	 */
	private function configuration(): ?array {
		$path = '' !== $this->path ? $this->path : PrivateConfigDirectory::path( 'sunriver-smtp.env' );
		if ( '' === $path || ! is_readable( $path ) ) {
			return null;
		}
		$bytes = file_get_contents( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- private config file outside the website.
		if ( false === $bytes ) {
			return null;
		}
		$env = array();
		foreach ( explode( "\n", $bytes ) as $line ) {
			$line = trim( $line );
			if ( '' === $line || str_starts_with( $line, '#' ) || ! str_contains( $line, '=' ) ) {
				continue;
			}
			list( $key, $value ) = explode( '=', $line, 2 );
			$key                 = trim( $key );
			$value               = trim( $value );
			if ( ( str_starts_with( $value, "'" ) && str_ends_with( $value, "'" ) ) || ( str_starts_with( $value, '"' ) && str_ends_with( $value, '"' ) ) ) {
				$value = substr( $value, 1, -1 );
			}
			$env[ $key ] = $value;
		}
		foreach ( array( 'LINKER_SMTP_HOST', 'LINKER_SMTP_PORT', 'LINKER_SMTP_USER', 'LINKER_SMTP_PASS' ) as $key ) {
			if ( ! isset( $env[ $key ] ) || '' === trim( $env[ $key ] ) ) {
				return null;
			}
		}
		$port = filter_var( $env['LINKER_SMTP_PORT'], FILTER_VALIDATE_INT );
		// TCP port bounds (IANA); SMTP encryption follows PHPMailer's 465/587 conventions.
		if ( false === $port || $port < 1 || $port > 65535 ) {
			return null;
		}
		// PHPMailer accepts host lists and URI prefixes; this file names one host (#297).
		if ( 1 !== preg_match( '/^[a-zA-Z0-9.-]+$/D', $env['LINKER_SMTP_HOST'] ) ) {
			return null;
		}
		// PHPMailer's encryption names: implicit TLS on 465, STARTTLS otherwise.
		$secure = $env['LINKER_SMTP_SECURE'] ?? ( 465 === $port ? 'ssl' : 'tls' );
		if ( ! in_array( $secure, array( '', 'ssl', 'tls' ), true ) ) {
			return null;
		}
		return array(
			'host'     => $env['LINKER_SMTP_HOST'],
			'port'     => $port,
			'user'     => $env['LINKER_SMTP_USER'],
			'password' => $env['LINKER_SMTP_PASS'],
			'secure'   => $secure,
		);
	}
}
