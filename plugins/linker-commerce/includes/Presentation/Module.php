<?php
/**
 * Hooks of the presentation module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * Shortcodes, the empty Proforma-request gate and WindPress.
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
	}
}
