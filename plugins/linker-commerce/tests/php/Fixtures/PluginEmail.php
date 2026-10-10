<?php
/**
 * An email of this plugin, for tests that tell the plugin's emails from WooCommerce's.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

use WC_Email;

/**
 * An email whose class lives in the plugin's namespace.
 */
final class PluginEmail extends WC_Email {

	/**
	 * Email id.
	 *
	 * @var string
	 */
	public $id = 'linker_fixture';
}
