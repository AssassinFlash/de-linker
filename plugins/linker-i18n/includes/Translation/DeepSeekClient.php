<?php
/**
 * DeepSeek as the machine translator.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Calls DeepSeek's chat completions API (OpenAI format) with JSON output.
 *
 * Facts from DeepSeek's documentation, read through Apify on 2026-10-09:
 * the endpoint https://api.deepseek.com/chat/completions and the model name
 * deepseek-flash (api-docs.deepseek.com/quick_start/pricing); JSON output
 * needs response_format json_object, the word "json" and an example in the
 * prompt, a max_tokens large enough, and "may occasionally return empty
 * content" (guides/json_mode); thinking is on by default and
 * {"thinking": {"type": "disabled"}} turns it off, and temperature only
 * acts without it (guides/thinking_mode); lower temperatures such as 0.2
 * are "more focused and deterministic" (api/create-chat-completion).
 *
 * The key comes from the process environment or the private deepseek.env
 * outside the website ({@see Credentials::deepseek_key()}).
 * LINKER_I18N_DEEPSEEK_ENDPOINT accepts a loopback stand-in only in local
 * or development environments; production always uses the official endpoint.
 */
final class DeepSeekClient implements Client {

	public const ENDPOINT = 'https://api.deepseek.com/chat/completions';

	public const MODEL = 'deepseek-flash';

	/**
	 * Sampling temperature: placeholders and figures must survive, so the
	 * deterministic end of the range.
	 */
	private const TEMPERATURE = 0.2;

	/**
	 * Output budget per call. A batch holds at most Translator::BATCH_CHARACTERS
	 * (6,000) characters of English; German runs longer and the JSON adds
	 * quotes and escapes, which this leaves several times the room for.
	 */
	private const MAX_TOKENS = 8192;

	/**
	 * Seconds to wait for an answer.
	 */
	private const TIMEOUT = 90;

	/**
	 * Sets up the client.
	 *
	 * @param Rules  $rules Glossary and banned words, for the prompt.
	 * @param string $key   API key; empty when there is none.
	 */
	public function __construct( private readonly Rules $rules, private readonly string $key ) {}

	/**
	 * A client with the key of the environment variable DEEPSEEK_API_KEY.
	 *
	 * @param Rules $rules Glossary and banned words, for the prompt.
	 */
	public static function from_environment( Rules $rules ): self {
		return new self( $rules, Credentials::deepseek_key() );
	}

	/**
	 * Whether there is a key.
	 */
	public function available(): bool {
		return '' !== $this->key;
	}

