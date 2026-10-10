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
	 * Model the #10 bake-off adopted.
	 */
	public const MODEL = 'gemini-embedding-2';

	/**
	 * Encodes `$query` as a JSON array of floats, or null when this host has no key.
	 *
	 * @param string $query Search text.
	 * @return list<float>|null
	 */
	public function vector( string $query ): ?array {
		$key  = $this->api_key();
		$base = $this->base_url();
		if ( '' === $key || '' === $base ) {
			return null;
		}
		$body = wp_json_encode(
			array(
				'model' => self::MODEL,
				'input' => array( 'task: question answering | query: ' . $query ),
			)
		);
		if ( ! is_string( $body ) ) {
			return null;
		}
		$response = wp_remote_post(
			rtrim( $base, '/' ) . '/v1/embeddings',
			array(
				'headers' => array(
					'Authorization' => 'Bearer ' . $key,
					'Content-Type'  => 'application/json',
				),
				'body'    => $body,
				'timeout' => 15,
			)
		);
		if ( is_wp_error( $response ) ) {
			return null;
		}
		$decoded = json_decode( (string) wp_remote_retrieve_body( $response ), true );
		$row     = $decoded['data'][0]['embedding'] ?? null;
		if ( ! is_array( $row ) ) {
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
	 * AIHUBMIX_API_KEY from the environment, loading the config file once if needed.
	 */
	private function api_key(): string {
		return $this->credential( 'AIHUBMIX_API_KEY' );
	}

	/**
	 * AIHUBMIX_BASE_URL from the environment.
	 */
	private function base_url(): string {
		return $this->credential( 'AIHUBMIX_BASE_URL' );
	}

	/**
	 * One credential: process env first, then the aihubmix env file.
	 *
	 * @param 'AIHUBMIX_API_KEY'|'AIHUBMIX_BASE_URL' $name Variable.
	 */
	private function credential( string $name ): string {
		$from_env = getenv( $name );
		if ( is_string( $from_env ) && '' !== $from_env ) {
			return $from_env;
		}
		$from_file = $this->env_value( $name );
		if ( '' !== $from_file ) {
			return $from_file;
		}
		$this->load_env_file();
		return $this->env_value( $name );
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
	 * Reads ~/.config/terravolt-builder/aihubmix.env into $_ENV when the
	 * variables are not already set. The file is never opened from the repo.
	 */
	private function load_env_file(): void {
		static $loaded = false;
		if ( $loaded ) {
			return;
		}
		$loaded = true;
		$home   = getenv( 'HOME' );
		if ( ! is_string( $home ) || '' === $home ) {
			return;
		}
		$path = $home . '/.config/terravolt-builder/aihubmix.env';
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
			if ( ( 'AIHUBMIX_API_KEY' === $name || 'AIHUBMIX_BASE_URL' === $name ) && ! isset( $_ENV[ $name ] ) ) {
				$_ENV[ $name ] = $value;
			}
		}
	}
}
