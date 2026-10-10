<?php
/**
 * What WC() returns in a test.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

use WC_Countries;

/**
 * The members of WooCommerce's main object that this plugin uses for a
 * language switch: the country list and the text domain loader, which counts
 * its calls.
 */
final class WooCommerce {

	/**
	 * The country list.
	 *
	 * @var WC_Countries
	 */
	public $countries;

	/**
	 * How often the text domain was loaded.
	 *
	 * @var int
	 */
	public int $textdomain_loads = 0;

	/**
	 * A country list of its own.
	 */
	public function __construct() {
		$this->countries = new WC_Countries();
	}

	/**
	 * Loads WooCommerce's translations.
	 */
	public function load_plugin_textdomain(): void {
		++$this->textdomain_loads;
	}
}
