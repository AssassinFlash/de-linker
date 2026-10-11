<?php
/**
 * Query vector for the document index (gemini-embedding-2 via AIHubMix).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

/**
 * Encodes a search query the same way the #10 index was built: gemini-embedding-2
 * through AIHubMix's OpenAI-compatible `/v1/embeddings`, query format
 * `task: question answering | query: {text}` (docs/research/2026-10-09/embedding-bakeoff.md).
 * The key is read from the process environment (or the aihubmix env file under
 * the user's config directory). Nothing here writes a secret.
 */
final class QueryEmbedding {

	/**
	 * Model the #10 bake-off adopted; the index fingerprint compares this name.
	 */
	public const MODEL = 'gemini-embedding-2';

	/**
	 * The same model as OpenRouter names it.
	 */
	private const OPENROUTER_MODEL = 'google/gemini-embedding-2';

	/**
	 * Credential file per provider.
	 */
	private const ENV_FILES = array(
		'openrouter' => 'openrouter.env',
		'aihubmix'   => 'aihubmix.env',
	);

	/**
	 * Encodes `$query` as a JSON array of floats, or null when this host has no key.
	 *
	 * @param string $query Search text.
	 * @return list<float>|null
	 */
	public function vector( string $query ): ?array {
		$provider = $this->provider();
		$key      = $this->credential( strtoupper( $provider ) . '_API_KEY' );
		$default  = 'openrouter' === $provider ? 'https://openrouter.ai/api/v1' : '';
		$base     = $this->credential( strtoupper( $provider ) . '_BASE_URL', $default );
		if ( '' === $key || '' === $base ) {
			return null;
		}
		$model = 'openrouter' === $provider ? self::OPENROUTER_MODEL : self::MODEL;
		$body  = wp_json_encode(
			array(
				'model' => $model,
				'input' => array( 'task: question answering | query: ' . $query ),
			)
		);
		if ( ! is_string( $body ) ) {
			return null;
		}
		// Bases may carry their own /v1 (OpenRouter does); keep exactly one.
		$base    = rtrim( (string) preg_replace( '~/v1$~', '', rtrim( $base, '/' ) ), '/' );
		$url     = $base . '/v1/embeddings';
		$headers = array(
			'Authorization' => 'Bearer ' . $key,
			'Content-Type'  => 'application/json',
		);
		$decoded = null;
		for ( $attempt = 1; $attempt <= 3; $attempt++ ) {
			$response = wp_remote_post(
				$url,
				array(
					'headers' => $headers,
					'body'    => $body,
					'timeout' => 15,
				)
			);
			$code     = is_wp_error( $response ) ? 0 : (int) wp_remote_retrieve_response_code( $response );
			if ( $code >= 200 && $code < 500 ) {
				$decoded = json_decode( (string) wp_remote_retrieve_body( $response ), true );
				break;
			}
			// 5xx and transport errors retry; 4xx answers are final.
			if ( $attempt < 3 ) {
				usleep( 500000 * ( 2 ** ( $attempt - 1 ) ) );
			}
		}
		if ( null === $decoded ) {
			error_log( // phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_error_log -- the routing law demands loud failure
				'[linker-embedding] query encoding failed on ' . $provider . ' after retries'
			);
			return null;
		}
		$row = $decoded['data'][0]['embedding'] ?? null;
		if ( ! is_array( $row ) ) {
			error_log( // phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_error_log -- the routing law demands loud failure
				'[linker-embedding] unexpected response shape from ' . $provider
			);
			return null;
		}
		$vector = array();
		foreach ( $row as $value ) {
			if ( ! is_numeric( $value ) ) {
				return null;
			}
			$vector[] = (float) $value;
		}

		return $vector;
	}

	/**
	 * The provider law: OpenRouter by default; AIHubMix only by explicit switch.
	 */
	private function provider(): string {
		$switch = getenv( 'LINKER_EMBEDDING_PROVIDER' );
		return ( is_string( $switch ) && 'aihubmix' === $switch ) ? 'aihubmix' : 'openrouter';
	}

	/**
	 * One credential: process env first, then the provider's env file.
	 *
	 * @param string $name Variable.
	 * @param string $fallback Value when unset everywhere.
	 */
	private function credential( string $name, string $fallback = '' ): string {
		$from_env = getenv( $name );
		if ( is_string( $from_env ) && '' !== $from_env ) {
			return $from_env;
		}
		$from_file = $this->env_value( $name );
		if ( '' !== $from_file ) {
			return $from_file;
		}
		$this->load_env_file();
		$value = $this->env_value( $name );
		return '' !== $value ? $value : $fallback;
	}

	/**
	 * A string already present in $_ENV, or empty. These are process credentials,
	 * not request input.
	 *
	 * @param string $name Variable.
	 */
	private function env_value( string $name ): string {
		$value = $_ENV[ $name ] ?? ''; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- process credentials, not request input.
		return is_string( $value ) ? $value : '';
	}

	/**
	 * Reads the active provider's env file into $_ENV when the variables are
	 * not already set. The file is never opened from the repo.
	 */
	private function load_env_file(): void {
		static $loaded = false;
		if ( $loaded ) {
			return;
		}
		$loaded  = true;
		$home    = getenv( 'HOME' );
		$allowed = array();
		foreach ( array( 'OPENROUTER_API_KEY', 'OPENROUTER_BASE_URL', 'AIHUBMIX_API_KEY', 'AIHUBMIX_BASE_URL' ) as $variable ) {
			$allowed[ $variable ] = true;
		}
		if ( ! is_string( $home ) || '' === $home ) {
			return;
		}
		$path = $home . '/.config/terravolt-builder/' . self::ENV_FILES[ $this->provider() ];
		if ( ! is_readable( $path ) ) {
			return;
		}
		$bytes = file_get_contents( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a user config file outside the repository.
		if ( false === $bytes ) {
			return;
		}
		foreach ( explode( "\n", $bytes ) as $line ) {
			$line = trim( $line );
			if ( '' === $line || str_starts_with( $line, '#' ) || ! str_contains( $line, '=' ) ) {
				continue;
			}
			list( $name, $value ) = explode( '=', $line, 2 );
			$name                 = trim( $name );
			$value                = trim( $value, " \t\"'" );
			if ( isset( $allowed[ $name ] ) && ! isset( $_ENV[ $name ] ) ) {
				$_ENV[ $name ] = $value;
			}
		}
	}
}
