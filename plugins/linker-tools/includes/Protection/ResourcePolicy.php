<?php
/**
 * Server-selected public resource dimensions (#508 decision 6324114050).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;

/** Resource writes never spend the separate direct-inquiry business allowance. */
final class ResourcePolicy {
	/**
	 * Map only actual mutating resource routes. Reads consume no turn allowance.
	 *
	 * @param string $route Native route.
	 * @param string $method Native method.
	 * @param bool   $select Existing conversation selection.
	 */
	public static function action( string $route, string $method, bool $select = false ): string {
		if ( ! in_array( $method, array( 'POST', 'DELETE' ), true ) ) {
			return '';
		}
		// WP_REST_Server matches registered paths with the i modifier.
		$route = strtolower( $route );
		return match ( true ) {
			'/linker-ai/v1/genie/turn' === $route => 'genie',
			'/linker-ai/v1/genie/solution' === $route => 'solution_save',
			'/linker-ai/v1/genie/conversations' === $route => $select ? '' : 'conversation_create',
			default => '',
		};
	}

	/**
	 * Atomic dimensions and account carry, using the browser identity across login.
	 *
	 * @param string   $action Server action.
	 * @param Identity $identity Current private identity.
	 * @param int      $files Files in this turn, checked before decode.
	 * @return array{limits:Allowance[],carry:list<array{source:Allowance,target:Allowance}>}
	 */
	public static function plan( string $action, Identity $identity, int $files = 0 ): array {
		$limits  = array();
		$carry   = array();
		$account = '' !== $identity->account;
		$add     = static function ( string $name, int $anonymous, int $signed, int $window, int $units = 1 ) use ( $identity, $account, &$limits, &$carry ): void {
			$capacity = $account ? $signed : $anonymous;
			$limits[] = new Allowance( $name, $identity->browser, $capacity, $window, $units );
			if ( $account ) {
				$target   = new Allowance( $name, $identity->account, $signed, $window, $units );
				$limits[] = $target;
				if ( $window > 0 ) {
					$carry[] = array(
						'source' => new Allowance( $name, $identity->browser, $anonymous, $window ),
						'target' => $target,
					);
				}
			}
		};
		if ( 'genie' === $action ) {
			$add( 'genie_day', 30, 120, DAY_IN_SECONDS );
			$add( 'genie_burst', 10, 30, 10 * MINUTE_IN_SECONDS );
			$add( 'genie_busy', 1, 1, 0 );
			$limits[] = new Allowance( 'genie_site_busy', 'site', 2, 0 );
			if ( $files > 0 ) {
				$add( 'genie_files_day', 10, 40, DAY_IN_SECONDS, $files );
			}
		} elseif ( in_array( $action, array( 'design', 'roof' ), true ) ) {
			// Roof and sizing share this allowance: changing the entrance is
			// not a new budget. #508 approved 30/120 recomputations per hour.
			$add( 'design_hour', 30, 120, HOUR_IN_SECONDS );
			$add( 'design_busy', 1, 1, 0 );
			$limits[] = new Allowance( 'design_site_busy', 'site', 4, 0 );
		} elseif ( 'report_pdf' === $action ) {
			$add( 'report_day', 10, 10, DAY_IN_SECONDS );
			$add( 'design_busy', 1, 1, 0 );
			$limits[] = new Allowance( 'report_site_day', 'site', 100, DAY_IN_SECONDS );
			$limits[] = new Allowance( 'design_site_busy', 'site', 4, 0 );
		} else {
			// Recommended storage-only ceiling, #521: 4 mutations per maximum
			// signed-in turn (120/day), rounded to 500. No model work or mail.
			$add( 'tool_write_day', 500, 500, DAY_IN_SECONDS );
			$limits[] = new Allowance( 'tool_write_site_day', 'site', 2000, DAY_IN_SECONDS );
		}
		return array(
			'limits' => $limits,
			'carry'  => $carry,
		);
	}
}