	/**
	 * Translates texts in one request.
	 *
	 * @param array<int, string> $texts    English texts with placeholders.
	 * @param string             $feedback What was wrong with an earlier answer.
	 * @return list<string>
	 * @throws TranslationFailed When no usable answer came back.
	 */
	public function translate( array $texts, string $feedback = '' ): array {
		if ( ! $this->available() ) {
			throw new TranslationFailed( 'DEEPSEEK_API_KEY is not set', false );
		}
		$user = (string) wp_json_encode( array( 'segments' => $texts ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
		if ( '' !== $feedback ) {
			$user .= "\n\nYour previous answer was rejected: " . $feedback . '. Translate again and fix this.';
		}
		$endpoint = self::ENDPOINT;
		if ( defined( 'LINKER_I18N_DEEPSEEK_ENDPOINT' ) && in_array( wp_get_environment_type(), array( 'local', 'development' ), true ) ) {
			$stub = (string) constant( 'LINKER_I18N_DEEPSEEK_ENDPOINT' );
			if ( in_array( wp_parse_url( $stub, PHP_URL_HOST ), array( '127.0.0.1', 'localhost', '::1' ), true ) ) {
				$endpoint = $stub;
			}
		}
		// #508/#521: this is one actual paid request, independent of public
		// observe mode. Missing Tools/service guard must never grant a permit.
		$mode_environment = getenv( 'LINKER_PROVIDER_BUDGET_MODE' );
		$budget_mode      = defined( 'LINKER_PROVIDER_BUDGET_MODE' ) ? constant( 'LINKER_PROVIDER_BUDGET_MODE' ) : ( is_string( $mode_environment ) ? $mode_environment : 'off' );
		if ( 'off' !== $budget_mode ) {
			/**
			 * Private Tools dispatch budget.
			 *
			 * @since 0.1.0
			 */
			$permit = 'enforce' === $budget_mode ? apply_filters( 'linker_tools_provider_debit', false, 'deepseek' ) : false; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Tools owns the trusted provider budget.
			if ( true !== $permit ) {
				throw new TranslationFailed( 'Provider budget unavailable or exhausted.', true );
			}
		}
		$response = wp_remote_post(
			$endpoint,
			array(
				'timeout' => self::TIMEOUT,
				'headers' => array(
					'Authorization' => 'Bearer ' . $this->key,
					'Content-Type'  => 'application/json',
				),
				'body'    => (string) wp_json_encode(
					array(
						'model'           => self::MODEL,
						'thinking'        => array( 'type' => 'disabled' ),
						'temperature'     => self::TEMPERATURE,
						'max_tokens'      => self::MAX_TOKENS,
						'response_format' => array( 'type' => 'json_object' ),
						'messages'        => array(
							array(
								'role'    => 'system',
								'content' => $this->prompt(),
							),
							array(
								'role'    => 'user',
								'content' => $user,
							),
						),
					)
				),
			)
		);
		if ( is_wp_error( $response ) ) {
			throw new TranslationFailed( 'DeepSeek unreachable', true );
		}
		$status = (int) wp_remote_retrieve_response_code( $response );
		if ( 200 !== $status ) {
			// 429 and 5xx pass; 400, 401, 402 (no balance) and 422 need someone to act.
			$passing = 429 === $status || $status >= 500;
			throw new TranslationFailed( esc_html( sprintf( 'DeepSeek answered HTTP %d', $status ) ), $passing ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- $passing is a boolean flag, not part of the message.
		}
		$body    = json_decode( (string) wp_remote_retrieve_body( $response ), true );
		$content = is_array( $body ) ? ( $body['choices'][0]['message']['content'] ?? '' ) : '';
		$answer  = is_string( $content ) ? json_decode( $content, true ) : null;
		$out     = is_array( $answer ) ? ( $answer['translations'] ?? null ) : null;
		if ( ! is_array( $out ) || count( $out ) !== count( $texts ) || array() !== array_filter( $out, static fn( $text ): bool => ! is_string( $text ) ) ) {
			throw new TranslationFailed( 'DeepSeek answered without the expected JSON', true );
		}
		return array_values( $out );
	}

	/**
	 * The system prompt: the task, the placeholder contract, the language
	 * rules of the site and the JSON shape.
	 */
	private function prompt(): string {
		$glossary = array();
		foreach ( $this->rules->terms as $term ) {
			$glossary[] = sprintf( '- %s → %s', $term['en'], $term['de'] );
		}
		$banned = array_map( static fn( string $word ): string => rtrim( $word, '*' ), $this->rules->banned );
		return implode(
			"\n",
			array(
				'You translate the English texts of a German B2B shop for solar inverters, batteries and energy storage into German, for installers, EPCs and distributors.',
				'Address the reader formally with "Sie". Write the German a professional in the trade writes; keep the meaning and the facts, add and drop nothing.',
				'Placeholders such as <t1>, </t1>, <t2/> and <k3/> stand for markup and protected names: copy every placeholder exactly once, keep each <tN>…</tN> pair around the words it belongs to, and never translate or change a <kN/>.',
				'Keep every figure as digits with the same value, written the German way (20.0 kW → 20,0 kW; 29,999 W → 29.999 W).',
				'Use these terms:',
				implode( "\n", $glossary ),
				'Keep these names as they are: ' . implode( ', ', $this->rules->keep ) . '.',
				'Never use these words: ' . implode( ', ', $banned ) . '.',
				'Answer in json: {"translations": ["…", "…"]}, one German text per English segment, in the same order.',
				'Example input: {"segments": ["<t1>Rated AC power:</t1> 10.0 kW", "Download the datasheet"]}',
				'Example output: {"translations": ["<t1>AC-Nennleistung:</t1> 10,0 kW", "Laden Sie das Datenblatt herunter"]}',
			)
		);
	}
}
