<?php
/**
 * Retired design writes point to the unified project workflow.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use Linker\Commerce\Presentation\PageUrls;
use WP_Error;

/** Historical records and downloads stay with their existing read handlers. */
final class LegacyRoutes {

	/** Register cheap retirement replies without a parallel save/draft mechanism. */
	public function register(): void {
		foreach ( array( '/solutions', '/solutions/draft' ) as $path ) {
			register_rest_route(
				'linker/v1',
				$path,
				array(
					'methods'             => 'POST',
					'callback'            => array( self::class, 'required' ),
					'permission_callback' => '__return_true',
				)
			);
		}
	}

	/**
	 * Use the native translated page, optionally restoring an owned source.
	 *
	 * @param int $solution_id Already-authorised historical source, or no source.
	 */
	public static function url( int $solution_id = 0 ): string {
		$url = PageUrls::page( 'solution-configurator' );
		return '' !== $url && $solution_id > 0 ? add_query_arg( array( 'saved_solution' => $solution_id ), $url ) : $url;
	}

	/** A stale client receives a next step without calculating or writing data. */
	public static function required(): WP_Error {
		return new WP_Error(
			'linker_planner_required',
			__( 'Open the Solution Configurator', 'linker-commerce' ),
			array(
				'status'           => 410,
				'configurator_url' => self::url(),
			)
		);
	}
}
