<?php
/**
 * Forward the commercial sizing command to the engine's existing design route.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/**
 * The engine sizes commercial storage only when it receives the load profile
 * and the target peak (services/engine/src/linker_engine/commercial.py
 * `design()`); without them it answers indicative ranges by design. The
 * planner workspace collects both, so this seam carries them.
 *
 * The command is rebuilt from an allowlist instead of forwarded verbatim: the
 * browser may only reach the engine's own commercial input contract, never an
 * arbitrary engine path or field.
 */
final class CommercialDesign {

	/** Matches the engine's own `load_profile_csv` bound. */
	public const MAX_PROFILE_CHARS = 4000000;

	/** Bounded engine reply; a design answer is smaller than a product feed. */
	private const MAX_REPLY_BYTES = 4 * 1024 * 1024;

	/** The engine's numeric field bounds, mirrored from its input model. */
	private const NUMBERS = array(
		'grid_connection_kva' => array( 10000.0, false ),
		'annual_kwh'          => array( 100000000.0, false ),
		'peak_kw'             => array( 10000.0, true ),
		'target_peak_kw'      => array( 10000.0, true ),
		'pv_kwp'              => array( 10000.0, true ),
		'backup_load_kw'      => array( 10000.0, true ),
		'backup_hours'        => array( 72.0, true ),
	);

	/** The engine's own goal vocabulary. */
	private const GOALS = array( 'peak_shaving', 'self_consumption', 'backup' );

	/**
	 * Select the native HTTP transport or a test adapter.
	 *
	 * @param (callable(string,array<string,mixed>):(array<string,mixed>|WP_Error))|null $fetch Native HTTP test seam.
	 */
	public function __construct( private mixed $fetch = null ) {}

