<?php
/**
 * Recording stand-ins for Plugin's collaborators.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Entries;
use Linker\Tools\Genie\Proxy;

/**
 * An Entries whose register() does not touch WordPress.
 */
final class RecordingEntries extends Entries {

	/**
	 * The calls.
	 *
	 * @var list<string>
	 */
	public array $calls = array();

	/**
	 * Records instead of registering.
	 */
	public function register(): void {
		$this->calls[] = 'registered';
	}
}
