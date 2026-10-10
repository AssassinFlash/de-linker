<?php
/**
 * Hooks of the presentation module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * Shortcodes, the empty Proforma-request gate, WindPress and the live scope classes.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param Shortcodes $shortcodes B2B shortcodes.
	 * @param LoginGate  $gate       Empty Proforma-request page.
	 * @param WindPress  $windpress  Compile provider.
	 */
	public function __construct(
		private readonly Shortcodes $shortcodes,
		private readonly LoginGate $gate,
		private readonly WindPress $windpress
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		$this->shortcodes->register();
		$this->gate->register();
		$this->windpress->register();
		add_filter( 'body_class', array( $this, 'body_class' ) );
	}

	/**
	 * Live scope classes the rebuilt CSS still keys off.
	 *
	 * @param string[] $classes Body classes.
	 * @return string[]
	 */
	public function body_class( array $classes ): array {
		if ( function_exists( 'is_account_page' ) && is_account_page() ) {
			$classes[] = 'sf-account-page';
		}
		return $classes;
	}
}
