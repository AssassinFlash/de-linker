<?php
/**
 * Retirement response for the former public design-engine proxy.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Configurator;

use Linker\Commerce\Planning\LegacyRoutes;
use WP_Error;

/** Current project commands use Planner\Gateway and its private transport. */
final class EngineProxy {

	public const NAMESPACE = 'linker-ai/v1';
	public const ROUTE     = '/engine';
	public const OPTION    = 'linker_engine_url';

	/** Keep stale GET/POST clients on an explicit retirement response. */
	public function register(): void {
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE . '/(?P<path>.+)',
			array(
				'methods'             => array( 'GET', 'POST' ),
				'callback'            => array( self::class, 'forward' ),
				'permission_callback' => '__return_true',
			)
		);
	}

	/** No former engine path can calculate, pack a roof or generate a report. */
	public static function forward(): WP_Error {
		return class_exists( LegacyRoutes::class ) ? LegacyRoutes::required() : new WP_Error( 'linker_planner_required', __( 'Solution Configurator', 'linker-tools' ), array( 'status' => 410 ) );
	}
}
