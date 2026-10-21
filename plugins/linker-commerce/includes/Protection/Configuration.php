<?php
/**
 * Private configuration of the shared public-entry verification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Secrets never travel through the WordPress options or public health data. */
final class Configuration {
	/**
	 * Explicit values make local fixtures independent of production credentials.
	 *
	 * @param string $mode off, observe or enforce.
	 * @param string $site_key Public widget key.
	 * @param string $secret Private validation key.
	 * @param string $hostname Expected challenge hostname.
	 */
	public function __construct(
		public readonly string $mode,
		public readonly string $site_key,
		private readonly string $secret,
		public readonly string $hostname
	) {}

	/** Constants in private wp-config take precedence over the process environment. */
	public static function current(): self {
		return new self(
			self::active_mode(),
			self::value( 'LINKER_TURNSTILE_SITE_KEY' ),
			self::value( 'LINKER_TURNSTILE_SECRET_KEY' ),
			self::value( 'LINKER_TURNSTILE_HOSTNAME', (string) wp_parse_url( home_url(), PHP_URL_HOST ) )
		);
	}

	/** Disabled consumers need only the private mode, without resolving site URLs. */
	public static function active_mode(): string {
		return self::value( 'LINKER_PUBLIC_PROTECTION_MODE', 'off' );
	}

	/** Do not treat an invalid mode or incomplete key pair as usable protection. */
	public function ready(): bool {
		return in_array( $this->mode, array( 'observe', 'enforce' ), true ) && $this->configured();
	}

	/** Key readiness is distinct from whether enforcement has been enabled. */
	public function configured(): bool {
		return '' !== $this->site_key && '' !== $this->secret && '' !== $this->hostname
			&& ( 'production' !== wp_get_environment_type() || ! $this->test_keys() );
	}

	/**
	 * The private value appears only in the canonical outgoing validation body.
	 *
	 * @param string $token Current challenge token.
	 * @param string $request_id Stable verification UUID.
	 * @return array{secret: string, response: string, idempotency_key: string}
	 */
	public function verification_body( string $token, string $request_id ): array {
		return array(
			'secret'          => $this->secret,
			'response'        => $token,
			'idempotency_key' => $request_id,
		);
	}

	/**
	 * Health deliberately contains neither secret nor the public widget key.
	 *
	 * @return array{mode: string, configured: bool, ready: bool, test_keys: bool}
	 */
	public function health(): array {
		return array(
			'mode'       => $this->mode,
			'configured' => $this->configured(),
			'ready'      => $this->ready(),
			'test_keys'  => $this->test_keys(),
		);
	}

	/** Official dummy key families are permitted only outside production. */
	private function test_keys(): bool {
		return 1 === preg_match( '/\A[123]x0{8}/', $this->site_key )
			|| 1 === preg_match( '/\A[123]x0{8}/', $this->secret );
	}

	/**
	 * Read only the named private setting, without logging its value.
	 *
	 * @param string $name Constant/environment name.
	 * @param string $fallback Value when absent.
	 */
	private static function value( string $name, string $fallback = '' ): string {
		$value = defined( $name ) ? constant( $name ) : getenv( $name );
		return is_string( $value ) && '' !== trim( $value ) ? trim( $value ) : $fallback;
	}
}
