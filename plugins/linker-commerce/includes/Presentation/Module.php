<?php
/**
 * Hooks of the presentation module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * Shortcodes, the empty Proforma-request gate, the comparison page, the
 * document library page and WindPress.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param Shortcodes  $shortcodes B2B shortcodes.
	 * @param LoginGate   $gate       Empty Proforma-request page.
	 * @param WindPress   $windpress  Compile provider.
	 * @param ComparePage $compare    The comparison page and its chip (#66).
	 * @param LibraryPage $library    The document library page (#66).
	 */
	public function __construct(
		private readonly Shortcodes $shortcodes,
		private readonly LoginGate $gate,
		private readonly WindPress $windpress,
		private readonly ComparePage $compare = new ComparePage(),
		private readonly LibraryPage $library = new LibraryPage()
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		$this->shortcodes->register();
		$this->gate->register();
		$this->windpress->register();
		$this->compare->register();
		$this->library->register();
	}
}
