<?php
/**
 * A translation that could not be made.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

/**
 * Why no translation was stored, and whether trying again later can help.
 */
final class TranslationFailed extends \RuntimeException {

	/**
	 * Sets up the failure.
	 *
	 * @param string $reason    What went wrong, for the admin screens.
	 * @param bool   $transient Whether a later attempt may succeed (network, rate limit, an empty answer).
	 */
	public function __construct( string $reason, public readonly bool $transient ) {
		parent::__construct( $reason );
	}
}