	/**
	 * Send one commercial sizing command and return the engine's own answer.
	 *
	 * @param Principal           $principal Verified owner; its digest is the engine slot subject.
	 * @param array<string,mixed> $command Parsed browser command.
	 * @return array{status:int,body:string}|WP_Error Bounded JSON reply or private refusal.
	 */
	public function forward( Principal $principal, array $command ): array|WP_Error {
		$body = $this->command( $command );
		if ( is_wp_error( $body ) ) {
			return $body;
		}
		$base  = rtrim( (string) get_option( 'linker_engine_url', '' ), '/' );
		$token = defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ? (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ) : '';
		if ( '' === $base || '' === $token ) {
			return Failure::make( 'configuration', 503 );
		}
		$json = wp_json_encode( $body, JSON_PRESERVE_ZERO_FRACTION );
		if ( ! is_string( $json ) ) {
			return Failure::make( 'input', 400 );
		}
		$url      = $base . '/design/commercial';
		$args     = array(
			// The engine checks current publication before it sizes anything; a
			// cold product read has its own ten-second network budget.
			'timeout'             => 30.0,
			'redirection'         => 0,
			'sslverify'           => true,
			'limit_response_size' => self::MAX_REPLY_BYTES + 1,
			'headers'             => array(
				'Content-Type'              => 'application/json; charset=utf-8',
				'X-Linker-Service-Token'    => $token,
				'X-Linker-Resource-Subject' => $this->subject( $principal ),
			),
			'body'                => $json,
		);
		$response = is_callable( $this->fetch ) ? ( $this->fetch )( $url, $args ) : wp_remote_post( $url, $args );
		if ( is_wp_error( $response ) ) {
			return Failure::make( 'unavailable', 503 );
		}
		$status = (int) wp_remote_retrieve_response_code( $response );
		$body   = (string) wp_remote_retrieve_body( $response );
		if ( $status >= 300 && $status < 400 ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		if ( strlen( $body ) > self::MAX_REPLY_BYTES ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		// The engine's own refusal of a specific profile is the customer's to
		// act on, but its message is English server text; only a stable code
		// crosses this seam, so the interface keeps its own reviewed copy in
		// both languages.
		if ( 422 === $status && 'load_profile' === $this->detail_code( $body ) ) {
			$payload = wp_json_encode(
				array(
					'error' => array(
						'code' => $this->profile_code( (string) $this->detail_message( $body ) ),
					),
				)
			);
			return array(
				'status' => 422,
				'body'   => is_string( $payload ) ? $payload : '{"error":{"code":"profile_invalid"}}',
			);
		}
		if ( 200 !== $status ) {
			return Failure::make( self::refusal_code( $status ), $status >= 400 && $status < 600 ? $status : 502 );
		}
		$value = json_decode( $body, true, 64 );
		if ( ! is_array( $value ) || ! JsonNumbers::supported( $value ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		return array(
			'status' => 200,
			'body'   => $body,
		);
	}

	/**
	 * Rebuild only the engine's documented commercial input from the command.
	 *
	 * @param array<string,mixed> $command Parsed browser command.
	 * @return array<string,mixed>|WP_Error Engine input or explicit refusal.
	 */
	public function command( array $command ): array|WP_Error {
		$plz = $command['plz'] ?? null;
		if ( ! is_string( $plz ) || 1 !== preg_match( '/\A\d{5}\z/', $plz ) ) {
			return Failure::make( 'input', 422 );
		}
		$body = array(
			'plz'                 => $plz,
			'grid_connection_kva' => $this->number( $command['grid_connection_kva'] ?? null, 'grid_connection_kva' ),
			'annual_kwh'          => $this->number( $command['annual_kwh'] ?? null, 'annual_kwh' ),
			'goals'               => $this->goals( $command['goals'] ?? null ),
			'load_profile_unit'   => 'kWh' === ( $command['load_profile_unit'] ?? 'kW' ) ? 'kWh' : 'kW',
			'locale'              => 'de' === ( $command['locale'] ?? 'en' ) ? 'de' : 'en',
		);
		foreach ( $body as $key => $value ) {
			if ( is_wp_error( $value ) ) {
				return $value;
			}
		}
		foreach ( array_keys( self::NUMBERS ) as $key ) {
			if ( ! array_key_exists( $key, $command ) || null === $command[ $key ] ) {
				continue;
			}
			$body[ $key ] = $this->number( $command[ $key ], $key );
			if ( is_wp_error( $body[ $key ] ) ) {
				return $body[ $key ];
			}
		}
		$profile = $command['load_profile_csv'] ?? null;
		if ( null !== $profile ) {
			// The engine's own bound is a character count; a byte count would
			// refuse a file it accepts once a header carries a non-ASCII letter.
			if ( ! is_string( $profile ) || mb_strlen( $profile, 'UTF-8' ) > self::MAX_PROFILE_CHARS ) {
				return Failure::make( 'input', 422 );
			}
			$body['load_profile_csv'] = $profile;
		}
		return $body;
	}

	/**
	 * The engine slot subject is a stable digest, never the raw principal.
	 *
	 * @param Principal $principal Verified owner.
	 */
	private function subject( Principal $principal ): string {
		return hash( 'sha256', 'linker-commercial-design:v1|' . $principal->kind . '|' . $principal->subject );
	}

	/**
	 * One engine numeric field, with the engine's own positive/bound rule.
	 *
	 * @param mixed  $value Raw command value.
	 * @param string $key   Engine field name.
	 * @return float|WP_Error Accepted number or refusal.
	 */
	private function number( mixed $value, string $key ): float|WP_Error {
		if ( ! is_int( $value ) && ! is_float( $value ) ) {
			return Failure::make( 'input', 422 );
		}
		$number = (float) $value;
		$bound  = self::NUMBERS[ $key ] ?? null;
		if ( ! is_finite( $number ) || $number <= 0 || ( null !== $bound && $number > $bound[0] ) ) {
			return Failure::make( 'input', 422 );
		}
		return $number;
	}

	/**
	 * The engine requires at least one goal from its own vocabulary.
	 *
	 * @param mixed $value Raw command value.
	 * @return array<int,string>|WP_Error Accepted goals or refusal.
	 */
	private function goals( mixed $value ): array|WP_Error {
		if ( ! is_array( $value ) || ! $value ) {
			return Failure::make( 'input', 422 );
		}
		$goals = array();
		foreach ( $value as $goal ) {
			if ( ! is_string( $goal ) || ! in_array( $goal, self::GOALS, true ) ) {
				return Failure::make( 'input', 422 );
			}
			if ( ! in_array( $goal, $goals, true ) ) {
				$goals[] = $goal;
			}
		}
		return $goals;
	}

	/**
	 * The engine's own machine code for a refused profile, if it sent one.
	 *
	 * @param string $body Raw engine reply.
	 */
	private function detail_code( string $body ): ?string {
		$value = json_decode( $body, true, 16 );
		$code  = is_array( $value ) && is_array( $value['detail'] ?? null ) ? ( $value['detail']['error'] ?? null ) : null;
		return is_string( $code ) ? $code : null;
	}

	/**
	 * The engine's bounded profile diagnosis, used only to pick a stable code.
	 *
	 * @param string $body Raw engine reply.
	 */
	private function detail_message( string $body ): ?string {
		$value   = json_decode( $body, true, 16 );
		$message = is_array( $value ) && is_array( $value['detail'] ?? null ) ? ( $value['detail']['message'] ?? null ) : null;
		return is_string( $message ) ? $message : null;
	}

	/**
	 * Name the two diagnoses the interface explains, as one stable vocabulary.
	 *
	 * @param string $message Engine's own English diagnosis.
	 */
	private function profile_code( string $message ): string {
		if ( str_contains( $message, 'at least one week' ) ) {
			return 'profile_too_short';
		}
		if ( str_contains( $message, 'negative' ) ) {
			return 'profile_negative';
		}
		return 'profile_invalid';
	}

	/**
	 * Map an engine status class onto this gateway's stable codes.
	 *
	 * @param int $status HTTP status from the engine.
	 */
	private static function refusal_code( int $status ): string {
		return match ( $status ) {
			409     => 'publication_changed',
			422     => 'input',
			429     => 'limited',
			503     => 'unavailable',
			default => 'upstream',
		};
	}
}
