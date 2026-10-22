<?php
/**
 * Stop a native first save with its translated, explicitly unsaved result.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** Woo's create_order translates an exception into its ordinary form error. */
final class CapacityFull extends \RuntimeException {
	/**
	 * Preserve the actual admission error for non-checkout native callers.
	 *
	 * @param WP_Error $problem Explicit unsaved result.
	 */
	public function __construct( public readonly WP_Error $problem ) {
		parent::__construct( $problem->get_error_message() );
	}
}
