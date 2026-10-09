<?php
/**
 * A stand-in for DeepSeek's chat completions endpoint, for the integration
 * tests: `php -S 127.0.0.1:8119 tests/php/Integration/stub/deepseek.php`.
 *
 * It answers in DeepSeek's format with a "translation" that keeps every
 * placeholder and figure, puts the glossary's German terms in place and marks
 * the text with "[de]", so a test can tell machine German from the German it
 * already had. A segment containing "BREAK-PLACEHOLDERS" comes back without
 * its placeholders, to make the validator reject it.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.Security, WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions, WordPress.NamingConventions.PrefixAllGlobals -- a stand-alone test server, no WordPress.

$request  = json_decode( (string) file_get_contents( 'php://input' ), true );
$messages = is_array( $request ) && is_array( $request['messages'] ?? null ) ? $request['messages'] : array();
$user     = (string) ( end( $messages )['content'] ?? '' );
$first    = strstr( $user, "\n\n", true ); // A retry appends the reasons after a blank line.
$payload  = json_decode( false === $first ? $user : $first, true );
$segments = is_array( $payload ) && is_array( $payload['segments'] ?? null ) ? $payload['segments'] : array();

$glossary = json_decode( (string) file_get_contents( dirname( __DIR__, 4 ) . '/data/glossary-de.json' ), true );
$terms    = is_array( $glossary['terms'] ?? null ) ? $glossary['terms'] : array();
usort( $terms, static fn( array $a, array $b ): int => strlen( $b['en'] ) <=> strlen( $a['en'] ) );

$translations = array();
foreach ( $segments as $segment ) {
	$text = (string) $segment;
	foreach ( $terms as $entry ) {
		$text = (string) preg_replace( '/(?<![\p{L}\p{N}])' . preg_quote( $entry['en'], '/' ) . 's?(?![\p{L}\p{N}])/iu', $entry['de'], $text );
	}
	if ( str_contains( $text, 'BREAK-PLACEHOLDERS' ) ) {
		$text = (string) preg_replace( '/<\/?[tk]\d+\/?>/', '', $text );
	}
	$translations[] = '[de] ' . $text;
}

header( 'Content-Type: application/json' );
echo json_encode(
	array(
		'id'      => 'stub',
		'object'  => 'chat.completion',
		'model'   => (string) ( $request['model'] ?? '' ),
		'choices' => array(
			array(
				'index'         => 0,
				'finish_reason' => 'stop',
				'message'       => array(
					'role'    => 'assistant',
					'content' => json_encode( array( 'translations' => $translations ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ),
				),
			),
		),
	),
	JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
);
