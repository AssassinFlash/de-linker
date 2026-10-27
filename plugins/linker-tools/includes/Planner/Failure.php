<?php
/**
 * Stable gateway error codes with already reviewed recovery copy.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/** The UI maps codes to specific fields; raw upstream diagnostics stay private. */
final class Failure {

	/**
	 * Build a private recoverable gateway error.
	 *
	 * @param string $code Stable machine code.
	 * @param int    $status HTTP status.
	 */
	public static function make( string $code, int $status ): WP_Error {
		return new WP_Error(
			'linker_planner_' . $code,
			__( 'Your request could not be completed. Your input is still here. Please try again.', 'linker-tools' ),
			array( 'status' => $status )
		);
	}
}
