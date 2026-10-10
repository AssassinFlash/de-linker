<?php
/**
 * Applying the site's words.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Vocabulary;

/**
 * Replaces WooCommerce's strings through gettext (docs/specs/11-commerce.md,
 * Vocabulary), so the replacement holds in every template and notice, in both
 * languages, without copying templates. The replacements are built once per
 * language and request.
 */
final class Overrides {

	/**
	 * Replacements of the current language, built on first use.
	 *
	 * @var array{singular: array<string, string>, context: array<string, string>, plural: array<string, array<int|string, mixed>>}|null
	 */
	private ?array $current = null;

	/**
	 * Sets up the overrides.
	 *
	 * @param Terms $terms The replacements.
	 */
	public function __construct( private readonly Terms $terms ) {}

	/**
	 * Forgets the replacements when the language changes; runs on change_locale.
	 */
	public function reset(): void {
		$this->current = null;
	}

	/**
	 * Runs on gettext_woocommerce.
	 *
	 * @param string $translation WooCommerce's translation.
	 * @param string $text        Source string.
	 */
	public function gettext( string $translation, string $text ): string {
		if ( ! did_action( 'init' ) ) {
			return $translation;
		}
		return $this->replacements()['singular'][ $text ] ?? $translation;
	}

	/**
	 * Runs on gettext_with_context_woocommerce.
	 *
	 * @param string $translation WooCommerce's translation.
	 * @param string $text        Source string.
	 * @param string $context     Context.
	 */
	public function gettext_with_context( string $translation, string $text, string $context ): string {
		if ( ! did_action( 'init' ) ) {
			return $translation;
		}
		return $this->replacements()['context'][ $context . "\004" . $text ] ?? $translation;
	}

	/**
	 * Runs on ngettext_woocommerce.
	 *
	 * @param string $translation WooCommerce's translation.
	 * @param string $single      Singular source string.
	 * @param string $plural      Plural source string.
	 * @param int    $number      Number deciding the form.
	 */
	public function ngettext( string $translation, string $single, string $plural, $number ): string {
		if ( ! did_action( 'init' ) ) {
			return $translation;
		}
		$nooped = $this->replacements()['plural'][ $single ] ?? null;
		return null === $nooped ? $translation : translate_nooped_plural( $nooped, (int) $number, 'linker-commerce' );
	}

	/**
	 * The replacements of the current language.
	 *
	 * @return array{singular: array<string, string>, context: array<string, string>, plural: array<string, array<int|string, mixed>>}
	 */
	private function replacements(): array {
		$this->current ??= array(
			'singular' => $this->terms->singular(),
			'context'  => $this->terms->with_context(),
			'plural'   => $this->terms->plural(),
		);
		return $this->current;
	}
}
