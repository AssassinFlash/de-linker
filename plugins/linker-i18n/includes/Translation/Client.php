<?php
/**
 * A machine translator.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Translates segments from English to German.
 */
interface Client {

	/**
	 * Whether the translator can be called at all (it has its key).
	 */
	public function available(): bool;

	/**
	 * Translates texts, keeping their order and their placeholders.
	 *
	 * @param array<int, string> $texts    English texts with placeholders.
	 * @param string             $feedback What was wrong with an earlier answer, for a second try.
	 * @return list<string> German texts, one per English text.
	 * @throws TranslationFailed When no usable answer came back.
	 */
	public function translate( array $texts, string $feedback = '' ): array;
}
