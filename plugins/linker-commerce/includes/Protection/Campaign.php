<?php
/**
 * Human-confirmed, narrowly scoped incident rule; no model classification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Whole-field incident matches never generalize language, email or shared hosting. */
final class Campaign {

	public const VERSION  = 'confirmed-content-20261023-v3';
	public const DISABLED = 'linker_confirmed_campaign_disabled';

	/**
	 * Match editable recovery content using the native submission's normalization.
	 *
	 * @param array<string,mixed> $post Unslashed form values; credentials are excluded.
	 * @param bool                $selection Contact's optional normalized selection.
	 */
	public static function recovery_matches( array $post, bool $selection = true ): bool {
		$fields = array();
		foreach ( array( 'name', 'email', 'company' ) as $key ) {
			$value          = $post[ $key ] ?? '';
			$fields[ $key ] = mb_substr( trim( sanitize_text_field( is_scalar( $value ) ? (string) $value : '' ) ), 0, \Linker\Commerce\Contact\Submission::MAX_TEXT );
		}
		$message           = $post['message'] ?? '';
		$fields['message'] = mb_substr( trim( sanitize_textarea_field( is_scalar( $message ) ? (string) $message : '' ) ), 0, \Linker\Commerce\Contact\Submission::MAX_MESSAGE );
		if ( $selection ) {
			$raw                 = $post[ \Linker\Commerce\Contact\SelectionContext::FIELD ] ?? '';
			$fields['selection'] = \Linker\Commerce\Contact\SelectionContext::normalize( is_string( $raw ) ? json_decode( $raw, true ) : null );
		}
		return self::submitted( $fields );
	}

	/**
	 * Inspect the validated semantic fields, never transport credentials or joined text.
	 *
	 * @param array<string,mixed> $payload Native contact/inquiry semantic input.
	 */
	public static function submitted( array $payload ): bool {
		$matched = false;
		array_walk_recursive(
			$payload,
			static function ( mixed $value ) use ( &$matched ): void {
				$matched = $matched || ( is_string( $value ) && self::matches( $value ) );
			}
		);
		return $matched;
	}

	/**
	 * Only the exact activity independently confirmed in the incident evidence.
	 *
	 * @param string $message Validated, sanitized message.
	 */
	public static function matches( string $message ): bool {
		if ( 'yes' === get_option( self::DISABLED, 'no' ) ) {
			return false;
		}
		if ( 1 === preg_match( '~\AВам перевод\s+[0-9]+\s+руб\.\s+(?:получить|забрать)\s+тут\s+(https?://\S+)\s*\z~u', $message, $match ) ) {
			$host = wp_parse_url( $match[1], PHP_URL_HOST );
			// Exact hosts independently confirmed from the saved incident messages; see docs/acceptance/2026-10-22/542-campaign-extension/README.md.
			return is_string( $host ) && in_array( strtolower( $host ), array( 'fredmer.buzz', 'xtimex.buzz' ), true );
		}
		// The six saved activity variants carry this complete invitation + weekly
		// return + deposit combination. Native name truncation removes most URLs.
		// These literal amounts identify that activity, not general finance limits.
		$patterns = array(
			'~\A(?:(?:Добрый день[!.]|Здравствуйте\.)\s+)?(?:Для вас открыт к платформе с доходностью|Вам доступен к системе с доходом)\s+от 12% в неделю\.\s+(?:Мин\. сумма|Вход)\s+100 долларов\b[\s\S]*\z~u',
			'~\AДля вас открыт закрытому фонду #[0-9]+\. Система автоматически генерирует доход от 12% еженедельно от вложенной суммы\. Вход 100 долларов\b[\s\S]*\z~u',
			'~\A(?:Здравствуйте\.|Добрый день\.) Вы получили это письмо по своей подписке, и для новых участников открыт доступ к закрытому фонду\. Доходность от 12% в неделю при (?:минимальном вложении|депозите от) 100\$[.\s][\s\S]*\z~u',
		);
		foreach ( $patterns as $pattern ) {
			if ( 1 === preg_match( $pattern, $message ) ) {
				return true;
			}
		}
		return false;
	}
}
